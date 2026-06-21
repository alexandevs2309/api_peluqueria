import logging
import requests
import json
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from apps.chatbot_api.serializers import ChatPromptSerializer

logger = logging.getLogger(__name__)

# Base de conocimiento estática rica para respuestas de fallback dinámicas e inteligentes
KNOWLEDGE_BASE = {
    "saludo": (
        "¡Hola! Bienvenido a Auron Suite. 💈✨\n\n"
        "Soy tu asistente virtual inteligente. Estoy aquí para ayudarte a explorar todas las ventajas del software de gestión "
        "definitivo para salones de belleza, barberías y centros estéticos en Latinoamérica.\n\n"
        "Puedo informarte en detalle sobre:\n"
        "• 💰 **Planes y precios oficiales** (y el descuento anual del 20%).\n"
        "• 🎁 **Prueba gratis de 7 días** (sin tarjeta de crédito).\n"
        "• ⚙️ **Funcionalidades core**: Agenda en línea, POS fiscal DGII (NCF), Control de cajas, Inventarios y Comisiones de personal.\n"
        "• 📲 **Integración QR de WhatsApp** (Evolution API modular).\n\n"
        "¿De qué te gustaría hablar hoy?"
    ),
    "planes_precios": (
        "Auron Suite cuenta con 4 planes comerciales altamente competitivos. Ofrecemos facturación mensual o anual (esta última incluye un **descuento del 15% al 20%**).\n\n"
        "💵 **Planes y Tarifas Oficiales (DOP / USD):**\n"
        "1️⃣ **Plan Basic** ($29.99 USD/mes ~ 1,800 DOP):\n"
        "   - Ideal para profesionales independientes.\n"
        "   - Incluye: Agenda interactiva, POS básico, base de datos de clientes e historial.\n"
        "   - Limitado a **1 sucursal activa** y 50 empleados.\n\n"
        "2️⃣ **Plan Pro** ($69.99 USD/mes ~ 4,200 DOP) [Recomendado]:\n"
        "   - Excelente para locales en crecimiento.\n"
        "   - Incluye: POS completo, **Control de inventario**, alertas de bajo stock y reportes avanzados de ingresos.\n"
        "   - Limitado a **1 sucursal activa**.\n\n"
        "3️⃣ **Plan Business** ($129.99 USD/mes ~ 7,800 DOP):\n"
        "   - Para locales multi-sucursal y consolidados.\n"
        "   - Incluye: **Sucursales ilimitadas**, cálculo automático de comisiones, nóminas avanzadas, reloj marcador de asistencia y branding personalizado.\n\n"
        "4️⃣ **Plan Enterprise** ($149.00 USD/mes ~ 9,000 DOP):\n"
        "   - Para franquicias y grandes marcas.\n"
        "   - Incluye: Todo lo anterior, soporte prioritario 24/7 y acceso a **API keys públicas** para integraciones a medida.\n\n"
        "¿Te gustaría iniciar tu prueba gratuita en alguno de estos planes?"
    ),
    "prueba_gratis": (
        "¡Iniciar es súper sencillo y sin riesgos! 🎉\n\n"
        "Ofrecemos una **prueba gratuita de 7 días** con las siguientes condiciones:\n"
        "• **Cero ataduras**: No requieres ingresar tarjeta de crédito ni métodos de pago para registrarte.\n"
        "• **Acceso Total**: Eliges el plan que desees y tienes habilitadas todas sus herramientas desde el primer minuto.\n"
        "• **Acompañamiento**: Te asistimos en la configuración inicial de tus sucursales, barberos, estilistas y catálogo de servicios.\n\n"
        "Al finalizar los 7 días, tú decides si deseas suscribirte de forma definitiva para seguir operando. ¿Quieres que te envíe el enlace de registro?"
    ),
    "agenda_citas": (
        "La **agenda y reservas online** de Auron Suite está diseñada para ahorrar tiempo y profesionalizar tu salón:\n\n"
        "• **Reservas 24/7**: Te proporcionamos un portal de reservas público para que tus clientes agenden solos desde su celular, sin interrumpir tu trabajo.\n"
        "• **Prevención de Doble Agenda**: El motor del backend bloquea los slots automáticamente basándose en la disponibilidad real del barbero y la duración del servicio.\n"
        "• **Recordatorios por WhatsApp/Email**: El sistema envía alertas automáticas previas a la cita para mitigar las inasistencias (no-shows) de forma efectiva.\n"
        "• **Control Visual**: Agenda interactiva con estados de color para citas programadas, en curso, cobradas, canceladas o ausentes."
    ),
    "pos_facturacion": (
        "El módulo de **Punto de Venta (POS) y Facturación** está completamente localizado para República Dominicana y LatAm:\n\n"
        "• **Soporte DGII (NCF)**: Emisión automática y secuenciación de Comprobantes Fiscales dominicanos. Gestiona NCF de Crédito Fiscal (B01), Consumidor Final (B02) y Gubernamentales de forma segura.\n"
        "• **Control de Efectivo y Cierres**: Registra aperturas de caja, arqueos al final del día y calcula de forma automática discrepancias de efectivo (faltantes o sobrantes).\n"
        "• **Métodos Flexibles**: Soporta pagos combinados en efectivo, tarjeta de crédito, transferencia bancaria, Stripe y PayPal.\n"
        "• **Impresión Térmica**: Formato de ticket optimizado para ticketeras de 80mm o 58mm."
    ),
    "inventario": (
        "El módulo de **Inventarios y Productos** te brinda control milimétrico de tu stock:\n\n"
        "• **Alertas de Bajo Stock**: Notificaciones instantáneas en tu panel cuando un producto está por agotarse, ayudándote a planificar compras.\n"
        "• **Lector de Código de Barras**: Integra una búsqueda y venta veloz en el POS escaneando códigos de barra nativos.\n"
        "• **Trazabilidad de Movimientos**: Historial detallado de entradas, salidas, compras a proveedores y productos consumidos internamente para el lavado o tintado."
    ),
    "comisiones_nomina": (
        "Auron Suite elimina el dolor de cabeza de calcular nóminas y comisiones a mano:\n\n"
        "• **Comisiones Flexibles**: Configura comisiones personalizadas (porcentaje o monto fijo) por empleado o por servicio específico.\n"
        "• **Cálculo Transaccional**: El sistema computa los montos a pagar de forma automática basándose únicamente en ventas marcadas como pagadas en el POS.\n"
        "• **Reloj Marcador de Asistencia**: Tus empleados registran sus horas de llegada y salida (Clock-In / Clock-Out) con un widget de acceso seguro, calculando horas trabajadas y faltas."
    ),
    "whatsapp_modular": (
        "Nuestra integración de **WhatsApp QR (Evolution API)** es revolucionaria para el sector:\n\n"
        "• **Descentralizada**: A diferencia de otros sistemas que te cobran cargos altos por mensaje usando números globales, aquí escaneas un código QR y los recordatorios se envían desde tu propio número celular.\n"
        "• **Automatización Total**: Confirmaciones de citas al agendar, cancelaciones, cambios de horario y felicitaciones de cumpleaños.\n"
        "• **Ahorro Garantizado**: Al correr sobre nuestra Evolution API local en Docker, el envío de mensajes no tiene costos variables de pasarela para tu negocio."
    ),
    "seguridad_tecnica": (
        "La **seguridad, estabilidad y privacidad** de tus datos son nuestra prioridad absoluta:\n\n"
        "• **Aislamiento Tenant estricto**: Cada salón (tenant) opera con un alcance de datos estrictamente aislado en el backend mediante filtros automatizados por base de datos, evitando cualquier fuga cruzada de datos.\n"
        "• **Autenticación Segura**: Uso de tokens JWT de doble canal (cookies httpOnly + localStorage) y encriptación de datos sensibles en base de datos.\n"
        "• **Copias de Seguridad**: Backups automáticos y programados de la base de datos PostgreSQL para garantizar continuidad de negocio en entornos productivos.\n"
        "• **Infraestructura**: Despliegue seguro sobre servidores en la nube con soporte de fallback ante caídas de caché de memoria Redis."
    ),
    "soporte_ayuda": (
        "Estamos a tu disposición para ayudarte a tener éxito en tu negocio:\n\n"
        "• **Soporte Centralizado**: Puedes escribirnos en cualquier momento a **soporte@auronsuite.com**.\n"
        "• **Tickets Integrados**: Dentro de la plataforma, los administradores y gerentes pueden abrir tickets formales de soporte con diferentes prioridades. Estos tickets notifican directamente a nuestro equipo técnico central con acuse de recibo.\n"
        "• **Canal Humano**: En el widget de chat, siempre tienes la opción de hacer clic en **'Hablar con un asesor'** para ser redirigido directamente a una conversación de WhatsApp con un especialista de soporte."
    ),
    "cancelacion_reembolso": (
        "Creemos en una relación justa y transparente con nuestros clientes:\n\n"
        "• **Cancelación Flexible**: Puedes cancelar tu suscripción activa en cualquier momento directamente desde la sección de Configuración de tu Perfil, sin preguntas ni llamadas telefónicas.\n"
        "• **Acceso hasta el final del ciclo**: Al cancelar, tu cuenta permanecerá activa y con todas sus funciones operando con normalidad hasta que finalice el período de facturación que ya pagaste (mensual o anual).\n"
        "• **Retención de Datos**: Exportamos tus datos de clientes e historial de ventas antes de que decidas marcharte."
    ),
    "general": (
        "Auron Suite es la plataforma SaaS todo-en-uno definitiva para salones de belleza, barberías y centros estéticos en Latinoamérica.\n\n"
        "Centralizamos tu agenda de reservas, facturación fiscal DGII (NCF), control de inventarios, cálculo automatizado de comisiones y recordatorios por WhatsApp QR para potenciar tus ventas y ahorrarte horas de trabajo administrativo.\n\n"
        "¿De qué te gustaría recibir más información?\n"
        "• 💰 Precios y planes comerciales.\n"
        "• 🎁 Cómo iniciar la prueba gratuita de 7 días.\n"
        "• 🧾 Emisión de comprobantes fiscales DGII (NCF).\n"
        "• 💇‍♂️ Cálculo automático de comisiones y nóminas.\n"
        "• 📲 Cómo conectar tu número de WhatsApp con el código QR."
    )
}

