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
import json
from django.conf import settings as django_settings

logger = logging.getLogger(__name__)


class BarbershopSettingsViewSet(viewsets.ViewSet):
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'settings_api.view_barbershopsettings',
        'create': 'settings_api.change_barbershopsettings',
        'admin_settings': 'settings_api.change_barbershopsettings',
        'upload_logo': 'settings_api.change_barbershopsettings',
        'whatsapp_status': 'settings_api.view_barbershopsettings',
        'whatsapp_connect': 'settings_api.change_barbershopsettings',
        'whatsapp_disconnect': 'settings_api.change_barbershopsettings',
    }


    def get_permissions(self):
        if self.action == 'whatsapp_webhook':
            from rest_framework.permissions import AllowAny
            return [AllowAny()]
        return super().get_permissions()
    
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
            tenant = getattr(request, 'tenant', None) or getattr(request.user, 'tenant', None)
            pos, created = PosConfiguration.objects.get_or_create(
                user=request.user,
                defaults={'tenant': tenant}
            )
            # Si ya existía pero sin tenant, asignarlo ahora
            if not created and pos.tenant is None and tenant is not None:
                pos.tenant = tenant
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
                'brand_colors': {
                    'primary': '#2563EB',
                    'secondary': '#4F46E5',
                    'accent': '#059669',
                },
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
                'brand_colors': {
                    'primary': '#2563EB',
                    'secondary': '#4F46E5',
                    'accent': '#059669',
                },
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

    @action(detail=False, methods=['get'])
    def whatsapp_status(self, request):
        """
        GET /api/settings/barbershop/whatsapp_status/
        Devuelve el estado de conexión de WhatsApp para el tenant actual
        """
        tenant = getattr(request, 'tenant', request.user.tenant)
        settings, _ = BarbershopSettings.objects.get_or_create(tenant=tenant)
        
        from .whatsapp_provider import get_whatsapp_provider
        provider = get_whatsapp_provider()
        
        if settings.whatsapp_instance_name:
            current_status = provider.get_status(settings.whatsapp_instance_name)
            should_save = False
            if current_status != settings.whatsapp_status:
                settings.whatsapp_status = current_status
                should_save = True
            
            if current_status == "connected" and not settings.whatsapp_enabled:
                settings.whatsapp_enabled = True
                should_save = True
            elif current_status == "disconnected" and settings.whatsapp_enabled:
                settings.whatsapp_enabled = False
                should_save = True
                
            if should_save:
                settings.save(update_fields=['whatsapp_status', 'whatsapp_enabled'])
        
        return Response({
            'whatsapp_enabled': settings.whatsapp_enabled,
            'whatsapp_status': settings.whatsapp_status,
            'whatsapp_phone': settings.whatsapp_phone,
            'whatsapp_instance_name': settings.whatsapp_instance_name
        })

    @action(detail=False, methods=['post'])
    def whatsapp_connect(self, request):
        """
        POST /api/settings/barbershop/whatsapp_connect/
        Crea/recupera instancia de WhatsApp y devuelve el código QR
        """
        tenant = getattr(request, 'tenant', request.user.tenant)
        
        from apps.subscriptions_api.access_control import tenant_has_feature
        if not tenant_has_feature(tenant, 'whatsapp_notifications'):
            return Response({
                'error': 'Tu plan no incluye notificaciones por WhatsApp. Actualiza tu plan.'
            }, status=status.HTTP_403_FORBIDDEN)
            
        settings, _ = BarbershopSettings.objects.get_or_create(tenant=tenant)
        
        instance_name = f"tenant_{tenant.subdomain or tenant.id}"
        
        import secrets
        token = settings.whatsapp_token or secrets.token_hex(16)
        
        from .whatsapp_provider import get_whatsapp_provider
        provider = get_whatsapp_provider()
        
        result = provider.create_instance(instance_name, token)
        
        if result.get('success'):
            settings.whatsapp_instance_name = instance_name
            settings.whatsapp_token = result.get('token')
            settings.whatsapp_status = 'connecting'
            settings.save(update_fields=['whatsapp_instance_name', 'whatsapp_token', 'whatsapp_status'])
            
            # Configurar webhook
            platform_domain = getattr(django_settings, 'PLATFORM_DOMAIN', None)
            if not platform_domain:
                import os
                # Si estamos en la red interna de Docker, la pasarela 'evolution' necesita apuntar al host 'web'
                evolution_url = os.getenv("EVOLUTION_API_URL", "")
                if "evolution" in evolution_url:
                    platform_domain = "http://web:8000"
                else:
                    platform_domain = "http://localhost:8000"
            
            webhook_url = f"{platform_domain}/api/settings/barbershop/whatsapp_webhook/"
            provider.set_webhook(instance_name, webhook_url)

            
            return Response({
                'success': True,
                'qrcode_base64': result.get('qrcode_base64'),
                'qrcode_code': result.get('qrcode_code'),
                'status': 'connecting'
            })
            
        return Response({
            'success': False,
            'error': result.get('error', 'No se pudo conectar a la pasarela de WhatsApp')
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def whatsapp_disconnect(self, request):
        """
        POST /api/settings/barbershop/whatsapp_disconnect/
        Desconecta e inhabilita WhatsApp para el tenant actual
        """
        tenant = getattr(request, 'tenant', request.user.tenant)
        settings, _ = BarbershopSettings.objects.get_or_create(tenant=tenant)
        
        if settings.whatsapp_instance_name:
            from .whatsapp_provider import get_whatsapp_provider
            provider = get_whatsapp_provider()
            provider.delete_instance(settings.whatsapp_instance_name)
            
        settings.whatsapp_enabled = False
        settings.whatsapp_instance_name = ''
        settings.whatsapp_token = ''
        settings.whatsapp_status = 'disconnected'
        settings.whatsapp_phone = ''
        settings.save()
        
        return Response({'success': True, 'message': 'WhatsApp desconectado correctamente'})

    @action(detail=False, methods=['post'])
    def whatsapp_webhook(self, request):
        """
        POST /api/settings/barbershop/whatsapp_webhook/
        Webhook público llamado por la pasarela para notificar cambios de conexión
        """
        data = request.data
        logger.info("WhatsApp Webhook received: %s", json.dumps(data)[:300])
        
        event_type = (data.get("event") or "").lower()
        instance_name = data.get("instance")
        
        if event_type in ("connection.update", "connection_update") and instance_name:
            status_data = data.get("data", {})
            status_state = status_data.get("state")
            
            settings = BarbershopSettings.objects.filter(whatsapp_instance_name=instance_name).first()
            if settings:
                if status_state == "open":
                    settings.whatsapp_status = "connected"
                    settings.whatsapp_enabled = True
                    settings.whatsapp_phone = status_data.get("phone") or status_data.get("number") or settings.whatsapp_phone
                elif status_state == "close":
                    settings.whatsapp_status = "disconnected"
                    settings.whatsapp_enabled = False
                elif status_state == "connecting":
                    settings.whatsapp_status = "connecting"
                settings.save(update_fields=['whatsapp_status', 'whatsapp_enabled', 'whatsapp_phone'])
                
        return Response({'success': True})
