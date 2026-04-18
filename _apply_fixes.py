"""
Script de fixes de seguridad - ejecutar desde api_peluqueria/
"""
import os

CRLF = '\r\n'

def fix_file(path, old, new, label):
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8')
    if old in content:
        content = content.replace(old, new, 1)
        with open(path, 'wb') as f:
            f.write(content.encode('utf-8'))
        print(f'OK: {label}')
    else:
        print(f'SKIP (not found): {label}')

# ─── FIX 1: calendar_events - filtro de tenant ───────────────────────────────
fix_file(
    'apps/appointments_api/views.py',
    (
        '    appointments = Appointment.objects.filter(\r\n'
        '        date_time__gte=start_date,\r\n'
        '        date_time__lte=end_date\r\n'
        '    )\r\n'
        '    \r\n'
        '    events = []'
    ),
    (
        '    appointments = Appointment.objects.filter(\r\n'
        '        date_time__gte=start_date,\r\n'
        '        date_time__lte=end_date\r\n'
        '    )\r\n'
        '\r\n'
        '    # Filtro de tenant obligatorio - previene fuga cross-tenant\r\n'
        '    if not request.user.is_superuser:\r\n'
        '        if not hasattr(request, \'tenant\') or not request.tenant:\r\n'
        '            return Response([], status=200)\r\n'
        '        appointments = appointments.filter(client__tenant=request.tenant)\r\n'
        '\r\n'
        '    events = []'
    ),
    'Fix 1: calendar_events tenant filter'
)

# ─── FIX 2: PromotionViewSet.get_queryset - filtro de tenant ─────────────────
fix_file(
    'apps/pos_api/views.py',
    (
        '    def get_queryset(self):\r\n'
        '        return Promotion.objects.filter(is_active=True)'
    ),
    (
        '    def get_queryset(self):\r\n'
        '        user = self.request.user\r\n'
        '        if user.is_superuser:\r\n'
        '            return Promotion.objects.filter(is_active=True)\r\n'
        '        if not hasattr(self.request, \'tenant\') or not self.request.tenant:\r\n'
        '            return Promotion.objects.none()\r\n'
        '        return Promotion.objects.filter(is_active=True, tenant=self.request.tenant)'
    ),
    'Fix 2: PromotionViewSet tenant filter'
)

# ─── FIX 3: pos_categories - filtro de tenant ────────────────────────────────
fix_file(
    'apps/pos_api/views.py',
    (
        '        # Obtener categorías de productos (Service no tiene category)\r\n'
        '        product_categories = list(Product.objects.filter(\r\n'
        '            is_active=True,\r\n'
        '            category__isnull=False\r\n'
        '        ).exclude(category=\'\').values_list(\'category\', flat=True).distinct())'
    ),
    (
        '        # Obtener categorías de productos filtradas por tenant\r\n'
        '        tenant = getattr(request, \'tenant\', None)\r\n'
        '        product_qs = Product.objects.filter(is_active=True, category__isnull=False).exclude(category=\'\')\r\n'
        '        if not request.user.is_superuser and tenant:\r\n'
        '            product_qs = product_qs.filter(tenant=tenant)\r\n'
        '        elif not request.user.is_superuser:\r\n'
        '            product_qs = Product.objects.none()\r\n'
        '        product_categories = list(product_qs.values_list(\'category\', flat=True).distinct())'
    ),
    'Fix 3: pos_categories tenant filter'
)

