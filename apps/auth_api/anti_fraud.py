import hashlib
import logging
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

logger = logging.getLogger(__name__)
User = get_user_model()

# ✅ Configuración centralizada
MAX_LOGIN_ATTEMPTS = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
LOCKOUT_DURATION = getattr(settings, 'LOCKOUT_DURATION_MINUTES', 15) * 60  # Segundos
MAX_REGISTRATIONS_PER_IP = getattr(settings, 'MAX_REGISTRATIONS_PER_IP', 3)
MAX_REGISTRATIONS_PER_EMAIL = getattr(settings, 'MAX_REGISTRATIONS_PER_EMAIL', 1)
REGISTRATION_WINDOW = getattr(settings, 'REGISTRATION_WINDOW_HOURS', 24) * 3600  # Segundos


def get_client_ip(request):
    """Obtener IP real del cliente (considera proxies)"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def hash_email(email):
    """Hash de email para privacidad"""
    return hashlib.sha256(email.lower().encode()).hexdigest()[:16]


class AntiFraudService:
    """Servicio anti-fraude usando Redis para escalabilidad horizontal"""
    
    @staticmethod
    def check_login_attempts(ip_address):
        """
        Verificar intentos de login fallidos
        Returns: (is_blocked, attempts_remaining)
        """
        key = f"login_attempts:{ip_address}"
        attempts = cache.get(key, 0)
        
        if attempts >= MAX_LOGIN_ATTEMPTS:
            ttl = cache.ttl(key) if hasattr(cache, 'ttl') else LOCKOUT_DURATION
            logger.warning(f"IP {ip_address} bloqueada por {ttl}s")
            return True, 0
        
        return False, MAX_LOGIN_ATTEMPTS - attempts
    
    @staticmethod
    def record_failed_login(ip_address):
        """
        Registrar intento fallido de login
        Returns: attempts_count
        """
        key = f"login_attempts:{ip_address}"
        
        # ✅ Operación atómica con Redis incr
        try:
            # Intentar incremento atómico
            try:
                attempts = cache.incr(key)
                # Asegurar TTL en primera creación
                if attempts == 1:
                    cache.expire(key, LOCKOUT_DURATION)
            except ValueError:
                # Key no existe, crear con valor 1
                cache.set(key, 1, LOCKOUT_DURATION)
                attempts = 1
            
            if attempts >= MAX_LOGIN_ATTEMPTS:
                logger.warning(f"IP {ip_address} bloqueada después de {attempts} intentos")
            
            return attempts
        except Exception as e:
            logger.error(f"Error recording failed login: {e}")
            return 0
    
    @staticmethod
    def reset_login_attempts(ip_address):
        """Limpiar intentos después de login exitoso"""
        key = f"login_attempts:{ip_address}"
        cache.delete(key)
    
    @staticmethod
    def check_registration_limits(ip_address, email):
        """
        Verificar límites de registro
        Returns: (is_allowed, reason)
        """
        # Verificar límite por IP
        ip_key = f"registrations_ip:{ip_address}"
        ip_count = cache.get(ip_key, 0)
        
        if ip_count >= MAX_REGISTRATIONS_PER_IP:
            logger.warning(f"IP {ip_address} excedió límite de registros ({ip_count})")
            return False, f"Too many registrations from this IP. Limit: {MAX_REGISTRATIONS_PER_IP}"
        
        # Verificar límite por email
        email_hash = hash_email(email)
        email_key = f"registrations_email:{email_hash}"
        email_count = cache.get(email_key, 0)
        
        if email_count >= MAX_REGISTRATIONS_PER_EMAIL:
            logger.warning(f"Email {email[:3]}*** excedió límite de registros")
            return False, "This email has already been registered"
        
        return True, None
    
    @staticmethod
    def record_registration(ip_address, email):
        """
        Registrar nuevo registro exitoso
        """
        # ✅ Incrementar contador de IP atómicamente
        ip_key = f"registrations_ip:{ip_address}"
        try:
            try:
                ip_count = cache.incr(ip_key)
                if ip_count == 1:
                    cache.expire(ip_key, REGISTRATION_WINDOW)
            except ValueError:
                cache.set(ip_key, 1, REGISTRATION_WINDOW)
        except Exception as e:
            logger.error(f"Error recording IP registration: {e}")
        
        # ✅ Incrementar contador de email atómicamente
        email_hash = hash_email(email)
        email_key = f"registrations_email:{email_hash}"
        try:
            try:
                email_count = cache.incr(email_key)
                if email_count == 1:
                    cache.expire(email_key, REGISTRATION_WINDOW)
            except ValueError:
                cache.set(email_key, 1, REGISTRATION_WINDOW)
        except Exception as e:
            logger.error(f"Error recording email registration: {e}")
    
    @staticmethod
    def get_stats(ip_address=None, email=None):
        """
        Obtener estadísticas de anti-fraude (para debugging)
        """
        stats = {}
        
        if ip_address:
            login_key = f"login_attempts:{ip_address}"
            reg_key = f"registrations_ip:{ip_address}"
            stats['login_attempts'] = cache.get(login_key, 0)
            stats['registrations'] = cache.get(reg_key, 0)
        
        if email:
            email_hash = hash_email(email)
            email_key = f"registrations_email:{email_hash}"
            stats['email_registrations'] = cache.get(email_key, 0)
        
        return stats


# ✅ Funciones de compatibilidad (mantener API existente)
def check_login_attempts(ip_address):
    return AntiFraudService.check_login_attempts(ip_address)

def record_failed_login(ip_address):
    return AntiFraudService.record_failed_login(ip_address)

def reset_login_attempts(ip_address):
    return AntiFraudService.reset_login_attempts(ip_address)

def check_registration_limits(ip_address, email):
    return AntiFraudService.check_registration_limits(ip_address, email)

def record_registration(ip_address, email):
    return AntiFraudService.record_registration(ip_address, email)


# ✅ Mantener AntiFraudValidator para compatibilidad con código existente
class AntiFraudValidator:
    """Sistema anti-fraude para prevenir múltiples cuentas FREE"""
    
    @staticmethod
    def normalize_email(email):
        """Normalizar email para detectar variaciones"""
        email = email.lower().strip()
        
        # Gmail: ignorar puntos y + aliases
        if '@gmail.com' in email:
            local, domain = email.split('@')
            local = local.split('+')[0]
            local = local.replace('.', '')
            email = f"{local}@{domain}"
            
        # Outlook: ignorar + aliases
        elif any(domain in email for domain in ['@outlook.com', '@hotmail.com', '@live.com']):
            local, domain = email.split('@')
            local = local.split('+')[0]
            email = f"{local}@{domain}"
            
        return email
    
    @staticmethod
    def get_email_hash(email):
        """Generar hash del email normalizado"""
        normalized = AntiFraudValidator.normalize_email(email)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    @staticmethod
    def check_email_fraud(email, ip_address=None):
        """
        Verificar si email/IP ya usó plan FREE
        Returns: (is_fraud, reason, blocked_until)
        """
        email_hash = AntiFraudValidator.get_email_hash(email)
        
        # ✅ Verificar en Redis primero
        redis_key = f"fraud_email:{email_hash}"
        if cache.get(redis_key):
            return True, 'EMAIL_ALREADY_USED_FREE', None
        
        # Verificar email normalizado en base de datos
        normalized_email = AntiFraudValidator.normalize_email(email)
        existing_users = User.objects.filter(
            email__icontains=normalized_email.split('@')[0]
        ).filter(
            email__icontains=f"@{normalized_email.split('@')[1]}"
        )
        
        for user in existing_users:
            if AntiFraudValidator.normalize_email(user.email) == normalized_email:
                if user.tenant and user.tenant.subscription_plan and user.tenant.subscription_plan.name == 'free':
                    # ✅ Cachear resultado
                    cache.set(redis_key, True, 86400 * 365)  # 1 año
                    return True, 'EMAIL_ALREADY_USED_FREE', None
        
        # ✅ Verificar límite por IP en Redis
        if ip_address:
            ip_key = f"fraud_ip:{ip_address}"
            ip_count = cache.get(ip_key, 0)
            if ip_count >= 3:
                blocked_until = timezone.now() + timezone.timedelta(hours=24)
                return True, 'IP_LIMIT_EXCEEDED', blocked_until
            
        return False, None, None
    
    @staticmethod
    def record_free_signup(email, ip_address=None):
        """Registrar signup de plan FREE"""
        email_hash = AntiFraudValidator.get_email_hash(email)
        
        # ✅ Marcar email como usado en Redis (permanente)
        redis_key = f"fraud_email:{email_hash}"
        cache.set(redis_key, True, 86400 * 365)  # 1 año
        
        # ✅ Incrementar contador de IP atómicamente (24 horas)
        if ip_address:
            ip_key = f"fraud_ip:{ip_address}"
            try:
                try:
                    cache.incr(ip_key)
                    cache.expire(ip_key, 86400)
                except ValueError:
                    cache.set(ip_key, 1, 86400)
            except Exception as e:
                logger.error(f"Error recording fraud IP: {e}")
