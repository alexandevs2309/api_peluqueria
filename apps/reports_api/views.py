from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .serializers import SalesReportSerializer, AppointmentsReportSerializer, EmployeePerformanceSerializer
from apps.pos_api.models import Sale
from apps.appointments_api.models import Appointment
from apps.employees_api.models import Employee
from django.utils import timezone
from django.db.models import Sum, Count

class SalesReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        sales_qs = Sale.objects.filter(date_time__date=today)

        data = {
            "date": today,
            "total_sales": sales_qs.aggregate(Sum('total'))["total__sum"] or 0,
            "transaction_count": sales_qs.count()
        }

        serializer = SalesReportSerializer(data)
        return Response(serializer.data)


class AppointmentsReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        appointments_qs = Appointment.objects.filter(date_time__date=today)

        data = {
            "date": today,
            "total_appointments": appointments_qs.count(),
            "completed_appointments": appointments_qs.filter(status="completed").count(),
            "cancelled_appointments": appointments_qs.filter(status="cancelled").count()
        }

        serializer = AppointmentsReportSerializer(data)
        return Response(serializer.data)


class EmployeePerformanceReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        appointments_qs = Appointment.objects.filter(date_time__date=today, status="completed")
        performance_data = []
        for employee in Employee.objects.all():
            employee_appointments = appointments_qs.filter(stylist=employee.user)
            total_revenue = employee_appointments.aggregate(Sum('service__price'))["service__price__sum"] or 0
            performance_data.append({
                "employee_id": employee.id,
                "employee_name": str(employee),
                "total_appointments": employee_appointments.count(),
                "total_revenue": total_revenue
            })

        serializer = EmployeePerformanceSerializer(performance_data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
