import stripe
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from apps.billing_api.models import Invoice
from apps.billing_api.reconciliation_models import ReconciliationLog, ReconciliationAlert
import logging

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


@shared_task(bind=True, max_retries=3)
def daily_financial_reconciliation(self):
    """
    Reconciliación diaria Stripe ↔ DB
    Detecta: pagos faltantes, duplicados, discrepancias
    """
    reconciliation = ReconciliationLog.objects.create(status='running')
    
    try:
        # Período: últimas 24 horas + 1 hora buffer
        end_time = timezone.now()
        start_time = end_time - timedelta(hours=25)
        
        logger.info(f"Starting reconciliation from {start_time} to {end_time}")
        
        # 1. Obtener pagos exitosos de Stripe
        stripe_payments = fetch_stripe_payments(start_time, end_time)
        reconciliation.stripe_payments_checked = len(stripe_payments)
        
        # 2. Obtener facturas pagadas de DB
        db_invoices = Invoice.objects.filter(
            is_paid=True,
            paid_at__gte=start_time,
            paid_at__lte=end_time,
            payment_method='stripe'
        ).select_related('user')
        reconciliation.db_invoices_checked = db_invoices.count()
        
        # 3. Crear mapeos para comparación
        stripe_map = {p['payment_intent']: p for p in stripe_payments if p.get('payment_intent')}
        db_map = {inv.stripe_payment_intent_id: inv for inv in db_invoices if inv.stripe_payment_intent_id}
        
        # 4. Detectar pagos en Stripe no en DB
        missing_in_db = []
        for payment_intent_id, stripe_payment in stripe_map.items():
            if payment_intent_id not in db_map:
                missing_in_db.append({
                    'payment_intent_id': payment_intent_id,
                    'amount': stripe_payment['amount'] / 100,
                    'customer': stripe_payment.get('customer'),
                    'created': stripe_payment['created']
                })
                create_alert(
                    reconciliation,
                    'critical',
                    'missing_payment',
                    f"Payment {payment_intent_id} exists in Stripe but not in DB",
                    stripe_payment
                )
        
        # 5. Detectar pagos en DB no en Stripe
        missing_in_stripe = []
        for payment_intent_id, db_invoice in db_map.items():
            if payment_intent_id not in stripe_map:
                missing_in_stripe.append({
                    'invoice_id': db_invoice.id,
                    'payment_intent_id': payment_intent_id,
                    'amount': float(db_invoice.amount),
                    'user_id': db_invoice.user_id
                })
                create_alert(
                    reconciliation,
                    'high',
                    'orphan_payment',
                    f"Invoice {db_invoice.id} marked as paid but payment_intent {payment_intent_id} not found in Stripe",
                    {
                        'invoice_id': db_invoice.id,
                        'amount': float(db_invoice.amount),
                        'user_id': db_invoice.user_id
                    }
                )
        
        # 6. Detectar duplicados (mismo payment_intent múltiples facturas)
        duplicates = []
        payment_intent_counts = {}
        for inv in db_invoices:
            if inv.stripe_payment_intent_id:
                payment_intent_counts[inv.stripe_payment_intent_id] = \
                    payment_intent_counts.get(inv.stripe_payment_intent_id, 0) + 1
        
        for payment_intent_id, count in payment_intent_counts.items():
            if count > 1:
                duplicate_invoices = db_invoices.filter(stripe_payment_intent_id=payment_intent_id)
                duplicates.append({
                    'payment_intent_id': payment_intent_id,
                    'count': count,
                    'invoice_ids': [inv.id for inv in duplicate_invoices]
                })
                create_alert(
                    reconciliation,
                    'critical',
                    'duplicate',
                    f"Payment intent {payment_intent_id} has {count} invoices in DB",
                    {
                        'payment_intent_id': payment_intent_id,
                        'invoice_ids': [inv.id for inv in duplicate_invoices]
                    }
                )
        
        # 7. Verificar montos coincidentes
        for payment_intent_id in set(stripe_map.keys()) & set(db_map.keys()):
            stripe_amount = Decimal(str(stripe_map[payment_intent_id]['amount'] / 100))
            db_amount = db_map[payment_intent_id].amount
            
            if abs(stripe_amount - db_amount) > Decimal('0.01'):  # Tolerancia 1 centavo
                create_alert(
                    reconciliation,
                    'high',
                    'amount_mismatch',
                    f"Amount mismatch for {payment_intent_id}: Stripe={stripe_amount}, DB={db_amount}",
                    {
                        'payment_intent_id': payment_intent_id,
                        'stripe_amount': float(stripe_amount),
                        'db_amount': float(db_amount)
                    }
                )
        
        # 8. Guardar resultados
        reconciliation.missing_in_db = missing_in_db
        reconciliation.missing_in_stripe = missing_in_stripe
        reconciliation.duplicates = duplicates
        reconciliation.discrepancies_found = len(missing_in_db) + len(missing_in_stripe) + len(duplicates)
        reconciliation.status = 'completed'
        reconciliation.completed_at = timezone.now()
        reconciliation.save()
        
        logger.info(f"Reconciliation completed: {reconciliation.discrepancies_found} discrepancies found")
        
        # 9. Enviar notificación si hay discrepancias críticas
        if reconciliation.discrepancies_found > 0:
            send_reconciliation_alert(reconciliation)
        
        return {
            'status': 'completed',
            'discrepancies': reconciliation.discrepancies_found,
            'missing_in_db': len(missing_in_db),
            'missing_in_stripe': len(missing_in_stripe),
            'duplicates': len(duplicates)
        }
        
    except Exception as e:
        logger.error(f"Reconciliation failed: {str(e)}")
        reconciliation.status = 'failed'
        reconciliation.error_message = str(e)
        reconciliation.completed_at = timezone.now()
        reconciliation.save()
        raise self.retry(exc=e, countdown=300)  # Retry en 5 minutos


