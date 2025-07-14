from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from apps.subscriptions_api.permissions import CanAccessReports ,CanExportData
from .serializers import SalesReportSerializer, AppointmentsReportSerializer, EmployeePerformanceSerializer
from rest_framework.permissions import IsAdminUser
from apps.pos_api.models import Sale
from apps.appointments_api.models import Appointment
from apps.employees_api.models import Employee
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Sum
import csv

class SalesReportView(APIView):
    permission_classes = [permissions.IsAuthenticated , CanAccessReports]

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

class ReportExportView(APIView):
    permission_classes = [IsAdminUser ,CanExportData]

    def get(self, request, *args, **kwargs):
        # Validar parámetro format
        export_format = request.query_params.get("format", "csv").lower()
        if export_format != "csv":
            return Response({"detail": "Formato no soportado"}, status=status.HTTP_400_BAD_REQUEST)

        # Filtros opcionales
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        sales = Sale.objects.all()

        if start_date:
            sales = sales.filter(date_time__date__gte=start_date)
        if end_date:
            sales = sales.filter(date_time__date__lte=end_date)

        # Crear respuesta CSV
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="sales_report_{timezone.now().date()}.csv"'

        writer = csv.writer(response)
        writer.writerow(["ID", "Cliente", "Total", "Pagado", "Método de pago", "Fecha"])

        for sale in sales:
            writer.writerow([
                sale.id,
                sale.client.full_name if sale.client else "Sin cliente",
                sale.total,
                sale.paid,
                sale.payment_method,
                sale.date_time.strftime("%Y-%m-%d %H:%M:%S")
            ])

        return response
