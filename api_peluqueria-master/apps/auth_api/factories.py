import factory
from django.contrib.auth import get_user_model
from faker import Faker

fake = Faker('es_ES')

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Faker('email')
    full_name = factory.Faker('name')
    is_email_verified = True
    tenant = None

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        is_superuser = kwargs.get('is_superuser', False)
        tenant = kwargs.get('tenant')

        if not is_superuser and not tenant:
            from apps.tenants_api.models import Tenant
            from uuid import uuid4
            tenant = Tenant.objects.create(
                name=f"test-tenant-{uuid4().hex[:8]}",
                subdomain=f"test-{uuid4().hex[:8]}",
            )
            kwargs['tenant'] = tenant

        return super()._create(model_class, *args, **kwargs)

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        raw_password = extracted or 'testpassword'
        self.set_password(raw_password)
        if create:
            self.save(skip_validation=True)

    @factory.post_generation
    def set_tenant(self, create, extracted, **kwargs):
        if extracted is not None:
            self.tenant = extracted
            if create:
                self.save()
