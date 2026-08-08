import pytest
from decimal import Decimal
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from django.core.cache import cache
from apps.auth_api.models import User
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan, UserSubscription, Subscription
from apps.auth_api.factories import UserFactory
from apps.settings_api.models import SystemSettings, Branch
from apps.employees_api.models import Employee
from apps.services_api.models import Service, ServiceEmployee
from apps.clients_api.models import Client as AppClient
from apps.appointments_api.models import Appointment

@pytest.mark.django_db
class TestMonetizationValidation:

    def setup_method(self):
        # Limpiar caché de configuraciones al inicio del test para evitar interferencias
        cache.delete('system_settings')
        
        # Asegurarse de que exista el owner superadmin por defecto en la suite de pruebas
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_user(
                email='test-tenant-owner@example.com',
                password='pass',
                is_superuser=True
            )
        # Configurar un plan básico por defecto en base de datos para pruebas
        self.basic_plan, _ = SubscriptionPlan.objects.get_or_create(
            name='basic',
            defaults={
                'price': Decimal('29.99'),
                'annual_price': Decimal('299.99'),
                'is_active': True,
                'is_public': True,
                'max_employees': 2,
                'max_users': 5,
                'allows_multiple_branches': False,
                'features': {'appointments': True, 'pos': True, 'client_history': True}
            }
        )
        self.pro_plan, _ = SubscriptionPlan.objects.get_or_create(
            name='standard',
            defaults={
                'price': Decimal('49.99'),
                'annual_price': Decimal('499.99'),
                'is_active': True,
                'is_public': True,
                'max_employees': 15,
                'max_users': 15,
                'allows_multiple_branches': True,
                'features': {'appointments': True, 'pos': True, 'client_history': True, 'inventory': True}
            }
        )

    def _grant_permission(self, user, app_label, codename):
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from apps.roles_api.models import Role, UserRole
        
        model_name = codename.split('_', 1)[1] if '_' in codename else 'generic'
        content_type, _ = ContentType.objects.get_or_create(app_label=app_label, model=model_name)
        perm, _ = Permission.objects.get_or_create(
            codename=codename,
            content_type=content_type,
            defaults={'name': f'Can {codename.replace("_", " ")}'}
        )
        
        role, _ = Role.objects.get_or_create(name=f'Role-{app_label}-{codename}')
        role.permissions.add(perm)
        
        UserRole.objects.get_or_create(
            user=user,
            role=role,
            tenant=user.tenant
        )

    def _authenticate_client(self, client, user):
        from rest_framework_simplejwt.tokens import AccessToken
        token = AccessToken.for_user(user)
        if user.tenant:
            token['tenant_id'] = user.tenant.id
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_1_past_due_access(self):
        """
        Escenario 1: Mora (past_due)
        Verificar si un tenant en estado past_due puede seguir consumiendo endpoints
        de escritura/creación en el backend (ej: Citas o Clientes).
        """
        user = UserFactory(role='Client-Admin')
        tenant = user.tenant
        tenant.subscription_plan = self.basic_plan
        tenant.subscription_status = 'past_due'
        tenant.is_active = True
        tenant.access_until = timezone.now() - timezone.timedelta(days=1)
        tenant.save()

        UserSubscription.objects.create(
            user=user,
            plan=self.basic_plan,
            start_date=timezone.now() - timezone.timedelta(days=30),
            end_date=timezone.now() - timezone.timedelta(days=1),
            is_active=True
        )

        self._grant_permission(user, 'clients_api', 'add_client')

        client = APIClient()
        self._authenticate_client(client, user)

        client_data = {
            'full_name': 'Cliente Test Past Due',
            'email': 'pastdue_client@example.com',
            'phone': '1234567890'
        }
        response = client.post('/api/clients/clients/', client_data, format='json')
        
        print(f"\n[TEST_PAST_DUE] HTTP Response: {response.status_code}")
        print(f"[TEST_PAST_DUE] Content: {response.content}")
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED, response.content

    def test_2_expired_trial_blocked(self):
        """
        Escenario 2: Trial Expirado
        Verificar que un tenant con trial expirado es bloqueado con HTTP 402 por el middleware.
        """
        user = UserFactory(role='Client-Admin')
        tenant = user.tenant
        tenant.subscription_plan = self.basic_plan
        tenant.subscription_status = 'trial'
        tenant.trial_end_date = (timezone.now() - timezone.timedelta(days=5)).date()
        tenant.save()

        client = APIClient()
        self._authenticate_client(client, user)

        response = client.get('/api/clients/clients/')
        print(f"\n[TEST_EXPIRED_TRIAL] HTTP Response: {response.status_code}")
        print(f"[TEST_EXPIRED_TRIAL] Content: {response.content}")
        
        assert response.status_code in (status.HTTP_402_PAYMENT_REQUIRED, status.HTTP_403_FORBIDDEN), response.content

    def test_3_employee_limit_enforced(self):
        """
        Escenario 3: Límite de Empleados
        Verificar que el límite max_employees se impone al crear empleados vía API.
        """
        user = UserFactory(role='Client-Admin')
        tenant = user.tenant
        tenant.subscription_plan = self.basic_plan
        tenant.max_employees = 2
        tenant.subscription_status = 'active'
        tenant.save()

        UserSubscription.objects.create(
            user=user,
            plan=self.basic_plan,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=30),
            is_active=True
        )

        from django.contrib.auth import get_user_model
        User_Model = get_user_model()
        
        for i in range(2):
            emp_user = User_Model.objects.create_user(
                email=f'emp{i}@example.com',
                password='pass',
                tenant=tenant
            )
            Employee.objects.create(
                tenant=tenant,
                user=emp_user,
                is_active=True
            )

        # Crear un usuario válido que asociaremos al nuevo empleado que excederá el límite
        target_user = User_Model.objects.create_user(
            email='new_emp@example.com',
            password='pass',
            tenant=tenant
        )

        self._grant_permission(user, 'employees_api', 'add_employee')

        client = APIClient()
        self._authenticate_client(client, user)

        emp_data = {
            'user_id': target_user.id,
            'profession': 'stylist',
            'phone': '1234567890',
            'is_active': True
        }
        
        system_settings = SystemSettings.get_settings()
        original_auto_upgrade = system_settings.auto_upgrade_limits
        system_settings.auto_upgrade_limits = False
        system_settings.save()
        cache.delete('system_settings')

        try:
            response = client.post('/api/employees/employees/', emp_data, format='json')
            print(f"\n[TEST_EMPLOYEE_LIMIT] HTTP Response: {response.status_code}")
            print(f"[TEST_EMPLOYEE_LIMIT] Content: {response.content}")
            assert response.status_code == status.HTTP_400_BAD_REQUEST, response.content
        finally:
            system_settings.auto_upgrade_limits = original_auto_upgrade
            system_settings.save()
            cache.delete('system_settings')

    def test_4_client_limit_enforced(self):
        """
        Escenario 4: Límite de Clientes
        Verificar si el límite max_clients del plan se impone en el backend.
        """
        user = UserFactory(role='Client-Admin')
        tenant = user.tenant
        tenant.subscription_plan = self.basic_plan
        tenant.subscription_status = 'active'
        tenant.save()

        clients_to_create = []
        for i in range(50):
            clients_to_create.append(
                AppClient(
                    tenant=tenant,
                    full_name=f'Cliente {i}',
                    email=f'client{i}@example.com',
                    created_by=user
                )
            )
        AppClient.objects.bulk_create(clients_to_create)

        self._grant_permission(user, 'clients_api', 'add_client')

        client = APIClient()
        self._authenticate_client(client, user)

        client_data = {
            'full_name': 'Cliente Excedido',
            'email': 'exceeded@example.com',
            'phone': '1122334455'
        }
        response = client.post('/api/clients/clients/', client_data, format='json')
        print(f"\n[TEST_CLIENT_LIMIT] HTTP Response: {response.status_code}")
        print(f"[TEST_CLIENT_LIMIT] Content: {response.content}")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.content

    def test_5_appointment_limit_enforced(self):
        """
        Escenario 5: Límite de Citas
        Verificar si el límite max_appointments del plan se impone en el backend.
        """
        user = UserFactory(role='Client-Admin')
        tenant = user.tenant
        tenant.subscription_plan = self.basic_plan
        tenant.subscription_status = 'active'
        tenant.save()

        from apps.employees_api.models import Employee as EmpModel
        from django.contrib.auth import get_user_model
        User_Model = get_user_model()
        
        emp_user = User_Model.objects.create_user(email='stylist1@example.com', password='pass', tenant=tenant)
        employee = EmpModel.objects.create(tenant=tenant, user=emp_user, is_active=True)
        
        service = Service.objects.create(tenant=tenant, name='Corte Test', price=Decimal('20.00'), is_active=True)
        db_client = AppClient.objects.create(tenant=tenant, full_name='Cliente Test Citas', created_by=user)
        
        ServiceEmployee.objects.create(employee=employee, service=service)

        appointments_to_create = []
        for i in range(100):
            appointments_to_create.append(
                Appointment(
                    tenant=tenant,
                    client=db_client,
                    stylist=emp_user,
                    service=service,
                    date_time=timezone.now() - timezone.timedelta(minutes=i*5),
                    status='scheduled'
                )
            )
        Appointment.objects.bulk_create(appointments_to_create)

        self._grant_permission(user, 'appointments_api', 'add_appointment')

        client = APIClient()
        self._authenticate_client(client, user)

        # Usamos una fecha de mañana en date_time para que no sea rechazada por estar en el pasado
        future_date_time = timezone.now() + timezone.timedelta(days=1)

        appointment_data = {
            'client': db_client.id,
            'stylist': emp_user.id,
            'service': service.id,
            'date_time': future_date_time.isoformat(),
            'status': 'scheduled'
        }
        
        response = client.post('/api/appointments/appointments/', appointment_data, format='json')
        print(f"\n[TEST_APPOINTMENT_LIMIT] HTTP Response: {response.status_code}")
        print(f"[TEST_APPOINTMENT_LIMIT] Content: {response.content}")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.content

    def test_6_auto_upgrade_logic(self):
        """
        Escenario 6: Auto-Upgrade de Plan
        Verificar que cuando auto_upgrade_limits está activo, al superar el límite de empleados,
        el plan del tenant se actualiza localmente en base de datos al realizar el cargo en Stripe.
        """
        user = UserFactory(role='Client-Admin')
        tenant = user.tenant
        tenant.subscription_plan = self.basic_plan
        tenant.max_employees = 2
        tenant.subscription_status = 'active'
        tenant.save()

        # Configurar los IDs de precios de Stripe en los planes de test
        self.basic_plan.stripe_price_id = 'price_basic_123'
        self.basic_plan.save()
        self.pro_plan.stripe_price_id = 'price_pro_123'
        self.pro_plan.save()

        UserSubscription.objects.create(
            user=user,
            plan=self.basic_plan,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=30),
            is_active=True
        )

        # Crear la suscripción del tenant con Stripe ID
        Subscription.objects.create(
            tenant=tenant,
            plan=self.basic_plan,
            stripe_subscription_id='sub_test_stripe_123',
            is_active=True,
            billing_interval='month'
        )

        from django.contrib.auth import get_user_model
        User_Model = get_user_model()
        for i in range(2):
            emp_user = User_Model.objects.create_user(email=f'emp_auto{i}@example.com', password='pass', tenant=tenant)
            Employee.objects.create(tenant=tenant, user=emp_user, is_active=True)

        # Crear el nuevo usuario al que asignaremos el empleado para disparar el upgrade
        target_user = User_Model.objects.create_user(
            email='new_emp_auto@example.com',
            password='pass',
            tenant=tenant
        )

        self._grant_permission(user, 'employees_api', 'add_employee')

        system_settings = SystemSettings.get_settings()
        original_auto_upgrade = system_settings.auto_upgrade_limits
        system_settings.auto_upgrade_limits = True
        system_settings.save()
        cache.delete('system_settings')

        client = APIClient()
        self._authenticate_client(client, user)

        emp_data = {
            'user_id': target_user.id,
            'profession': 'stylist',
            'phone': '1234567890',
            'is_active': True
        }

        # Mockear las llamadas a Stripe
        import unittest.mock
        mock_retrieve_response = {
            'items': {
                'data': [{'id': 'si_test_123'}]
            }
        }
        with unittest.mock.patch('stripe.Subscription.retrieve', return_value=mock_retrieve_response) as mock_retrieve, \
             unittest.mock.patch('stripe.Subscription.modify') as mock_modify:
            try:
                response = client.post('/api/employees/employees/', emp_data, format='json')
                print(f"\n[TEST_AUTO_UPGRADE] HTTP Response: {response.status_code}")
                print(f"[TEST_AUTO_UPGRADE] Content: {response.content}")
                
                assert response.status_code == status.HTTP_201_CREATED, response.content
                
                tenant.refresh_from_db()
                print(f"[TEST_AUTO_UPGRADE] New Plan in DB: {tenant.subscription_plan.name}")
                assert tenant.subscription_plan == self.pro_plan
                
                # Verificar que se llamó a Stripe con el precio correcto y prorrateo
                mock_retrieve.assert_called_once_with('sub_test_stripe_123')
                mock_modify.assert_called_once_with(
                    'sub_test_stripe_123',
                    proration_behavior='always_invoice',
                    items=[{'id': 'si_test_123', 'price': 'price_pro_123'}]
                )
            finally:
                system_settings.auto_upgrade_limits = original_auto_upgrade
                system_settings.save()
                cache.delete('system_settings')

    def test_7_subscription_cancellation(self):
        """
        Escenario 7: Cancelación de Suscripción
        Verificar que al cancelar una suscripción activa, se mantenga el acceso hasta end_date
        y que cancelled_at quede registrado.
        """
        user = UserFactory(role='Client-Admin')
        tenant = user.tenant
        tenant.subscription_plan = self.basic_plan
        tenant.subscription_status = 'active'
        tenant.save()

        sub = UserSubscription.objects.create(
            user=user,
            plan=self.basic_plan,
            start_date=timezone.now() - timezone.timedelta(days=1),
            end_date=timezone.now() + timezone.timedelta(days=29),
            is_active=True
        )

        self._grant_permission(user, 'subscriptions_api', 'change_usersubscription')

        client = APIClient()
        self._authenticate_client(client, user)

        # Mockear send_cancellation_confirmation_email para evitar hilos de fondo en SQLite
        import unittest.mock
        with unittest.mock.patch('apps.subscriptions_api.tasks.send_cancellation_confirmation_email') as mock_email:
            response = client.post(f'/api/subscriptions/user-subscriptions/{sub.id}/cancel/')
            print(f"\n[TEST_CANCELLATION] HTTP Response: {response.status_code}")
            print(f"[TEST_CANCELLATION] Content: {response.content}")

        assert response.status_code == status.HTTP_200_OK, response.content
        
        sub.refresh_from_db()
        assert sub.cancelled_at is not None
        assert sub.is_active is True
        
        tenant.refresh_from_db()
        from apps.tenants_api.subscription_lifecycle import sync_subscription_state
        sync_subscription_state(tenant, save=True)
        assert tenant.subscription_status == 'active'

    def test_8_subscription_renewal(self):
        """
        Escenario 8: Renovación de Suscripción
        Verificar que la renovación manual extiende access_until.
        """
        user = UserFactory(role='Client-Admin')
        tenant = user.tenant
        tenant.subscription_plan = self.basic_plan
        tenant.subscription_status = 'active'
        tenant.access_until = timezone.now() + timezone.timedelta(days=2)
        tenant.save()

        import django.conf
        original_debug = django.conf.settings.DEBUG
        django.conf.settings.DEBUG = True

        client = APIClient()
        self._authenticate_client(client, user)

        renewal_data = {
            'plan_id': self.basic_plan.id,
            'payment_method_id': 'manual',
            'months': 3,
            'billing_interval': 'month'
        }

        try:
            response = client.post('/api/subscriptions/renew/', renewal_data, format='json')
            print(f"\n[TEST_RENEWAL] HTTP Response: {response.status_code}")
            print(f"[TEST_RENEWAL] Content: {response.content}")

            assert response.status_code == status.HTTP_200_OK, response.content
            tenant.refresh_from_db()
            
            expected_min_date = timezone.now() + timezone.timedelta(days=90)
            print(f"[TEST_RENEWAL] New access_until: {tenant.access_until}")
            assert tenant.access_until >= expected_min_date
        finally:
            django.conf.settings.DEBUG = original_debug

    def test_9_login_suspended_tenant(self):
        """
        Escenario 9: Login con Tenant Suspendido
        Verificar que un usuario de un tenant suspendido no puede consumir APIs protegidas.
        """
        user = UserFactory(role='Client-Admin')
        tenant = user.tenant
        tenant.subscription_plan = self.basic_plan
        tenant.subscription_status = 'suspended'
        tenant.is_active = False
        tenant.save()

        client = APIClient()
        self._authenticate_client(client, user)

        response = client.get('/api/clients/clients/')
        print(f"\n[TEST_LOGIN_SUSPENDED] HTTP Response: {response.status_code}")
        print(f"[TEST_LOGIN_SUSPENDED] Content: {response.content}")

        assert response.status_code in (status.HTTP_402_PAYMENT_REQUIRED, status.HTTP_403_FORBIDDEN), response.content
