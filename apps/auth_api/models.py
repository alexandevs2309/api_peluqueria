from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone



from apps.roles_api.models import Role, UserRole

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
       

        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, max_length=255)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=255, blank=True, null=True)
    mfa_secret = models.CharField(max_length=255, blank=True, null=True)
    mfa_enabled = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login_ip_address = models.GenericIPAddressField(null=True, blank=True)



    is_deleted = models.BooleanField(default=False)
    
    # Multitenancy: Usuario pertenece a un tenant
    tenant = models.ForeignKey(
        'tenants_api.Tenant', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='users'
    )

    roles = models.ManyToManyField(
        'roles_api.Role',
        through='roles_api.UserRole',
        related_name='assigned_users',
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']


    class Meta:
        indexes = [
            models.Index(fields=['email']),
           
        ]

    def __str__(self):
        return self.email


class LoginAudit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="login_audits")
    ip_address = models.GenericIPAddressField(null=True, blank=True,)
    user_agent = models.TextField(null=True, blank=True,)
    successful = models.BooleanField(default=False)
    message = models.TextField(null=True, blank=True,)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['successful']),
        ]

    def __str__(self):
        return f"Login attempt for {self.user.email if self.user else 'unknown'} - {'Success' if self.successful else 'Failed'}"
    



EVENT_CHOICES = [
    ('LOGIN', 'Login'),
    ('LOGOUT', 'Logout'),
    ('PASSWORD_RESET', 'Password Reset'),
    ('PASSWORD_CHANGE', 'Password Change'),
]

class AccessLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)


    class Meta:
        indexes = [
            models.Index(fields=['timestamp']),
        ]
    def __str__(self):
        return f"{self.user} - {self.event_type} at {self.timestamp}"



class ActiveSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions_active")
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True , null=True) 
    token_jti = models.CharField(max_length=255, unique=True)
    refresh_token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    expired_at = models.DateTimeField(null=True, blank=True)

    def expire_session(self):
        self.is_active = False
        self.expired_at = timezone.now()
        self.save()
    
   
    class Meta:
        verbose_name = "Sesión "
        verbose_name_plural = "Sesiones "
        ordering = ['-last_seen']
    
    def __str__(self):
        return f"{self.user.email} - {self.ip_address} - {'Activa' if self.is_active else 'Inactiva'}"