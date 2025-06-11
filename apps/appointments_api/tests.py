from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from django.utils import timezone
from apps.clients_api.models import Client
from apps.roles_api.models import Role
from apps.auth_api.models import User
from datetime import timedelta
from .models import Appointment

class AppointmentTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='testuser@example.com',
            full_name='Test User',
            password='testpass'
        )
        self.stylist_role = Role.objects.create(name='stylist')
        self.stylist_user = User.objects.create_user(
            email='stylist@example.com',
            full_name='Stylist User',
            password='stylistpass'
        )
        self.stylist_user.roles.add(self.stylist_role)
        self.stylist_user.save()
        self.client_obj = Client.objects.create(
            user=self.user,
            full_name='Test Client',
            created_by=self.user
        )
        self.other_role = Role.objects.create(name='admin')
        self.client.force_authenticate(user=self.user)

    def test_create_appointment(self):
        url = reverse('appointment-list')
        data = {
            'client': self.client_obj.id,
            'stylist': self.stylist_role.id,
            'role': self.other_role.id,
            'date_time': (timezone.now() + timedelta(days=1)).isoformat(),
            'status': 'scheduled',
            'description': 'Test appointment'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'scheduled')
        self.assertEqual(response.data['description'], 'Test appointment')
        # Limpiar citas creadas
        Appointment.objects.all().delete()

    def test_list_appointments(self):
        url = reverse('appointment-list')
        # Limpiar citas existentes
        Appointment.objects.all().delete()
        # Crear una cita directamente
        appointment = Appointment.objects.create(
            client=self.client_obj,
            stylist=self.stylist_role,
            role=self.other_role,
            date_time=timezone.now() + timedelta(days=1),
            status='scheduled',
            description='Test appointment'
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Manejar paginación
        data = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(data), 1)