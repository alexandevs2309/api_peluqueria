from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .barbershop_models import BarbershopSettings
from .barbershop_serializers import (
    BarbershopPublicSerializer,
    BarbershopAdminSerializer,
    BarbershopWriteSerializer
)
from .audit_models import SettingsAuditLog
from .permissions import IsClientAdmin


class BarbershopSettingsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Control de permisos por acción"""
        if self.action in ['create', 'upload_logo', 'admin_settings']:
            return [IsAuthenticated(), IsClientAdmin()]
        return [IsAuthenticated()]
    
    # Campos críticos que requieren confirmación
    CRITICAL_FIELDS = ['currency']
    
    # Campos que se auditan
    AUDITED_FIELDS = ['currency']
    
    def list(self, request):
        """
        GET /api/settings/barbershop/
        Información pública para todos los empleados (ClientAdmin + ClientStaff).
        Solo campos necesarios para operación diaria.
        """
        try:
            settings = BarbershopSettings.objects.get(tenant=request.user.tenant)
            serializer = BarbershopPublicSerializer(settings)
            data = serializer.data
            
            # Cargar configuración POS si existe
            pos_config = None
            try:
                from apps.pos_api.models import PosConfiguration
                pos = PosConfiguration.objects.filter(user=request.user).first()
                if pos:
                    pos_config = {
                        'business_name': pos.business_name,
                        'address': pos.address,
                        'phone': pos.phone,
                        'email': pos.email,
                        'website': pos.website
                    }
            except:
                pass
            
            data['pos_config'] = pos_config
            return Response(data)
        except BarbershopSettings.DoesNotExist:
            # Return default public settings
            return Response({
                'name': '',
                'logo': None,
                'currency': 'COP',
                'currency_symbol': '$',
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
                'pos_config': None
            })
    
    @action(detail=False, methods=['get'])
    def admin_settings(self, request):
        """
        GET /api/settings/barbershop/admin_settings/
        Configuración completa solo para ClientAdmin.
        Incluye campos financieros y críticos.
        """
        try:
            settings = BarbershopSettings.objects.get(tenant=request.user.tenant)
            serializer = BarbershopAdminSerializer(settings)
            return Response(serializer.data)
        except BarbershopSettings.DoesNotExist:
            # Return default admin settings
            return Response({
                'name': '',
                'logo': None,
                'currency': 'COP',
                'currency_symbol': '$',
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
                'created_at': None,
                'updated_at': None
            })
    
    def create(self, request):
        """Save barbershop settings con validaciones y auditoría"""
        data = request.data
        tenant = request.user.tenant
        
        # Obtener o crear settings
        try:
            settings = BarbershopSettings.objects.get(tenant=tenant)
            is_update = True
        except BarbershopSettings.DoesNotExist:
            settings = None
            is_update = False
        
        # Usar serializer para validación
        serializer = BarbershopWriteSerializer(settings, data=data, partial=is_update)
        serializer.is_valid(raise_exception=True)
        
        # FIX 2: Validar cambio de moneda
        if is_update and 'currency' in data:
            old_currency = settings.currency
            new_currency = data.get('currency')
            
            if old_currency != new_currency:
                # Verificar si existen transacciones
                from apps.pos_api.models import Sale
                from apps.employees_api.earnings_models import PayrollPeriod
                
                has_sales = Sale.objects.filter(employee__tenant=tenant).exists()
                has_payroll = PayrollPeriod.objects.filter(employee__tenant=tenant).exists()
                
                if has_sales or has_payroll:
                    return Response({
                        'error': 'No se puede cambiar la moneda porque existen transacciones registradas',
                        'code': 'CURRENCY_LOCKED',
                        'details': 'El sistema tiene ventas o nóminas registradas. Cambiar la moneda causaría inconsistencias.'
                    }, status=400)
        
        # FIX 4: Gobierno defensivo - Detectar cambios críticos
        if is_update and not data.get('confirmed_critical', False):
            critical_changes = []
            
            for field in self.CRITICAL_FIELDS:
                if field in data:
                    old_value = str(getattr(settings, field, ''))
                    new_value = str(data.get(field, ''))
                    
                    if old_value != new_value:
                        critical_changes.append({
                            'setting': field,
                            'old_value': old_value,
                            'new_value': new_value,
                            'type': 'critical',
                            'impact': self._get_field_impact(field)
                        })
            
            if critical_changes:
                return Response({
                    'requires_confirmation': True,
                    'critical_changes': critical_changes,
                    'message': 'Este cambio puede afectar el comportamiento futuro del sistema'
                }, status=200)
        
        # Usar transacción atómica
        with transaction.atomic():
            if is_update:
                # FIX 3: Auditar cambios
                self._audit_changes(settings, data, request.user, tenant)
                
                # Actualizar con datos validados
                for field, value in serializer.validated_data.items():
                    setattr(settings, field, value)
                settings.save()
            else:
                # Crear nuevo con datos validados
                settings = BarbershopSettings.objects.create(
                    tenant=tenant,
                    **serializer.validated_data
                )
        
        return Response({'message': 'Settings saved successfully'})
    
    def _audit_changes(self, settings, data, user, tenant):
        """Registrar cambios en campos auditados"""
        for field in self.AUDITED_FIELDS:
            if field in data:
                old_value = str(getattr(settings, field, ''))
                new_value = str(data.get(field, ''))
                
                if old_value != new_value:
                    SettingsAuditLog.objects.create(
                        tenant=tenant,
                        user=user,
                        field_name=field,
                        old_value=old_value,
                        new_value=new_value
                    )
    
    def _get_field_impact(self, field):
        """Obtener descripción de impacto por campo"""
        impacts = {
            'currency': 'Afecta la visualización de todos los montos en el sistema'
        }
        return impacts.get(field, 'Cambio en configuración del sistema')
    
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