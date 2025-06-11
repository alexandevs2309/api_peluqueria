from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from .models import Appointment
from .serializers import AppointmentSerializer


class AppointmentViewSet(ModelViewSet):
    """
    A viewset for viewing and editing appointment instances.
    """
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            # Verificar si el usuario tiene el rol 'stylist'
            if user.roles.filter(name='stylist').exists():
                return Appointment.objects.filter(stylist__in=user.roles.all())
            # Filtrar citas por los clientes asociados al usuario
            return Appointment.objects.filter(client__user=user)
        return Appointment.objects.none()