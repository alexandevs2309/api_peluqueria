import json
import logging
import re
from datetime import date, timedelta

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import tools
from .llm import SYSTEM_PROMPT_MCP, _resolve_provider, run_tool_chat

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
        "description": "Buscar clientes por nombre, teléfono o email.",
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


# ---------------------------------------------------------------------------
# Offline intent detection (fallback when no LLM key is configured)
# ---------------------------------------------------------------------------

_ACCENT_MAP = str.maketrans('áéíóúñü', 'aeiounu')


def _normalize(text: str) -> str:
    return text.lower().translate(_ACCENT_MAP)


def _detect_tool_offline(message: str):
    m = _normalize(message)

    # period detection
    period = "today"
    if any(k in m for k in ("semana", "semanal", "weekly", "ultimos 7", "ultimas 7", "ultimos dias")):
        period = "week"
    elif any(k in m for k in ("mes", "mensual", "month", "ultimos 30", "ultimo mes")):
        period = "month"

    # date detection
    day = None
    has_tomorrow = "manana" in m
    has_morning = any(k in m for k in ("esta manana", "por la manana", "de la manana"))
    if has_tomorrow and not has_morning:
        day = (date.today() + timedelta(days=1)).isoformat()
    elif "hoy" in m:
        day = date.today().isoformat()
    elif "ayer" in m:
        day = (date.today() - timedelta(days=1)).isoformat()

    mdate = re.search(r'(\d{1,2})\D(\d{1,2})(?:\D(\d{2,4}))?$', m)
    if mdate:
        try:
            year = int(mdate.group(3)) if mdate.group(3) else date.today().year
            day = date(year, int(mdate.group(2)), int(mdate.group(1))).isoformat()
        except ValueError:
            pass

    # appointment status
    appt_status = None
    if any(k in m for k in ("pendient", "programad", "por venir", "confirmad", "reservad", "activa")):
        appt_status = "scheduled"
    elif any(k in m for k in ("completad", "realizad", "cobrad", "pagad", "hech", "finalizad")):
        appt_status = "completed"
    elif "cancelad" in m:
        appt_status = "cancelled"
    elif any(k in m for k in ("ausente", "no asist", "no show", "falto", "no vino")):
        appt_status = "no_show"

    # appointments
    if any(k in m for k in ("cita", "appointment", "reserva", "calendario")):
        params = {"day": day} if day else {}
        if appt_status:
            params["status"] = appt_status
        return "appointments_list", params

    # sales
    if any(k in m for k in ("venta", "ventas", "vend", "factura", "cobr", "ingreso", "facturado")):
        return "sales_summary", {"period": period}

    # employee performance
    if any(k in m for k in ("rendimiento", "performance", "desempeno", "comision", "comisiones")):
        return "employee_performance", {"period": period}

    # employees list
    if any(k in m for k in ("empleado", "empleados", "employee", "estilista", "estilistas", "personal")):
        return "employees_list", {}

    # inventory
    if any(k in m for k in ("inventar", "stock", "producto", "productos", "agot", "repuesto")):
        return "inventory_alerts", {}

    # services
    if any(k in m for k in ("servicio", "servicios", "service", "corte", "lavado", "tinte")):
        return "services_list", {}

    # clients search
    if any(k in m for k in ("cliente", "clientes", "client")):
        q = re.sub(
            r'^(buscar|busca|busque|encontrar|encuentra|buscame|ver|mostrar|dime|quien|quienes)\s+(al|la|el|los|las|del|de|un|una|sus|tu)?\s*',
            '', m
        ).strip()
        if len(q) < 2:
            q = message.strip()
        return "clients_search", {"query": q}

    return None, None


FRIENDLY_NO_INTENT = (
    "Puedo ayudarte con información de tu negocio: ventas, citas, clientes, servicios, "
    "inventario, empleados o rendimiento. Prueba por ejemplo \"ventas de hoy\", "
    "\"citas de mañana\" o \"buscar cliente Juan\"."
)


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------

class McpChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        message = request.data.get("message", "").strip()
        if not message:
            return Response({"error": "message is required"}, status=status.HTTP_400_BAD_REQUEST)

        history = request.data.get("history") or []
        if not isinstance(history, list):
            history = []

        tenant = getattr(request, "tenant", None)

        # --- 1. LLM path (tool-calling) ---
        if _resolve_provider() is not None:
            try:
                response_text, tool_names, tool_data = run_tool_chat(
                    tenant=tenant,
                    history=history,
                    user_message=message,
                    tools=TOOL_DEFINITIONS,
                    tool_map=TOOL_MAP,
                    system=SYSTEM_PROMPT_MCP,
                )
                if response_text is not None:
                    return Response({
                        "response": response_text,
                        "tool_called": tool_names[0] if tool_names else None,
                        "data": tool_data,
                    }, status=status.HTTP_200_OK)
            except Exception as e:
                logger.exception("LLM MCP failed, falling back: %s", e)

        # --- 2. Offline fallback ---
        try:
            tool_name, params = _detect_tool_offline(message)
            if tool_name:
                tool_fn = TOOL_MAP[tool_name]
                if tool_name == "clients_search" and not params.get("query"):
                    params["query"] = message
                result = tool_fn(tenant=tenant, **params)
                return Response({
                    "response": _format_response(tool_name, result),
                    "tool_called": tool_name,
                    "data": result,
                }, status=status.HTTP_200_OK)

            return Response({
                "response": FRIENDLY_NO_INTENT,
                "tool_called": None,
                "data": None,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("MCP fallback error: %s", e)
            return Response({
                "response": "Ocurrió un error al consultarlo. Intenta de nuevo o escribe \"ayuda\".",
                "tool_called": None,
                "data": None,
            }, status=status.HTTP_200_OK)


def _format_response(tool_name, data):
    if tool_name == "sales_summary":
        count = data.get("count", 0)
        total = data.get("total", 0)
        period = {"today": "hoy", "week": "esta semana", "month": "este mes"}.get(data.get("period"), "hoy")
        return f"{count} ventas {period} por RD${total:,.2f}"

    if tool_name == "appointments_list":
        count = data.get("count", 0)
        if count == 0:
            return "No hay citas para esta fecha."
        items = data.get("appointments", [])
        lines = [f"{a['time']} - {a['client']} ({a['status']})" for a in items[:10]]
        return f"{count} citas:\n" + "\n".join(lines)

    if tool_name == "clients_search":
        if not data:
            return "No se encontraron clientes con ese dato."
        lines = [f"{c['name']} - {c['phone']} ({c['loyalty_points']} pts)" for c in data[:5]]
        return "Clientes:\n" + "\n".join(lines)

    if tool_name == "services_list":
        if not data:
            return "No hay servicios registrados."
        lines = [f"{s['name']} - RD${s['price']:.0f} ({s['duration']} min)" for s in data[:10]]
        return "Servicios:\n" + "\n".join(lines)

    if tool_name == "inventory_alerts":
        if not data:
            return "Inventario al día, no hay productos con stock bajo."
        lines = [f"{p['name']} - stock: {p['stock']} (mínimo: {p['min_stock']})" for p in data[:5]]
        return "Productos con stock bajo:\n" + "\n".join(lines)

    if tool_name == "employees_list":
        if not data:
            return "No hay empleados activos registrados."
        lines = [f"{e['name']} - {e['specialty'] or 'General'} ({e['payment_type']})" for e in data[:10]]
        return "Empleados:\n" + "\n".join(lines)

    if tool_name == "employee_performance":
        emps = data.get("employees", [])
        if not emps:
            return "No hay datos de rendimiento para este período."
        lines = [f"{e['name']}: RD${e['sales_total']:,.2f} ({e['sales_count']} ventas)" for e in emps[:5]]
        return f"Rendimiento ({data.get('period')}):\n" + "\n".join(lines)

    return json.dumps(data, ensure_ascii=False)
