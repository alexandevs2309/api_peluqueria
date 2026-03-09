"""
Tests de seguridad IDOR (Insecure Direct Object Reference).
Valida que usuarios de un tenant no puedan acceder a recursos de otro tenant.
"""
from datetime import timedelta
from decimal import Decimal
import uuid

from django.contrib.auth.models import Permission
from django.test import RequestFactory, TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.appointments_api.models import Appointment
from apps.auth_api.models import User
from apps.clients_api.models import Client
from apps.employees_api.models import Employee
from apps.pos_api.models import Sale
from apps.roles_api.models import Role, UserRole
from apps.subscriptions_api.models import SubscriptionPlan
from apps.tenants_api.models import Tenant


class IDORSecurityTests(TestCase):
    """Tests de seguridad cross-tenant."""

    @staticmethod
    def _make_plan(name: str, price: str = "29.99") -> SubscriptionPlan:
        return SubscriptionPlan.objects.create(
            name=name,
            description=f"Plan {name}",
            price=price,
            duration_month=1,
            is_active=True,
            max_employees=50,
            max_users=100,
            features={},
        )

    @staticmethod
    def _grant_tenant_permissions(user: User, tenant: Tenant) -> None:
        role = Role.objects.create(
            name=f"SecurityRole-{uuid.uuid4().hex[:8]}",
            description="Role para tests de seguridad",
            scope="TENANT",
        )
        required_permissions = [
            ("employees_api", "view_employee"),
            ("employees_api", "change_employee"),
            ("employees_api", "delete_employee"),
            ("clients_api", "view_client"),
            ("appointments_api", "view_appointment"),
            ("pos_api", "view_sale"),
        ]
        for app_label, codename in required_permissions:
            permission = Permission.objects.filter(
                content_type__app_label=app_label,
                codename=codename,
            ).first()
            if permission:
                role.permissions.add(permission)

        UserRole.objects.create(user=user, role=role, tenant=tenant)

    @staticmethod
    def _client_with_token(user: User) -> APIClient:
        client = APIClient()
        token = AccessToken.for_user(user)
        if user.tenant_id:
            token["tenant_id"] = user.tenant_id
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")
        return client

    def setUp(self):
        """Setup: crear 2 tenants con usuarios y datos."""
        self.plan_premium = self._make_plan("premium", "99.99")
        self.plan_basic = self._make_plan("basic", "29.99")

        self.owner_a = User.objects.create_superuser(
            email="owner-a@system.com",
            password="test123",
            full_name="Owner A",
        )
        self.owner_b = User.objects.create_superuser(
            email="owner-b@system.com",
            password="test123",
            full_name="Owner B",
        )

        self.tenant_a = Tenant.objects.create(
            name="Barberia A",
            subdomain="tenant-a",
            owner=self.owner_a,
            subscription_plan=self.plan_premium,
            subscription_status="active",
            is_active=True,
        )
        self.tenant_b = Tenant.objects.create(
            name="Barberia B",
            subdomain="tenant-b",
            owner=self.owner_b,
            subscription_plan=self.plan_basic,
            subscription_status="active",
            is_active=True,
        )

        self.user_a = User.objects.create_user(
            email="admin@tenant-a.com",
            password="test123",
            full_name="Admin A",
            tenant=self.tenant_a,
            role="Client-Admin",
            is_staff=True,
        )
        self.user_b = User.objects.create_user(
            email="admin@tenant-b.com",
            password="test123",
            full_name="Admin B",
            tenant=self.tenant_b,
            role="Client-Admin",
            is_staff=True,
        )

        self._grant_tenant_permissions(self.user_a, self.tenant_a)
        self._grant_tenant_permissions(self.user_b, self.tenant_b)

        self.employee_a, _ = Employee.objects.get_or_create(
            user=self.user_a,
            defaults={"tenant": self.tenant_a, "is_active": True},
        )
        self.employee_b, _ = Employee.objects.get_or_create(
            user=self.user_b,
            defaults={"tenant": self.tenant_b, "is_active": True},
        )

        self.client_a = Client.objects.create(
            user=self.user_a,
            tenant=self.tenant_a,
            full_name="Cliente A",
            email="cliente-a@tenant-a.com",
            created_by=self.user_a,
        )
        self.client_b = Client.objects.create(
            user=self.user_b,
            tenant=self.tenant_b,
            full_name="Cliente B",
            email="cliente-b@tenant-b.com",
            created_by=self.user_b,
        )

        self.appointment_b = Appointment.objects.create(
            tenant=self.tenant_b,
            client=self.client_b,
            stylist=self.user_b,
            date_time=timezone.now() + timedelta(days=1),
            status="scheduled",
        )
        self.sale_b = Sale.objects.create(
            tenant=self.tenant_b,
            user=self.user_b,
            employee=self.employee_b,
            client=self.client_b,
            total=Decimal("100.00"),
            paid=Decimal("100.00"),
            payment_method="cash",
        )

        self.api_client_a = self._client_with_token(self.user_a)

    def test_idor_employee_retrieve_cross_tenant(self):
        response = self.api_client_a.get(f"/api/employees/employees/{self.employee_b.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_idor_employee_update_cross_tenant(self):
        response = self.api_client_a.patch(
            f"/api/employees/employees/{self.employee_b.id}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.employee_b.refresh_from_db()
        self.assertTrue(self.employee_b.is_active)

    def test_idor_employee_delete_cross_tenant(self):
        response = self.api_client_a.delete(f"/api/employees/employees/{self.employee_b.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Employee.objects.filter(id=self.employee_b.id).exists())

    def test_idor_client_retrieve_cross_tenant(self):
        response = self.api_client_a.get(f"/api/clients/clients/{self.client_b.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_idor_client_list_isolation(self):
        response = self.api_client_a.get("/api/clients/clients/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data.get("results", response.data)
        client_ids = [client["id"] for client in payload]
        self.assertIn(self.client_a.id, client_ids)
        self.assertNotIn(self.client_b.id, client_ids)

    def test_idor_appointment_retrieve_cross_tenant(self):
        response = self.api_client_a.get(f"/api/appointments/appointments/{self.appointment_b.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_idor_sale_retrieve_cross_tenant(self):
        response = self.api_client_a.get(f"/api/pos/sales/{self.sale_b.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_idor_custom_action_cross_tenant(self):
        response = self.api_client_a.get(f"/api/employees/employees/{self.employee_b.id}/stats/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_superadmin_can_access_all_tenants(self):
        api_client = self._client_with_token(self.owner_a)
        response_a = api_client.get(f"/api/employees/employees/{self.employee_a.id}/")
        response_b = api_client.get(f"/api/employees/employees/{self.employee_b.id}/")
        self.assertEqual(response_a.status_code, status.HTTP_200_OK)
        self.assertEqual(response_b.status_code, status.HTTP_200_OK)

    def test_user_can_access_own_tenant_resources(self):
        response = self.api_client_a.get(f"/api/employees/employees/{self.employee_a.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.employee_a.id)


class AdminPanelSecurityTests(TestCase):
    """Tests de seguridad del Django Admin."""

    @staticmethod
    def _make_plan(name: str, price: str = "29.99") -> SubscriptionPlan:
        return SubscriptionPlan.objects.create(
            name=name,
            description=f"Plan {name}",
            price=price,
            duration_month=1,
            is_active=True,
            max_employees=50,
            max_users=100,
            features={},
        )

    def setUp(self):
        plan_standard = self._make_plan("standard", "49.99")
        plan_enterprise = self._make_plan("enterprise", "199.99")

        owner_a = User.objects.create_superuser(
            email="owner-admin-a@system.com",
            password="test123",
            full_name="Owner Admin A",
        )
        owner_b = User.objects.create_superuser(
            email="owner-admin-b@system.com",
            password="test123",
            full_name="Owner Admin B",
        )

        self.tenant_a = Tenant.objects.create(
            name="Tenant A Admin",
            subdomain="tenant-a-admin",
            owner=owner_a,
            subscription_plan=plan_standard,
            subscription_status="active",
            is_active=True,
        )
        self.tenant_b = Tenant.objects.create(
            name="Tenant B Admin",
            subdomain="tenant-b-admin",
            owner=owner_b,
            subscription_plan=plan_enterprise,
            subscription_status="active",
            is_active=True,
        )

        self.admin_a = User.objects.create_user(
            email="admin@tenant-a-admin.com",
            password="test123",
            full_name="Tenant Admin A",
            tenant=self.tenant_a,
            is_staff=True,
            role="Client-Admin",
        )

        self.employee_a, _ = Employee.objects.get_or_create(
            user=self.admin_a,
            defaults={"tenant": self.tenant_a},
        )
        other_user = User.objects.create_user(
            email="user@tenant-b-admin.com",
            password="test123",
            full_name="Tenant User B",
            tenant=self.tenant_b,
            role="Client-Staff",
        )
        self.employee_b, _ = Employee.objects.get_or_create(
            user=other_user,
            defaults={"tenant": self.tenant_b},
        )

    def test_admin_only_sees_own_tenant_employees(self):
        from django.contrib.admin.sites import AdminSite
        from apps.employees_api.admin import EmployeeAdmin

        request = RequestFactory().get("/admin/employees_api/employee/")
        request.user = self.admin_a

        admin_view = EmployeeAdmin(Employee, AdminSite())
        queryset = admin_view.get_queryset(request)

        self.assertIn(self.employee_a, queryset)
        self.assertNotIn(self.employee_b, queryset)