# Diccionario de intenciones enriquecido para mapear semánticamente los prompts
INTENT_KEYWORDS = {
    "saludo": {
        "words": ["hola", "buenas", "buen dia", "tarde", "noche", "saludo", "ey", "hello", "hi", "que tal", "como estas", "que hay", "ola"],
        "score": 1
    },
    "planes_precios": {
        "words": ["precio", "costo", "plan", "suscripcion", "tarifa", "mensual", "anual", "pagar", "valer", "cuesta", "dinero", "dolares", "pesos", "dop", "usd", "basic", "pro", "business", "enterprise", "comprar", "costar", "valor", "cuanto es", "oferta", "precio de"],
        "score": 1
    },
    "prueba_gratis": {
        "words": ["prueba", "gratis", "demo", "probar", "free", "evaluar", "7 dias", "comenzar", "iniciar", "crear cuenta", "registrarse", "registro", "probarlo", "suscripcion gratis"],
        "score": 1
    },
    "agenda_citas": {
        "words": ["agenda", "cita", "turno", "reserva", "calendario", "agendar", "bloqueo", "cliente", "estilista", "barbero", "servicio", "doble agenda", "online", "reservar", "programar", "turnos", "citas", "en linea"],
        "score": 1
    },
    "pos_facturacion": {
        "words": ["pos", "caja", "factura", "ncf", "dgii", "fiscal", "comprobante", "arqueo", "cierre", "efectivo", "pago", "cobrar", "tarjeta", "impuesto", "itbis", "rnc", "credito fiscal", "consumidor final", "ticket", "impresora", "termica", "dgii", "facturacion", "comprobantes"],
        "score": 1
    },
    "inventario": {
        "words": ["inventario", "stock", "producto", "bajo stock", "codigo", "barra", "proveedor", "compras", "ajuste", "almacen", "mercancia", "productos", "inventarios", "escanear", "escaner"],
        "score": 1
    },
    "comisiones_nomina": {
        "words": ["comision", "nomina", "empleado", "horario", "asistencia", "marcador", "clock", "estilista", "barbero", "sueldo", "porcentaje", "fijo", "asistir", "reloj", "comisiones", "nominas", "salario", "pagar a"],
        "score": 1
    },
    "whatsapp_modular": {
        "words": ["whatsapp", "notificacion", "qr", "instance", "evolution", "mensaje", "enviar", "confirmacion", "recordatorio", "celular", "telefono", "mensajes", "recordatorios", "avisar"],
        "score": 1
    },
    "seguridad_tecnica": {
        "words": ["seguridad", "proteccion", "backup", "respaldo", "datos", "privacidad", "hackear", "encriptar", "jwt", "token", "tenant", "aislamiento", "robado", "caer", "servidor", "caido", "estable", "resguardo"],
        "score": 1
    },
    "soporte_ayuda": {
        "words": ["soporte", "ayuda", "ticket", "problema", "correo", "contacto", "asesor", "humano", "telefono", "escribir", "email", "chat", "hablar", "gerente", "administrador", "ayudar", "fallo", "falla", "error"],
        "score": 1
    },
    "cancelacion_reembolso": {
        "words": ["cancelar", "reembolso", "devolucion", "quitar", "eliminar cuenta", "dar de baja", "baja", "politica", "reembolsar", "devolver", "irme", "des suscribirme"],
        "score": 1
    }
}


