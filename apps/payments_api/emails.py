"""
Correos electrónicos del flujo de pago manual (transferencia/depósito).

Se envían SIEMPRE después de confirmar la transacción de base de datos
(transaction.on_commit) para que un rollback no dispare emisiones fantasma.
"""
import logging

logger = logging.getLogger(__name__)


def _base_context(subject, tenant, user):
    from django.conf import settings

    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:4200').rstrip('/')
    return {
        'business_name': tenant.name if tenant else 'Auron Suite',
        'title': subject,
        'tenant_name': tenant.name if tenant else 'Auron Suite',
        'user_full_name': (user.full_name if user and user.full_name else '') or (user.email if user else 'Cliente'),
        'cta_url': f"{frontend_url}/client/invoices",
    }


def _render(template_name, context):
    from apps.emails.service import EmailRenderer

    try:
        return EmailRenderer.render(template_name, context)
    except Exception as exc:  # noqa: BLE001 - nunca romper el flujo por un email
        logger.warning('EmailRenderer fallo para %s: %s', template_name, exc)
        return ''


def _dispatch(user, subject, text_body, html_body):
    from apps.auth_api.tasks import send_email_async

    if not user or not user.email:
        logger.warning('Email de pago manual omitido: usuario sin email')
        return
    send_email_async.delay(subject, text_body, '', [user.email], html_message=html_body)


def _amount(value):
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return ''


def send_manual_payment_pending_email(user, tenant, invoice, proof):
    """Avisa al cliente que su comprobante fue recibido y está en revisión."""
    subject = "Comprobante recibido - Pago pendiente de verificación"
    context = _base_context(subject, tenant, user)
    context.update({
        'invoice_id': str(invoice.id),
        'plan_amount': _amount(proof.amount_provided),
        'plan_name': invoice.subscription.plan.get_name_display() if invoice.subscription and invoice.subscription.plan else 'Suscripción',
        'payment_method': 'Transferencia bancaria',
        'bank_reference': proof.bank_reference,
        'cta_label': 'Ver estado del pago',
        'cta_url': context['cta_url'],
    })

    text_body = (
        f"Hola {context['user_full_name']},\n\n"
        f"Hemos recibido tu comprobante de transferencia para la factura "
        f"#{invoice.id} por {context['plan_amount']}.\n\n"
        f"Referencia: {proof.bank_reference}\n\n"
        f"Tu pago está pendiente de verificación. Normalmente estará "
        f"confirmado dentro de 24 h hábiles.\n\n"
        f"El equipo de Auron Suite"
    )
    _dispatch(user, subject, text_body, _render('payment_pending.html', context))
    logger.info('payment_pending email -> %s (invoice=%s)', user.email, invoice.id)


def send_manual_payment_approved_email(user, tenant, invoice, proof, access_until):
    """Confirma al cliente la aprobación de su transferencia."""
    subject = "¡Pago confirmado! - Suscripción activada"
    context = _base_context(subject, tenant, user)
    
    if hasattr(access_until, 'strftime'):
        access_until_fmt = access_until.strftime('%d/%m/%Y')
    else:
        access_until_fmt = str(access_until)[:10]

    context.update({
        'invoice_id': str(invoice.id),
        'plan_amount': _amount(invoice.amount),
        'plan_name': invoice.subscription.plan.get_name_display() if invoice.subscription and invoice.subscription.plan else 'Suscripción',
        'payment_method': 'Transferencia bancaria',
        'access_until': access_until_fmt,
        'cta_label': 'Ir a mi cuenta',
        'cta_url': f"{context['cta_url'].rsplit('/', 2)[0]}/auth/login",
    })

    text_body = (
        f"Hola {context['user_full_name']},\n\n"
        f"Tu pago por transferencia bancaria fue aprobado.\n\n"
        f"Factura: #{invoice.id}\n"
        f"Monto: {context['plan_amount']}\n"
        f"Plan: {context['plan_name']}\n"
        f"Acceso hasta: {context['access_until']}\n\n"
        f"Ya puedes disfrutar de todas las funcionalidades de tu plan.\n\n"
        f"El equipo de Auron Suite"
    )
    _dispatch(user, subject, text_body, _render('payment_approved.html', context))
    logger.info('payment_approved email -> %s (invoice=%s)', user.email, invoice.id)


def send_manual_payment_rejected_email(user, tenant, invoice, proof):
    """Informa al cliente que su comprobante fue rechazado y por qué."""
    subject = "Comprobante rechazado - Acción requerida"
    context = _base_context(subject, tenant, user)
    context.update({
        'invoice_id': str(invoice.id),
        'plan_amount': _amount(proof.amount_provided),
        'plan_name': invoice.subscription.plan.get_name_display() if invoice.subscription and invoice.subscription.plan else 'Suscripción',
        'payment_method': 'Transferencia bancaria',
        'reason': proof.decision_note or '—',
        'cta_label': 'Volver a subir comprobante',
        'cta_url': context['cta_url'],
    })

    text_body = (
        f"Hola {context['user_full_name']},\n\n"
        f"El comprobante de transferencia de la factura #{invoice.id} "
        f"({context['plan_amount']}) fue rechazado.\n\n"
        f"Motivo: {context['reason']}\n\n"
        f"Puedes subir un comprobante corregido desde tu panel de facturas.\n\n"
        f"El equipo de Auron Suite"
    )
    _dispatch(user, subject, text_body, _render('payment_rejected.html', context))
    logger.info('payment_rejected email -> %s (invoice=%s)', user.email, invoice.id)