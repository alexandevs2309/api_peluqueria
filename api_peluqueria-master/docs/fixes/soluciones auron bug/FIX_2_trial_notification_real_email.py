# ============================================================
# FIX 2: apps/tenants_api/middleware.py — método send_trial_notification
# PROBLEMA: Solo hace logger.info() — los emails NUNCA se envían.
# SOLUCIÓN: Reemplazar el método completo con envío real de email
#            usando el sistema de Celery ya configurado.
#
# INSTRUCCIÓN: Reemplaza el método send_trial_notification() en
#              TenantMiddleware con el código de abajo.
# ============================================================

# ---------- REEMPLAZAR ESTE MÉTODO EN TenantMiddleware ----------

    def send_trial_notification(self, tenant, days_left):
        """
        Enviar notificación real de trial via Celery (async).
        Usa send_trial_expiry_email task que ya existe en subscriptions_api.
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Disparar tarea Celery (no bloquea el request)
            from apps.subscriptions_api.tasks import send_trial_warning_email
            send_trial_warning_email.delay(
                tenant_id=tenant.id,
                days_left=days_left,
            )
            logger.info(
                "Trial warning email queued tenant=%s days_left=%d",
                tenant.subdomain, days_left
            )
        except Exception as exc:
            logger.error(
                "Failed to queue trial warning email tenant=%s: %s",
                tenant.subdomain, exc
            )


# ============================================================
# FIX 2b: apps/subscriptions_api/tasks.py
# AGREGAR esta nueva tarea al archivo existente.
# La infraestructura de email (send_mail + templates HTML)
# ya está implementada en las otras tasks del mismo archivo.
# ============================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_trial_warning_email(self, tenant_id: int, days_left: int):
    """
    Enviar aviso de expiración de trial al owner del tenant.
    Usa la infraestructura _build_html_email ya definida en este módulo.
    """
    try:
        tenant = Tenant.objects.select_related('owner').get(id=tenant_id)
    except Tenant.DoesNotExist:
        logger.warning("send_trial_warning_email: tenant %s not found", tenant_id)
        return

    owner = tenant.owner
    if not owner or not owner.email:
        logger.warning(
            "send_trial_warning_email: tenant %s has no owner email", tenant_id
        )
        return

    # No re-enviar si ya se marcó como enviada
    notification_key = f'trial_warning_{days_left}d'
    if tenant.trial_notifications_sent.get(notification_key):
        logger.info(
            "send_trial_warning_email: already sent for tenant=%s days=%d",
            tenant.subdomain, days_left
        )
        return

    if days_left > 0:
        subject = f"Tu período de prueba vence en {days_left} día{'s' if days_left != 1 else ''} — {tenant.name}"
        title = f"Quedan {days_left} día{'s' if days_left != 1 else ''} de tu prueba gratuita"
        message_lines = [
            f"Hola {owner.full_name or owner.email},",
            f"Tu período de prueba de {tenant.name} en Auron Suite vencerá en {days_left} día{'s' if days_left != 1 else ''}.",
            "Para continuar usando la plataforma sin interrupciones, activa tu suscripción ahora.",
            "Si tienes preguntas, estamos aquí para ayudarte.",
        ]
        cta_url = f"{getattr(settings, 'FRONTEND_URL', '')}/client/payment"
    else:
        subject = f"Tu período de prueba ha vencido — {tenant.name}"
        title = "Tu prueba gratuita ha finalizado"
        message_lines = [
            f"Hola {owner.full_name or owner.email},",
            f"El período de prueba de {tenant.name} ha finalizado.",
            "Para recuperar el acceso completo, activa tu suscripción.",
            "Todos tus datos están guardados y estarán disponibles al reactivar.",
        ]
        cta_url = f"{getattr(settings, 'FRONTEND_URL', '')}/client/payment"

    html_body = _build_html_email(tenant, title, message_lines)

    try:
        from django.core.mail import send_mail
        send_mail(
            subject=subject,
            message='\n'.join(message_lines),  # fallback texto plano
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[owner.email],
            html_message=html_body,
            fail_silently=False,
        )

        # Marcar como enviada para evitar duplicados
        tenant.trial_notifications_sent[notification_key] = True
        tenant.save(update_fields=['trial_notifications_sent'])

        logger.info(
            "Trial warning email sent tenant=%s days_left=%d recipient=%s",
            tenant.subdomain, days_left, owner.email
        )
    except Exception as exc:
        logger.error(
            "Trial warning email FAILED tenant=%s: %s",
            tenant.subdomain, exc
        )
        raise self.retry(exc=exc)
