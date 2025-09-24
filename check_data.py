#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.appointments_api.models import Appointment
from apps.pos_api.models import Sale
from apps.clients_api.models import Client
from apps.services_api.models import Service
from apps.inventory_api.models import Product
from django.utils import timezone

print('=== CITAS (Appointments) ===')
appointments = Appointment.objects.all()
print(f'Total citas: {appointments.count()}')
for apt in appointments[:5]:
    print(f'  - {apt.date_time.strftime("%Y-%m-%d %H:%M")} | Cliente: {apt.client.full_name if apt.client else "Sin cliente"} | Servicio: {apt.service.name if apt.service else "Sin servicio"} | Estado: {apt.status}')

print('\n=== VENTAS (Sales) ===')
sales = Sale.objects.all()
print(f'Total ventas: {sales.count()}')
for sale in sales[:5]:
    print(f'  - {sale.date_time.strftime("%Y-%m-%d %H:%M")} | Total: ${sale.total} | Cliente: {sale.client.full_name if sale.client else "Sin cliente"} | Método: {sale.payment_method}')

print('\n=== CLIENTES (Clients) ===')
clients = Client.objects.all()
print(f'Total clientes: {clients.count()}')
for client in clients[:5]:
    print(f'  - {client.full_name} | Tel: {client.phone} | Email: {client.email}')

print('\n=== SERVICIOS (Services) ===')
services = Service.objects.all()
print(f'Total servicios: {services.count()}')
for service in services[:5]:
    print(f'  - {service.name} | Precio: ${service.price} | Duración: {service.duration}min')

print('\n=== PRODUCTOS (Products) ===')
products = Product.objects.all()
print(f'Total productos: {products.count()}')
for product in products[:5]:
    print(f'  - {product.name} | Stock: {product.stock} | Precio: ${product.price}')