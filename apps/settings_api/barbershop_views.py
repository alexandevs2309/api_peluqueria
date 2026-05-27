from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.db import transaction
from .barbershop_models import BarbershopSettings
from .barbershop_serializers import (
    BarbershopPublicSerializer,
    BarbershopAdminSerializer,
    BarbershopWriteSerializer
)
from .audit_models import SettingsAuditLog
from .permissions import IsClientAdmin
from apps.core.tenant_permissions import TenantPermissionByAction
from apps.pos_api.models import PosConfiguration
from apps.pos_api.models import Sale
from apps.employees_api.earnings_models import PayrollPeriod
from apps.subscriptions_api.access_control import has_feature
from apps.subscriptions_api.permissions import requires_feature
import logging

logger = logging.getLogger(__name__)


class BarbershopSettingsViewSet(viewsets.ViewSet):
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'settings_api.view_barbershopsettings',
        'create': 'settings_api.change_barbershopsettings',
        'admin_settings': 'settings_api.change_barbershopsettings',
        'upload_logo': 'settings_api.change_barbershopsettings',
    }
    
    # Campos críticos que requieren confirmación
    CRITICAL_FIELDS = ['currency']
    
    # Campos que se auditan
    AUDITED_FIELDS = ['currency']

    def _is_currency_locked(self, tenant):
        """
        Moneda bloqueada si existen transacciones históricas (ventas o nómina).
        """
        has_sales = Sale.objects.filter(tenant=tenant).exists()
        has_payroll = PayrollPeriod.objects.filter(employee__tenant=tenant).exists()
        return has_sales or has_payroll

    def _get_pos_config_data(self, request):
        """
        Obtener configuración POS priorizando usuario actual y con fallback al tenant.
        """
        pos = PosConfiguration.objects.filter(user=request.user).first()
        if not pos and hasattr(request.user, 'tenant') and getattr(request, 'tenant', request.user.tenant):
            pos = PosConfiguration.objects.filter(user__tenant=getattr(request, 'tenant', request.user.tenant)).first()

        if not pos:
            return None

        logger.debug(f"_get_pos_config_data: user_id={request.user.id}")
        
        return {
            'business_name': pos.business_name,
            'address': pos.address,
            'phone': pos.phone,
            'email': pos.email,
            'website': pos.website,
            'rnc': pos.rnc
        }

    def _save_pos_config(self, request, pos_config_data):
        """
        Persistir configuración POS para el usuario actual si viene en payload.
        """
        logger.debug("_save_pos_config: user_id=%s", request.user.id)
        
        if not isinstance(pos_config_data, dict):
            logger.warning("pos_config_data no es dict, es: %s", type(pos_config_data).__name__)
            return

        try:
            pos, created = PosConfiguration.objects.get_or_create(user=request.user)
            logger.debug("PosConfiguration: user_id=%s, created=%s", request.user.id, created)
            
            # Guardar valores anteriores
            old_values = {
                'business_name': pos.business_name,
                'address': pos.address,
                'phone': pos.phone,
                'email': pos.email,
                'website': pos.website,
                'rnc': pos.rnc
            }
            
            # Actualizar campos
            pos.business_name = pos_config_data.get('business_name', pos.business_name)
            pos.address = pos_config_data.get('address', pos.address)
            pos.phone = pos_config_data.get('phone', pos.phone)
            pos.email = pos_config_data.get('email', pos.email)
            pos.website = pos_config_data.get('website', pos.website)
            pos.rnc = pos_config_data.get('rnc', pos.rnc)
            
            logger.info(f"[DEBUG] Valores a guardar: business_name={pos.business_name}, address={pos.address}, phone={pos.phone}, email={pos.email}, website={pos.website}, rnc={pos.rnc}")
            
            pos.save()
            logger.info(f"[DEBUG] PosConfiguration guardado exitosamente. user_id={request.user.id}, rnc={pos.rnc}")
            
        except Exception as e:
            logger.error(f"[ERROR] Error al guardar PosConfiguration: {str(e)}", exc_info=True)
    
    def list(self, request):
        """
        GET /api/settings/barbershop/
        Información pública para todos los empleados (ClientAdmin + ClientStaff).
        Solo campos necesarios para operación diaria.
        """
        try:
            settings = BarbershopSettings.objects.get(tenant=getattr(request, 'tenant', request.user.tenant))
            serializer = BarbershopPublicSerializer(settings)
            data = serializer.data
            
            data['pos_config'] = self._get_pos_config_data(request)
            data['currency_locked'] = self._is_currency_locked(getattr(request, 'tenant', request.user.tenant))
            data['currency_lock_reason'] = (
                'No se puede cambiar la moneda porque existen transacciones registradas.'
                if data['currency_locked'] else ''
            )
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
                'pos_config': self._get_pos_config_data(request),
                'currency_locked': self._is_currency_locked(getattr(request, 'tenant', request.user.tenant)),
                'currency_lock_reason': (
                    'No se puede cambiar la moneda porque existen transacciones registradas.'
                    if self._is_currency_locked(getattr(request, 'tenant', request.user.tenant)) else ''
                )
            })
    
    @action(detail=False, methods=['get'])
    def admin_settings(self, request):
        """
        GET /api/settings/barbershop/admin_settings/
        Configuración completa solo para ClientAdmin.
        Incluye campos financieros y críticos.
        """
        try:
            settings = BarbershopSettings.objects.get(tenant=getattr(request, 'tenant', request.user.tenant))
            serializer = BarbershopAdminSerializer(settings)
            data = serializer.data
            data['pos_config'] = self._get_pos_config_data(request)
            data['currency_locked'] = self._is_currency_locked(getattr(request, 'tenant', request.user.tenant))
            data['currency_lock_reason'] = (
                'No se puede cambiar la moneda porque existen transacciones registradas.'
                if data['currency_locked'] else ''
            )
            return Response(data)
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
                'pos_config': self._get_pos_config_data(request),
                'created_at': None,
                'updated_at': None
            })
    
    def create(self, request):
        """Save barbershop settings con validaciones y auditoría"""
        logger.info(f"[DEBUG] create() called. tenant={getattr(request.user, 'tenant_id', None)}")
        
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        tenant = getattr(request, 'tenant', request.user.tenant)

        # Campos auxiliares que no pertenecen al serializer principal.
        pos_config_data = data.pop('pos_config', None)
        logger.info(f"[DEBUG] pos_config_data extraído (redactado)")
        confirmed_critical = bool(data.pop('confirmed_critical', False))
        data.pop('currency_locked', None)
        data.pop('currency_lock_reason', None)
        
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
                
                has_sales = Sale.objects.filter(tenant=tenant).exists()
                has_payroll = PayrollPeriod.objects.filter(employee__tenant=tenant).exists()
                
                if has_sales or has_payroll:
                    return Response({
                        'error': 'No se puede cambiar la moneda porque existen transacciones registradas',
                        'code': 'CURRENCY_LOCKED',
                        'details': 'El sistema tiene ventas o nóminas registradas. Cambiar la moneda causaría inconsistencias.'
                    }, status=400)
        
        # FIX 4: Gobierno defensivo - Detectar cambios críticos
        if is_update and not confirmed_critical:
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

            # Guardar configuración POS anidada si se envía.
            self._save_pos_config(request, pos_config_data)
        
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
    @requires_feature('custom_branding')
    def upload_logo(self, request):
        """Upload logo"""
        tenant = getattr(request.user, 'tenant', None)
        if not has_feature(tenant, 'custom_branding'):
            raise PermissionDenied('Tu plan no incluye branding personalizado.')

        if 'logo' not in request.FILES:
            return Response({'error': 'No logo file provided'}, status=400)

        logo_file = request.FILES['logo']

        allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
        if logo_file.content_type not in allowed_types:
            return Response(
                {'error': 'Tipo de archivo no permitido. Use JPEG, PNG, WebP o GIF.'},
                status=400
            )

        max_size = 1 * 1024 * 1024
        if logo_file.size > max_size:
            return Response(
                {'error': 'El logo no puede superar 1MB.'},
                status=400
            )

        ext = logo_file.name.split('.')[-1].lower()
        allowed_exts = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
        if ext not in allowed_exts:
            return Response(
                {'error': 'Extensión de archivo no permitida.'},
                status=400
            )

        settings, created = BarbershopSettings.objects.get_or_create(
            tenant=tenant
        )

        settings.logo = logo_file
        settings.save()

        return Response({
            'logo_url': settings.logo.url,
            'message': 'Logo uploaded successfully'
        })
