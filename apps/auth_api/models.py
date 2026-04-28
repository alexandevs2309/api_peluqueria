from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from .role_utils import map_business_role_to_legacy_role, map_legacy_role_to_business_role, normalize_business_role

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
    email = models.EmailField(max_length=255)  # ✅ Removido unique=True
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.ImageField(upload_to='users/avatars/', null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)

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

    ROLE_CHOICES = [
        ('SuperAdmin', 'Super Admin'),
        ('Client-Admin', 'Client Admin'),
        ('Client-Staff', 'Client Staff'),
        ('Estilista', 'Estilista'),
        ('Cajera', 'Cajera'),
        ('Manager', 'Manager'),
        ('Utility', 'Utility'),
    ]
    BUSINESS_ROLE_CHOICES = [
        ('owner', 'Propietario'),
        ('manager', 'Gerente'),
        ('frontdesk_cashier', 'Recepcion / Caja'),
        ('professional', 'Profesional'),
        ('internal_support', 'Soporte interno'),
        ('marketing', 'Marketing'),
        ('accounting', 'Contabilidad'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True, null=True)
    business_role = models.CharField(
        max_length=32,
        choices=BUSINESS_ROLE_CHOICES,
        blank=True,
        null=True,
        db_index=True,
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
            models.Index(fields=['email', 'tenant']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(tenant__isnull=False) | models.Q(is_superuser=True),
                name='user_must_have_tenant_or_be_superuser',
                violation_error_message='Los usuarios no superadmin deben tener un tenant asignado.'
            )
        ]
        # ✅ UNIQUE CONSTRAINT POR TENANT
        unique_together = [['email', 'tenant']]

    def clean(self):
        """Validación estructural multi-tenant"""
        super().clean()
        if not self.is_superuser and not self.tenant_id:
            raise ValidationError({
                'tenant': 'Los usuarios no superadmin deben tener un tenant asignado.'
            })

    def save(self, *args, **kwargs):
        if self.role:
            self.business_role = map_legacy_role_to_business_role(
                self.role,
                is_superuser=self.is_superuser,
            ) or self.business_role
        elif self.business_role:
            normalized_business_role = normalize_business_role(
                self.business_role,
                is_superuser=self.is_superuser,
            )
            self.business_role = normalized_business_role or self.business_role
            inferred_legacy_role = map_business_role_to_legacy_role(
                self.business_role,
                is_superuser=self.is_superuser,
            )
            if inferred_legacy_role:
                self.role = inferred_legacy_role

        if self.is_superuser and not self.business_role:
            self.business_role = 'internal_support'

        # Validar antes de guardar (excepto en creación de superuser)
        if not kwargs.pop('skip_validation', False):
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class LoginAudit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="login_audits")
    ip_address = models.GenericIPAddressField(null=True, blank=True,)
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    successful = models.BooleanField(default=False)
    message = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['successful']),
        ]

    def __str__(self):
        # Evitar resolver FK durante cascadas de borrado (puede lanzar User.DoesNotExist).
        user_label = f"user_id={self.user_id}" if self.user_id else "unknown"
        return f"Login attempt for {user_label} - {'Success' if self.successful else 'Failed'}"
    



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
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)


    class Meta:
        indexes = [
            models.Index(fields=['timestamp']),
        ]
    def __str__(self):
        user_label = f"user_id={self.user_id}" if self.user_id else "unknown"
        return f"{user_label} - {self.event_type} at {self.timestamp}"



class ActiveSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions_active")
    tenant = models.ForeignKey('tenants_api.Tenant', on_delete=models.CASCADE, null=True, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True) 
    token_jti = models.TextField(unique=True)
    refresh_token = models.TextField(unique=True)
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
        user_label = f"user_id={self.user_id}" if self.user_id else "unknown"
        return f"{user_label} - {self.ip_address} - {'Activa' if self.is_active else 'Inactiva'}"