def fetch_stripe_payments(start_time, end_time):
    """Obtener pagos exitosos de Stripe en período"""
    payments = []
    
    try:
        # Convertir a timestamp Unix
        start_timestamp = int(start_time.timestamp())
        end_timestamp = int(end_time.timestamp())
        
        # Obtener payment intents exitosos
        payment_intents = stripe.PaymentIntent.list(
            created={'gte': start_timestamp, 'lte': end_timestamp},
            limit=100
        )
        
        for pi in payment_intents.auto_paging_iter():
            if pi.status == 'succeeded':
                payments.append({
                    'payment_intent': pi.id,
                    'amount': pi.amount,
                    'customer': pi.customer,
                    'created': pi.created,
                    'metadata': pi.metadata
                })
        
        logger.info(f"Fetched {len(payments)} successful payments from Stripe")
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe API error: {str(e)}")
        raise
    
    return payments


def create_alert(reconciliation, severity, alert_type, description, details):
    """Crear alerta de discrepancia"""
    ReconciliationAlert.objects.create(
        reconciliation=reconciliation,
        severity=severity,
        alert_type=alert_type,
        description=description,
        details=details
    )


def send_reconciliation_alert(reconciliation):
    """Enviar notificación de discrepancias (integrar con Sentry/email)"""
    critical_alerts = reconciliation.alerts.filter(severity='critical').count()
    high_alerts = reconciliation.alerts.filter(severity='high').count()
    
    message = f"""
    FINANCIAL RECONCILIATION ALERT
    
    Date: {reconciliation.started_at.date()}
    Status: {reconciliation.status}
    
    Discrepancies Found: {reconciliation.discrepancies_found}
    - Critical: {critical_alerts}
    - High: {high_alerts}
    
    Missing in DB: {len(reconciliation.missing_in_db)}
    Missing in Stripe: {len(reconciliation.missing_in_stripe)}
    Duplicates: {len(reconciliation.duplicates)}
    
    Action Required: Review reconciliation log #{reconciliation.id}
    """
    
    logger.critical(message)
    
    # TODO: Integrar con Sentry
    # sentry_sdk.capture_message(message, level='error')
    
    # TODO: Enviar email a finance team
    # send_mail(
    #     subject='[CRITICAL] Financial Reconciliation Alert',
    #     message=message,
    #     from_email=settings.DEFAULT_FROM_EMAIL,
    #     recipient_list=settings.FINANCE_ALERT_EMAILS,
    # )
