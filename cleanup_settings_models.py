#!/usr/bin/env python3
"""
Script para limpiar modelos redundantes en settings_api
Elimina Branch y Setting ya que no se usan en el SaaS actual
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.settings_api.models import Branch, Setting, SettingAuditLog

def cleanup_redundant_models():
    """Eliminar datos de modelos redundantes"""
    print("🧹 Limpiando modelos redundantes...")
    
    # Eliminar datos existentes
    SettingAuditLog.objects.all().delete()
    print("✅ SettingAuditLog eliminados")
    
    Setting.objects.all().delete()
    print("✅ Setting eliminados")
    
    Branch.objects.all().delete()
    print("✅ Branch eliminados")
    
    print("🎉 Limpieza completada!")

if __name__ == "__main__":
    cleanup_redundant_models()