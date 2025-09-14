from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework import status, serializers
from django.utils import timezone
from datetime import datetime, timedelta
from apps.audit_api.mixins import AuditLoggingMixin
from .models import Appointment
from .serializers import AppointmentSerializer
from django.contrib.auth import get_user_model
from apps.employees_api.models import WorkSchedule

User = get_user_model() 

class AppointmentViewSet(AuditLoggingMixin, ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and hasattr(user, 'tenant'):
            # Filtrar por tenant del usuario
            return Appointment.objects.filter(client__tenant=user.tenant)
        return Appointment.objects.none()

    def perform_create(self, serializer):
        appointment_datetime = serializer.validated_data['date_time']
        stylist = serializer.validated_data['stylist']
        
        # Validar que no hay conflictos de horario
        conflicting_appointments = Appointment.objects.filter(
            stylist=stylist,
            date_time=appointment_datetime,
            status__in=['scheduled', 'completed']
        ).exclude(pk=getattr(serializer.instance, 'pk', None))
        
        if conflicting_appointments.exists():
            raise serializers.ValidationError(
                "El estilista ya tiene una cita programada en ese horario"
            )
        
        # Validar horario de trabajo
        day_of_week = appointment_datetime.strftime('%A').lower()
        work_schedule = WorkSchedule.objects.filter(
            employee__user=stylist,
            day_of_week=day_of_week
        ).first()
        
        if work_schedule:
            appointment_time = appointment_datetime.time()
            if not (work_schedule.start_time <= appointment_time <= work_schedule.end_time):
                raise serializers.ValidationError(
                    f"El estilista no trabaja en ese horario el {day_of_week}"
                )
        
        serializer.save()

    @action(detail=False, methods=['get'])
    def availability(self, request):
        stylist_id = request.query_params.get('stylist_id')
        date = request.query_params.get('date')
        
        if not stylist_id or not date:
            return Response(
                {'error': 'stylist_id y date son requeridos'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            stylist = User.objects.get(id=stylist_id)
            target_date = datetime.fromisoformat(date).date()
        except (User.DoesNotExist, ValueError):
            return Response(
                {'error': 'Estilista o fecha inválida'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener horario de trabajo
        day_of_week = target_date.strftime('%A').lower()
        work_schedule = WorkSchedule.objects.filter(
            employee__user=stylist,
            day_of_week=day_of_week
        ).first()
        
        if not work_schedule:
            return Response({
                'available_slots': [],
                'message': f'El estilista no trabaja los {day_of_week}s'
            })
        
        # Generar slots de 30 minutos
        slots = []
        current_time = datetime.combine(target_date, work_schedule.start_time)
        end_time = datetime.combine(target_date, work_schedule.end_time)
        
        while current_time < end_time:
            # Verificar si hay cita en este horario
            existing_appointment = Appointment.objects.filter(
                stylist=stylist,
                date_time=current_time,
                status__in=['scheduled', 'completed']
            ).exists()
            
            if not existing_appointment:
                slots.append({
                    'datetime': current_time.isoformat(),
                    'time': current_time.strftime('%H:%M'),
                    'available': True
                })
            
            current_time += timedelta(minutes=30)
        
        return Response({
            'date': date,
            'stylist': stylist.full_name,
            'available_slots': slots
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        
        if appointment.status == 'cancelled':
            return Response(
                {'error': 'La cita ya está cancelada'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        appointment.status = 'cancelled'
        appointment.save()
        
        return Response({'detail': 'Cita cancelada correctamente'})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        appointment = self.get_object()
        
        if appointment.status == 'completed':
            return Response(
                {'error': 'La cita ya está completada'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        appointment.status = 'completed'
        appointment.save()
        
        # Actualizar última visita del cliente
        if appointment.client:
            appointment.client.last_visit = timezone.now()
            appointment.client.save()
        
        return Response({'detail': 'Cita completada correctamente'})

    @action(detail=False, methods=['get'])
    def today(self, request):
        today = timezone.now().date()
        appointments = self.get_queryset().filter(
            date_time__date=today
        ).order_by('date_time')
        
        serializer = AppointmentSerializer(appointments, many=True)
        return Response(serializer.data)

@api_view(['POST'])
def test_appointment(request):
    """Endpoint de prueba para debuggear"""
    try:
        data = request.data
        print(f"Received data: {data}")
        
        # Crear cita simple sin validaciones
        appointment = Appointment.objects.create(
            client_id=data.get('client'),
            stylist_id=data.get('stylist'),
            service_id=data.get('service'),
            date_time=data.get('date_time'),
            status=data.get('status', 'scheduled')
        )
        
        return Response({'id': appointment.id, 'message': 'Created successfully'})
    except Exception as e:
        print(f"Error: {str(e)}")
        return Response({'error': str(e)}, status=400)