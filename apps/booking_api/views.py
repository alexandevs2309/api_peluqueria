from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Prefetch
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from datetime import datetime, timedelta, date, time, timezone as dt_timezone
from apps.tenants_api.models import Tenant
from apps.services_api.models import Service
from apps.employees_api.models import Employee, WorkSchedule
from apps.clients_api.models import Client
from django.contrib.auth import get_user_model
from .serializers import (
    PublicTenantInfoSerializer,
    PublicServiceSerializer,
    PublicStylistSerializer,
    PublicBookingSerializer,
)

User = get_user_model()


class PublicBookingThrottle(AnonRateThrottle):
    scope = 'public_booking'


def get_tenant_or_404(subdomain):
    tenant = get_object_or_404(
        Tenant,
        subdomain=subdomain,
        is_active=True,
        deleted_at__isnull=True,
    )
    return tenant


@api_view(['GET'])
@permission_classes([AllowAny])
def tenant_info(request, subdomain):
    tenant = get_tenant_or_404(subdomain)
    serializer = PublicTenantInfoSerializer({'tenant': tenant})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_services(request, subdomain):
    tenant = get_tenant_or_404(subdomain)
    services = Service.objects.filter(
        tenant=tenant,
        is_active=True,
    )
    serializer = PublicServiceSerializer(services, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_stylists(request, subdomain):
    tenant = get_tenant_or_404(subdomain)
    service_id = request.query_params.get('service_id')

    employees = Employee.objects.filter(
        tenant=tenant,
        is_active=True,
    ).select_related('user')

    if service_id:
        employees = employees.filter(
            Q(services__service_id=service_id) | Q(user__stylist_services__service_id=service_id)
        ).distinct()

    serializer = PublicStylistSerializer(employees, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def availability(request, subdomain):
    tenant = get_tenant_or_404(subdomain)
    stylist_id = request.query_params.get('stylist_id')
    date_str = request.query_params.get('date')

    if not stylist_id:
        return Response({'error': 'stylist_id es requerido'}, status=400)
    if not date_str:
        return Response({'error': 'date es requerido (YYYY-MM-DD)'}, status=400)

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Formato de fecha inválido, use YYYY-MM-DD'}, status=400)

    if target_date < date.today():
        return Response({'error': 'La fecha no puede ser en el pasado'}, status=400)

    employee = get_object_or_404(
        Employee.objects.select_related('user'),
        id=stylist_id,
        tenant=tenant,
        is_active=True,
    )

    day_name = target_date.strftime('%A').lower()
    day_map = {
        'monday': 'monday', 'tuesday': 'tuesday', 'wednesday': 'wednesday',
        'thursday': 'thursday', 'friday': 'friday', 'saturday': 'saturday', 'sunday': 'sunday',
    }
    day_key = day_map.get(day_name)
    if not day_key:
        return Response({'slots': []})

    schedules = WorkSchedule.objects.filter(
        employee=employee,
        day_of_week=day_key,
    )

    if not schedules.exists():
        return Response({'slots': []})

    existing_appointments = list(
        employee.user.stylist_appointments.filter(
            date_time__date=target_date,
            status__in=['scheduled', 'completed'],
        ).values_list('date_time', flat=True)
    )
    booked_times = {appt.astimezone(dt_timezone.utc).time() for appt in existing_appointments}

    slots = []
    slot_duration = 30
    now = timezone.now()

    for schedule in schedules:
        current = datetime.combine(target_date, schedule.start_time)
        end = datetime.combine(target_date, schedule.end_time)

        while current + timedelta(minutes=slot_duration) <= end:
            slot_time = current.time()
            slot_datetime = timezone.make_aware(
                current,
                timezone.get_current_timezone(),
            )

            if target_date == date.today() and slot_datetime <= now:
                current += timedelta(minutes=slot_duration)
                continue

            if slot_time not in booked_times:
                slots.append(slot_time.strftime('%H:%M'))

            current += timedelta(minutes=slot_duration)

    return Response({'slots': slots, 'date': date_str})


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([PublicBookingThrottle])
def book_appointment(request, subdomain):
    tenant = get_tenant_or_404(subdomain)

    serializer = PublicBookingSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    data = serializer.validated_data

    employee = get_object_or_404(
        Employee.objects.select_related('user'),
        id=data['stylist_id'],
        tenant=tenant,
        is_active=True,
    )
    service = get_object_or_404(
        Service,
        id=data['service_id'],
        tenant=tenant,
        is_active=True,
    )

    client_email = data.get('client_email', '').strip().lower()
    client_phone = data.get('client_phone', '').strip()

    if client_email:
        existing = Client.objects.filter(
            tenant=tenant,
            email=client_email,
        ).first()
        if existing:
            client = existing
        else:
            client = Client.objects.create(
                tenant=tenant,
                full_name=data['client_name'],
                email=client_email,
                phone=client_phone or None,
                source='Public Booking',
            )
    elif client_phone:
        existing = Client.objects.filter(
            tenant=tenant,
            phone=client_phone,
        ).first()
        if existing:
            client = existing
        else:
            client = Client.objects.create(
                tenant=tenant,
                full_name=data['client_name'],
                phone=client_phone,
                source='Public Booking',
            )
    else:
        client = Client.objects.create(
            tenant=tenant,
            full_name=data['client_name'],
            source='Public Booking',
        )

    date_time = timezone.make_aware(
        datetime.combine(data['date'], data['time']),
        timezone.get_current_timezone(),
    )

    conflict = employee.user.stylist_appointments.filter(
        date_time=date_time,
        status__in=['scheduled', 'completed'],
    ).exists()
    if conflict:
        return Response(
            {'error': 'El horario seleccionado ya no está disponible'},
            status=409,
        )

    from apps.appointments_api.models import Appointment
    appointment = Appointment.objects.create(
        tenant=tenant,
        client=client,
        stylist=employee.user,
        service=service,
        date_time=date_time,
        status='scheduled',
        description=data.get('notes', ''),
    )

    return Response({
        'id': appointment.id,
        'message': 'Cita agendada exitosamente',
        'client_name': client.full_name,
        'stylist_name': employee.user.full_name or employee.user.email,
        'service_name': service.name,
        'date_time': date_time.isoformat(),
        'status': appointment.status,
    }, status=201)
