from apps.appointments_api.models import Appointment
from apps.notifications_api.models import InAppNotification

print(f'Total citas: {Appointment.objects.count()}')
print(f'Total notificaciones: {InAppNotification.objects.count()}')
print('---')

for apt in Appointment.objects.all()[:5]:
    stylist_email = apt.stylist.email if apt.stylist else None
    print(f'Cita ID={apt.id}, Stylist={stylist_email}, Created={apt.created_at}')

print('---')
print('Notificaciones:')
for notif in InAppNotification.objects.all()[:5]:
    print(f'ID={notif.id}, Recipient={notif.recipient.email}, Title={notif.title}, Read={notif.is_read}')
