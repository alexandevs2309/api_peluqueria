import pytest
from django.utils import timezone
from datetime import timedelta
from apps.auth_api.factories import UserFactory
from apps.notifications_api.models import (
    Notification, NotificationTemplate, NotificationPreference,
    NotificationLog, InAppNotification
)
from apps.notifications_api.services import NotificationService


@pytest.fixture
def email_template():
    return NotificationTemplate.objects.create(
        name='test_email',
        type='email',
        notification_type='appointment_reminder',
        subject='Recordatorio: {{appointment_date}}',
        body='Hola {{user_name}}, tienes una cita el {{appointment_date}}.',
        is_active=True
    )


@pytest.fixture
def sms_template():
    return NotificationTemplate.objects.create(
        name='test_sms',
        type='sms',
        notification_type='appointment_reminder',
        subject='',
        body='Recordatorio: cita el {{appointment_date}}',
        is_active=True
    )


@pytest.fixture
def push_template():
    return NotificationTemplate.objects.create(
        name='test_push',
        type='push',
        notification_type='appointment_reminder',
        subject='',
        body='Nueva notificación push',
        is_active=True
    )


@pytest.mark.django_db
class TestNotificationTemplateModel:
    def test_create_template(self):
        tmpl = NotificationTemplate.objects.create(
            name='welcome_email',
            type='email',
            notification_type='welcome',
            subject='Bienvenido',
            body='Hola, bienvenido!'
        )
        assert tmpl.is_active is True
        assert str(tmpl) == 'Email - welcome_email'
        assert tmpl.available_variables == {}

    def test_template_str_with_type(self):
        tmpl = NotificationTemplate.objects.create(
            name='sms_alert', type='sms', notification_type='stock_alert',
            body='Stock bajo'
        )
        assert 'SMS' in str(tmpl)

    def test_template_ordering(self):
        NotificationTemplate.objects.create(
            name='a', type='email', notification_type='welcome',
            body='test'
        )
        NotificationTemplate.objects.create(
            name='b', type='sms', notification_type='stock_alert',
            body='test'
        )
        qs = NotificationTemplate.objects.all()
        assert qs.count() == 2


@pytest.mark.django_db
class TestNotificationModel:
    def test_create_notification(self, email_template):
        user = UserFactory()
        notif = Notification.objects.create(
            recipient=user,
            template=email_template,
            subject='Recordatorio: 2024-01-15',
            message='Hola Juan, tienes una cita el 2024-01-15.',
            status='pending'
        )
        assert notif.id is not None
        assert notif.status == 'pending'
        assert str(notif) == f"{user.email} - {email_template.name} (pending)"

    def test_notification_default_priority(self, email_template):
        user = UserFactory()
        notif = Notification.objects.create(
            recipient=user, template=email_template,
            subject='Test', message='Test'
        )
        assert notif.priority == 'normal'

    def test_notification_send_method(self, email_template):
        user = UserFactory()
        notif = Notification.objects.create(
            recipient=user, template=email_template,
            subject='Test', message='Test'
        )
        result = notif.send()
        assert result is True
        notif.refresh_from_db()
        assert notif.status in ['sent', 'failed']


@pytest.mark.django_db
class TestNotificationPreferenceModel:
    def test_create_preferences(self):
        user = UserFactory()
        prefs = NotificationPreference.objects.create(user=user)
        assert prefs.email_enabled is True
        assert prefs.sms_enabled is False
        assert prefs.push_enabled is True
        assert str(prefs) == f"Preferencias de {user.email}"

    def test_one_to_one_user(self):
        user = UserFactory()
        NotificationPreference.objects.create(user=user)
        with pytest.raises(Exception):
            NotificationPreference.objects.create(user=user)


@pytest.mark.django_db
class TestNotificationLogModel:
    def test_create_log(self, email_template):
        user = UserFactory()
        notif = Notification.objects.create(
            recipient=user, template=email_template,
            subject='Test', message='Test'
        )
        log = NotificationLog.objects.create(
            notification=notif,
            channel='email',
            provider='sendgrid',
            status='sent'
        )
        assert log.id is not None
        assert log.status == 'sent'
        assert str(log) == f"{notif} - email (sent)"


@pytest.mark.django_db
class TestInAppNotificationModel:
    def test_create_in_app(self):
        user = UserFactory()
        note = InAppNotification.objects.create(
            recipient=user,
            type='system',
            title='Bienvenido',
            message='Gracias por registrarte'
        )
        assert note.is_read is False
        assert str(note) == f"{user.email} - Bienvenido"

    def test_mark_as_read(self):
        user = UserFactory()
        note = InAppNotification.objects.create(
            recipient=user, type='appointment',
            title='Cita', message='Tienes una cita'
        )
        note.is_read = True
        note.save()
        note.refresh_from_db()
        assert note.is_read is True


