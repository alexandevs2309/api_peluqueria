from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from .models import Tenant
import requests

class TenantValidationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if self.is_public_endpoint(request.path):
            return None
            
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
            
        if request.user.is_superuser:
            return None
            
        tenant_from_location = self.get_tenant_from_location(request)
        
        if not tenant_from_location:
            return None
            
        if request.user.tenant and request.user.tenant.id != tenant_from_location.id:
            return JsonResponse({
                'error': 'Acceso denegado: Usuario no pertenece a este tenant geográfico',
                'user_tenant': request.user.tenant.name,
                'location_tenant': tenant_from_location.name,
                'user_ip': self.get_client_ip(request)
            }, status=403)
            
        return None
    
    def is_public_endpoint(self, path):
        public_paths = ['/api/auth/login/', '/api/auth/register/', '/admin/']
        return any(path.startswith(p) for p in public_paths)
    
    def get_tenant_from_location(self, request):
        try:
            ip = self.get_client_ip(request)
            country = self.get_country_from_ip(ip)
            
            # Debug log
            print(f"DEBUG - IP: {ip}, Country: {country}")
            
            if country == 'MX':
                return Tenant.objects.filter(name__icontains='México').first()
            else:
                return Tenant.objects.filter(name__icontains='Basic').first()
        except Exception as e:
            print(f"DEBUG - Error: {e}")
            return Tenant.objects.first()
    
    def get_client_ip(self, request):
        # Obtener IP real del cliente
        ip = request.META.get('HTTP_X_FORWARDED_FOR')
        if ip:
            return ip.split(',')[0].strip()
        
        ip = request.META.get('HTTP_X_REAL_IP')
        if ip:
            return ip
            
        ip = request.META.get('REMOTE_ADDR')
        
        # Si es localhost, obtener IP pública real
        if ip in ['127.0.0.1', 'localhost', '::1']:
            try:
                import requests
                response = requests.get('https://api.ipify.org', timeout=3)
                return response.text.strip()
            except:
                pass
                
        return ip
    
    def get_country_from_ip(self, ip):
        try:
            response = requests.get(f'http://ip-api.com/json/{ip}', timeout=2)
            return response.json().get('countryCode', 'DO')
        except:
            return 'DO'