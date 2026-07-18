import logging
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

logger = logging.getLogger('metrics.financial')


class FinancialMetrics:
    """Sistema de métricas financieras en tiempo real"""
    
    @staticmethod
    def record_payment_success(amount, tenant_id=None, user_id=None):
        """Registrar pago exitoso"""
        key = f'metrics:payments:success:{timezone.now().date()}'
        cache.incr(key, 1)
        cache.expire(key, 86400 * 7)  # 7 días
        
        logger.info({
            'metric': 'stripe.payment.success',
            'amount': float(amount),
            'tenant_id': tenant_id,
            'user_id': user_id,
            'timestamp': timezone.now().isoformat(),
        })
    
    @staticmethod
    def record_payment_failure(reason, tenant_id=None, user_id=None):
        """Registrar pago fallido"""
        key = f'metrics:payments:failure:{timezone.now().date()}'
        cache.incr(key, 1)
        cache.expire(key, 86400 * 7)
        
        # Contador por tenant
        if tenant_id:
            tenant_key = f'metrics:tenant:{tenant_id}:failures'
            count = cache.incr(tenant_key, 1)
            cache.expire(tenant_key, 600)  # 10 minutos
            
            # Alerta si >5 fallos en 10 min
            if count >= 5:
                FinancialMetrics.alert_payment_spike(tenant_id, count)
        
        logger.error({
            'metric': 'stripe.payment.failure',
            'reason': reason,
            'tenant_id': tenant_id,
            'user_id': user_id,
            'timestamp': timezone.now().isoformat(),
        })
    
    @staticmethod
    def calculate_mrr():
        """Calcular MRR diario"""
        from apps.subscriptions_api.models import UserSubscription
        
        active_subs = UserSubscription.objects.filter(
            is_active=True,
            end_date__gte=timezone.now()
        ).select_related('plan')
        
        mrr = sum(
            sub.plan.price for sub in active_subs 
            if sub.plan and sub.plan.duration_month == 1
        )
        
        # Guardar en cache
        cache.set('metrics:mrr:current', float(mrr), 86400)
        
        # Actualizar promedio 7 días
        mrr_history = cache.get('metrics:mrr:history', [])
        mrr_history.append(float(mrr))
        mrr_history = mrr_history[-7:]  # Últimos 7 días
        cache.set('metrics:mrr:history', mrr_history, 86400 * 7)
        
        avg_7d = sum(mrr_history) / len(mrr_history) if mrr_history else float(mrr)
        cache.set('metrics:mrr:avg_7d', avg_7d, 86400)
        
        logger.info({
            'metric': 'subscription.mrr.daily',
            'value': float(mrr),
            'avg_7d': avg_7d,
            'active_subscriptions': active_subs.count(),
            'timestamp': timezone.now().isoformat(),
        })
        
        return mrr
    
    @staticmethod
    def alert_payment_spike(tenant_id, failure_count):
        """Alerta de spike de pagos fallidos"""
        try:
            import sentry_sdk
            sentry_sdk.capture_message(
                f'Payment failure spike: {failure_count} failures in 10 minutes',
                level='error',
                extras={
                    'tenant_id': tenant_id,
                    'failure_count': failure_count,
                }
            )
        except ImportError:
            logger.critical(f'Payment spike for tenant {tenant_id}: {failure_count} failures')
    
    @staticmethod
    def check_mrr_drop():
        """Verificar caída de MRR"""
        current_mrr = cache.get('metrics:mrr:current', 0)
        avg_7d = cache.get('metrics:mrr:avg_7d', current_mrr)
        
        if current_mrr < avg_7d * 0.9:  # Caída >10%
            drop_pct = ((avg_7d - current_mrr) / avg_7d) * 100 if avg_7d > 0 else 0
            
            try:
                import sentry_sdk
                sentry_sdk.capture_message(
                    f'MRR drop detected: {drop_pct:.1f}% decrease',
                    level='warning',
                    extras={
                        'current_mrr': current_mrr,
                        'avg_7d': avg_7d,
                        'drop_percentage': drop_pct,
                    }
                )
            except ImportError:
                logger.warning(f'MRR drop: {current_mrr} vs {avg_7d} avg ({drop_pct:.1f}%)')
    
    @staticmethod
    def get_metrics_summary():
        """Obtener resumen de métricas"""
        today = timezone.now().date()
        
        return {
            'payments': {
                'success_today': cache.get(f'metrics:payments:success:{today}', 0),
                'failure_today': cache.get(f'metrics:payments:failure:{today}', 0),
            },
            'mrr': {
                'current': cache.get('metrics:mrr:current', 0),
                'avg_7d': cache.get('metrics:mrr:avg_7d', 0),
            }
        }
