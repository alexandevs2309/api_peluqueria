from datetime import datetime, timedelta, date
from django.template.loader import render_to_string
from django.conf import settings
import logging
from typing import Tuple, Union

def compute_period_range(frequency: str, reference_date) -> Tuple:
    """
    Compute period range for given frequency and reference date.
    Returns: (period_start, period_end, period_year, period_index)
    """
    if isinstance(reference_date, str):
        reference_date = datetime.strptime(reference_date, '%Y-%m-%d').date()
    
    year = reference_date.year
    
    if frequency == 'daily':
        period_start = reference_date
        period_end = reference_date
        period_index = reference_date.timetuple().tm_yday  # Day of year (1-365/366)
        
    elif frequency == 'weekly':
        # Monday-based weeks
        days_since_monday = reference_date.weekday()
        period_start = reference_date - timedelta(days=days_since_monday)
        period_end = period_start + timedelta(days=6)
        period_index = period_start.isocalendar()[1]  # ISO week number (1-52/53)
        
    elif frequency == 'biweekly':
        # Existing fortnight logic (1-15, 16-end)
        day = reference_date.day
        month = reference_date.month
        if day <= 15:
            period_start = reference_date.replace(day=1)
            period_end = reference_date.replace(day=15)
            fortnight_in_month = 1
        else:
            period_start = reference_date.replace(day=16)
            if month == 12:
                next_month = reference_date.replace(year=year+1, month=1, day=1)
            else:
                next_month = reference_date.replace(month=month+1, day=1)
            last_day = (next_month - timedelta(days=1)).day
            period_end = reference_date.replace(day=last_day)
            fortnight_in_month = 2
        period_index = (month - 1) * 2 + fortnight_in_month  # 1-24
        
    elif frequency == 'monthly':
        month = reference_date.month
        period_start = reference_date.replace(day=1)
        if month == 12:
            next_month = reference_date.replace(year=year+1, month=1, day=1)
        else:
            next_month = reference_date.replace(month=month+1, day=1)
        period_end = next_month - timedelta(days=1)
        period_index = reference_date.month  # 1-12
        
    else:
        raise ValueError(f"Unsupported frequency: {frequency}")
    
    return period_start, period_end, year, period_index



def date_to_year_fortnight(reference_date: Union[str, date, datetime]) -> Tuple[int, int]:
    """
    Convert reference date to year and fortnight for earnings API fallback.
    
    This function exists as a temporary fallback while frontend normalizes
    to use year/fortnight parameters directly instead of frequency/reference_date.
    
    Args:
        reference_date: ISO date string ("YYYY-MM-DD") or date/datetime object
        
    Returns:
        Tuple of (year, fortnight) where fortnight is 1-24
        
    Raises:
        ValueError: If reference_date is invalid or unparseable
    """
    try:
        if isinstance(reference_date, str):
            parsed_date = datetime.strptime(reference_date, '%Y-%m-%d').date()
        elif isinstance(reference_date, datetime):
            parsed_date = reference_date.date()
        elif isinstance(reference_date, date):
            parsed_date = reference_date
        else:
            raise ValueError(f"Invalid reference_date type: {type(reference_date)}")
            
        year = parsed_date.year
        month = parsed_date.month
        day = parsed_date.day
        
        # Calculate fortnight: (month - 1) * 2 + (1 if day <= 15 else 2)
        fortnight_in_month = 1 if day <= 15 else 2
        fortnight = (month - 1) * 2 + fortnight_in_month
        
        # Validate fortnight range (1-24)
        if not (1 <= fortnight <= 24):
            raise ValueError(f"Calculated fortnight {fortnight} is out of valid range 1-24")
            
        return year, fortnight
        
    except ValueError as e:
        if "time data" in str(e) or "does not match format" in str(e):
            raise ValueError("Invalid reference_date format. Expected YYYY-MM-DD.")
        raise e
    except Exception as e:
        raise ValueError(f"Error parsing reference_date: {str(e)}")

def generate_payroll_batch_pdf(batch):
    """
    Generar PDF de lote de nómina usando WeasyPrint
    """
    try:
        # Intentar con WeasyPrint primero
        import weasyprint
        
        # Renderizar template HTML
        html_content = render_to_string('employees/payroll_batch_pdf.html', {
            'batch': batch,
            'items': batch.items.select_related('employee__user').all(),
            'generated_at': datetime.now()
        })
        
        # Generar PDF
        pdf = weasyprint.HTML(string=html_content).write_pdf()
        logger.info(f"PDF generado con WeasyPrint para batch {batch.id}")
        return pdf
        
    except ImportError:
        logger.warning("WeasyPrint no disponible, usando ReportLab como fallback")
        
        # Fallback a ReportLab
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from io import BytesIO
        
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        
        # Contenido básico del PDF
        p.drawString(100, 750, f"Lote de Nómina: {batch.batch_number}")
        p.drawString(100, 730, f"Período: {batch.period_start} - {batch.period_end}")
        p.drawString(100, 710, f"Total: ${batch.total_amount}")
        
        p.showPage()
        p.save()
        
        logger.info(f"PDF generado con ReportLab para batch {batch.id}")
        return buffer.getvalue()