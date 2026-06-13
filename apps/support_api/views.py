import logging

from django.conf import settings

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.tenants_api.base_viewsets import TenantScopedViewSet
from apps.core.tenant_permissions import TenantPermissionByAction
from apps.auth_api.tasks import send_email_async

from .models import SupportTicket
from .serializers import SupportTicketSerializer

logger = logging.getLogger(__name__)


class SupportTicketViewSet(TenantScopedViewSet):
    queryset = SupportTicket.objects.all()
    serializer_class = SupportTicketSerializer
    permission_classes = [TenantPermissionByAction]
    pagination_class = None
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

    def _notify_new_ticket(self, ticket):
        try:
            tenant = ticket.tenant
            support_email = getattr(settings, 'SUPPORT_EMAIL', 'soporte@auronsuite.com')

            alert_subject = f'[Soporte] Nuevo ticket: {ticket.subject}'
            alert_message = (
                f"Se ha creado un nuevo ticket de soporte.\n\n"
                f"Tenant: {tenant.name if tenant else 'N/A'}\n"
                f"Usuario: {ticket.created_by.get_full_name()} ({ticket.created_by.email})\n"
                f"Prioridad: {ticket.get_priority_display()}\n"
                f"Asunto: {ticket.subject}\n"
                f"Descripción: {ticket.description}\n\n"
                f"Ingresa a la plataforma para gestionar este ticket."
            )
            send_email_async.delay(
                alert_subject, alert_message, '',
                [support_email],
                html_message=alert_message.replace('\n', '<br>')
            )

            ack_subject = f'Recibimos tu ticket: {ticket.subject}'
            ack_message = (
                f"Hola {ticket.created_by.get_full_name()},\n\n"
                f"Hemos recibido tu ticket de soporte y será revisado a la brevedad.\n\n"
                f"Asunto: {ticket.subject}\n"
                f"Descripción: {ticket.description}\n"
                f"Prioridad: {ticket.get_priority_display()}\n\n"
                f"Te notificaremos cuando haya una respuesta."
            )
            send_email_async.delay(
                ack_subject, ack_message, '',
                [ticket.created_by.email],
                html_message=ack_message.replace('\n', '<br>')
            )
        except Exception as e:
            logger.error("Error sending ticket notification: %s", str(e))

    def _notify_status_change(self, ticket):
        try:
            subject = f'Ticket actualizado: {ticket.subject} — {ticket.get_status_display()}'
            message = (
                f"El estado de tu ticket ha cambiado.\n\n"
                f"Asunto: {ticket.subject}\n"
                f"Estado: {ticket.get_status_display()}\n\n"
                f"Ver ticket en el panel de soporte."
            )
            send_email_async.delay(
                subject, message, '',
                [ticket.created_by.email],
                html_message=message.replace('\n', '<br>')
            )
        except Exception as e:
            logger.error("Error sending status notification: %s", str(e))
