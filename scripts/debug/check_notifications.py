import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.appointments_api.models import Appointment
from apps.notifications_api.models import InAppNotification

print("=" * 50)
print("APPOINTMENTS IN DATABASE")
print("=" * 50)
appointments = Appointment.objects.all()
print(f"Total appointments: {appointments.count()}")
for apt in appointments:
    print(f"  - ID: {apt.id} | Client: {apt.client.full_name} | Date: {apt.date_time} | Status: {apt.status}")

print("\n" + "=" * 50)
print("NOTIFICATIONS IN DATABASE")
print("=" * 50)
notifications = InAppNotification.objects.all()
print(f"Total notifications: {notifications.count()}")
for notif in notifications:
    print(f"  - ID: {notif.id} | Type: {notif.type} | Title: {notif.title} | Read: {notif.is_read} | Recipient: {notif.recipient.email}")

print("\n" + "=" * 50)
print("APPOINTMENT NOTIFICATIONS")
print("=" * 50)
apt_notifs = InAppNotification.objects.filter(type='appointment')
print(f"Total appointment notifications: {apt_notifs.count()}")
for notif in apt_notifs:
    print(f"  - ID: {notif.id} | Title: {notif.title} | Read: {notif.is_read}")
