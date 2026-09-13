"""
Lógica de negocio de pagos manuales (transferencia/depósito).

Flujo soportado:
  1. El cliente elige "Transferencia bancaria" en el checkout -> se crea una
     Invoice "pending" + Payment manual "pending" SIN activar la suscripción.
  2. El cliente sube un comprobante (PaymentProof) -> resta "pending".
  3. Un administrador A PRUEBA -> Payment "completed", Invoice "paid",
     suscripción activada (apply_paid_access) y email de confirmación.
  4. Un administrador RECHAZA -> PaymentProof "rejected" con motivo, la
     Invoice y el Payment permanecen pendientes para que el cliente pueda
     volver a presentar un comprobante corregido.

Reglas de seguridad:
  - Nunca se confía en tenant_id/amount/user_id que vengan del cliente: la
    Invoice y el Payment son la única autoridad.
  - Desde el upload solo se aceptan facturas del tenant del usuario autenticado.
  - El archivo se valida (tamaño, MIME, extensión, nombre) y se almacena fuera
    de MEDIA_ROOT.
  - La referencia bancaria se normaliza y se deduplica para evitar que el
    mismo folio financie dos pagos activos (heurística anti-fraude; la
    aprobación administrativa sigue siendo la decisión final).
"""
import os
import unicodedata
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.utils import timezone


ALLOWED_PROOF_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_PROOF_CONTENT_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/webp',
}
DANGEROUS_PROOF_EXTENSIONS = {
    '.exe', '.sh', '.bat', '.cmd', '.com', '.msi', '.dll', '.ps1', '.vbs',
    '.js', '.html', '.htm', '.svg', '.php', '.py', '.jar', '.apk', '.phtml',
}


def _max_proof_size_bytes():
    from django.conf import settings
    mb = getattr(settings, 'PAYMENT_PROOF_MAX_SIZE_MB', 5)
    try:
        return int(mb) * 1024 * 1024
    except (TypeError, ValueError):
        return 5 * 1024 * 1024


def normalize_bank_reference(reference):
    """Normaliza una referencia bancaria para deduplicación.

    - Elimina espacios y tabulaciones.
    - Elimina diacríticos.
    - Convierte a mayúsculas.
    - Conserva solo caracteres alfanuméricos y separadores básicos.
    """
    if not reference:
        return ''
    value = str(reference) or ''
    value = unicodedata.normalize('NFKD', value)
    value = value.encode('ascii', 'ignore').decode('ascii')
    value = ' '.join(value.split())
    allowed = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._')
    return ''.join(ch for ch in value.upper() if ch in allowed)


def sanitize_proof_filename(filename):
    """Sanea el nombre de archivo: solo basename, sin rutas ni traversal."""
    if filename is None:
        raise ValidationError('Nombre de archivo inválido.')
    name = str(filename).replace('\\', '/')
    name = os.path.basename(name)
    name = name.replace('\x00', '').strip()
    if not name or name in {'.', '..'} or '..' in name:
        raise ValidationError('Nombre de archivo inválido.')
    return name


def validate_proof_file(uploaded_file):
    """Valida el archivo de comprobante y retorna el nombre saneado."""
    if uploaded_file is None:
        raise ValidationError('Se requiere el archivo del comprobante.')

    if getattr(uploaded_file, 'size', 0) > _max_proof_size_bytes():
        raise ValidationError('El archivo excede el tamaño máximo permitido.')

    content_type = (getattr(uploaded_file, 'content_type', None) or '').lower()
    if content_type and content_type not in ALLOWED_PROOF_CONTENT_TYPES:
        raise ValidationError('El tipo de archivo no está permitido.')

    raw_name = getattr(uploaded_file, 'name', '') or ''
    name = sanitize_proof_filename(raw_name)
    ext = os.path.splitext(name)[1].lower()
    if ext and ext not in ALLOWED_PROOF_EXTENSIONS:
        raise ValidationError('La extensión del archivo no está permitida.')
    if ext in DANGEROUS_PROOF_EXTENSIONS:
        raise ValidationError('La extensión del archivo no está permitida.')

    return name


def get_manual_provider():
    """Devuelve (creando si hace falta) el PaymentProvider 'manual'."""
    from .models import PaymentProvider

    provider, _ = PaymentProvider.objects.get_or_create(
        name='manual',
        defaults={'is_active': True},
    )
    if not provider.is_active:
        provider.is_active = True
        provider.save(update_fields=['is_active'])
    return provider


