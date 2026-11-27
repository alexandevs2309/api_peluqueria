from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import IntegrityError, transaction
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
            Q(employee_services__service_id=service_id)
            | Q(user__stylist_services__service_id=service_id)
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

    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    day_key = weekdays[target_date.weekday()]

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

    # BE-08: el booking público está exento del paywall de middleware porque el
    # visitante es anónimo y no hay JWT. Aplicamos aquí la misma regla sobre el
    # tenant resuelto por subdomain (nunca desde el payload del cliente).
    if tenant.subscription_status in {'past_due', 'suspended'}:
        return Response(
            {
                'error': 'La suscripción del negocio no está vigente',
                'code': 'PAYMENT_REQUIRED',
                'action_required': 'renew_subscription',
            },
            status=402,
        )
    if tenant.subscription_status in {'archived', 'cancelled'}:
        return Response(
            {'error': 'El negocio no está disponible', 'code': 'TENANT_UNAVAILABLE'},
            status=403,
        )

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

    date_time = timezone.make_aware(
        datetime.combine(data['date'], data['time']),
        timezone.get_current_timezone(),
    )

    from apps.appointments_api.models import Appointment
    from django.contrib.auth import get_user_model
    User = get_user_model()

    # CR-16/BE-08: exists()+create() es una carrera. Serializamos todas las
    # reservas del estilista bloqueando su fila de usuario dentro de atomic().
    # En PostgreSQL un segundo POST espera a que el primero confirme y entonces
    # vuelve a evaluar el conflicto.
    # BE-08: una Response devuelta DENTRO de atomic() confirma la transacción;
    # por eso los rechazos se marcan con set_rollback(True) y la respuesta se
    # devuelve después del bloque. Así no queda un Client huérfano cuando la
    # cita no se pudo crear (p. ej. IntegrityError por la constraint única).
    conflict_response = None

    with transaction.atomic():
        User.objects.select_for_update().get(pk=employee.user_id)

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

        conflict = employee.user.stylist_appointments.filter(
            date_time=date_time,
            status__in=['scheduled', 'completed'],
        ).exists()
        if conflict:
            conflict_response = Response(
                {'error': 'El horario seleccionado ya no está disponible'},
                status=409,
            )
            transaction.set_rollback(True)
        else:
            try:
                appointment = Appointment.objects.create(
                    tenant=tenant,
                    branch=employee.branch,
                    client=client,
                    # El contacto puede reutilizarse por teléfono/correo, pero la
                    # cita conserva el nombre que el visitante escribió ahora.
                    client_name=data['client_name'],
                    stylist=employee.user,
                    service=service,
                    date_time=date_time,
                    status='scheduled',
                    description=data.get('notes', ''),
                )
            except IntegrityError:
                # Defensa en profundidad: la restricción única existente
                # (tenant, stylist, client, date_time) gana la carrera si el
                # lock no se aplicó. set_rollback(True) evita que el Client
                # creado antes quede persistido sin su cita (BE-08).
                conflict_response = Response(
                    {'error': 'El horario seleccionado ya no está disponible'},
                    status=409,
                )
                transaction.set_rollback(True)

    if conflict_response is not None:
        return conflict_response

    return Response({
        'id': appointment.id,
        'message': 'Cita agendada exitosamente',
        'client_name': appointment.client_name,
        'stylist_name': employee.user.full_name or employee.user.email,
        'service_name': service.name,
        'date_time': date_time.isoformat(),
        'status': appointment.status,
    }, status=201)
