from celery import shared_task
from django.db.models import Sum, Count
from django.db import models
from .models import Employee

# Tareas obsoletas eliminadas - el sistema de nómina ahora usa PayrollPeriod directamente