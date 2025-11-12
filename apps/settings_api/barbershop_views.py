from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .barbershop_models import BarbershopSettings

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
        """Save barbershop settings"""
        data = request.data
        
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
            # Update existing settings
            settings.name = data.get('name', settings.name)
            settings.currency = data.get('currency', settings.currency)
            settings.currency_symbol = data.get('currency_symbol', settings.currency_symbol)
            settings.default_commission_rate = data.get('default_commission_rate', settings.default_commission_rate)
            settings.default_fixed_salary = data.get('default_fixed_salary', settings.default_fixed_salary)
            settings.business_hours = data.get('business_hours', settings.business_hours)
            settings.contact = data.get('contact', settings.contact)
            settings.tax_rate = data.get('tax_rate', settings.tax_rate)
            settings.service_discount_limit = data.get('service_discount_limit', settings.service_discount_limit)
            settings.cancellation_policy_hours = data.get('cancellation_policy_hours', settings.cancellation_policy_hours)
            settings.late_arrival_grace_minutes = data.get('late_arrival_grace_minutes', settings.late_arrival_grace_minutes)
            settings.booking_advance_days = data.get('booking_advance_days', settings.booking_advance_days)
            settings.save()
        
        return Response({'message': 'Settings saved successfully'})
    
    @action(detail=False, methods=['post'])
    def upload_logo(self, request):
        """Upload logo"""
        if 'logo' not in request.FILES:
            return Response({'error': 'No logo file provided'}, status=400)
        
        settings, created = BarbershopSettings.objects.get_or_create(
            tenant=request.user.tenant
        )
        
        settings.logo = request.FILES['logo']
        settings.save()
        
        return Response({
            'logo_url': settings.logo.url,
            'message': 'Logo uploaded successfully'
        })