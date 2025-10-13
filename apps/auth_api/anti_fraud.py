from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import re
import hashlib
import os
import json

User = get_user_model()

class AntiFraudValidator:
    """
    Sistema anti-fraude para prevenir múltiples cuentas FREE
    """
    
    @staticmethod
    def normalize_email(email):
        """Normalizar email para detectar variaciones"""
        email = email.lower().strip()
        
        # Gmail: ignorar puntos y + aliases
        if '@gmail.com' in email:
            local, domain = email.split('@')
            local = local.split('+')[0]  # Remover +alias
            local = local.replace('.', '')  # Remover puntos
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
        
        # Verificar email normalizado en base de datos
        normalized_email = AntiFraudValidator.normalize_email(email)
        existing_users = User.objects.filter(
            email__icontains=normalized_email.split('@')[0]
        ).filter(
            email__icontains=f"@{normalized_email.split('@')[1]}"
        )
        
        # Verificar si ya existe usuario con email similar
        for user in existing_users:
            if AntiFraudValidator.normalize_email(user.email) == normalized_email:
                if user.tenant and user.tenant.subscription_plan and user.tenant.subscription_plan.name == 'free':
                    return True, 'EMAIL_ALREADY_USED_FREE', None
        
        # Verificar archivo temporal de intentos por IP
        if ip_address:
            ip_file = f"/tmp/fraud_ip_{ip_address.replace('.', '_')}.json"
            if os.path.exists(ip_file):
                with open(ip_file, 'r') as f:
                    data = json.load(f)
                    if data.get('count', 0) >= 3:
                        blocked_until = timezone.now() + timedelta(hours=24)
                        return True, 'IP_LIMIT_EXCEEDED', blocked_until
        
        # Verificar archivo temporal de intentos por email hash
        email_file = f"/tmp/fraud_email_{email_hash}.json"
        if os.path.exists(email_file):
            return True, 'EMAIL_LIMIT_EXCEEDED', None
            
        return False, None, None
    
    @staticmethod
    def record_free_signup(email, ip_address=None):
        """Registrar signup de plan FREE"""
        email_hash = AntiFraudValidator.get_email_hash(email)
        
        # Marcar email como usado (permanente)
        email_file = f"/tmp/fraud_email_{email_hash}.json"
        with open(email_file, 'w') as f:
            json.dump({'used': True, 'timestamp': timezone.now().isoformat()}, f)
        
        # Incrementar contador de IP (24 horas)
        if ip_address:
            ip_file = f"/tmp/fraud_ip_{ip_address.replace('.', '_')}.json"
            current_count = 0
            if os.path.exists(ip_file):
                with open(ip_file, 'r') as f:
                    data = json.load(f)
                    current_count = data.get('count', 0)
            
            with open(ip_file, 'w') as f:
                json.dump({
                    'count': current_count + 1,
                    'timestamp': timezone.now().isoformat()
                }, f)