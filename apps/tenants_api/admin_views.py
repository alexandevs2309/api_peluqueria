from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from apps.auth_api.models import User
from apps.auth_api.serializers import UserListSerializer
from apps.roles_api.models import Role, UserRole
from .models import Tenant

class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.roles.filter(name='Super-Admin').exists()
        )

class AdminUserManagementViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de usuarios por SuperAdmin"""
    serializer_class = UserListSerializer
    permission_classes = [IsSuperAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'tenant', 'role']
    search_fields = ['email', 'full_name', 'tenant__name']
    ordering_fields = ['date_joined', 'email', 'full_name']
    ordering = ['-date_joined']
    
    def get_queryset(self):
        """SuperAdmin ve todos los usuarios excepto otros SuperAdmins"""
        try:
            return User.objects.exclude(
                roles__name='Super-Admin'
            ).select_related('tenant').prefetch_related('roles')
        except:
            # Fallback si hay problemas con roles
            return User.objects.filter(
                role__in=['ClientAdmin', 'ClientStaff', 'Employee']
            ).select_related('tenant')
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activar usuario"""
        user = self.get_object()
        if user.is_active:
            return Response({
                'message': 'El usuario ya está activo'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.is_active = True
        user.save()
        
        return Response({
            'message': f'Usuario {user.email} activado correctamente'
        })
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Desactivar usuario"""
        user = self.get_object()
        if not user.is_active:
            return Response({
                'message': 'El usuario ya está inactivo'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.is_active = False
        user.save()
        
        return Response({
            'message': f'Usuario {user.email} desactivado correctamente'
        })
    
    @action(detail=True, methods=['post'])
    def change_role(self, request, pk=None):
        """Cambiar rol de usuario"""
        user = self.get_object()
        new_role_name = request.data.get('role')
        
        if not new_role_name:
            return Response({
                'error': 'Rol requerido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            new_role = Role.objects.get(name=new_role_name)
            
            # No permitir asignar Super-Admin
            if new_role.name == 'Super-Admin':
                return Response({
                    'error': 'No se puede asignar rol Super-Admin'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Remover roles actuales y asignar nuevo
            UserRole.objects.filter(user=user).delete()
            UserRole.objects.create(user=user, role=new_role)
            
            # Actualizar campo role del usuario
            user.role = new_role_name
            user.save()
            
            return Response({
                'message': f'Rol cambiado a {new_role_name} para {user.email}'
            })
            
        except Role.DoesNotExist:
            return Response({
                'error': 'Rol no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def change_tenant(self, request, pk=None):
        """Cambiar tenant de usuario"""
        user = self.get_object()
        tenant_id = request.data.get('tenant_id')
        
        if not tenant_id:
            return Response({
                'error': 'ID de tenant requerido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            tenant = Tenant.objects.get(id=tenant_id, is_active=True)
            user.tenant = tenant
            user.save()
            
            return Response({
                'message': f'Usuario {user.email} movido a tenant {tenant.name}'
            })
            
        except Tenant.DoesNotExist:
            return Response({
                'error': 'Tenant no encontrado o inactivo'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Estadísticas de usuarios"""
        try:
            queryset = self.get_queryset()
            total_users = queryset.count()
            active_users = queryset.filter(is_active=True).count()
            
            # Usuarios por rol (usando campo role directamente)
            users_by_role = []
            role_counts = queryset.values('role').annotate(count=Count('role'))
            for item in role_counts:
                if item['role'] and item['role'] != 'SuperAdmin':
                    users_by_role.append({
                        'role': item['role'],
                        'count': item['count']
                    })
            
            # Usuarios por tenant
            users_by_tenant = []
            for tenant in Tenant.objects.filter(is_active=True)[:10]:
                count = queryset.filter(tenant=tenant).count()
                if count > 0:
                    users_by_tenant.append({
                        'tenant_name': tenant.name,
                        'user_count': count
                    })
            
            # Usuarios recientes
            recent_users = []
            for user in queryset.order_by('-date_joined')[:5]:
                recent_users.append({
                    'email': user.email,
                    'full_name': user.full_name,
                    'tenant': user.tenant.name if user.tenant else None,
                    'role': user.role,
                    'created_at': user.date_joined.isoformat()
                })
            
            return Response({
                'total_users': total_users,
                'active_users': active_users,
                'inactive_users': total_users - active_users,
                'users_by_role': users_by_role,
                'users_by_tenant': users_by_tenant,
                'recent_users': recent_users
            })
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Error al obtener estadísticas de usuarios'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def available_roles(self, request):
        """Roles disponibles para asignar"""
        roles = Role.objects.exclude(name='Super-Admin').values('name', 'description')
        return Response(list(roles))
    
    @action(detail=False, methods=['get'])
    def available_tenants(self, request):
        """Tenants disponibles"""
        tenants = Tenant.objects.filter(is_active=True).values('id', 'name')
        return Response(list(tenants))