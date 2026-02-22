from apps.appointments_api.models import Appointment
from apps.notifications_api.models import InAppNotification
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 60)
print("BACKEND AUDIT - NOTIFICATION SYSTEM")
print("=" * 60)

# 1. Verificar modelo InAppNotification
print("\n1. MODELO InAppNotification:")
print(f"   - Campos: {[f.name for f in InAppNotification._meta.get_fields()]}")
print(f"   - type field exists: {'type' in [f.name for f in InAppNotification._meta.get_fields()]}")
print(f"   - is_read field exists: {'is_read' in [f.name for f in InAppNotification._meta.get_fields()]}")

# 2. Verificar citas existentes
print("\n2. CITAS EXISTENTES:")
appointments = Appointment.objects.all()[:5]
print(f"   Total citas: {Appointment.objects.count()}")
for apt in appointments:
    print(f"   - ID={apt.id}, Stylist={apt.stylist.email}, Created={apt.created_at}")

# 3. Verificar notificaciones existentes
print("\n3. NOTIFICACIONES EXISTENTES:")
notifications = InAppNotification.objects.all()[:10]
print(f"   Total notificaciones: {InAppNotification.objects.count()}")
for notif in notifications:
    print(f"   - ID={notif.id}, Type={notif.type}, Recipient={notif.recipient.email}, Read={notif.is_read}, Title={notif.title}")

# 4. Verificar notificaciones de tipo appointment
print("\n4. NOTIFICACIONES TIPO 'appointment':")
apt_notifs = InAppNotification.objects.filter(type='appointment')
print(f"   Total: {apt_notifs.count()}")
for notif in apt_notifs:
    print(f"   - ID={notif.id}, Recipient={notif.recipient.email}, Read={notif.is_read}")

# 5. Verificar usuario actual (alejav.zuniga@gmail.com)
print("\n5. NOTIFICACIONES PARA alejav.zuniga@gmail.com:")
try:
    user = User.objects.get(email='alejav.zuniga@gmail.com')
    user_notifs = InAppNotification.objects.filter(recipient=user)
    print(f"   Total notificaciones: {user_notifs.count()}")
    for notif in user_notifs:
        print(f"   - ID={notif.id}, Type={notif.type}, Read={notif.is_read}, Title={notif.title}")
    
    apt_user_notifs = user_notifs.filter(type='appointment', is_read=False)
    print(f"\n   Notificaciones appointment NO LEÍDAS: {apt_user_notifs.count()}")
except User.DoesNotExist:
    print("   Usuario no encontrado")

print("\n" + "=" * 60)
print("DIAGNÓSTICO:")
print("=" * 60)

# Diagnóstico
total_apts = Appointment.objects.count()
total_apt_notifs = InAppNotification.objects.filter(type='appointment').count()

if total_apts > total_apt_notifs:
    print(f"⚠️  PROBLEMA: Hay {total_apts} citas pero solo {total_apt_notifs} notificaciones")
    print("   El signal NO está creando notificaciones para todas las citas")
else:
    print(f"✅ Signal funcionando: {total_apt_notifs} notificaciones para {total_apts} citas")
