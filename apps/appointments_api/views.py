from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, serializers
from django.utils import timezone
from django.db.models import Prefetch, Q
from datetime import datetime, timedelta, time
from apps.audit_api.mixins import AuditLoggingMixin
from apps.tenants_api.base_viewsets import TenantScopedViewSet
from apps.core.tenant_permissions import TenantPermissionByAction, tenant_permission
from apps.subscriptions_api.permissions import HasFeaturePermission
from .models import Appointment
from .serializers import AppointmentSerializer
from django.contrib.auth import get_user_model
from apps.employees_api.models import Employee, EmployeeService, WorkSchedule

User = get_user_model() 

class AppointmentViewSet(AuditLoggingMixin, TenantScopedViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [TenantPermissionByAction, HasFeaturePermission]

    def get_queryset(self):
        qs = super().get_queryset()
        # Always scope queries to the current tenant to avoid cross‑tenant data leaks
        if not self.request.user.is_superuser:
            tenant = getattr(self.request, 'tenant', None)
            if tenant:
                qs = qs.filter(tenant=tenant)
        # Apply optional branch filter supplied via querystring (e.g. ?branch=2)
        branch_id = self.request.query_params.get('branch')
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if self.action in ('list', 'retrieve', 'today'):
            qs = qs.select_related('client', 'stylist', 'service', 'role')
            qs = qs.prefetch_related(
                Prefetch(
                    'stylist__employee_profile',
                    queryset=Employee.objects.select_related('user').prefetch_related('services')
                )
            )
        return qs
    required_feature = 'appointments'
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
        service = serializer.validated_data.get('service')
        
        # Validar que el estilista tiene un perfil de empleado
        if not hasattr(stylist, 'employee_profile') or not stylist.employee_profile:
            raise serializers.ValidationError(
                "El estilista seleccionado no tiene un perfil de empleado"
            )

        # Validar que el estilista ofrece el servicio (via EmployeeService, que es lo que puebla el frontend)
        if service:
            employee = getattr(stylist, 'employee_profile', None)
            if not employee or not EmployeeService.objects.filter(employee=employee, service=service).exists():
                raise serializers.ValidationError(
                    "El estilista no ofrece este servicio"
                )
        
        # Asignar tenant automáticamente y validar sucursal
        tenant = None
        user = self.request.user
        if user.is_superuser:
            # SuperAdmin: usar tenant del client
            client = serializer.validated_data.get('client')
            if client and hasattr(client, 'tenant'):
                tenant = client.tenant
        else:
            tenant = self.request.tenant

        save_kwargs = {'tenant': tenant}

        # Restricción y autoset de sucursal para empleados no administradores
        if user and getattr(user, 'is_authenticated', False) and not user.is_superuser:
            from apps.auth_api.role_utils import get_effective_role_api
            user_role = get_effective_role_api(user, tenant=tenant)
            if user_role != 'CLIENT_ADMIN' and hasattr(user, 'employee_profile') and user.employee_profile:
                if user.employee_profile.branch_id:
                    branch = serializer.validated_data.get('branch')
                    if branch and branch.id != user.employee_profile.branch_id:
                        raise serializers.ValidationError("No tienes permiso para programar citas en otra sucursal")
                    save_kwargs['branch_id'] = user.employee_profile.branch_id
        
        # Convertir a hora local para validaciones de zona horaria
        local_datetime = timezone.localtime(appointment_datetime)
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        day_of_week = weekdays[local_datetime.weekday()]

        # Validar que no hay conflictos de horario (solapamientos considerando duración)
        day_start = local_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        conflicting_appointments = Appointment.objects.filter(
            tenant=tenant,
            stylist=stylist,
            date_time__gte=day_start,
            date_time__lt=day_end,
            status__in=['scheduled', 'completed']
        ).exclude(pk=getattr(serializer.instance, 'pk', None)).select_related('service')

        new_duration = service.duration if service else 30
        new_start = appointment_datetime
        new_end = new_start + timedelta(minutes=new_duration)

        for exist in conflicting_appointments:
            exist_duration = exist.service.duration if exist.service else 30
            exist_start = exist.date_time
            exist_end = exist_start + timedelta(minutes=exist_duration)

            # Verificar solapamiento de intervalos
            if new_start < exist_end and exist_start < new_end:
                raise serializers.ValidationError(
                    f"El estilista ya tiene una cita programada de {timezone.localtime(exist_start).strftime('%H:%M')} a {timezone.localtime(exist_end).strftime('%H:%M')}"
                )

        # Validar horario de trabajo
        work_schedule = WorkSchedule.objects.filter(
            employee__user=stylist,
            employee__tenant=tenant,
            day_of_week=day_of_week
        ).first()

        if work_schedule:
            appointment_time = local_datetime.time()
            if not (work_schedule.start_time <= appointment_time <= work_schedule.end_time):
                raise serializers.ValidationError(
                    f"El estilista no trabaja en ese horario el {day_of_week}"
                )

        serializer.save(**save_kwargs)

    @action(detail=False, methods=['get'])
    def availability(self, request):
        stylist_id = request.query_params.get('stylist_id')
        date = request.query_params.get('date')
        exclude_id = request.query_params.get('exclude_id') or request.query_params.get('exclude_appointment_id')
        
        if not stylist_id or not date:
            return Response(
                {'error': 'stylist_id y date son requeridos'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            stylist = User.objects.get(id=stylist_id, tenant=self.request.tenant)
            target_date = datetime.fromisoformat(date).date()
        except (User.DoesNotExist, ValueError):
            return Response(
                {'error': 'Estilista o fecha inválida'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener horario de trabajo
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        day_of_week = weekdays[target_date.weekday()]
        work_schedule = WorkSchedule.objects.filter(
            employee__user=stylist,
            employee__tenant=self.request.tenant,
            day_of_week=day_of_week
        ).first()
        
        if not work_schedule:
            start_time_t = time(9, 0)
            end_time_t = time(18, 0)
        else:
            start_time_t = work_schedule.start_time
            end_time_t = work_schedule.end_time

        # Obtener citas del estilista en el día y calcular rangos ocupados
        day_appointments = Appointment.objects.filter(
            tenant=self.request.tenant,
            stylist=stylist,
            date_time__date=target_date,
            status__in=['scheduled', 'completed']
        )
        if exclude_id:
            try:
                day_appointments = day_appointments.exclude(id=int(exclude_id))
            except ValueError:
                pass
        day_appointments = day_appointments.select_related('service')

        occupied_ranges = []
        for apt in day_appointments:
            apt_duration = apt.service.duration if apt.service else 30
            occupied_ranges.append((apt.date_time, apt.date_time + timedelta(minutes=apt_duration)))

        # Generar slots de 30 minutos
        slots = []
        current_time = datetime.combine(target_date, start_time_t)
        end_time = datetime.combine(target_date, end_time_t)
        
        local_now = timezone.localtime(timezone.now())
        is_today = target_date == local_now.date()
        while current_time < end_time:
            # Saltar slots que ya pasaron (solo para hoy)
            if is_today and current_time.time() <= local_now.time():
                current_time += timedelta(minutes=30)
                continue

            slot_start = timezone.make_aware(current_time, timezone.get_current_timezone())
            slot_end = slot_start + timedelta(minutes=30)

            # Verificar si se solapa con algún rango ocupado
            is_overlap = False
            for start, end in occupied_ranges:
                if slot_start < end and start < slot_end:
                    is_overlap = True
                    break
            
            if not is_overlap:
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
        today_local = timezone.localtime(timezone.now()).date()
        today_start = timezone.make_aware(datetime.combine(today_local, time.min), timezone.get_current_timezone())
        tomorrow_start = today_start + timedelta(days=1)
        
        appointments = self.get_queryset().filter(
            date_time__gte=today_start,
            date_time__lt=tomorrow_start
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

    # Limitar rango a 3 meses para evitar queries masivos
    max_range = timedelta(days=90)
    if end_date - start_date > max_range:
        end_date = start_date + max_range
    
    base_filter = Q(date_time__gte=start_date, date_time__lte=end_date)

    # Filtro de tenant obligatorio - previene fuga cross-tenant
    tenant = getattr(request, 'tenant', None)
    if not request.user.is_superuser:
        if not tenant:
            return Response([], status=200)
        base_filter &= Q(tenant=tenant)
    else:
        if tenant:
            base_filter &= Q(tenant=tenant)

    # Filtrar por sucursal si se solicita
    branch_id = request.GET.get('branch_id') or request.GET.get('branch')
    if branch_id:
        base_filter &= Q(branch_id=branch_id)

    appointments = Appointment.objects.filter(base_filter).select_related('client', 'stylist', 'service')

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
                tenant=request.tenant
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
        
        # Validar disponibilidad (solapamientos considerando duración)
        day_start = new_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        conflicting_appointments = Appointment.objects.filter(
            tenant=appointment.tenant,
            stylist=appointment.stylist,
            date_time__gte=day_start,
            date_time__lt=day_end,
            status__in=['scheduled', 'completed']
        ).exclude(id=appointment.id).select_related('service')
        
        new_duration = appointment.service.duration if appointment.service else 30
        new_start = new_dt
        new_end = new_start + timedelta(minutes=new_duration)
        
        for exist in conflicting_appointments:
            exist_duration = exist.service.duration if exist.service else 30
            exist_start = exist.date_time
            exist_end = exist_start + timedelta(minutes=exist_duration)
            
            if new_start < exist_end and exist_start < new_end:
                return Response({
                    'error': f"El estilista ya tiene una cita programada de {timezone.localtime(exist_start).strftime('%H:%M')} a {timezone.localtime(exist_end).strftime('%H:%M')}"
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
            employee__user=stylist,
            employee__tenant=request.tenant
        ).values('day_of_week', 'start_time', 'end_time')
        
        # Obtener citas de la semana
        today = timezone.localtime(timezone.now()).date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        tenant_filter = {}
        if not user.is_superuser and hasattr(request, 'tenant') and request.tenant:
            tenant_filter['tenant'] = request.tenant
        appointments = Appointment.objects.filter(
            stylist=stylist,
            date_time__date__gte=week_start,
            date_time__date__lte=week_end,
            status__in=['scheduled', 'completed'],
            **tenant_filter
        ).values('date_time', 'client__full_name', 'service__name', 'status')
        
        return Response({
            'stylist_name': stylist.full_name,
            'work_schedules': list(schedules),
            'appointments': list(appointments),
            'week_range': f"{week_start} - {week_end}"
        })
        
    except User.DoesNotExist:
        return Response({'error': 'Estilista no encontrado'}, status=404)
