from datetime import date, timedelta

from django.db.models import Count, Sum, Q
from django.utils import timezone


def sales_summary(tenant, branch=None, period="today"):
    from apps.pos_api.models import Sale

    now = timezone.now()
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    qs = Sale.objects.filter(tenant=tenant, created_at__gte=start, status="completed")
    if branch:
        qs = qs.filter(branch=branch)

    stats = qs.aggregate(
        total=Sum("total"),
        count=Count("id"),
    )

    by_payment = list(
        qs.values("payment_method").annotate(total=Sum("total"), count=Count("id")).order_by("-total")
    )

    return {
        "period": period,
        "total": float(stats["total"] or 0),
        "count": stats["count"] or 0,
        "by_payment_method": [
            {"method": p["payment_method"], "total": float(p["total"] or 0), "count": p["count"]}
            for p in by_payment
        ],
    }


def appointments_list(tenant, branch=None, status=None, day=None):
    from apps.appointments_api.models import Appointment

    now = timezone.now()
    if day:
        start = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()))
        end = start + timedelta(days=1)
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

    qs = Appointment.objects.filter(tenant=tenant, date_time__gte=start, date_time__lt=end)
    if branch:
        qs = qs.filter(branch=branch)
    if status:
        qs = qs.filter(status=status)

    qs = qs.select_related("client", "stylist", "service").order_by("date_time")

    items = []
    for a in qs[:50]:
        items.append({
            "id": str(a.id),
            "time": a.date_time.strftime("%H:%M"),
            "client": str(a.client) if a.client else None,
            "stylist": str(a.stylist) if a.stylist else None,
            "service": str(a.service) if a.service else None,
            "status": a.status,
        })

    return {"date": (day or date.today()).isoformat(), "count": len(items), "appointments": items}


def clients_search(tenant, query, limit=20):
    from apps.clients_api.models import Client

    qs = Client.objects.filter(tenant=tenant).filter(
        Q(full_name__icontains=query) | Q(phone__icontains=query) | Q(email__icontains=query)
    )[:limit]

    return [
        {
            "id": str(c.id),
            "name": c.full_name,
            "phone": c.phone,
            "email": c.email,
            "loyalty_points": c.loyalty_points,
        }
        for c in qs
    ]


def services_list(tenant, category=None):
    from apps.services_api.models import Service

    qs = Service.objects.filter(tenant=tenant, is_active=True)
    if category:
        qs = qs.filter(category__name__icontains=category)

    return [
        {
            "id": str(s.id),
            "name": s.name,
            "category": str(s.category) if s.category else None,
            "price": float(s.price),
            "duration": s.duration,
        }
        for s in qs.select_related("category")[:50]
    ]


def inventory_alerts(tenant):
    from django.db.models import F
    from apps.inventory_api.models import Product

    low_stock = Product.objects.filter(
        tenant=tenant, stock__lte=F("min_stock"), is_active=True
    ).select_related("category", "supplier")[:20]

    return [
        {
            "id": str(p.id),
            "name": p.name,
            "sku": p.sku,
            "stock": p.stock,
            "min_stock": p.min_stock,
            "category": str(p.category) if p.category else None,
            "supplier": str(p.supplier) if p.supplier else None,
        }
        for p in low_stock
    ]


def employees_list(tenant, branch=None):
    from apps.employees_api.models import Employee

    qs = Employee.objects.filter(tenant=tenant, is_active=True).select_related("user")
    if branch:
        qs = qs.filter(branch=branch)

    return [
        {
            "id": str(e.id),
            "name": str(e.user) if e.user else None,
            "role": e.user.role if e.user else None,
            "specialty": e.specialty,
            "payment_type": e.payment_type,
            "commission_rate": float(e.commission_rate) if e.commission_rate else None,
        }
        for e in qs[:30]
    ]


def employee_performance(tenant, employee_id=None, period="month"):
    from apps.employees_api.models import Employee
    from apps.pos_api.models import Sale

    now = timezone.now()
    if period == "month":
        start = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    employees = Employee.objects.filter(tenant=tenant, is_active=True).select_related("user")
    if employee_id:
        employees = employees.filter(id=employee_id)

    results = []
    for e in employees:
        sales = Sale.objects.filter(
            tenant=tenant, employee=e, created_at__gte=start, status="completed"
        )
        stats = sales.aggregate(total=Sum("total"), count=Count("id"))
        results.append({
            "employee_id": str(e.id),
            "name": str(e.user) if e.user else None,
            "sales_total": float(stats["total"] or 0),
            "sales_count": stats["count"] or 0,
        })

    return {"period": period, "employees": sorted(results, key=lambda x: x["sales_total"], reverse=True)}
