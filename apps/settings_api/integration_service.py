from django.conf import settings
from .models import SystemSettings
import os

class IntegrationService:
    """Servicio para manejar integraciones basado en feature toggles"""
    
    @staticmethod
    def get_system_settings():
        """Obtener configuraciones del sistema"""
        return SystemSettings.get_settings()
    
    @staticmethod
    def is_stripe_enabled():
        """Verificar si Stripe está habilitado"""
        system_settings = IntegrationService.get_system_settings()
        return system_settings.stripe_enabled and bool(os.getenv('STRIPE_SECRET_KEY'))
    
    @staticmethod
    def is_paypal_enabled():
        """Verificar si PayPal está habilitado"""
        system_settings = IntegrationService.get_system_settings()
        return system_settings.paypal_enabled and bool(os.getenv('PAYPAL_CLIENT_ID'))
    
    @staticmethod
    def is_twilio_enabled():
        """Verificar si Twilio (SMS) está habilitado"""
        system_settings = IntegrationService.get_system_settings()
        return (system_settings.twilio_enabled and 
                bool(os.getenv('TWILIO_ACCOUNT_SID')) and 
                bool(os.getenv('TWILIO_AUTH_TOKEN')))
    
    @staticmethod
    def is_sendgrid_enabled():
        """Verificar si SendGrid (Email) está habilitado"""
        system_settings = IntegrationService.get_system_settings()
        return system_settings.sendgrid_enabled and bool(os.getenv('SENDGRID_API_KEY'))
    
    @staticmethod
    def is_aws_s3_enabled():
        """Verificar si AWS S3 está habilitado"""
        system_settings = IntegrationService.get_system_settings()
        return (system_settings.aws_s3_enabled and 
                bool(os.getenv('AWS_ACCESS_KEY_ID')) and 
                bool(os.getenv('AWS_SECRET_ACCESS_KEY')))
    
    @staticmethod
    def get_integration_status():
        """Obtener estado de todas las integraciones"""
        return {
            'stripe': IntegrationService.is_stripe_enabled(),
            'paypal': IntegrationService.is_paypal_enabled(),
            'twilio': IntegrationService.is_twilio_enabled(),
            'sendgrid': IntegrationService.is_sendgrid_enabled(),
            'aws_s3': IntegrationService.is_aws_s3_enabled(),
        }
    
    @staticmethod
    def send_sms(phone, message):
        """Enviar SMS si Twilio está habilitado"""
        if not IntegrationService.is_twilio_enabled():
            raise Exception("Twilio no está habilitado")
        
        # TODO: Implementar envío real con Twilio
        print(f"SMS a {phone}: {message}")
        return True
    
    @staticmethod
    def send_email(to_email, subject, message):
        """Enviar email si SendGrid está habilitado"""
        if not IntegrationService.is_sendgrid_enabled():
            raise Exception("SendGrid no está habilitado")
        
        # TODO: Implementar envío real con SendGrid
        print(f"Email a {to_email}: {subject} - {message}")
        return True
    
    @staticmethod
    def upload_to_s3(file, bucket, key):
        """Subir archivo a S3 si está habilitado"""
        if not IntegrationService.is_aws_s3_enabled():
            raise Exception("AWS S3 no está habilitado")
        
        # TODO: Implementar subida real a S3
        print(f"Subiendo {key} a bucket {bucket}")
        return f"https://{bucket}.s3.amazonaws.com/{key}"