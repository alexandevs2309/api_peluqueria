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

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        raw_password = extracted or 'testpassword'
        self.set_password(raw_password)
        if create:
            self.save()