def create_manual_payment_for_invoice(invoice):
    """Crea y vincula un Payment manual 'pending' para una Invoice pendiente."""
    from .models import Payment

    if invoice.payment:
        return invoice.payment

    payment = Payment.objects.create(
        tenant=invoice.tenant,
        user=invoice.user,
        subscription=invoice.subscription,
        provider=get_manual_provider(),
        amount=invoice.amount,
        currency='USD',
        status='pending',
        metadata={'invoice_id': str(invoice.id)},
    )
    invoice.payment = payment
    invoice.save(update_fields=['payment'])
    return payment


def _error(status_code, error):
    return {'ok': False, 'status': status_code, 'error': error}


def _success(data):
    return {'ok': True, 'status': 200, 'data': data}


def _resolve_plan(payment, invoice):
    """Determina el SubscriptionPlan de la renovación manual."""
    from apps.subscriptions_api.models import SubscriptionPlan

    if invoice.subscription and invoice.subscription.plan:
        return invoice.subscription.plan
    if invoice.tenant and invoice.tenant.subscription_plan:
        return invoice.tenant.subscription_plan

    plan_id = (payment.metadata or {}).get('plan_id')
    if plan_id:
        try:
            return SubscriptionPlan.objects.filter(id=plan_id, is_active=True).first()
        except (ValueError, TypeError):
            return None
    return None


def _months_from_metadata(payment):
    try:
        months = int((payment.metadata or {}).get('months') or 1)
    except (TypeError, ValueError):
        months = 1
    if months < 1 or months > 24:
        months = 1
    return months


def upload_manual_proof(invoice, uploaded_file, bank_reference, amount_provided):
    """Registra un PaymentProof 'pending' para una Invoice pendiente.

    La Invoice ya debe haber sido validada como perteneciente al tenant del
    usuario autenticado ANTES de llamar a esta función.
    """
    from django.conf import settings as django_settings

    from .models import PaymentProof

    if invoice.is_paid or invoice.status == 'paid':
        return _error(400, 'La factura ya está pagada.')

    payment = create_manual_payment_for_invoice(invoice)

    if payment.status == 'completed':
        return _error(400, 'El pago asociado a esta factura ya fue completado.')
    if payment.status not in {'pending', 'processing'}:
        return _error(400, 'El pago asociado a esta factura no está pendiente.')
    if payment.proofs.filter(decision='approved').exists():
        return _error(400, 'Este pago ya fue aprobado.')
    if payment.proofs.filter(decision='pending').exists():
        return _error(400, 'Ya existe un comprobante pendiente de revisión para este pago.')

    try:
        file_name = validate_proof_file(uploaded_file)
    except ValidationError as exc:
        return _error(400, '; '.join(exc.messages))

    reference = normalize_bank_reference(bank_reference)
    if not reference:
        return _error(400, 'La referencia bancaria es obligatoria.')

    try:
        amount = Decimal(str(amount_provided))
    except (InvalidOperation, TypeError, ValueError):
        return _error(400, 'El importe del comprobante es inválido.')
    if amount <= 0:
        return _error(400, 'El importe del comprobante debe ser mayor a cero.')

    # Deduplicación de referencia: el mismo folio no puede financiar dos pagos
    # activos (anti-fraude). Se permite reutilizarla solo SI corresponde al
    # mismo Payment (re-subida tras un rechazo).
    dup = PaymentProof.objects.filter(
        bank_reference=reference,
        payment__status__in=['pending', 'processing', 'completed'],
    ).exclude(payment_id=payment.id).exists()
    if dup:
        return _error(409, 'La referencia bancaria ya fue utilizada para otro pago.')

    proof = PaymentProof.objects.create(
        payment=payment,
        file=uploaded_file,
        file_name=file_name,
        bank_reference=reference,
        amount_provided=amount,
        decision='pending',
    )

    return _success({
        'message': 'Comprobante recibido. Está pendiente de verificación.',
        'invoice_id': str(invoice.id),
        'payment_id': str(payment.id),
        'proof_id': str(proof.id),
        'decision': 'pending',
        'bank_reference': reference,
        'amount_provided': float(amount),
        'proof_max_size_mb': getattr(django_settings, 'PAYMENT_PROOF_MAX_SIZE_MB', 5),
    })


