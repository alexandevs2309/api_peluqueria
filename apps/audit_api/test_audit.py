import pytest
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from apps.auth_api.factories import UserFactory
from apps.audit_api.models import AuditLog
from apps.audit_api.utils import create_audit_log
from apps.audit_api.signals import _safe_instance_label


@pytest.fixture
def sample_user():
    return UserFactory()


@pytest.mark.django_db
class TestAuditLogModel:
    def test_create_audit_log(self, sample_user):
        log = AuditLog.objects.create(
            user=sample_user,
            action='LOGIN',
            description=f"Inicio de sesión: {sample_user.email}",
            source='AUTH',
            ip_address='127.0.0.1'
        )
        assert log.id is not None
        assert log.action == 'LOGIN'
        assert str(log) == f"{sample_user} - LOGIN - {log.timestamp}"

    def test_audit_log_all_actions(self, sample_user):
        for action, _ in AuditLog.ACTION_CHOICES:
            log = AuditLog.objects.create(
                user=sample_user, action=action,
                description=f"Test {action}", source='SYSTEM'
            )
            assert log.action == action

    def test_audit_log_all_sources(self, sample_user):
        for source, _ in AuditLog._meta.get_field('source').choices:
            log = AuditLog.objects.create(
                user=sample_user, action='SYSTEM_ERROR',
                description=f"Test {source}", source=source
            )
            assert log.source == source

    def test_audit_log_ordering(self, sample_user):
        log1 = AuditLog.objects.create(
            user=sample_user, action='LOGIN',
            description='First', source='AUTH',
            timestamp=timezone.now()
        )
        log2 = AuditLog.objects.create(
            user=sample_user, action='LOGOUT',
            description='Second', source='AUTH',
            timestamp=timezone.now()
        )
        qs = AuditLog.objects.all()
        assert qs[0] == log2
        assert qs[1] == log1

    def test_audit_log_with_content_object(self, sample_user):
        ct = ContentType.objects.get_for_model(sample_user.__class__)
        log = AuditLog.objects.create(
            user=sample_user, action='UPDATE',
            description='Updated user',
            content_type=ct, object_id=sample_user.id,
            extra_data={'changes': {'email': 'new@example.com'}}
        )
        assert log.content_object == sample_user

    def test_audit_log_with_extra_data(self, sample_user):
        log = AuditLog.objects.create(
            user=sample_user, action='ROLE_ASSIGN',
            description='Role assigned',
            extra_data={'role': 'Admin', 'tenant_id': 1}
        )
        assert log.extra_data['role'] == 'Admin'

    def test_audit_log_null_user(self):
        log = AuditLog.objects.create(
            user=None, action='SYSTEM_ERROR',
            description='System error occurred',
            source='SYSTEM'
        )
        assert log.user is None

    def test_audit_log_long_description(self, sample_user):
        long_desc = "A" * 1000
        log = AuditLog.objects.create(
            user=sample_user, action='SYSTEM_ERROR',
            description=long_desc
        )
        assert len(log.description) == 1000


@pytest.mark.django_db
class TestCreateAuditLog:
    def test_create_audit_log_util(self, sample_user):
        log = create_audit_log(
            user=sample_user,
            action='LOGIN',
            description="Test util function",
            ip_address='192.168.1.1'
        )
        assert log is not None
        assert log.action == 'LOGIN'
        assert log.ip_address == '192.168.1.1'

    def test_create_audit_log_with_extra_data(self, sample_user):
        log = create_audit_log(
            user=sample_user, action='UPDATE',
            description="Profile updated",
            extra_data={'field': 'phone'}
        )
        assert log.extra_data == {'field': 'phone'}

    def test_create_audit_log_with_content_object(self, sample_user):
        log = create_audit_log(
            user=sample_user, action='CREATE',
            description="User created",
            content_object=sample_user
        )
        assert log.content_object == sample_user


@pytest.mark.django_db
class TestSafeInstanceLabel:
    def test_safe_label_with_str(self, sample_user):
        label = _safe_instance_label(sample_user)
        assert sample_user.email in label

    def test_safe_label_with_broken_str(self):
        class BrokenModel:
            _meta = type('Meta', (), {'label': 'tests.BrokenModel'})()
            pk = 42

            def __str__(self):
                raise Exception("broken")

        instance = BrokenModel()
        label = _safe_instance_label(instance)
        assert 'tests.BrokenModel' in label
        assert 'pk=42' in label

    def test_safe_label_no_pk(self):
        class NoPkModel:
            _meta = type('Meta', (), {'label': 'tests.NoPkModel'})()
            pk = None

            def __str__(self):
                raise Exception("no pk")

        label = _safe_instance_label(NoPkModel())
        assert 'pk=None' in label


@pytest.mark.django_db
class TestAuditLogQueries:
    def test_filter_by_action(self, sample_user):
        AuditLog.objects.create(user=sample_user, action='LOGIN', description='login', source='AUTH')
        AuditLog.objects.create(user=sample_user, action='LOGOUT', description='logout', source='AUTH')
        assert AuditLog.objects.filter(action='LOGIN').count() == 1

    def test_filter_by_user(self, sample_user):
        other = UserFactory()
        AuditLog.objects.create(user=sample_user, action='LOGIN', description='login', source='AUTH')
        AuditLog.objects.create(user=other, action='LOGIN', description='login', source='AUTH')
        assert AuditLog.objects.filter(user=sample_user).count() == 1

    def test_filter_by_timerange(self, sample_user):
        from datetime import timedelta
        old = timezone.now() - timedelta(days=10)
        AuditLog.objects.create(
            user=sample_user, action='LOGIN', description='old',
            source='AUTH', timestamp=old
        )
        AuditLog.objects.create(
            user=sample_user, action='LOGIN', description='new',
            source='AUTH', timestamp=timezone.now()
        )
        recent = timezone.now() - timedelta(days=1)
        assert AuditLog.objects.filter(timestamp__gte=recent, description='new').count() == 1
        assert AuditLog.objects.filter(timestamp__lte=recent, description='old').count() == 1
