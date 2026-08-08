#!/usr/bin/env python
"""
Comando Django para limpiar el backlog de producción de usuarios.

Propósito:
    Eliminar el 99% del acceso de usuario manteniendo solo 2 usuarios clave:
    - alexandeadp@gmail.com
    - alexanderdelrosarioperez@gmail.com
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model

from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import UserSubscription
from apps.roles_api.models import Role, UserRole
from apps.clients_api.models import Client
from apps.services_api.models import Service
from apps.appointments_api.models import Appointment
from apps.pos_api.models import Sale, CashRegister, SaleDetail
from apps.billing_api.models import Invoice, PaymentAttempt
from apps.payments_api.models import Payment
from apps.notifications_api.models import Notification, NotificationTemplate
from apps.support_api.models import SupportTicket
from apps.inventory_api.models import Product, ProductCategory
from apps.employees_api.models import Employee
from apps.audit_api.models import AuditLog
from apps.auth_api.models import User

User = get_user_model()


class Command(BaseCommand):
    help = 'Limpia la base de datos de producción eliminando todos los usuarios excepto dos clave'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la eliminación sin modificar la base de datos',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Salta la confirmación para scripts automatizados',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']

        protected_emails = {'alexandeadp@gmail.com', 'alexanderdelrosarioperez@gmail.com'}
        all_users = User.objects.select_related('tenant').all()

        users_to_keep = []
        users_to_delete = []

        for user in all_users:
            if user.email in protected_emails:
                users_to_keep.append(user)
            else:
                users_to_delete.append(user)

        print('=' * 70)
        print('COMANDO DE LIMPIEZA DE PRODUCCIÓN DE USUARIOS')
        print('=' * 70)
        print('')
        print('Usuarios que SE CONSERVARÁN:')
        for u in users_to_keep:
            print(f'  • {u.email} ({u.full_name})')
        print('')
        print('Usuarios que SE ELIMINARÁN:')
        for u in users_to_delete:
            print(f'  • {u.email} ({u.full_name})')
        print('')

        # Recolectar información de impacto
        tenant_ids = set()
        subscription_count = 0
        role_count = 0
        client_count = 0
        service_count = 0
        appointment_count = 0
        sale_count = 0
        cash_register_count = 0
        invoice_count = 0
        payment_attempt_count = 0
        payment_count = 0
        notification_count = 0
        support_ticket_count = 0
        employee_count = 0
        product_count = 0
        category_count = 0
        sale_item_count = 0
        audit_log_count = 0

        for user in users_to_delete:
            if user.tenant:
                tenant_ids.add(user.tenant.id)

            subscription_count += UserSubscription.objects.filter(user=user).count()
            role_count += UserRole.objects.filter(user=user).count()
            client_count += Client.objects.filter(user=user).count()
            employee_count += Employee.objects.filter(user=user).count()
            notification_count += Notification.objects.filter(recipient=user).count()
            support_ticket_count += SupportTicket.objects.filter(created_by=user).count()
            audit_log_count += AuditLog.objects.filter(user=user).count()

            if user.tenant:
                service_count += Service.objects.filter(tenant=user.tenant).count()
                appointment_count += Appointment.objects.filter(tenant=user.tenant).count()
                sale_count += Sale.objects.filter(tenant=user.tenant).count()
                cash_register_count += CashRegister.objects.filter(tenant=user.tenant).count()
                invoice_count += Invoice.objects.filter(tenant=user.tenant).count()
                payment_attempt_count += PaymentAttempt.objects.filter(invoice__tenant=user.tenant).count()
                payment_count += Payment.objects.filter(tenant=user.tenant).count()
                product_count += Product.objects.filter(tenant=user.tenant).count()
                category_count += ProductCategory.objects.filter(tenant=user.tenant).count()
                sale_item_count += SaleDetail.objects.filter(sale__tenant=user.tenant).count()

        print('RESUMEN DE IMPACTO:')
        print('=' * 70)
        print(f'  Usuarios a eliminar:           {len(users_to_delete)}')
        print(f'  Tenants afectados:             {len(tenant_ids)}')
        print(f'  Suscripciones:                 {subscription_count}')
        print(f'  Roles (UserRole):              {role_count}')
        print(f'  Clientes:                      {client_count}')
        print(f'  Empleados:                     {employee_count}')
        print(f'  Servicios:                     {service_count}')
        print(f'  Citas:                         {appointment_count}')
        print(f'  Ventas:                        {sale_count}')
        print(f'  Cajas registradoras:           {cash_register_count}')
        print(f'  Facturas:                      {invoice_count}')
        print(f'  Intentos de pago:              {payment_attempt_count}')
        print(f'  Pagos:                         {payment_count}')
        print(f'  Notificaciones:                {notification_count}')
        print(f'  Tickets de soporte:            {support_ticket_count}')
        print(f'  Productos:                     {product_count}')
        print(f'  Categorías:                    {category_count}')
        print(f'  Detalles de venta:             {sale_item_count}')
        print(f'  Logs de auditoría:             {audit_log_count}')
        print('')

        if dry_run:
            print('MODO DRY-RUN: No se eliminará nada.')
            return

        if not force:
            confirm = input('Escribe DELETE para confirmar: ').strip()
            if confirm != 'DELETE':
                print('\n❌ COMANDO CANCELADO: Se requiere confirmación \'DELETE\'')
                return

        print('\n🗑️  EJECUTANDO: Eliminando registros...')

        deleted_summary = {
            'users': 0,
            'tenants': 0,
            'related': 0,
            'errors': [],
        }

        try:
            with transaction.atomic():
                user_ids = [u.id for u in users_to_delete]

                # 1. Eliminar datos relacionados a usuarios
                print('  Eliminando UserRole...')
                UserRole.objects.filter(user_id__in=user_ids).delete()

                print('  Eliminando Notification...')
                Notification.objects.filter(recipient_id__in=user_ids).delete()

                print('  Eliminando SupportTicket...')
                SupportTicket.objects.filter(created_by_id__in=user_ids).delete()

                print('  Eliminando Client...')
                Client.objects.filter(user_id__in=user_ids).delete()

                print('  Eliminando Employee...')
                Employee.objects.filter(user_id__in=user_ids).delete()

                print('  Eliminando UserSubscription...')
                UserSubscription.objects.filter(user_id__in=user_ids).delete()

                print('  Eliminando AuditLog...')
                AuditLog.objects.filter(user_id__in=user_ids).delete()

                # 2. Eliminar los usuarios
                print('  Eliminando Users...')
                deleted_user_count, _ = User.objects.filter(id__in=user_ids).delete()
                deleted_summary['users'] = deleted_user_count

                # 3. Eliminar tenants que quedan sin usuarios
                tenant_ids_list = list(tenant_ids)
                if tenant_ids_list:
                    tenants_to_check = Tenant.objects.filter(id__in=tenant_ids_list)
                    tenants_to_delete = []

                    for tenant in tenants_to_check:
                        remaining_users = User.objects.filter(tenant=tenant).count()
                        if remaining_users == 0:
                            tenants_to_delete.append(tenant.id)

                    if tenants_to_delete:
                        print(f'  Eliminando {len(tenants_to_delete)} tenants vacíos y sus datos...')

                        # Eliminar datos del tenant
                        Service.objects.filter(tenant_id__in=tenants_to_delete).delete()
                        Product.objects.filter(tenant_id__in=tenants_to_delete).delete()
                        ProductCategory.objects.filter(tenant_id__in=tenants_to_delete).delete()
                        CashRegister.objects.filter(tenant_id__in=tenants_to_delete).delete()
                        Invoice.objects.filter(tenant_id__in=tenants_to_delete).delete()
                        PaymentAttempt.objects.filter(invoice__tenant_id__in=tenants_to_delete).delete()
                        Payment.objects.filter(tenant_id__in=tenants_to_delete).delete()
                        Sale.objects.filter(tenant_id__in=tenants_to_delete).delete()
                        SaleDetail.objects.filter(sale__tenant_id__in=tenants_to_delete).delete()
                        Appointment.objects.filter(tenant_id__in=tenants_to_delete).delete()
                        Client.objects.filter(tenant_id__in=tenants_to_delete).delete()
                        Employee.objects.filter(tenant_id__in=tenants_to_delete).delete()
                        UserSubscription.objects.filter(tenant_id__in=tenants_to_delete).delete()
                        Notification.objects.filter(recipient__tenant_id__in=tenants_to_delete).delete()
                        SupportTicket.objects.filter(tenant_id__in=tenants_to_delete).delete()
                        AuditLog.objects.filter(tenant_id__in=tenants_to_delete).delete()

                        # Eliminar tenants
                        Tenant.objects.filter(id__in=tenants_to_delete).delete()
                        deleted_summary['tenants'] = len(tenants_to_delete)

        except Exception as e:
            deleted_summary['errors'].append(str(e))
            print(f'\n❌ ERROR: {e}')
            raise

        print('')
        print('✅ LIMPIEZA DE PRODUCCIÓN COMPLETADA:')
        print('=' * 70)
        print(f'   Usuarios eliminados: {deleted_summary["users"]}')
        print(f'   Usuarios conservados: {len(users_to_keep)}')
        print(f'   Tenants eliminados: {deleted_summary["tenants"]}')
        print(f'   Errores encontrados: {len(deleted_summary["errors"])}')
        print('')
        print('   Los usuarios de producción restantes son:')
        for u in users_to_keep:
            print(f'   • {u.email}')
        print('=' * 70)