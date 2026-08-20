# MCP API — Tareas Pendientes

## Completado
- [x] App `mcp_api` integrada en Django backend
- [x] 7 tools: sales_summary, appointments_list, clients_search, services_list, inventory_alerts, employees_list, employee_performance
- [x] Chat endpoint con detección de intención por keywords
- [x] Widget de chat en Angular (ChatWidgetComponent)
- [x] Servicio McpChatService con auth JWT automática
- [x] Endpoints: `/api/mcp/tools/`, `/api/mcp/call/`, `/api/mcp/chat/`
- [x] Deploy backend (Render) y frontend (Cloudflare)

---

## Pendiente — Prioridad Alta

### 1. LLM real (reemplazar keyword matching)
**Archivo:** `apps/mcp_api/views.py` → `_detect_tool()`

Actualmente detecta intención por keywords ("vend", "cita", "cliente"...). Falta integrar un LLM real para:
- Entender preguntas complejas: "¿cuánto vendí el martes pasado vs el lunes?"
- Manejar contexto conversacional: "¿y el mes pasado?"
- Formatear respuestas naturales

**Opciones:**
- OpenAI GPT-4o (costo ~$0.005/consulta)
- Google Gemini 2.0 Flash (tier gratuito generoso)
- Anthropic Claude Haiku (rápido, barato)

**Cómo:**
```python
# En views.py, reemplazar _detect_tool() con:
def _detect_tool_with_llm(message, tools):
    prompt = f"""Dado el mensaje del usuario, devuelve JSON con:
    - tool: nombre del tool a usar
    - params: parámetros extraídos
    
    Tools disponibles: {json.dumps(tools)}
    Mensaje: {message}"""
    
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)
```

---

### 2. Más tools

#### 2a. Products (inventario detallado)
```python
def products_list(tenant, category=None, low_stock=False):
    # Lista productos con stock, precio, categoría
```

#### 2b. Payments (pagos recientes)
```python
def payments_summary(tenant, period="today"):
    # Pagos por método: efectivo, tarjeta, transferencia
```

#### 2c. Reports (reportes predefinidos)
```python
def daily_report(tenant):
    # Resumen completo del día: ventas, citas, ingresos, gastos
```

#### 2d. Settings (configuración del negocio)
```python
def business_info(tenant):
    # Nombre, horario, dirección, teléfono del negocio
```

---

### 3. Historial de chat
**Archivo nuevo:** `apps/mcp_api/models.py`

```python
class ChatMessage(TenantModel):
    user = ForeignKey(settings.AUTH_USER_MODEL)
    role = CharField(choices=[('user', 'User'), ('assistant', 'Assistant')])
    content = TextField()
    tool_called = CharField(null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
```

- Guardar cada mensaje en BD
- Mostrar historial al abrir el chat
- Permitir buscar en conversaciones anteriores

---

## Pendiente — Prioridad Media

### 4. Chat con contexto conversacional
El LLM debería recordar los últimos 5-10 mensajes para manejar follow-ups:
- "¿Cuánto vendí hoy?" → respuesta
- "¿Y ayer?" → entender que se refiere a ventas del día anterior

**Implementación:** enviar historial de mensajes al LLM como contexto.

---

### 5. Sugerencias dinámicas
En lugar de 4 sugerencias fijas, generarlas según el contexto:
- Si es hora de cierre: "Resumen del día", "Cerrar caja"
- Si hay stock bajo: "Productos a reponer"
- Si es lunes: "Citas de la semana"

---

### 6. Notificaciones proactivas
El chat podría notificar al barbero automáticamente:
- "Tienes 3 citas pendientes para hoy"
- "Stock bajo en Shampoo X"
- "Hoy vendiste RD$5,000 menos que el promedio"

**Implementación:** Celery task que revisa datos periódicamente y envía notificaciones via SSE o in-app.

---

### 7. Soporte de imágenes
El barbero podría enviar una foto de un producto y que el asistente lo identifique:
- Foto de un producto → buscar en inventario
- Foto de un recibo → registrar venta

---

## Pendiente — Prioridad Baja

### 8. Multi-idioma
El chat responde en español. Podría detectar el idioma del usuario y responder en consecuencia.

### 9. Exportar conversaciones
Exportar el chat como PDF o TXT para auditoría.

### 10. Rate limiting por usuario
Límite de 30 mensajes por hora por usuario (evitar abuso de LLM).

### 11. Analytics
Trackear qué preguntas hacen los barberos más frecuentemente.
- Dashboard de uso del asistente
- Tools más consultados
- Horas pico de uso

### 12. Voice input
El barbero podría hablar en lugar de escribir (Web Speech API).

---

## Archivos relacionados
- `apps/mcp_api/tools.py` — tools existentes
- `apps/mcp_api/views.py` — endpoints y keyword matching
- `apps/mcp_api/urls.py` — rutas
- `src/app/core/services/mcp/mcp-chat.service.ts` — servicio Angular
- `src/app/shared/components/chat-widget/chat-widget.component.ts` — widget UI
