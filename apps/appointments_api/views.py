from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, serializers
from django.utils import timezone
from datetime import datetime, timedelta
from apps.audit_api.mixins import AuditLoggingMixin
from apps.tenants_api.base_viewsets import TenantScopedViewSet
from apps.core.tenant_permissions import TenantPermissionByAction, tenant_permission
from .models import Appointment
from .serializers import AppointmentSerializer
from django.contrib.auth import get_user_model
from apps.employees_api.models import WorkSchedule

User = get_user_model() 

class AppointmentViewSet(AuditLoggingMixin, TenantScopedViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'appointments_api.view_appointment',
        'retrieve': 'appointments_api.view_appointment',
        'create': 'appointments_api.add_appointment',
        'update': 'appointments_api.change_appointment',
        'partial_update': 'appointments_api.change_appointment',
        'destroy': 'appointments_api.delete_appointment',
        'availability': 'appointments_api.view_appointment',
        'cancel': 'appointments_api.cancel_appointment',
        'complete': 'appointments_api.complete_appointment',
        'today': 'appointments_api.view_appointment',
    }

    def perform_create(self, serializer):
        appointment_datetime = serializer.validated_data['date_time']
        stylist = serializer.validated_data['stylist']
        
        # Asignar tenant automáticamente
        tenant = None
        if self.request.user.is_superuser:
            # SuperAdmin: usar tenant del client
            client = serializer.validated_data.get('client')
            if client and hasattr(client, 'tenant'):
                tenant = client.tenant
        else:
            tenant = self.request.tenant
        
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
        
        serializer.save(tenant=tenant)

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



@api_view(['GET'])
@permission_classes([tenant_permission('appointments_api.view_appointment')])
def calendar_events(request):
    """Eventos para calendario - formato FullCalendar"""
    start = request.GET.get('start')
    end = request.GET.get('end')
    
    if not start or not end:
        return Response({'error': 'start y end son requeridos'}, status=400)
    
    try:
        start_date = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(end.replace('Z', '+00:00'))
    except ValueError:
        return Response({'error': 'Formato de fecha inválido'}, status=400)
    
    appointments = Appointment.objects.filter(
        date_time__gte=start_date,
        date_time__lte=end_date
    )
    
    events = []
    for apt in appointments:
        duration = apt.service.duration if apt.service else 30
        end_time = apt.date_time + timedelta(minutes=duration)
        
        color = {
            'scheduled': '#3498db',
            'completed': '#2ecc71',
            'cancelled': '#e74c3c'
        }.get(apt.status, '#95a5a6')
        
        events.append({
            'id': apt.id,
            'title': f"{apt.client.full_name}",
            'start': apt.date_time.isoformat(),
            'end': end_time.isoformat(),
            'backgroundColor': color,
            'borderColor': color,
            'extendedProps': {
                'clientName': apt.client.full_name,
                'clientPhone': apt.client.phone or '',
                'stylistName': apt.stylist.full_name if apt.stylist else 'Sin asignar',
                'serviceName': apt.service.name if apt.service else 'Sin servicio',
                'status': apt.status,
                'notes': apt.description or ''
            }
        })
    
    return Response(events)

@api_view(['POST'])
@permission_classes([tenant_permission('appointments_api.change_appointment')])
def reschedule_appointment(request, pk):
    """Reprogramar cita"""
    try:
        # Validar tenant antes de buscar
        if not request.user.is_superuser:
            if not hasattr(request, 'tenant') or not request.tenant:
                return Response({'error': 'Usuario sin tenant'}, status=404)
            
            appointment = Appointment.objects.get(
                id=pk,
                client__tenant=request.tenant
            )
        else:
            appointment = Appointment.objects.get(id=pk)
        
        new_datetime = request.data.get('new_datetime')
        if not new_datetime:
            return Response({'error': 'new_datetime es requerido'}, status=400)
        
        try:
            new_dt = datetime.fromisoformat(new_datetime.replace('Z', '+00:00'))
        except ValueError:
            return Response({'error': 'Formato de fecha inválido'}, status=400)
        
        # Validar disponibilidad
        conflicting = Appointment.objects.filter(
            stylist=appointment.stylist,
            date_time=new_dt,
            status__in=['scheduled', 'completed']
        ).exclude(id=appointment.id)
        
        if conflicting.exists():
            return Response({
                'error': 'El estilista ya tiene una cita en ese horario'
            }, status=400)
        
        old_datetime = appointment.date_time
        appointment.date_time = new_dt
        appointment.save()
        
        return Response({
            'message': 'Cita reprogramada correctamente',
            'old_datetime': old_datetime.isoformat(),
            'new_datetime': new_dt.isoformat()
        })
        
    except Appointment.DoesNotExist:
        return Response({'error': 'Cita no encontrada'}, status=404)

@api_view(['GET'])
@permission_classes([tenant_permission('appointments_api.view_appointment')])
def stylist_schedule(request, stylist_id):
    """Horario completo de un estilista"""
    try:
        # ✅ FIX: Definir user correctamente
        user = request.user
        
        # ✅ VALIDAR TENANT del stylist
        if not user.is_superuser:
            if not hasattr(request, 'tenant') or not request.tenant:
                return Response({'error': 'Usuario sin tenant'}, status=404)
            
            stylist = User.objects.get(
                id=stylist_id,
                tenant=request.tenant
            )
        else:
            stylist = User.objects.get(id=stylist_id)
        
        # Obtener horarios de trabajo
        from apps.employees_api.models import WorkSchedule
        schedules = WorkSchedule.objects.filter(
            employee__user=stylist
        ).values('day_of_week', 'start_time', 'end_time')
        
        # Obtener citas de la semana
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        appointments = Appointment.objects.filter(
            stylist=stylist,
            date_time__date__gte=week_start,
            date_time__date__lte=week_end,
            status__in=['scheduled', 'completed']
        ).values('date_time', 'client__full_name', 'service__name', 'status')
        
        return Response({
            'stylist_name': stylist.full_name,
            'work_schedules': list(schedules),
            'appointments': list(appointments),
            'week_range': f"{week_start} - {week_end}"
        })
        
    except User.DoesNotExist:
        return Response({'error': 'Estilista no encontrado'}, status=404)
