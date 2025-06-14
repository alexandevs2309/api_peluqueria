from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from .models import Appointment
from .serializers import AppointmentSerializer
from django.contrib.auth import get_user_model

User = get_user_model() 

class AppointmentViewSet(ModelViewSet):
   
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
           
            if user.roles.filter(name='stylist').exists():
               
                return Appointment.objects.filter(stylist=user) 
            else:
                return Appointment.objects.filter(client__user=user)
        return Appointment.objects.none()