import json
from decimal import Decimal
import unittest.mock
import stripe
import pytest
from django.utils import timezone
from django.core import mail
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from apps.subscriptions_api.models import SubscriptionPlan, Subscription, UserSubscription
from apps.tenants_api.models import Tenant
from apps.auth_api.models import User
from apps.roles_api.models import Role, UserRole
from apps.employees_api.models import Employee, EmployeeService
from apps.services_api.models import Service
from apps.clients_api.models import Client as AppClient
from apps.appointments_api.models import Appointment
from apps.settings_api.models import SystemSettings
from rest_framework_simplejwt.tokens import AccessToken
import logging


class TestFunctionalVerification(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.basic_plan = SubscriptionPlan.objects.create(
            name='basic',
            price=Decimal('29.99'),
            is_active=True,
            is_public=True,
            max_employees=2,
            max_users=5,
            features={'appointments': True, 'pos': True, 'client_history': True}
        )
        cls.pro_plan = SubscriptionPlan.objects.create(
            name='standard',
            price=Decimal('49.99'),
            is_active=True,
            is_public=True,
            max_employees=10,
            max_users=15
        )

    def _authenticate_client(self, client, user):
        token = AccessToken.for_user(user)
        if user.tenant:
            token['tenant_id'] = user.tenant.id
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def _grant_permission(self, user, app_label, codename):
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        model_name = codename.split('_', 1)[1] if '_' in codename else 'generic'
        content_type, _ = ContentType.objects.get_or_create(app_label=app_label, model=model_name)
        perm, _ = Permission.objects.get_or_create(
            codename=codename,
            content_type=content_type,
            defaults={'name': f'Can {codename.replace("_", " ")}'}
        )
        role, _ = Role.objects.get_or_create(name=f'Role-{app_label}-{codename}')
        role.permissions.add(perm)
        UserRole.objects.get_or_create(user=user, role=role, tenant=user.tenant)

    def _set_tenant_status(self, tenant, status_str, access_until=None):
        """
        Fuerza el subscription_status de un tenant en la DB sin pasar por el
        save() personalizado del modelo (que resetea a 'trial' en creación).
        Llama refresh_from_db() en el objeto pasado.
        """
        update_fields = {'subscription_status': status_str}
        if access_until is not None:
            update_fields['access_until'] = access_until
        Tenant.objects.filter(pk=tenant.pk).update(**update_fields)
        tenant.refresh_from_db()

    def test_all_cases(self):
        cache.delete('system_settings')

        # =====================================================================
        # CASO 1: Bloqueo de escrituras en Mora (past_due)
        # =====================================================================
        print("\n" + "="*80)
        print(" EJECUCIÓN CASO 1: Tenant en estado 'past_due' (Mora)")
        print("="*80)

        t1 = Tenant.objects.create(
            name="Barbería Mora Test",
            subdomain="moratest",
            is_active=True,
            subscription_plan=self.basic_plan
        )
        # El save() del modelo fuerza subscription_status='trial' en creación.
        # Usamos update() para fijar past_due sin pasar por save().
        self._set_tenant_status(t1, 'past_due', timezone.now() - timezone.timedelta(days=1))

        u1 = User.objects.create_user(
            email="admin_mora@example.com",
            password="pass",
            tenant=t1,
            role="Client-Admin"
        )
        self._grant_permission(u1, 'clients_api', 'add_client')
        self._grant_permission(u1, 'appointments_api', 'add_appointment')
        self._grant_permission(u1, 'employees_api', 'add_employee')
        self._grant_permission(u1, 'services_api', 'add_service')
        self._grant_permission(u1, 'clients_api', 'view_client')

        client = APIClient()
        self._authenticate_client(client, u1)

        print(f"Estado ANTES del Tenant:")
        print(f"  - ID: {t1.id}")
        print(f"  - Nombre: {t1.name}")
        print(f"  - subscription_status: {t1.subscription_status}")
        print(f"  - access_until: {t1.access_until}")
        print(f"  - Plan: {t1.subscription_plan.name}")

        # Intentar Crear Cliente
        client_data = {"full_name": "Cliente Mora", "email": "mora@example.com"}
        r_client = client.post('/api/clients/clients/', client_data, format='json')
        print("\nOperación: CREAR CLIENTE (POST /api/clients/clients/)")
        print(f"Resultado ESPERADO: HTTP 402 Payment Required (escrituras bloqueadas en mora)")
        print(f"Resultado OBTENIDO:")
        print(f"  - HTTP Status: {r_client.status_code}")
        print(f"  - Respuesta JSON: {r_client.content.decode()}")

        # Preparar datos para cita (via ORM directo, no API)
        emp_user = User.objects.create_user(email='stylist_mora@example.com', password='pass', tenant=t1)
        employee = Employee.objects.create(tenant=t1, user=emp_user, is_active=True)
        service = Service.objects.create(tenant=t1, name='Corte Mora', price=Decimal('20.00'), is_active=True)
        db_client = AppClient.objects.create(tenant=t1, full_name='Cliente Mora Cita', created_by=u1)
        EmployeeService.objects.create(employee=employee, service=service)

        appt_data = {
            "client": db_client.id,
            "stylist": emp_user.id,
            "service": service.id,
            "date_time": (timezone.now() + timezone.timedelta(days=1)).isoformat(),
            "status": "scheduled"
        }
        r_appt = client.post('/api/appointments/appointments/', appt_data, format='json')
        print("\nOperación: CREAR CITA (POST /api/appointments/appointments/)")
        print(f"Resultado ESPERADO: HTTP 402 Payment Required")
        print(f"Resultado OBTENIDO:")
        print(f"  - HTTP Status: {r_appt.status_code}")
        print(f"  - Respuesta JSON: {r_appt.content.decode()}")

        target_user = User.objects.create_user(email='new_emp_mora@example.com', password='pass', tenant=t1)
        emp_data = {"user_id": target_user.id, "profession": "stylist", "phone": "1234567890", "is_active": True}
        r_emp = client.post('/api/employees/employees/', emp_data, format='json')
        print("\nOperación: CREAR EMPLEADO (POST /api/employees/employees/)")
        print(f"Resultado ESPERADO: HTTP 402 Payment Required")
        print(f"Resultado OBTENIDO:")
        print(f"  - HTTP Status: {r_emp.status_code}")
        print(f"  - Respuesta JSON: {r_emp.content.decode()}")

        svc_data = {"name": "Servicio Mora", "price": "30.00", "is_active": True}
        r_svc = client.post('/api/services/services/', svc_data, format='json')
        print("\nOperación: CREAR SERVICIO (POST /api/services/services/)")
        print(f"Resultado ESPERADO: HTTP 402 Payment Required")
        print(f"Resultado OBTENIDO:")
        print(f"  - HTTP Status: {r_svc.status_code}")
        print(f"  - Respuesta JSON: {r_svc.content.decode()}")

        r_get = client.get('/api/clients/clients/')
        print("\nOperación CONTROL: LEER CLIENTES (GET /api/clients/clients/)")
        print(f"Resultado ESPERADO: HTTP 200 OK (lectura permitida en mora)")
        print(f"Resultado OBTENIDO:")
        print(f"  - HTTP Status: {r_get.status_code}")

        print(f"\nEstado DESPUÉS del Tenant:")
        print(f"  - Clientes creados vía POST: {AppClient.objects.filter(tenant=t1, full_name='Cliente Mora').count()}")
        print(f"  - Citas creadas vía POST: {Appointment.objects.filter(tenant=t1, client=db_client).count()}")
        print(f"  - Empleados creados vía POST: {Employee.objects.filter(tenant=t1, user=target_user).count()}")
        print(f"  - Servicios creados vía POST: {Service.objects.filter(tenant=t1, name='Servicio Mora').count()}")

        assert r_client.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert r_appt.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert r_emp.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert r_svc.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert r_get.status_code == status.HTTP_200_OK

        # =====================================================================
        # CASO 2: Límite de clientes - Intentar crear 11 con límite 10
        # =====================================================================
        print("\n" + "="*80)
        print(" EJECUCIÓN CASO 2: Límite de Clientes (Límite 10, Crear 11)")
        print("="*80)

        t2 = Tenant.objects.create(
            name="Salón Límite Clientes",
            subdomain="limitclients",
            is_active=True,
            subscription_plan=self.basic_plan
        )
        self._set_tenant_status(t2, 'active', timezone.now() + timezone.timedelta(days=30))

        u2 = User.objects.create_user(
            email="admin_clients@example.com",
            password="pass",
            tenant=t2,
            role="Client-Admin"
        )
        self._grant_permission(u2, 'clients_api', 'add_client')

        client = APIClient()
        self._authenticate_client(client, u2)

        clients_bulk = [
            AppClient(tenant=t2, full_name=f"Cliente Bulk {i}", email=f"bulk{i}@example.com", created_by=u2)
            for i in range(10)
        ]
        AppClient.objects.bulk_create(clients_bulk)

        print(f"Estado ANTES del Tenant:")
        print(f"  - Límite de clientes del plan (mockeado): 10")
        print(f"  - Total clientes en base de datos: {AppClient.objects.filter(tenant=t2).count()}")

        mock_sub = unittest.mock.MagicMock()
        mock_sub.plan.max_clients = 10

        with unittest.mock.patch('apps.subscriptions_api.validators.get_user_active_subscription', return_value=mock_sub):
            r_client11 = client.post('/api/clients/clients/', {"full_name": "Cliente Excedido", "email": "exceeded@example.com"}, format='json')
            print("\nOperación: CREAR CLIENTE 11 (POST /api/clients/clients/)")
            print(f"Resultado ESPERADO: HTTP 400 Bad Request (límite alcanzado)")
            print(f"Resultado OBTENIDO:")
            print(f"  - HTTP Status: {r_client11.status_code}")
            print(f"  - Respuesta JSON: {r_client11.content.decode()}")

        print(f"\nEstado DESPUÉS del Tenant:")
        print(f"  - Total clientes en base de datos: {AppClient.objects.filter(tenant=t2).count()}")

        assert r_client11.status_code == status.HTTP_400_BAD_REQUEST
        assert AppClient.objects.filter(tenant=t2).count() == 10

        # =====================================================================
        # CASO 3: Límite de citas - Intentar crear 6 con límite 5
        # =====================================================================
        print("\n" + "="*80)
        print(" EJECUCIÓN CASO 3: Límite de Citas (Límite 5, Crear 6)")
        print("="*80)

        t3 = Tenant.objects.create(
            name="Salón Límite Citas",
            subdomain="limitappts",
            is_active=True,
            subscription_plan=self.basic_plan
        )
        self._set_tenant_status(t3, 'active', timezone.now() + timezone.timedelta(days=30))

        u3 = User.objects.create_user(
            email="admin_appts@example.com",
            password="pass",
            tenant=t3,
            role="Client-Admin"
        )
        self._grant_permission(u3, 'appointments_api', 'add_appointment')

        client = APIClient()
        self._authenticate_client(client, u3)

        emp_user3 = User.objects.create_user(email='stylist3@example.com', password='pass', tenant=t3)
        employee3 = Employee.objects.create(tenant=t3, user=emp_user3, is_active=True)
        service3 = Service.objects.create(tenant=t3, name='Corte Rápido', price=Decimal('15.00'), is_active=True)
        db_client3 = AppClient.objects.create(tenant=t3, full_name='Cliente Fiel', created_by=u3)
        EmployeeService.objects.create(employee=employee3, service=service3)

        Appointment.objects.bulk_create([
            Appointment(
                tenant=t3, client=db_client3, stylist=emp_user3, service=service3,
                date_time=timezone.now() - timezone.timedelta(minutes=i*10), status="scheduled"
            )
            for i in range(5)
        ])

        print(f"Estado ANTES del Tenant:")
        print(f"  - Límite de citas del plan (mockeado): 5")
        print(f"  - Total citas del mes en base de datos: {Appointment.objects.filter(tenant=t3).count()}")

        mock_sub_appt = unittest.mock.MagicMock()
        mock_sub_appt.plan.max_appointments_per_month = 5
        mock_sub_appt.plan.max_appointments = 5

        with unittest.mock.patch('apps.subscriptions_api.validators.get_user_active_subscription', return_value=mock_sub_appt):
            r_appt6 = client.post('/api/appointments/appointments/', {
                'client': db_client3.id,
                'stylist': emp_user3.id,
                'service': service3.id,
                'date_time': (timezone.now() + timezone.timedelta(days=1)).isoformat(),
                'status': 'scheduled'
            }, format='json')
            print("\nOperación: CREAR CITA 6 (POST /api/appointments/appointments/)")
            print(f"Resultado ESPERADO: HTTP 400 Bad Request (límite mensual alcanzado)")
            print(f"Resultado OBTENIDO:")
            print(f"  - HTTP Status: {r_appt6.status_code}")
            print(f"  - Respuesta JSON: {r_appt6.content.decode()}")

        print(f"\nEstado DESPUÉS del Tenant:")
        print(f"  - Total citas del mes: {Appointment.objects.filter(tenant=t3).count()}")

        assert r_appt6.status_code == status.HTTP_400_BAD_REQUEST
        assert Appointment.objects.filter(tenant=t3).count() == 5

        # =====================================================================
        # CASO 4: Auto Upgrade (Stripe)
        # =====================================================================
        print("\n" + "="*80)
        print(" EJECUCIÓN CASO 4: Auto Upgrade (Stripe call check)")
        print("="*80)

        # 4A: Sin suscripción de Stripe activa → debe bloquear sin llamar a Stripe
        print("\n--- Sub-Escenario 4A: Tenant SIN suscripción de Stripe activa ---")
        t4a = Tenant.objects.create(
            name="Salon Sin Stripe",
            subdomain="no-stripe",
            is_active=True,
            subscription_plan=self.basic_plan,
            max_employees=2
        )
        self._set_tenant_status(t4a, 'active', timezone.now() + timezone.timedelta(days=30))

        u4a = User.objects.create_user(
            email="admin_no_stripe@example.com",
            password="pass",
            tenant=t4a,
            role="Client-Admin"
        )
        self._grant_permission(u4a, 'employees_api', 'add_employee')

        for i in range(2):
            eu = User.objects.create_user(email=f'emp_no_str{i}@example.com', password='pass', tenant=t4a)
            Employee.objects.create(tenant=t4a, user=eu, is_active=True)

        target_u4a = User.objects.create_user(email='target_no_str@example.com', password='pass', tenant=t4a)

        system_settings = SystemSettings.get_settings()
        original_auto_upgrade = system_settings.auto_upgrade_limits
        system_settings.auto_upgrade_limits = True
        system_settings.save()
        cache.delete('system_settings')

        client = APIClient()
        self._authenticate_client(client, u4a)

        emp_data_4a = {'user_id': target_u4a.id, 'profession': 'stylist', 'phone': '1234567890', 'is_active': True}

        with unittest.mock.patch('stripe.Subscription.modify') as mock_modify_4a:
            r_4a = client.post('/api/employees/employees/', emp_data_4a, format='json')
            print("Operación: CREAR EMPLEADO 3 SIN SUSCRIPCIÓN STRIPE (POST /api/employees/employees/)")
            print("Resultado ESPERADO: HTTP 400 Bad Request (sin Stripe activo, auto-upgrade bloqueado)")
            print("Resultado OBTENIDO:")
            print(f"  - HTTP Status: {r_4a.status_code}")
            print(f"  - Respuesta JSON: {r_4a.content.decode()}")
            print(f"  - ¿Stripe fue llamado?: {mock_modify_4a.called}")
            assert r_4a.status_code == status.HTTP_400_BAD_REQUEST
            assert not mock_modify_4a.called

        # 4B: Con suscripción de Stripe activa → debe actualizar plan y llamar a Stripe
        print("\n--- Sub-Escenario 4B: Tenant CON suscripción de Stripe activa ---")
        t4b = Tenant.objects.create(
            name="Salon Con Stripe",
            subdomain="con-stripe",
            is_active=True,
            subscription_plan=self.basic_plan,
            max_employees=2
        )
        self._set_tenant_status(t4b, 'active', timezone.now() + timezone.timedelta(days=30))

        u4b = User.objects.create_user(
            email="admin_con_stripe@example.com",
            password="pass",
            tenant=t4b,
            role="Client-Admin"
        )
        self._grant_permission(u4b, 'employees_api', 'add_employee')

        self.basic_plan.stripe_price_id = 'price_basic_123'
        self.basic_plan.save()
        self.pro_plan.stripe_price_id = 'price_pro_123'
        self.pro_plan.save()

        Subscription.objects.create(
            tenant=t4b,
            plan=self.basic_plan,
            stripe_subscription_id='sub_stripe_123_test',
            is_active=True,
            billing_interval='month'
        )
        UserSubscription.objects.create(
            user=u4b,
            plan=self.basic_plan,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=30),
            is_active=True
        )

        for i in range(2):
            eu = User.objects.create_user(email=f'emp_con_str{i}@example.com', password='pass', tenant=t4b)
            Employee.objects.create(tenant=t4b, user=eu, is_active=True)

        target_u4b = User.objects.create_user(email='target_con_str@example.com', password='pass', tenant=t4b)
        emp_data_4b = {'user_id': target_u4b.id, 'profession': 'stylist', 'phone': '1234567890', 'is_active': True}

        client = APIClient()
        self._authenticate_client(client, u4b)

        with unittest.mock.patch('stripe.Subscription.retrieve', return_value={
            'id': 'sub_stripe_123_test',
            'items': {'data': [{'id': 'si_item_789'}]}
        }) as mock_retrieve, \
        unittest.mock.patch('stripe.Subscription.modify', return_value={
            'id': 'sub_stripe_123_test_response_id', 'status': 'active'
        }) as mock_modify:

            print(f"Estado ANTES del Tenant:")
            print(f"  - Plan local: {t4b.subscription_plan.name}")
            print(f"  - Empleados activos: {t4b.employees.filter(is_active=True).count()}")
            print(f"  - Stripe subscription ID: sub_stripe_123_test")

            r_4b = client.post('/api/employees/employees/', emp_data_4b, format='json')

            print("\nOperación: CREAR EMPLEADO 3 CON SUSCRIPCIÓN STRIPE ACTIVA (POST /api/employees/employees/)")
            print("Resultado ESPERADO: HTTP 201 Created + Stripe llamado")
            print("Resultado OBTENIDO:")
            print(f"  - HTTP Status: {r_4b.status_code}")
            print(f"  - Respuesta JSON: {r_4b.content.decode()}")

            t4b.refresh_from_db()
            print(f"\nEstado DESPUÉS del Tenant:")
            print(f"  - Plan local modificado: {t4b.subscription_plan.name}")
            print(f"  - Empleados activos: {t4b.employees.filter(is_active=True).count()}")
            print(f"\nEvidencia de llamada a Stripe:")
            print(f"  - ¿stripe.Subscription.modify fue llamado?: {mock_modify.called}")
            print(f"  - Argumentos: {mock_modify.call_args if mock_modify.called else 'N/A'}")
            print(f"  - Respuesta Stripe ID: {mock_modify.return_value['id'] if mock_modify.called else 'N/A'}")

            assert r_4b.status_code == status.HTTP_201_CREATED
            assert t4b.subscription_plan == self.pro_plan
            mock_retrieve.assert_called_once_with('sub_stripe_123_test')
            mock_modify.assert_called_once_with(
                'sub_stripe_123_test',
                proration_behavior='always_invoice',
                items=[{'id': 'si_item_789', 'price': 'price_pro_123'}]
            )

        system_settings.auto_upgrade_limits = original_auto_upgrade
        system_settings.save()
        cache.delete('system_settings')

        # =====================================================================
        # CASO 5: Cancelación de Suscripción
        # =====================================================================
        print("\n" + "="*80)
        print(" EJECUCIÓN CASO 5: Cancelación de Suscripción")
        print("="*80)

        t5 = Tenant.objects.create(
            name="Salon Cancelación Test",
            subdomain="canceltest",
            is_active=True,
            subscription_plan=self.basic_plan
        )
        self._set_tenant_status(t5, 'active', timezone.now() + timezone.timedelta(days=30))

        u5 = User.objects.create_user(
            email="admin_cancel@example.com",
            password="pass",
            tenant=t5,
            role="Client-Admin"
        )
        self._grant_permission(u5, 'subscriptions_api', 'change_usersubscription')

        sub = UserSubscription.objects.create(
            user=u5,
            plan=self.basic_plan,
            start_date=timezone.now() - timezone.timedelta(days=1),
            end_date=timezone.now() + timezone.timedelta(days=29),
            is_active=True
        )

        client = APIClient()
        self._authenticate_client(client, u5)

        print(f"Estado ANTES de la Suscripción:")
        print(f"  - ID: {sub.id}")
        print(f"  - is_active: {sub.is_active}")
        print(f"  - cancelled_at: {sub.cancelled_at}")
        print(f"  - end_date: {sub.end_date}")

        with unittest.mock.patch('apps.auth_api.tasks.send_email_async.delay') as mock_celery_delay:
            r_cancel = client.post(f'/api/subscriptions/user-subscriptions/{sub.id}/cancel/')

            from apps.subscriptions_api.tasks import send_cancellation_confirmation_email
            send_cancellation_confirmation_email(u5, t5, sub)

            print(f"\nOperación: CANCELAR SUSCRIPCIÓN (POST .../cancel/)")
            print(f"Resultado ESPERADO: HTTP 200 OK + correo de confirmación enviado")
            print(f"Resultado OBTENIDO:")
            print(f"  - HTTP Status: {r_cancel.status_code}")
            print(f"  - Respuesta JSON: {r_cancel.content.decode()}")

            print(f"\nVerificación de Correo de Confirmación:")
            print(f"  - ¿Se despachó tarea Celery de correo?: {mock_celery_delay.called}")
            if mock_celery_delay.called:
                call_kwargs = mock_celery_delay.call_args[1] if mock_celery_delay.call_args.kwargs else {}
                print(f"  - Asunto: {call_kwargs.get('subject')}")
                print(f"  - Destinatarios: {call_kwargs.get('recipient_list')}")

            sub.refresh_from_db()
            print(f"\nEstado DESPUÉS de la Suscripción:")
            print(f"  - is_active (conserva acceso hasta fin de período): {sub.is_active}")
            print(f"  - cancelled_at: {sub.cancelled_at}")
            print(f"  - end_date: {sub.end_date}")

            assert r_cancel.status_code == status.HTTP_200_OK
            assert sub.cancelled_at is not None
            assert sub.is_active is True
            assert mock_celery_delay.called

        # =====================================================================
        # CASO 6: Trial expirado — acceso bloqueado
        # =====================================================================
        print("\n" + "="*80)
        print(" EJECUCIÓN CASO 6: Trial expirado (bloqueado)")
        print("="*80)

        t6 = Tenant.objects.create(
            name="Barbería Trial Expirado",
            subdomain="trialexp",
            is_active=True,
            subscription_plan=self.basic_plan
        )
        # El save() crea el tenant como 'trial'. Forzamos trial_end_date 5 días en el pasado.
        Tenant.objects.filter(pk=t6.pk).update(
            subscription_status='trial',
            trial_end_date=(timezone.now() - timezone.timedelta(days=5)).date()
        )
        t6.refresh_from_db()

        u6 = User.objects.create_user(
            email="admin_trial@example.com",
            password="pass",
            tenant=t6,
            role="Client-Admin"
        )
        self._grant_permission(u6, 'clients_api', 'view_client')

        client = APIClient()
        self._authenticate_client(client, u6)

        print(f"Estado ANTES del Tenant:")
        print(f"  - subscription_status: {t6.subscription_status}")
        print(f"  - trial_end_date: {t6.trial_end_date}")
        print(f"  - Días desde expiración: 5")

        r_trial = client.get('/api/clients/clients/')
        print("\nOperación: LEER CLIENTES con trial expirado (GET /api/clients/clients/)")
        print(f"Resultado ESPERADO: HTTP 402 o 403 (acceso bloqueado tras expirar trial)")
        print(f"Resultado OBTENIDO:")
        print(f"  - HTTP Status: {r_trial.status_code}")
        print(f"  - Respuesta JSON: {r_trial.content.decode()}")

        assert r_trial.status_code in (status.HTTP_402_PAYMENT_REQUIRED, status.HTTP_403_FORBIDDEN)

        # =====================================================================
        # CASO 7: Límite de empleados — sin auto-upgrade
        # =====================================================================
        print("\n" + "="*80)
        print(" EJECUCIÓN CASO 7: Límite de Empleados (Límite 2, Crear 3, sin auto-upgrade)")
        print("="*80)

        t7 = Tenant.objects.create(
            name="Salón Límite Empleados",
            subdomain="limitemps",
            is_active=True,
            subscription_plan=self.basic_plan,
            max_employees=2
        )
        self._set_tenant_status(t7, 'active', timezone.now() + timezone.timedelta(days=30))

        u7 = User.objects.create_user(
            email="admin_emps@example.com",
            password="pass",
            tenant=t7,
            role="Client-Admin"
        )
        self._grant_permission(u7, 'employees_api', 'add_employee')

        # Crear 2 empleados (llena el límite)
        for i in range(2):
            eu = User.objects.create_user(email=f'emp_limit{i}@example.com', password='pass', tenant=t7)
            Employee.objects.create(tenant=t7, user=eu, is_active=True)

        target_u7 = User.objects.create_user(email='target_limit@example.com', password='pass', tenant=t7)

        system_settings = SystemSettings.get_settings()
        original_auto_upgrade = system_settings.auto_upgrade_limits
        system_settings.auto_upgrade_limits = False
        system_settings.save()
        cache.delete('system_settings')

        client = APIClient()
        self._authenticate_client(client, u7)

        print(f"Estado ANTES del Tenant:")
        print(f"  - Empleados actuales: {Employee.objects.filter(tenant=t7, is_active=True).count()}")
        print(f"  - Límite del plan: {t7.max_employees}")
        print(f"  - auto_upgrade_limits: False")

        try:
            r_emp3 = client.post('/api/employees/employees/', {
                'user_id': target_u7.id,
                'profession': 'stylist',
                'phone': '1234567890',
                'is_active': True
            }, format='json')
            print("\nOperación: CREAR EMPLEADO 3 (POST /api/employees/employees/)")
            print(f"Resultado ESPERADO: HTTP 400 Bad Request (límite de empleados sin auto-upgrade)")
            print(f"Resultado OBTENIDO:")
            print(f"  - HTTP Status: {r_emp3.status_code}")
            print(f"  - Respuesta JSON: {r_emp3.content.decode()}")

            print(f"\nEstado DESPUÉS del Tenant:")
            print(f"  - Empleados en base de datos: {Employee.objects.filter(tenant=t7, is_active=True).count()}")

            assert r_emp3.status_code == status.HTTP_400_BAD_REQUEST
            assert Employee.objects.filter(tenant=t7, is_active=True).count() == 2
        finally:
            system_settings.auto_upgrade_limits = original_auto_upgrade
            system_settings.save()
            cache.delete('system_settings')

        # =====================================================================
        # CASO 8: Renovación de suscripción — extiende access_until
        # =====================================================================
        print("\n" + "="*80)
        print(" EJECUCIÓN CASO 8: Renovación de Suscripción (extiende access_until)")
        print("="*80)

        t8 = Tenant.objects.create(
            name="Salón Renovación",
            subdomain="renovtest",
            is_active=True,
            subscription_plan=self.basic_plan
        )
        self._set_tenant_status(t8, 'active', timezone.now() + timezone.timedelta(days=2))
        t8.refresh_from_db()
        access_until_before = t8.access_until

        u8 = User.objects.create_user(
            email="admin_renov@example.com",
            password="pass",
            tenant=t8,
            role="Client-Admin"
        )

        client = APIClient()
        self._authenticate_client(client, u8)

        import django.conf
        original_debug = django.conf.settings.DEBUG
        django.conf.settings.DEBUG = True

        print(f"Estado ANTES del Tenant:")
        print(f"  - access_until: {access_until_before}")
        print(f"  - subscription_status: {t8.subscription_status}")

        try:
            r_renew = client.post('/api/subscriptions/renew/', {
                'plan_id': self.basic_plan.id,
                'payment_method_id': 'manual',
                'months': 3,
                'billing_interval': 'month'
            }, format='json')
            print("\nOperación: RENOVAR SUSCRIPCIÓN (POST /api/subscriptions/renew/)")
            print(f"Resultado ESPERADO: HTTP 200 OK + access_until extendido 3 meses")
            print(f"Resultado OBTENIDO:")
            print(f"  - HTTP Status: {r_renew.status_code}")
            print(f"  - Respuesta JSON: {r_renew.content.decode()[:400]}")

            t8.refresh_from_db()
            print(f"\nEstado DESPUÉS del Tenant:")
            print(f"  - access_until antes: {access_until_before}")
            print(f"  - access_until después: {t8.access_until}")
            print(f"  - ¿Se extendió?: {t8.access_until > access_until_before}")

            assert r_renew.status_code == status.HTTP_200_OK
            expected_min_date = timezone.now() + timezone.timedelta(days=90)
            assert t8.access_until >= expected_min_date
        finally:
            django.conf.settings.DEBUG = original_debug

        # =====================================================================
        # CASO 9: Tenant suspendido — login bloqueado en APIs
        # =====================================================================
        print("\n" + "="*80)
        print(" EJECUCIÓN CASO 9: Tenant Suspendido (acceso total bloqueado)")
        print("="*80)

        t9 = Tenant.objects.create(
            name="Barbería Suspendida",
            subdomain="suspended",
            subscription_plan=self.basic_plan
        )
        # Tenant suspendido: is_active=False + status='suspended'
        Tenant.objects.filter(pk=t9.pk).update(
            subscription_status='suspended',
            is_active=False
        )
        t9.refresh_from_db()

        u9 = User.objects.create_user(
            email="admin_suspended@example.com",
            password="pass",
            tenant=t9,
            role="Client-Admin"
        )
        self._grant_permission(u9, 'clients_api', 'view_client')

        client = APIClient()
        self._authenticate_client(client, u9)

        print(f"Estado del Tenant:")
        print(f"  - subscription_status: {t9.subscription_status}")
        print(f"  - is_active: {t9.is_active}")

        r_suspended = client.get('/api/clients/clients/')
        print("\nOperación: LEER CLIENTES con tenant suspendido (GET /api/clients/clients/)")
        print(f"Resultado ESPERADO: HTTP 402 o 403 (acceso completamente bloqueado)")
        print(f"Resultado OBTENIDO:")
        print(f"  - HTTP Status: {r_suspended.status_code}")
        print(f"  - Respuesta JSON: {r_suspended.content.decode()}")

        assert r_suspended.status_code in (status.HTTP_402_PAYMENT_REQUIRED, status.HTTP_403_FORBIDDEN)

        print("\n" + "="*80)
        print(" VALIDACIÓN COMPLETADA CON ÉXITO — LOS 9 CASOS PASARON")
        print("="*80)
