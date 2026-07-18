from celery import shared_task
from django.utils import timezone
import pytz
from datetime import datetime, timedelta, time
from .models import Employee, WorkSchedule, AttendanceRecord
from apps.settings_api.models import Setting

@shared_task
def auto_process_daily_absences():
    """
    Cron diario que marca inasistencias automáticas al final de la jornada.
    Busca empleados que debieron trabajar hoy y no registran ningún Check-In.
    """
    employees = Employee.objects.filter(is_active=True).select_related('tenant', 'branch')
    
    days_mapping = {
        0: 'monday',
        1: 'tuesday',
        2: 'wednesday',
        3: 'thursday',
        4: 'friday',
        5: 'saturday',
        6: 'sunday'
    }
    
    created_count = 0
    
    for employee in employees:
        tz_name = "America/Santo_Domingo"
        if employee.branch_id:
            setting = Setting.objects.filter(branch_id=employee.branch_id, branch__tenant=employee.tenant).first()
            if setting and setting.timezone:
                tz_name = setting.timezone
        
        try:
            local_tz = pytz.timezone(tz_name)
        except Exception:
            local_tz = pytz.timezone("America/Santo_Domingo")
            
        local_now = timezone.localtime(timezone.now(), local_tz)
        local_date = local_now.date()
        day_name = days_mapping[local_date.weekday()]
        
        # Verificar si hoy trabaja
        schedule_exists = WorkSchedule.objects.filter(employee=employee, day_of_week=day_name).exists()
        if not schedule_exists:
            continue
            
        # Verificar si ya tiene asistencia registrada para hoy
        attendance_exists = AttendanceRecord.objects.filter(employee=employee, work_date=local_date).exists()
        if attendance_exists:
            continue
            
        # Crear falta injustificada
        AttendanceRecord.objects.create(
            employee=employee,
            work_date=local_date,
            status='absent',
            is_justified=False,
            notes="Inasistencia automática al cierre del día"
        )
        created_count += 1
        
    return f"Procesadas {created_count} inasistencias"

@shared_task
def auto_checkout_end_of_day():
    """
    Cierra registros de check-in que se hayan quedado abiertos (sin check_out_at).
    """
    open_attendances = AttendanceRecord.objects.filter(check_out_at__isnull=True).select_related('employee')
    
    closed_count = 0
    days_mapping = {
        0: 'monday',
        1: 'tuesday',
        2: 'wednesday',
        3: 'thursday',
        4: 'friday',
        5: 'saturday',
        6: 'sunday'
    }
    
    for record in open_attendances:
        tz_name = "America/Santo_Domingo"
        employee = record.employee
        if employee.branch_id:
            setting = Setting.objects.filter(branch_id=employee.branch_id, branch__tenant=employee.tenant).first()
            if setting and setting.timezone:
                tz_name = setting.timezone
                
        try:
            local_tz = pytz.timezone(tz_name)
        except Exception:
            local_tz = pytz.timezone("America/Santo_Domingo")
            
        work_date = record.work_date
        day_name = days_mapping[work_date.weekday()]
        
        schedule = WorkSchedule.objects.filter(employee=employee, day_of_week=day_name).first()
        
        if schedule:
            checkout_time = datetime.combine(work_date, schedule.end_time)
            checkout_time = local_tz.localize(checkout_time)
        else:
            checkout_time = datetime.combine(work_date, time(20, 0))
            checkout_time = local_tz.localize(checkout_time)
            
        if record.check_in_at and checkout_time <= record.check_in_at:
            checkout_time = record.check_in_at + timedelta(hours=1)
            
        record.check_out_at = checkout_time
        duration_str = "Cierre automático del sistema"
        record.notes = f"{record.notes} | {duration_str}" if record.notes else duration_str
        record.save(update_fields=['check_out_at', 'notes', 'updated_at'])
        closed_count += 1
        
    return f"Cerradas {closed_count} asistencias abiertas"