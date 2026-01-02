from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .barbershop_models import BarbershopSettings
from .settings_governor import SettingsGovernor
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

class BarbershopSettingsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get barbershop settings"""
        try:
            settings = BarbershopSettings.objects.get(tenant=request.user.tenant)
            return Response({
                'name': settings.name,
                'logo': settings.logo.url if settings.logo else None,
                'currency': settings.currency,
                'currency_symbol': settings.currency_symbol,
                'default_commission_rate': float(settings.default_commission_rate),
                'default_fixed_salary': float(settings.default_fixed_salary),
                'business_hours': settings.business_hours,
                'contact': settings.contact,
                'tax_rate': float(settings.tax_rate),
                'service_discount_limit': float(settings.service_discount_limit),
                'cancellation_policy_hours': settings.cancellation_policy_hours,
                'late_arrival_grace_minutes': settings.late_arrival_grace_minutes,
                'booking_advance_days': settings.booking_advance_days
            })
        except BarbershopSettings.DoesNotExist:
            # Return default settings
            return Response({
                'name': '',
                'logo': None,
                'currency': 'COP',
                'currency_symbol': '$',
                'default_commission_rate': 40.0,
                'default_fixed_salary': 1200000.0,
                'business_hours': {
                    'monday': {'open': '08:00', 'close': '18:00', 'closed': False},
                    'tuesday': {'open': '08:00', 'close': '18:00', 'closed': False},
                    'wednesday': {'open': '08:00', 'close': '18:00', 'closed': False},
                    'thursday': {'open': '08:00', 'close': '18:00', 'closed': False},
                    'friday': {'open': '08:00', 'close': '18:00', 'closed': False},
                    'saturday': {'open': '08:00', 'close': '16:00', 'closed': False},
                    'sunday': {'open': '10:00', 'close': '14:00', 'closed': True}
                },
                'contact': {
                    'phone': '',
                    'email': '',
                    'address': ''
                },
                'tax_rate': 0.0,
                'service_discount_limit': 20.0,
                'cancellation_policy_hours': 24,
                'late_arrival_grace_minutes': 15,
                'booking_advance_days': 30
            })
    
    def create(self, request):
        """Save barbershop settings with defensive governance"""
        data = request.data
        confirmed_critical = request.data.get('confirmed_critical', False)
        
        # Obtener configuraciones actuales
        try:
            current_settings = BarbershopSettings.objects.get(tenant=request.user.tenant)
        except BarbershopSettings.DoesNotExist:
            current_settings = None
        
        # Validar cambios críticos
        validation_errors = []
        requires_confirmation = False
        critical_changes = []
        
        for setting_name, new_value in data.items():
            if setting_name in ['confirmed_critical']:  # Skip control fields
                continue
                
            old_value = getattr(current_settings, setting_name, None) if current_settings else None
            
            # Solo validar si el valor cambió
            if str(old_value) != str(new_value):
                validation = SettingsGovernor.validate_change(
                    setting_name, new_value, old_value, request.user.tenant
                )
                
                if not validation['valid']:
                    validation_errors.append({
                        'setting': setting_name,
                        'error': validation['validation_error']
                    })
                
                if validation['requires_confirmation']:
                    requires_confirmation = True
                    critical_changes.append({
                        'setting': setting_name,
                        'old_value': old_value,
                        'new_value': new_value,
                        'impact': validation['impact_message'],
                        'type': validation['setting_type']
                    })
        
        # Si hay errores de validación, rechazar
        if validation_errors:
            return Response({
                'error': 'Validation failed',
                'validation_errors': validation_errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Si requiere confirmación y no se confirmó, solicitar confirmación
        if requires_confirmation and not confirmed_critical:
            return Response({
                'requires_confirmation': True,
                'critical_changes': critical_changes,
                'message': 'Los cambios críticos requieren confirmación explícita'
            }, status=status.HTTP_200_OK)
        
        # Proceder con el guardado
        with transaction.atomic():
            settings, created = BarbershopSettings.objects.get_or_create(
                tenant=request.user.tenant,
                defaults={
                    'name': data.get('name', ''),
                    'currency': data.get('currency', 'COP'),
                    'currency_symbol': data.get('currency_symbol', '$'),
                    'default_commission_rate': data.get('default_commission_rate', 40.0),
                    'default_fixed_salary': data.get('default_fixed_salary', 1200000.0),
                    'business_hours': data.get('business_hours', {}),
                    'contact': data.get('contact', {}),
                    'tax_rate': data.get('tax_rate', 0.0),
                    'service_discount_limit': data.get('service_discount_limit', 20.0),
                    'cancellation_policy_hours': data.get('cancellation_policy_hours', 24),
                    'late_arrival_grace_minutes': data.get('late_arrival_grace_minutes', 15),
                    'booking_advance_days': data.get('booking_advance_days', 30)
                }
            )
            
            if not created:
                # Registrar cambios y actualizar
                for setting_name, new_value in data.items():
                    if setting_name in ['confirmed_critical']:  # Skip control fields
                        continue
                        
                    old_value = getattr(settings, setting_name, None)
                    
                    if str(old_value) != str(new_value):
                        # Registrar cambio
                        SettingsGovernor.log_change(
                            tenant=request.user.tenant,
                            user=request.user,
                            setting_name=setting_name,
                            old_value=old_value,
                            new_value=new_value,
                            confirmed=confirmed_critical,
                            impact_acknowledged=requires_confirmation
                        )
                        
                        # Actualizar valor
                        setattr(settings, setting_name, new_value)
                
                settings.save()
            
            # Log para auditoría
            logger.info(f"Settings updated for tenant {request.user.tenant.id} by user {request.user.id}")
        
        return Response({
            'message': 'Settings saved successfully',
            'changes_logged': len(critical_changes) > 0
        })
    
    @action(detail=False, methods=['get'])
    def governance_info(self, request):
        """Get governance information for frontend"""
        return Response(SettingsGovernor.get_critical_settings_info())
    
    @action(detail=False, methods=['post'])
    def upload_logo(self, request):
        """Upload logo"""
        if 'logo' not in request.FILES:
            return Response({'error': 'No logo file provided'}, status=400)
        
        settings, created = BarbershopSettings.objects.get_or_create(
            tenant=request.user.tenant
        )
        
        old_logo = settings.logo.url if settings.logo else None
        settings.logo = request.FILES['logo']
        settings.save()
        
        # Log cosmetic change
        SettingsGovernor.log_change(
            tenant=request.user.tenant,
            user=request.user,
            setting_name='logo',
            old_value=old_logo,
            new_value=settings.logo.url,
            confirmed=False,
            impact_acknowledged=False
        )
        
        return Response({
            'logo_url': settings.logo.url,
            'message': 'Logo uploaded successfully'
        })