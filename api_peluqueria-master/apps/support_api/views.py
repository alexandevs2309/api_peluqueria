import logging

from django.conf import settings

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.tenants_api.base_viewsets import TenantScopedViewSet
from apps.core.tenant_permissions import TenantPermissionByAction, resolve_request_tenant, _check_permission_in_db
from apps.auth_api.tasks import send_email_async
from apps.emails.service import EmailRenderer

from .models import SupportTicket
from .serializers import SupportTicketSerializer

logger = logging.getLogger(__name__)


class SupportTicketPermission(TenantPermissionByAction):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        tenant = resolve_request_tenant(request)
        if not tenant:
            return False

        action = self._resolve_action(request, view)
        if not action:
            return False

        if action == 'close':
            return (
                _check_permission_in_db(request.user, tenant, 'support_api', 'change_supportticket') or
                _check_permission_in_db(request.user, tenant, 'support_api', 'view_supportticket')
            )

        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        if not super().has_object_permission(request, view, obj):
            return False

        if request.user.is_superuser:
            return True

        action = self._resolve_action(request, view)
        if action == 'close':
            tenant = resolve_request_tenant(request)
            if _check_permission_in_db(request.user, tenant, 'support_api', 'change_supportticket'):
                return True
            return obj.created_by == request.user

        return True


class SupportTicketViewSet(TenantScopedViewSet):
    queryset = SupportTicket.objects.all()
    serializer_class = SupportTicketSerializer
    permission_classes = [SupportTicketPermission]
    pagination_class = None

    def get_queryset(self):
        if self.request.user.is_superuser:
            return SupportTicket.objects.all()
        return super().get_queryset()
    permission_map = {
        'list': 'support_api.view_supportticket',
        'retrieve': 'support_api.view_supportticket',
        'create': 'support_api.add_supportticket',
        'update': 'support_api.change_supportticket',
        'partial_update': 'support_api.change_supportticket',
        'destroy': 'support_api.delete_supportticket',
        'close': 'support_api.change_supportticket',
    }

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', getattr(self.request.user, 'tenant', None))
        ticket = serializer.save(created_by=self.request.user, tenant=tenant)
        self._notify_new_ticket(ticket)

    def perform_update(self, serializer):
        old_status = self.get_object().status
        ticket = serializer.save()
        if ticket.status != old_status:
            self._notify_status_change(ticket)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        ticket = self.get_object()
        if ticket.status == 'closed':
            return Response({'status': 'already_closed'}, status=status.HTTP_400_BAD_REQUEST)
        old_status = ticket.status
        setattr(ticket, '_old_status', old_status)
        ticket.status = 'closed'
        ticket.save(update_fields=['status', 'updated_at'])
        self._notify_status_change(ticket)
        return Response({'status': 'closed'})

    @action(detail=True, methods=['post'])
    def reply(self, request, pk=None):
        from django.utils import timezone
        ticket = self.get_object()
        reply_text = request.data.get('reply', '').strip()
        if not reply_text:
            return Response({'detail': 'La respuesta no puede estar vacía.'}, status=status.HTTP_400_BAD_REQUEST)

        ticket.admin_reply = reply_text
        ticket.replied_at = timezone.now()
        if ticket.status == 'open':
            ticket.status = 'in_progress'
        ticket.save(update_fields=['admin_reply', 'replied_at', 'status', 'updated_at'])
        self._notify_admin_reply(ticket)
        serializer = self.get_serializer(ticket)
        return Response(serializer.data)

    def _notify_new_ticket(self, ticket):
        try:
            tenant = ticket.tenant
            support_email = getattr(settings, 'SUPPORT_EMAIL', 'soporte@auronsuite.com')

            alert_subject = f'[Soporte] Nuevo ticket: {ticket.subject}'
            alert_text = (
                f"Se ha creado un nuevo ticket de soporte.\n\n"
                f"Tenant: {tenant.name if tenant else 'N/A'}\n"
                f"Usuario: {ticket.created_by.get_full_name()} ({ticket.created_by.email})\n"
                f"Prioridad: {ticket.get_priority_display()}\n"
                f"Asunto: {ticket.subject}\n"
                f"Descripción: {ticket.description}\n\n"
                f"Ingresa a la plataforma para gestionar este ticket."
            )
            alert_html = EmailRenderer.render('support_new_ticket.html', {
                'title': 'Nuevo ticket de soporte',
                'tenant_name': tenant.name if tenant else 'N/A',
                'user_name': ticket.created_by.get_full_name(),
                'user_email': ticket.created_by.email,
                'priority': ticket.get_priority_display(),
                'subject': ticket.subject,
                'description': ticket.description,
            })
            send_email_async.delay(alert_subject, alert_text, '', [support_email], html_message=alert_html)

            ack_subject = f'Recibimos tu ticket: {ticket.subject}'
            ack_text = (
                f"Hola {ticket.created_by.get_full_name()},\n\n"
                f"Hemos recibido tu ticket de soporte y será revisado a la brevedad.\n\n"
                f"Asunto: {ticket.subject}\n"
                f"Descripción: {ticket.description}\n"
                f"Prioridad: {ticket.get_priority_display()}\n\n"
                f"Te notificaremos cuando haya una respuesta."
            )
            ack_html = EmailRenderer.render('support_ticket_received.html', {
                'title': 'Recibimos tu solicitud',
                'user_full_name': ticket.created_by.get_full_name(),
                'subject': ticket.subject,
                'description': ticket.description,
                'priority': ticket.get_priority_display(),
            })
            send_email_async.delay(ack_subject, ack_text, '', [ticket.created_by.email], html_message=ack_html)
        except Exception as e:
            logger.error("Error sending ticket notification: %s", str(e))

    def _notify_status_change(self, ticket):
        try:
            subject = f'Ticket actualizado: {ticket.subject} — {ticket.get_status_display()}'
            text = (
                f"El estado de tu ticket ha cambiado.\n\n"
                f"Asunto: {ticket.subject}\n"
                f"Estado: {ticket.get_status_display()}\n\n"
                f"Ver ticket en el panel de soporte."
            )
            html = EmailRenderer.render('support_status_changed.html', {
                'title': 'Ticket actualizado',
                'subject': ticket.subject,
                'status': ticket.get_status_display(),
            })
            send_email_async.delay(subject, text, '', [ticket.created_by.email], html_message=html)
        except Exception as e:
            logger.error("Error sending status notification: %s", str(e))

    def _notify_admin_reply(self, ticket):
        try:
            subject = f'Respuesta a tu ticket: {ticket.subject}'
            text = (
                f"Hola {ticket.created_by.get_full_name()},\n\n"
                f"El equipo de soporte ha respondido a tu ticket.\n\n"
                f"Asunto: {ticket.subject}\n"
                f"Respuesta del soporte:\n{ticket.admin_reply}\n\n"
                f"Puedes ver y gestionar tu ticket en el panel de soporte."
            )
            html = EmailRenderer.render('support_status_changed.html', {
                'title': 'Respuesta a tu ticket',
                'subject': ticket.subject,
                'status': f'Respuesta del soporte: {ticket.admin_reply}',
            })
            send_email_async.delay(subject, text, '', [ticket.created_by.email], html_message=html)
        except Exception as e:
            logger.error("Error sending admin reply notification: %s", str(e))
