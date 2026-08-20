import json
import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import tools

logger = logging.getLogger(__name__)

TOOL_MAP = {
    "sales_summary": tools.sales_summary,
    "appointments_list": tools.appointments_list,
    "clients_search": tools.clients_search,
    "services_list": tools.services_list,
    "inventory_alerts": tools.inventory_alerts,
    "employees_list": tools.employees_list,
    "employee_performance": tools.employee_performance,
}

TOOL_DEFINITIONS = [
    {
        "name": "sales_summary",
        "description": "Resumen de ventas del día, semana o mes. Incluye total, cantidad y desglose por método de pago.",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "enum": ["today", "week", "month"], "default": "today"},
            },
        },
    },
    {
        "name": "appointments_list",
        "description": "Lista de citas del día o de una fecha específica. Incluye cliente, estilista, servicio y estado.",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filtrar por estado: scheduled, completed, cancelled, no_show"},
                "day": {"type": "string", "description": "Fecha en formato YYYY-MM-DD"},
            },
        },
    },
    {
        "name": "clients_search",
        "description": "Buscar clientes por nombre, teléfono o email. Retorna información básica y puntos de lealtad.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Texto de búsqueda (nombre, teléfono o email)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "services_list",
        "description": "Listar servicios disponibles con precio y duración.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Filtrar por categoría de servicio"},
            },
        },
    },
    {
        "name": "inventory_alerts",
        "description": "Productos con stock bajo el mínimo. Alerta de reposición.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "employees_list",
        "description": "Listar empleados activos con su especialidad y tipo de pago.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "employee_performance",
        "description": "Rendimiento de empleados: ventas totales y cantidad de ventas en un período.",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "enum": ["week", "month"], "default": "month"},
            },
        },
    },
]


class McpToolsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"tools": TOOL_DEFINITIONS})


class McpCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tool_name = request.data.get("tool")
        params = request.data.get("params", {})

        if not tool_name:
            return Response({"error": "tool is required"}, status=status.HTTP_400_BAD_REQUEST)

        tool_fn = TOOL_MAP.get(tool_name)
        if not tool_fn:
            return Response({"error": f"Unknown tool: {tool_name}"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = tool_fn(tenant=request.tenant, **params)
            return Response({"tool": tool_name, "result": result})
        except TypeError as e:
            return Response({"error": f"Invalid params: {e}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("MCP tool error: %s", tool_name)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


KEYWORD_MAP = [
    (["vend", "ventas", "venta", "factura", "facturado", "cobr", "ingreso"], "sales_summary"),
    (["cita", "citas", "appointment", "reserva", "reservación"], "appointments_list"),
    (["cliente", "clientes", "client", "buscar cliente", "phone", "teléfono"], "clients_search"),
    (["servicio", "servicios", "service", "corte", "lavado", "tinte"], "services_list"),
    (["inventar", "stock", "producto", "productos", "agot", "repuesto"], "inventory_alerts"),
    (["empleado", "empleados", "employee", "estilista", "estilistas", "personal"], "employees_list"),
    (["rendimiento", "performance", "desempeño", "comisiones"], "employee_performance"),
]


def _detect_tool(message):
    msg = message.lower()
    for keywords, tool in KEYWORD_MAP:
        for kw in keywords:
            if kw in msg:
                return tool, {}
    return None, None


class McpChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        message = request.data.get("message", "").strip()
        if not message:
            return Response({"error": "message is required"}, status=status.HTTP_400_BAD_REQUEST)

        tool_name, default_params = _detect_tool(message)

        if not tool_name:
            return Response({
                "response": "Puedo ayudarte con: ventas, citas, clientes, servicios, inventario, empleados y rendimiento. ¿Qué necesitas?",
                "tool_called": None,
            })

        tool_fn = TOOL_MAP[tool_name]
        params = default_params or {}

        if tool_name == "clients_search":
            params["query"] = message

        try:
            result = tool_fn(tenant=request.tenant, **params)
            summary = _format_response(tool_name, result)
            return Response({"response": summary, "tool_called": tool_name, "data": result})
        except Exception as e:
            logger.exception("MCP chat error: %s", tool_name)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _format_response(tool_name, data):
    if tool_name == "sales_summary":
        count = data.get("count", 0)
        total = data.get("total", 0)
        period = {"today": "hoy", "week": "esta semana", "month": "este mes"}.get(data.get("period"), "hoy")
        return f"{count} ventas {period} por RD${total:,.2f}"

    if tool_name == "appointments_list":
        count = data.get("count", 0)
        if count == 0:
            return "No hay citas para esta fecha"
        items = data.get("appointments", [])
        lines = [f"{a['time']} - {a['client']} ({a['status']})" for a in items[:10]]
        return f"{count} citas:\n" + "\n".join(lines)

    if tool_name == "clients_search":
        if not data:
            return "No se encontraron clientes"
        lines = [f"{c['name']} - {c['phone']} ({c['loyalty_points']} pts)" for c in data[:5]]
        return "Clientes encontrados:\n" + "\n".join(lines)

    if tool_name == "services_list":
        if not data:
            return "No hay servicios disponibles"
        lines = [f"{s['name']} - RD${s['price']:.0f} ({s['duration']} min)" for s in data[:10]]
        return "Servicios:\n" + "\n".join(lines)

    if tool_name == "inventory_alerts":
        if not data:
            return "No hay productos con stock bajo"
        lines = [f"{p['name']} - stock: {p['stock']} (mínimo: {p['min_stock']})" for p in data[:5]]
        return "Productos con stock bajo:\n" + "\n".join(lines)

    if tool_name == "employees_list":
        if not data:
            return "No hay empleados activos"
        lines = [f"{e['name']} - {e['specialty'] or 'General'} ({e['payment_type']})" for e in data[:10]]
        return "Empleados:\n" + "\n".join(lines)

    if tool_name == "employee_performance":
        emps = data.get("employees", [])
        if not emps:
            return "No hay datos de rendimiento"
        lines = [f"{e['name']}: RD${e['sales_total']:,.2f} ({e['sales_count']} ventas)" for e in emps[:5]]
        return f"Rendimiento ({data.get('period')}):\n" + "\n".join(lines)

    return json.dumps(data, ensure_ascii=False)