# ─── FIX 4: active_promotions - reemplazar hardcoded con DB real ──────────────
fix_file(
    'apps/pos_api/views.py',
    (
        'def active_promotions(request):\r\n'
        '    """Promociones activas - placeholder"""\r\n'
        '    promotions = [\r\n'
        '        {\r\n'
        '            \'id\': 1,\r\n'
        '            \'name\': \'2x1 en Servicios\',\r\n'
        '            \'type\': \'buy_x_get_y\',\r\n'
        '            \'conditions\': {\'buy\': 2, \'get\': 1, \'category\': \'service\'},\r\n'
        '            \'active\': True\r\n'
        '        },\r\n'
        '        {\r\n'
        '            \'id\': 2,\r\n'
        '            \'name\': \'10% desc. productos +$50\',\r\n'
        '            \'type\': \'percentage\',\r\n'
        '            \'conditions\': {\'min_amount\': 50, \'discount\': 0.1},\r\n'
        '            \'active\': True\r\n'
        '        }\r\n'
        '    ]\r\n'
        '    \r\n'
        '    from apps.utils.response_formatter import StandardResponse\r\n'
        '    return Response(StandardResponse.list_response(\r\n'
        '        results=promotions,\r\n'
        '        count=len(promotions)\r\n'
        '    ))'
    ),
    (
        'def active_promotions(request):\r\n'
        '    """Promociones activas del tenant"""\r\n'
        '    if not request.user.is_superuser:\r\n'
        '        if not hasattr(request, \'tenant\') or not request.tenant:\r\n'
        '            from apps.utils.response_formatter import StandardResponse\r\n'
        '            return Response(StandardResponse.list_response(results=[], count=0))\r\n'
        '        promotions_qs = Promotion.objects.filter(is_active=True, tenant=request.tenant)\r\n'
        '    else:\r\n'
        '        promotions_qs = Promotion.objects.filter(is_active=True)\r\n'
        '    serializer = PromotionSerializer(promotions_qs, many=True)\r\n'
        '    from apps.utils.response_formatter import StandardResponse\r\n'
        '    return Response(StandardResponse.list_response(\r\n'
        '        results=serializer.data,\r\n'
        '        count=promotions_qs.count()\r\n'
        '    ))'
    ),
    'Fix 4: active_promotions real DB data'
)

# ─── FIX 5: SaleViewSet.get_queryset - eliminar restriccion user=request.user ─
fix_file(
    'apps/pos_api/views.py',
    (
        '            # Filtrar por tenant del request\r\n'
        '            qs = Sale.objects.select_related(\r\n'
        '                \'client\', \'employee\', \'user\', \'user__tenant\', \'tenant\'\r\n'
        '            ).prefetch_related(\'details\', \'details__content_type\').filter(\r\n'
        '                tenant=self.request.tenant\r\n'
        '            )\r\n'
        '            \r\n'
        '            # Si no es staff, solo sus propias ventas\r\n'
        '            if not user.is_staff:\r\n'
        '                qs = qs.filter(user=user)'
    ),
    (
        '            # Filtrar por tenant del request - todos los roles ven ventas del tenant\r\n'
        '            qs = Sale.objects.select_related(\r\n'
        '                \'client\', \'employee\', \'user\', \'user__tenant\', \'tenant\'\r\n'
        '            ).prefetch_related(\'details\', \'details__content_type\').filter(\r\n'
        '                tenant=self.request.tenant\r\n'
        '            )'
    ),
    'Fix 5: SaleViewSet remove user=request.user restriction'
)

# ─── FIX 6: Manager - agregar add_sale a permisos implicitos ─────────────────
fix_file(
    'apps/core/tenant_permissions.py',
    (
        '        \'Manager\': [\r\n'
        '            \'view_appointment\', \'add_appointment\', \'change_appointment\',\r\n'
        '            \'cancel_appointment\', \'complete_appointment\',\r\n'
        '            \'view_client\', \'add_client\', \'change_client\',\r\n'
        '            \'view_employee\',\r\n'
        '            \'view_service\',\r\n'
        '            \'view_employee_reports\', \'view_sales_reports\', \'view_kpi_dashboard\',\r\n'
        '        ],'
    ),
    (
        '        \'Manager\': [\r\n'
        '            \'view_appointment\', \'add_appointment\', \'change_appointment\',\r\n'
        '            \'cancel_appointment\', \'complete_appointment\',\r\n'
        '            \'view_client\', \'add_client\', \'change_client\',\r\n'
        '            \'view_employee\',\r\n'
        '            \'view_service\',\r\n'
        '            \'view_sale\', \'add_sale\', \'view_cashregister\', \'add_cashregister\',\r\n'
        '            \'change_cashregister\', \'view_promotion\', \'view_financial_reports\',\r\n'
        '            \'view_employee_reports\', \'view_sales_reports\', \'view_kpi_dashboard\',\r\n'
        '        ],'
    ),
    'Fix 6: Manager add_sale implicit permission'
)

print('Todos los fixes de backend aplicados.')