def approve_manual_payment(invoice, reviewer, decision_note=''):
    """Aprueba el comprobante pendiente y activa la suscripción.

    Invocar DENTRO de transaction.atomic con la Invoice bloqueada vía
    select_for_update. Es idempotente por estado: si ya fue aprobada, no
    vuelve a activar ni a enviar email.
    """
    from apps.subscriptions_api.utils import apply_paid_access, log_subscription_event

    payment = invoice.payment
    if not payment:
        return _error(400, 'La factura no tiene un pago vinculado.')
    if getattr(payment.provider, 'name', None) != 'manual':
        return _error(400, 'La factura no corresponde a un pago manual.')

    approved = payment.proofs.filter(decision='approved').first()
    if invoice.is_paid or invoice.status == 'paid':
        return _success({
            'message': 'El pago ya estaba aprobado.',
            'idempotent': True,
            'invoice_id': str(invoice.id),
            'payment_id': str(payment.id),
            'proof_id': str(approved.id) if approved else None,
            'decision': 'approved',
        })

    proof = payment.proofs.filter(
        decision='pending'
    ).select_for_update().order_by('-created_at', '-id').first()
    if not proof:
        return _error(400, 'No hay un comprobante de pago pendiente de revisión.')

    if payment.status == 'completed':
        return _error(400, 'El pago ya fue completado.')

    if proof.amount_provided != payment.amount:
        return _error(
            400,
            f"El importe del comprobante ({proof.amount_provided}) no coincide "
            f"con el importe esperado ({payment.amount}).",
        )

    plan = _resolve_plan(payment, invoice)
    months = _months_from_metadata(payment)
    billing_interval = (payment.metadata or {}).get('billing_interval') or 'month'
    if billing_interval not in {'month', 'year'}:
        billing_interval = 'month'

    access_until = apply_paid_access(
        tenant=invoice.tenant or payment.tenant,
        user=invoice.user,
        plan=plan,
        months=months,
        auto_renew=False,
        billing_interval=billing_interval,
    )

    proof.decision = 'approved'
    proof.reviewed_by = reviewer
    proof.reviewed_at = timezone.now()
    proof.decision_note = (decision_note or '').strip()
    proof.save(update_fields=['decision', 'reviewed_by', 'reviewed_at', 'decision_note'])

    payment.status = 'completed'
    payment.completed_at = timezone.now()
    payment.save(update_fields=['status', 'completed_at'])

    invoice.is_paid = True
    invoice.paid_at = timezone.now()
    invoice.status = 'paid'
    invoice.save(update_fields=['is_paid', 'paid_at', 'status'])

    if invoice.subscription:
        log_subscription_event(
            subscription=invoice.subscription,
            action='payment_successful',
            description=(
                f"Pago manual aprobado para factura #{invoice.id} "
                f"(monto {invoice.amount}, comprobante {proof.id})"
            ),
        )

    return _success({
        'message': 'Pago aprobado y suscripción activada.',
        'idempotent': False,
        'invoice_id': str(invoice.id),
        'payment_id': str(payment.id),
        'proof_id': str(proof.id),
        'decision': 'approved',
        'access_until': access_until.isoformat(),
        'months': months,
        'plan': plan.name if plan else None,
    })


def reject_manual_payment(invoice, reviewer, reason):
    """Rechaza el comprobante pendiente sin activar ni cobrar nada.

    La Invoice y el Payment permanecen pendientes para que el cliente pueda
    volver a presentar un comprobante.
    """
    payment = invoice.payment
    if not payment:
        return _error(400, 'La factura no tiene un pago vinculado.')
    if getattr(payment.provider, 'name', None) != 'manual':
        return _error(400, 'La factura no corresponde a un pago manual.')

    if invoice.is_paid or invoice.status == 'paid':
        return _error(400, 'No se puede rechazar un pago ya aprobado.')

    reason = (reason or '').strip()
    if not reason:
        return _error(400, 'El motivo del rechazo es obligatorio.')

    proof = payment.proofs.filter(decision='pending').select_for_update().first()
    if not proof:
        return _error(400, 'No hay un comprobante de pago pendiente de revisión.')

    proof.decision = 'rejected'
    proof.reviewed_by = reviewer
    proof.reviewed_at = timezone.now()
    proof.decision_note = reason
    proof.save(update_fields=['decision', 'reviewed_by', 'reviewed_at', 'decision_note'])

    return _success({
        'message': 'Comprobante rechazado. El pago queda pendiente para una nueva presentación.',
        'invoice_id': str(invoice.id),
        'payment_id': str(payment.id),
        'proof_id': str(proof.id),
        'decision': 'rejected',
    })