@pytest.mark.django_db
class TestNotificationService:
    def test_create_notification(self, email_template):
        service = NotificationService()
        user = UserFactory()
        notif = service.create_notification(
            recipient=user,
            template=email_template,
            context_data={'user_name': 'Juan', 'appointment_date': '2024-01-15'},
            priority='high'
        )
        assert notif.id is not None
        assert notif.priority == 'high'
        assert notif.sent_at is not None

    def test_create_scheduled_notification(self, email_template):
        service = NotificationService()
        user = UserFactory()
        notif = service.create_notification(
            recipient=user,
            template=email_template,
            scheduled_at=timezone.now() + timedelta(hours=1)
        )
        assert notif.scheduled_at is not None
        assert notif.status == 'pending'

    def test_send_notification_success(self, email_template):
        service = NotificationService()
        user = UserFactory()
        notif = Notification.objects.create(
            recipient=user, template=email_template,
            subject='Test', message='Test', status='pending'
        )
        result = service.send_notification(notif)
        notif.refresh_from_db()
        assert result is True
        assert notif.status == 'sent'
        assert notif.sent_at is not None

    def test_send_sms_notification(self, sms_template):
        service = NotificationService()
        user = UserFactory()
        NotificationPreference.objects.update_or_create(
            user=user, defaults={'sms_enabled': True}
        )
        notif = Notification.objects.create(
            recipient=user, template=sms_template,
            subject='', message='Recordatorio SMS', status='pending'
        )
        result = service.send_notification(notif)
        assert result is True
        assert NotificationLog.objects.filter(notification=notif, channel='sms').exists()

    def test_send_push_notification(self, push_template):
        service = NotificationService()
        user = UserFactory()
        notif = Notification.objects.create(
            recipient=user, template=push_template,
            subject='', message='Push test', status='pending'
        )
        result = service.send_notification(notif)
        assert result is True
        assert NotificationLog.objects.filter(notification=notif, channel='push').exists()

    def test_send_notification_fails_without_preferences(self, email_template):
        service = NotificationService()
        user = UserFactory()
        prefs = NotificationPreference.objects.create(
            user=user, email_enabled=False, sms_enabled=False, push_enabled=False
        )
        notif = Notification.objects.create(
            recipient=user, template=email_template,
            subject='Test', message='Test', status='pending'
        )
        result = service.send_notification(notif)
        assert result is False
        notif.refresh_from_db()
        assert notif.status == 'failed'

    def test_render_template(self, email_template):
        service = NotificationService()
        result = service._render_template(
            'Hola {{user_name}}, tu cita es el {{appointment_date}}',
            {'user_name': 'Juan', 'appointment_date': '2024-01-15'}
        )
        assert result == 'Hola Juan, tu cita es el 2024-01-15'

    def test_get_user_preferences_creates_defaults(self):
        service = NotificationService()
        user = UserFactory()
        prefs = service._get_user_preferences(user)
        assert prefs.email_enabled is True
        assert prefs.sms_enabled is False
        assert prefs.push_enabled is True

    def test_get_user_preferences_existing(self):
        service = NotificationService()
        user = UserFactory()
        NotificationPreference.objects.create(user=user, email_enabled=False)
        prefs = service._get_user_preferences(user)
        assert prefs.email_enabled is False

    def test_notification_stats(self, email_template):
        service = NotificationService()
        user = UserFactory()
        for i in range(3):
            Notification.objects.create(
                recipient=user, template=email_template,
                subject=f'Test {i}', message='Test',
                status='sent', sent_at=timezone.now()
            )
        Notification.objects.create(
            recipient=user, template=email_template,
            subject='Failed', message='Test',
            status='failed'
        )
        stats = service.get_notification_stats(user)
        assert stats['total'] == 4
        assert stats['sent'] == 3
        assert stats['failed'] == 1

    def test_send_bulk_notifications(self, email_template):
        service = NotificationService()
        user = UserFactory()
        notifications = [
            Notification.objects.create(
                recipient=user, template=email_template,
                subject=f'Bulk {i}', message='Test', status='pending'
            )
            for i in range(5)
        ]
        results = service.send_bulk_notifications(notifications)
        assert len(results) == 5
        assert all(results)

    def test_generate_ics_content(self):
        from apps.appointments_api.models import Appointment
        from apps.services_api.models import Service
        from apps.auth_api.factories import UserFactory
        from apps.clients_api.models import Client
        
        service = NotificationService()
        user = UserFactory()
        stylist = UserFactory()
        client_user = UserFactory()
        
        client = Client.objects.create(
            full_name="Pedro Gomez",
            email=client_user.email,
            tenant=user.tenant
        )
        
        apt_service = Service.objects.create(
            name="Corte Premium",
            price=500.0,
            duration=45,
            tenant=user.tenant
        )
        
        appointment = Appointment.objects.create(
            client=client,
            stylist=stylist,
            service=apt_service,
            date_time=timezone.now() + timedelta(days=1),
            tenant=user.tenant
        )
        
        ics_content = service.generate_ics_content(
            appointment,
            stylist_name="Juan Perez",
            service_name="Corte Premium",
            client_name="Pedro Gomez"
        )
        
        assert "BEGIN:VCALENDAR" in ics_content
        assert "BEGIN:VEVENT" in ics_content
        assert "SUMMARY:Cita: Corte Premium con Juan Perez" in ics_content
        assert "STATUS:CONFIRMED" in ics_content
        assert "END:VEVENT" in ics_content