def get_local_fallback_response(prompt):
    """Motor de fallback mejorado con heurística de puntuación de palabras clave"""
    p = prompt.lower()
    scores = {intent: 0 for intent in INTENT_KEYWORDS}
    
    # Calcular puntuación ponderada por la longitud del token coincidente
    for intent, config in INTENT_KEYWORDS.items():
        for word in config["words"]:
            if word in p:
                # Sumar puntos proporcional a la longitud de la palabra clave coincidente
                scores[intent] += len(word) * config["score"]
                
    best_intent = max(scores, key=scores.get)
    
    # Si no hay ninguna coincidencia real, usar respuesta general
    if scores[best_intent] == 0:
        return KNOWLEDGE_BASE["general"]
        
    return KNOWLEDGE_BASE[best_intent]


class ChatBotView(APIView):
    """
    Endpoint público para interactuar con el chatbot inteligente de Auron Suite.
    No requiere autenticación ya que se expone en la landing page del sitio.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        serializer = ChatPromptSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        prompt = serializer.validated_data['prompt']
        
        # 1. Intentar usar OpenAI si está configurado en settings
        openai_key = getattr(settings, "OPENAI_API_KEY", "")
        if openai_key:
            try:
                reply = query_openai(prompt, openai_key)
                return Response({"reply": reply}, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Error al invocar OpenAI API: {e}", exc_info=True)
                
        # 2. Intentar usar Gemini si está configurado en settings
        gemini_key = getattr(settings, "GEMINI_API_KEY", "")
        if gemini_key:
            try:
                reply = query_gemini(prompt, gemini_key)
                return Response({"reply": reply}, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Error al invocar Gemini API: {e}", exc_info=True)
                
        # 3. Fallback local estructurado inteligente
        try:
            reply = get_local_fallback_response(prompt)
            return Response({"reply": reply}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error en fallback del chatbot: {e}", exc_info=True)
            return Response(
                {"reply": "Lo siento, tengo problemas para procesar tu consulta en este momento. Por favor, intenta de nuevo o haz clic en 'Hablar con un asesor' para chatear directamente por WhatsApp."},
                status=status.HTTP_200_OK
            )
