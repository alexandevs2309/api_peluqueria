"""
============================================================
FIX 13: Stripe LIVE — activación y verificación del primer cobro real
PROBLEMA: STRIPE_SECRET_KEY = sk_test_... en producción.
           El sistema arranca y no bloquea. Clientes que completan
           el checkout no transfieren dinero real.
           settings.py solo hace warnings.warn(), no bloquea.

SOLUCIÓN EN 4 PASOS:
============================================================
"""

# =====================================================
# PASO 1: Bloquear arranque si Stripe está en TEST sin flag explícito
# En backend/settings.py — REEMPLAZAR el bloque de validación:
# =====================================================

import warnings

STRIPE_SECRET_KEY  = env('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = env('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK_SECRET  = env('STRIPE_WEBHOOK_SECRET', default='')
STRIPE_LIVE_MODE_CONFIRMED = env.bool('STRIPE_LIVE_MODE_CONFIRMED', default=False)

_using_test_keys = STRIPE_SECRET_KEY.startswith('sk_test_')
_is_production = not DEBUG

if _is_production and _using_test_keys and not STRIPE_LIVE_MODE_CONFIRMED:
    raise RuntimeError(
        "\n\n"
        "🚫 STRIPE EN MODO TEST EN PRODUCCIÓN\n"
        "─────────────────────────────────────\n"
        "STRIPE_SECRET_KEY comienza con 'sk_test_' y DEBUG=False.\n"
        "Esto significa que los cobros NO transfieren dinero real.\n\n"
        "OPCIONES:\n"
        "  A) Usar claves LIVE: STRIPE_SECRET_KEY=sk_live_...\n"
        "  B) Confirmar que esto es intencional (staging con test keys):\n"
        "     Agregar STRIPE_LIVE_MODE_CONFIRMED=True en env vars.\n"
        "─────────────────────────────────────\n"
    )

if _is_production and _using_test_keys and STRIPE_LIVE_MODE_CONFIRMED:
    warnings.warn(
        "Stripe en modo TEST con STRIPE_LIVE_MODE_CONFIRMED=True. "
        "Solo aceptable en staging. En producción real usar sk_live_.",
        RuntimeWarning,
        stacklevel=2
    )


# =====================================================
# PASO 2: Obtener claves LIVE de Stripe Dashboard
# =====================================================
"""
1. https://dashboard.stripe.com/apikeys
   → Activar cuenta si aún está en modo test
   → Copiar: sk_live_xxxx (Secret key)
   → Copiar: pk_live_xxxx (Publishable key)

2. Webhook secret LIVE:
   https://dashboard.stripe.com/webhooks
   → "Add endpoint"
   → URL: https://api.auron-suite.com/api/billing/webhook/
   → Eventos a escuchar:
       customer.subscription.created
       customer.subscription.updated
       customer.subscription.deleted
       invoice.payment_succeeded
       invoice.payment_failed
       payment_intent.succeeded
       payment_intent.payment_failed
   → Copiar: whsec_xxxx

3. Actualizar en Render Dashboard (Environment Variables):
   STRIPE_SECRET_KEY     = sk_live_xxxx
   STRIPE_PUBLISHABLE_KEY = pk_live_xxxx
   STRIPE_WEBHOOK_SECRET  = whsec_xxxx
   STRIPE_LIVE_MODE_CONFIRMED = (NO agregar — o False para producción real)
"""


# =====================================================
# PASO 3: Verificar cobro real con script
# Ejecutar: python manage.py shell < scripts/verify_stripe_live.py
# =====================================================

import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

print("=== VERIFICACIÓN STRIPE LIVE ===")
print(f"Modo: {'LIVE ✅' if stripe.api_key.startswith('sk_live_') else 'TEST ⚠️'}")

# Verificar conexión con Stripe
try:
    account = stripe.Account.retrieve()
    print(f"Cuenta: {account.get('display_name', account.get('email', 'N/A'))}")
    print(f"País: {account.get('country', 'N/A')}")
    print(f"Moneda default: {account.get('default_currency', 'N/A')}")
    print(f"Payouts habilitados: {'✅' if account.get('payouts_enabled') else '❌'}")
    print(f"Charges habilitados: {'✅' if account.get('charges_enabled') else '❌'}")
except stripe.error.AuthenticationError as e:
    print(f"❌ Error de autenticación: {e}")
    raise

# Verificar webhook secret
webhook_secret = settings.STRIPE_WEBHOOK_SECRET
if webhook_secret and webhook_secret.startswith('whsec_'):
    print(f"Webhook secret: ✅ configurado (whsec_...{webhook_secret[-6:]})")
else:
    print("❌ STRIPE_WEBHOOK_SECRET no configurado o inválido")

# Verificar precios/products configurados
try:
    products = stripe.Product.list(active=True, limit=5)
    print(f"\nProductos activos en Stripe: {len(products.data)}")
    for p in products.data:
        prices = stripe.Price.list(product=p.id, active=True)
        for price in prices.data:
            amount = price.unit_amount / 100 if price.unit_amount else 0
            print(f"  - {p.name}: ${amount:.2f}/{price.recurring.interval if price.recurring else 'one-time'}")
except Exception as e:
    print(f"⚠️  No se pudieron listar productos: {e}")

print("\n=== FIN VERIFICACIÓN ===")


# =====================================================
# PASO 4: Primer cobro de prueba LIVE
# (Con tarjeta real de $1, luego reembolsar)
# =====================================================
"""
1. En el frontend de producción, registrar un nuevo tenant de prueba
2. En el checkout, usar una tarjeta real (no 4242...)
3. Verificar en Stripe Dashboard > Payments que aparece el cobro
4. Verificar en tu cuenta bancaria (puede tardar 1-3 días)
5. Reembolsar desde Stripe Dashboard si fue un cobro de prueba
6. Marcar este paso como completado en GO_LIVE_CHECKLIST.md
"""
