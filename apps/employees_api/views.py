from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated , IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.roles_api.permissions import IsActiveAndRolePermission, role_permission_for
from .models import Employee, EmployeeService, WorkSchedule
from apps.auth_api.models import UserRole
from .serializers import EmployeeSerializer, EmployeeServiceSerializer, WorkScheduleSerializer
from .permissions import IsAdminOrOwnStylist, role_permission_for

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
  
    def get_permissions(self):
            if self.action in ['create', 'update', 'partial_update', 'destroy']:
                permission_classes = [IsAuthenticated, IsAdminUser]
            else:
                permission_classes = [IsAuthenticated, role_permission_for(['Admin', 'Stylist']), IsAdminOrOwnStylist]
            return [permission() for permission in permission_classes]

   
   
    def get_queryset(self):
        if UserRole.objects.filter(user=self.request.user, role__name='Admin').exists():
            return Employee.objects.all()
        return Employee.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, role_permission_for(['Admin'])])
    def assign_service(self, request, pk=None):
        employee = self.get_object()
        serializer = EmployeeServiceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(employee=employee)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class WorkScheduleViewSet(viewsets.ModelViewSet):
    queryset = WorkSchedule.objects.all()
    serializer_class = WorkScheduleSerializer
    permission_classes = [IsAdminOrOwnStylist]

    def get_queryset(self):
        if UserRole.objects.filter(user=self.request.user, role__name='Admin').exists():
            return WorkSchedule.objects.all()
        return WorkSchedule.objects.filter(employee__user=self.request.user)

    def perform_create(self, serializer):
        employee = Employee.objects.get(user=self.request.user)
        serializer.save(employee=employee)