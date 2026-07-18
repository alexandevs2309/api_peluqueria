# ACTUALIZACIÓN DE WEBHOOKS CON MÉTRICAS
# Agregar a apps/billing_api/webhooks_idempotent.py

from apps.billing_api.metrics import FinancialMetrics

# ============================================
# ACTUALIZAR handle_payment_succeeded
# ============================================

def handle_payment_succeeded(invoice_data):
    """Manejar pago exitoso con protección contra duplicados"""
    try:
        user_id = invoice_data['metadata'].get('user_id')
        payment_intent_id = invoice_data.get('payment_intent')
        
        if not user_id:
            logger.warning("Payment succeeded: missing user_id in metadata")
            return
        
        user = User.objects.get(id=user_id)
        
        # Validar tenant activo
        if hasattr(user, 'tenant') and user.tenant:
            try:
                get_active_tenant(user.tenant.id)
            except Exception as e:
                logger.warning(f"Payment succeeded for inactive tenant {user.tenant.id}: {str(e)}")
                return
        
        # Usar select_for_update para evitar race conditions
        with transaction.atomic():
            # Verificar si ya existe factura con este payment_intent
            existing = Invoice.objects.filter(
                stripe_payment_intent_id=payment_intent_id
            ).select_for_update().first()
            
            if existing:
                if existing.is_paid:
                    logger.info(f"Invoice for payment_intent {payment_intent_id} already marked as paid")
                    return
                # Actualizar factura existente
                existing.is_paid = True
                existing.paid_at = timezone.now()
                existing.payment_method = 'stripe'
                existing.status = 'paid'
                existing.save()
                invoice = existing
            else:
                # Crear nueva factura
                invoice = Invoice.objects.create(
                    user=user,
                    amount=invoice_data['amount_paid'] / 100,
                    due_date=timezone.now(),
                    is_paid=True,
                    paid_at=timezone.now(),
                    payment_method='stripe',
                    status='paid',
                    stripe_payment_intent_id=payment_intent_id,
                    description=f"Stripe Invoice {invoice_data.get('id', '')}"
                )
        
        # ============================================
        # NUEVO: REGISTRAR MÉTRICA
        # ============================================
        FinancialMetrics.record_payment_success(
            amount=invoice_data['amount_paid'] / 100,
            tenant_id=user.tenant.id if hasattr(user, 'tenant') and user.tenant else None,
            user_id=user.id
        )
        
        # Reactivar tenant si estaba suspendido
        if hasattr(user, 'tenant') and user.tenant:
            tenant = user.tenant
            if tenant.subscription_status == 'suspended':
                tenant.subscription_status = 'active'
                tenant.is_active = True
                tenant.save()
                logger.info(f"Tenant {tenant.id} reactivated after payment")
                
    except User.DoesNotExist:
        logger.warning(f"Payment succeeded: user {user_id} not found")
    except Exception as e:
        logger.error(f"Error handling payment succeeded: {str(e)}")
        raise


# ============================================
# ACTUALIZAR handle_payment_failed
# ============================================

def handle_payment_failed(invoice_data):
    """Manejar pago fallido"""
    try:
        user_id = invoice_data['metadata'].get('user_id')
        if not user_id:
            logger.warning("Payment failed: missing user_id in metadata")
            return
        
        user = User.objects.get(id=user_id)
        
        # Validar tenant activo
        if hasattr(user, 'tenant') and user.tenant:
            try:
                get_active_tenant(user.tenant.id)
            except Exception as e:
                logger.warning(f"Payment failed for inactive tenant {user.tenant.id}: {str(e)}")
                return
        
        # ============================================
        # NUEVO: REGISTRAR MÉTRICA
        # ============================================
        FinancialMetrics.record_payment_failure(
            reason=invoice_data.get('failure_reason', 'Unknown'),
            tenant_id=user.tenant.id if hasattr(user, 'tenant') and user.tenant else None,
            user_id=user.id
        )
        
        # Registrar intento fallido
        PaymentAttempt.objects.create(
            invoice_id=invoice_data.get('id'),
            success=False,
            status='failed',
            message=f"Payment failed: {invoice_data.get('failure_reason', 'Unknown')}"
        )
        
        # Suspender tenant después de 3 intentos fallidos
        failed_attempts = PaymentAttempt.objects.filter(
            invoice__user=user,
            success=False
        ).count()
        
        if failed_attempts >= 3 and hasattr(user, 'tenant'):
            tenant = user.tenant
            tenant.subscription_status = 'suspended'
            tenant.is_active = False
            tenant.save()
            logger.warning(f"Tenant {tenant.id} suspended after {failed_attempts} failed payments")
            
    except User.DoesNotExist:
        logger.warning(f"Payment failed: user {user_id} not found")
    except Exception as e:
        logger.error(f"Error handling payment failed: {str(e)}")
        raise
