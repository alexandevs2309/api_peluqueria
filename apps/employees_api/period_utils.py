"""
Utilidades para cálculo de períodos de pago
"""
from datetime import datetime, timedelta
from decimal import Decimal

def get_period_dates(employee, year=None, period_index=None):
    """
    Obtener fechas de inicio y fin del período según payment_frequency del empleado
    
    Args:
        employee: Instancia del empleado
        year: Año del período (default: año actual)
        period_index: Índice del período (default: período actual)
    
    Returns:
        tuple: (start_date, end_date)
    """
    if not year:
        year = datetime.now().year
    
    frequency = getattr(employee, 'payment_frequency', 'biweekly')
    
    if frequency == 'daily':
        if not period_index:
            period_index = datetime.now().timetuple().tm_yday
        start_date = datetime(year, 1, 1) + timedelta(days=period_index - 1)
        end_date = start_date
        return start_date.date(), end_date.date()
    
    elif frequency == 'weekly':
        if not period_index:
            period_index = datetime.now().isocalendar()[1]
        # Semana ISO: lunes a domingo
        jan_1 = datetime(year, 1, 1)
        week_start = jan_1 + timedelta(weeks=period_index - 1)
        # Ajustar al lunes de esa semana
        days_since_monday = week_start.weekday()
        week_start = week_start - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6)
        return week_start.date(), week_end.date()
    
    elif frequency == 'monthly':
        if not period_index:
            period_index = datetime.now().month
        # Para mensual, period_index debe ser 1-12
        if period_index > 12:
            # Si viene un índice de quincena (1-24), convertir a mes
            period_index = ((period_index - 1) // 2) + 1
        start_date = datetime(year, period_index, 1)
        if period_index == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, period_index + 1, 1) - timedelta(days=1)
        return start_date.date(), end_date.date()
    
    else:  # biweekly (default)
        if not period_index:
            # Calcular quincena actual
            today = datetime.now().date()
            _, period_index = calculate_fortnight(today)
        
        month = ((period_index - 1) // 2) + 1
        is_first_half = (period_index % 2) == 1
        
        if is_first_half:
            start_date = datetime(year, month, 1).date()
            end_date = datetime(year, month, 15).date()
        else:
            start_date = datetime(year, month, 16).date()
            if month == 12:
                next_month = datetime(year + 1, 1, 1)
            else:
                next_month = datetime(year, month + 1, 1)
            end_date = (next_month - timedelta(days=1)).date()
        
        return start_date, end_date

def calculate_fortnight(date):
    """Calcular año y número de quincena (1-24)"""
    year = date.year
    month = date.month
    day = date.day
    
    # Quincena 1: días 1-15, Quincena 2: días 16-fin de mes
    fortnight_in_month = 1 if day <= 15 else 2
    fortnight_number = (month - 1) * 2 + fortnight_in_month
    
    return year, fortnight_number

def get_current_period_for_employee(employee):
    """
    Obtener el período actual según la frecuencia del empleado
    
    Returns:
        dict: {'year': int, 'period_index': int, 'start_date': date, 'end_date': date}
    """
    today = datetime.now().date()
    frequency = getattr(employee, 'payment_frequency', 'biweekly')
    
    if frequency == 'daily':
        period_index = today.timetuple().tm_yday
        year = today.year
    elif frequency == 'weekly':
        year, week, _ = today.isocalendar()
        period_index = week
    elif frequency == 'monthly':
        year = today.year
        period_index = today.month
    else:  # biweekly
        year, period_index = calculate_fortnight(today)
    
    start_date, end_date = get_period_dates(employee, year, period_index)
    
    return {
        'year': year,
        'period_index': period_index,
        'start_date': start_date,
        'end_date': end_date,
        'frequency': frequency
    }