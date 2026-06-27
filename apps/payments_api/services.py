try:
    import stripe
except ImportError:
    stripe = None

import os
import json
from decimal import Decimal
from datetime import datetime, timezone as dt_timezone
from typing import Optional
import requests
from django.conf import settings
from django.db.models import Q
from django.core.cache import cache
import logging
from .models import Payment, PaymentProvider
from apps.subscriptions_api.models import UserSubscription, SubscriptionPlan
from apps.tenants_api.models import Tenant
from django.contrib.auth import get_user_model
from apps.settings_api.integration_service import IntegrationService
from .azul_provider import AZUL_CURRENCY_CODES, ERROR_MAP

User = get_user_model()
logger = logging.getLogger(__name__)


class PayPalService:
    """Servicio unificado para operaciones con PayPal (REST API v2)."""

    def __init__(self):
        self._load_config()

    def _load_config(self):
        system_settings = IntegrationService.get_system_settings()
        self.client_id = (
            system_settings.paypal_client_id
            or os.getenv('PAYPAL_CLIENT_ID')
            or getattr(settings, 'PAYPAL_CLIENT_ID', '')
        )
        self.client_secret = (
            system_settings.paypal_client_secret
            or os.getenv('PAYPAL_SECRET')
            or getattr(settings, 'PAYPAL_SECRET', '')
        )
        self.sandbox = getattr(system_settings, 'paypal_sandbox', True)
        self.base_url = 'https://api.sandbox.paypal.com' if self.sandbox else 'https://api.paypal.com'
        self.webhook_id = getattr(settings, 'PAYPAL_WEBHOOK_ID', '')

    @property
    def is_configured(self):
        return bool(self.client_id and self.client_secret)

    def get_access_token(self):
        """Obtener token OAuth2 de PayPal."""
        if not self.is_configured:
            return None, {
                'error': 'PayPal no configurado',
                'message': 'Configura PAYPAL_CLIENT_ID y PAYPAL_SECRET antes de cobrar con PayPal.',
            }
        try:
            resp = requests.post(
                f"{self.base_url}/v1/oauth2/token",
                headers={'Accept': 'application/json', 'Accept-Language': 'en_US'},
                data='grant_type=client_credentials',
                auth=(self.client_id, self.client_secret),
                timeout=20,
            )
        except requests.RequestException as exc:
            logger.exception('PayPal auth request failed')
            return None, {'error': 'PayPal unavailable', 'message': str(exc)}

        if resp.status_code != 200:
            logger.warning('PayPal auth failed status=%s', resp.status_code)
            return None, {
                'error': 'PayPal authentication failed',
                'message': f'PayPal respondió con estado {resp.status_code}.',
            }

        token = resp.json().get('access_token')
        if not token:
            return None, {
                'error': 'PayPal authentication failed',
                'message': 'PayPal no devolvió access_token.',
            }
        return token, None

    def create_order(self, user, tenant, plan, months, billing_interval='month', auto_renew=False):
        """Crear orden PayPal y devolver {order_id, approve_url}."""
        token, err = self.get_access_token()
        if err:
            return None, err

        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:4200').rstrip('/')
        price_per_cycle = plan.annual_price if billing_interval == 'year' else plan.price
        if billing_interval == 'year' and not price_per_cycle:
            price_per_cycle = plan.price * 12 * Decimal('0.8')

        if billing_interval == 'year':
            total_amount_val = price_per_cycle * months / 12
        else:
            total_amount_val = price_per_cycle * months

        total_amount = f"{total_amount_val:.2f}"
        payload = {
            'intent': 'CAPTURE',
            'purchase_units': [{
                'reference_id': f"tenant-{tenant.id}",
                'description': f"Suscripción {plan.get_name_display()} x{months}m",
                'custom_id': f"user:{user.id}|tenant:{tenant.id}|plan:{plan.id}|months:{months}",
                'amount': {'currency_code': 'USD', 'value': total_amount},
            }],
            'application_context': {
                'brand_name': 'Auron Suite',
                'landing_page': 'LOGIN',
                'user_action': 'PAY_NOW',
                'return_url': f"{frontend_url}/client/checkout?paypal=success",
                'cancel_url': f"{frontend_url}/client/checkout?paypal=cancelled",
            },
        }

        try:
            resp = requests.post(
                f"{self.base_url}/v2/checkout/orders",
                headers={
                    'Authorization': f"Bearer {token}",
                    'Content-Type': 'application/json',
                },
                json=payload,
                timeout=25,
            )
        except requests.RequestException as exc:
            logger.exception('PayPal order creation failed')
            return None, {'error': 'PayPal unavailable', 'message': str(exc)}

        if resp.status_code not in {200, 201}:
            logger.warning('PayPal order creation failed status=%s', resp.status_code)
            return None, {'error': 'No se pudo crear la orden PayPal', 'message': resp.text}

        order_data = resp.json()
        order_id = order_data.get('id')
        approve_url = next(
            (link.get('href') for link in order_data.get('links', []) if link.get('rel') == 'approve'),
            None,
        )
        if not order_id or not approve_url:
            return None, {'error': 'Respuesta inválida de PayPal', 'message': 'No se recibió id de orden o enlace de aprobación.'}

        return {
            'order_id': order_id,
            'approve_url': approve_url,
            'sandbox': self.sandbox,
            'amount': total_amount,
        }, None

    def sync_paypal_plan(self, plan: SubscriptionPlan, billing_interval='month'):
        """Crea producto y plan en PayPal si no existen."""
        token, err = self.get_access_token()
        if err:
            return None, err
            
        # 1. Crear producto si no existe
        if not plan.paypal_product_id:
            payload = {
                "name": f"Auron Suite - {plan.get_name_display()}",
                "description": f"Suscripción al plan {plan.get_name_display()} de Auron Suite",
                "type": "SERVICE",
                "category": "SOFTWARE"
            }
            try:
                resp = requests.post(
                    f"{self.base_url}/v1/catalogs/products",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=20
                )
                if resp.status_code in {200, 201}:
                    plan.paypal_product_id = resp.json().get('id')
                    plan.save(update_fields=['paypal_product_id'])
                else:
                    return None, {'error': 'Error creando producto', 'message': resp.text}
            except Exception as e:
                return None, {'error': 'Error de conexion', 'message': str(e)}
        
        # 2. Crear plan si no existe
        target_field = 'paypal_annual_plan_id' if billing_interval == 'year' else 'paypal_plan_id'
        plan_id = getattr(plan, target_field)
        
        if not plan_id:
            price = plan.annual_price if billing_interval == 'year' else plan.price
            if billing_interval == 'year' and not price:
                price = plan.price * 12 * Decimal('0.8')
                
            interval_unit = "YEAR" if billing_interval == 'year' else "MONTH"
            
            payload = {
                "product_id": plan.paypal_product_id,
                "name": f"Auron Suite - {plan.get_name_display()} ({interval_unit})",
                "description": f"Plan {plan.get_name_display()} cobrado de forma {interval_unit.lower()}",
                "status": "ACTIVE",
                "billing_cycles": [
                    {
                        "frequency": {
                            "interval_unit": interval_unit,
                            "interval_count": 1
                        },
                        "tenure_type": "REGULAR",
                        "sequence": 1,
                        "total_cycles": 0,
                        "pricing_scheme": {
                            "fixed_price": {
                                "value": str(price),
                                "currency_code": "USD"
                            }
                        }
                    }
                ],
                "payment_preferences": {
                    "auto_bill_outstanding": True,
                    "setup_fee": {
                        "value": "0",
                        "currency_code": "USD"
                    },
                    "setup_fee_failure_action": "CONTINUE",
                    "payment_failure_threshold": 3
                }
            }
            try:
                resp = requests.post(
                    f"{self.base_url}/v1/billing/plans",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=20
                )
                if resp.status_code in {200, 201}:
                    plan_id = resp.json().get('id')
                    setattr(plan, target_field, plan_id)
                    plan.save(update_fields=[target_field])
                else:
                    return None, {'error': 'Error creando plan de suscripcion', 'message': resp.text}
            except Exception as e:
                return None, {'error': 'Error de conexion', 'message': str(e)}
                
        return plan_id, None

    def create_subscription(self, user, tenant, plan, billing_interval='month'):
        """Crea una suscripción de PayPal y devuelve el enlace de aprobación."""
        plan_id, err = self.sync_paypal_plan(plan, billing_interval)
        if err:
            return None, err
            
        token, err = self.get_access_token()
        if err:
            return None, err
            
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:4200').rstrip('/')
        
        payload = {
            "plan_id": plan_id,
            "custom_id": f"user:{user.id}|tenant:{tenant.id}|plan:{plan.id}|interval:{billing_interval}",
            "application_context": {
                "brand_name": "Auron Suite",
                "shipping_preference": "NO_SHIPPING",
                "user_action": "SUBSCRIBE_NOW",
                "return_url": f"{frontend_url}/client/checkout?paypal_sub=success",
                "cancel_url": f"{frontend_url}/client/checkout?paypal_sub=cancelled"
            }
        }
        
        try:
            resp = requests.post(
                f"{self.base_url}/v1/billing/subscriptions",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=payload,
                timeout=20
            )
            if resp.status_code in {200, 201}:
                data = resp.json()
                sub_id = data.get('id')
                approve_url = next((l.get('href') for l in data.get('links', []) if l.get('rel') == 'approve'), None)
                return {
                    'subscription_id': sub_id,
                    'approve_url': approve_url,
                    'sandbox': self.sandbox
                }, None
            else:
                return None, {'error': 'Error creando subscripcion', 'message': resp.text}
        except Exception as e:
            return None, {'error': 'Error de conexion', 'message': str(e)}

    def capture_order(self, order_id):
        """Capturar orden PayPal. Retorna dict con capture_id, status, amount."""
        token, err = self.get_access_token()
        if err:
            return None, err

        try:
            resp = requests.post(
                f"{self.base_url}/v2/checkout/orders/{order_id}/capture",
                headers={
                    'Authorization': f"Bearer {token}",
                    'Content-Type': 'application/json',
                },
                timeout=25,
            )
        except requests.RequestException as exc:
            logger.exception('PayPal capture failed order_id=%s', order_id)
            return None, {'error': 'PayPal unavailable', 'message': str(exc)}

        if resp.status_code not in {200, 201}:
            logger.warning('PayPal capture failed status=%s', resp.status_code)
            return None, {
                'error': 'No se pudo capturar la orden PayPal',
                'message': resp.text,
            }

        capture_data = resp.json()
        capture_status = capture_data.get('status')
        purchase_units = capture_data.get('purchase_units') or []
        capture_entry = (((purchase_units[0] if purchase_units else {}).get('payments') or {}).get('captures') or [None])[0]

        if capture_status != 'COMPLETED' or not capture_entry or capture_entry.get('status') != 'COMPLETED':
            return None, {
                'error': 'PayPal capture incomplete',
                'message': f'Estado actual: {capture_status or "unknown"}',
            }

        return {
            'capture_id': capture_entry.get('id'),
            'status': 'COMPLETED',
            'amount': float(capture_entry.get('amount', {}).get('value', 0)),
            'currency': capture_entry.get('amount', {}).get('currency_code', 'USD'),
            'raw': capture_data,
        }, None

    def verify_webhook(self, request_body, headers_dict):
        """Verificar firma de webhook PayPal vía API."""
        webhook_id = self.webhook_id
        if not webhook_id:
            logger.error("PAYPAL_WEBHOOK_ID not configured")
            return False

        auth_algo = headers_dict.get('HTTP_PAYPAL_AUTH_ALGO', '')
        cert_url = headers_dict.get('HTTP_PAYPAL_CERT_URL', '')
        transmission_id = headers_dict.get('HTTP_PAYPAL_TRANSMISSION_ID', '')
        transmission_sig = headers_dict.get('HTTP_PAYPAL_TRANSMISSION_SIG', '')
        transmission_time = headers_dict.get('HTTP_PAYPAL_TRANSMISSION_TIME', '')

        if not all([auth_algo, cert_url, transmission_id, transmission_sig, transmission_time]):
            logger.warning("PayPal webhook missing required headers")
            return False

        try:
            auth_resp = requests.post(
                f"{self.base_url}/v1/oauth2/token",
                headers={'Accept': 'application/json'},
                data='grant_type=client_credentials',
                auth=(self.client_id, self.client_secret),
                timeout=15,
            )
            if auth_resp.status_code != 200:
                return False
            token = auth_resp.json().get('access_token')

            verify_payload = {
                'auth_algo': auth_algo,
                'cert_url': cert_url,
                'transmission_id': transmission_id,
                'transmission_sig': transmission_sig,
                'transmission_time': transmission_time,
                'webhook_id': webhook_id,
                'webhook_event': json.loads(request_body) if isinstance(request_body, (bytes, str)) else request_body,
            }
            verify_resp = requests.post(
                f"{self.base_url}/v1/notifications/verify-webhook-signature",
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json',
                },
                json=verify_payload,
                timeout=15,
            )
            if verify_resp.status_code != 200:
                return False
            return verify_resp.json().get('verification_status') == 'SUCCESS'
        except requests.RequestException:
            logger.exception("PayPal webhook verification request failed")
            return False

    @staticmethod
    def order_cache_key(order_id):
        return f'paypal:subscription:order:{order_id}'

    @staticmethod
    def capture_cache_key(order_id):
        return f'paypal:subscription:capture:{order_id}'

    @staticmethod
    def create_payment_record(user, tenant, amount, capture_id, order_id, plan=None, months=1):
        """Crear registro unificado Payment en payments_api."""
        provider = PaymentProvider.objects.filter(name='paypal').first()
        if not provider:
            logger.warning("PayPal PaymentProvider not found — skipping Payment record")
            return None
        payment = Payment.objects.create(
            user=user,
            tenant=tenant,
            provider=provider,
            amount=amount,
            currency='USD',
            status='completed',
            provider_payment_id=capture_id or '',
            metadata={
                'paypal_order_id': order_id or '',
                'plan_id': str(plan.id) if plan else '',
                'months': months,
                'source': 'paypal_capture',
            },
        )
        logger.info(
            "Payment record created id=%s user=%s amount=%s",
            payment.id, user.id, amount,
        )
        return payment


class AzulService:
    """Servicio de pagos con Azul para suscripciones (checkout).

    Azul es el procesador primario para República Dominicana.
    Stripe/PayPal quedan como opciones legacy/terceras.
    """

    def __init__(self):
        self._load_config()

    def _load_config(self):
        system = IntegrationService.get_system_settings()
        self.sandbox = getattr(system, 'azul_sandbox', True)
        self.base_url = (
            'https://sandbox.azul.com.do' if self.sandbox else 'https://azul.com.do'
        )
        self.store = (
            system.azul_store_id
            or os.getenv('AZUL_STORE_ID', '')
        )
        self.merchant = (
            system.azul_merchant_id
            or os.getenv('AZUL_MERCHANT_ID', '')
        )
        self.auth1 = (
            system.azul_auth1
            or os.getenv('AZUL_AUTH1', '')
        )
        self.auth2 = (
            system.azul_auth2
            or os.getenv('AZUL_AUTH2', '')
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.store and self.merchant and self.auth1 and self.auth2)

    def _auth(self) -> dict:
        return {
            'store': self.store,
            'merchant': self.merchant,
            'auth1': self.auth1,
            'auth2': self.auth2,
        }

    def _post(self, path: str, payload: dict, timeout: int = 30) -> dict:
        url = f'{self.base_url}{path}'
        logger.info('AzulService request path=%s store=%s', path, self.store)
        try:
            resp = requests.post(
                url,
                json=payload,
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                timeout=timeout,
            )
        except requests.RequestException as exc:
            logger.exception('AzulService network error path=%s', path)
            return {'success': False, 'error_message': f'Error de conexión con Azul: {str(exc)}'}

        if resp.status_code not in (200, 201):
            logger.warning('AzulService HTTP %s path=%s body=%s', resp.status_code, path, resp.text[:500])
            return {
                'success': False,
                'responseCode': 'ERR',
                'error_message': f'Azul respondió con estado HTTP {resp.status_code}',
            }

        try:
            return resp.json()
        except (ValueError, json.JSONDecodeError):
            logger.error('AzulService invalid JSON path=%s', path)
            return {'success': False, 'responseCode': 'ERR', 'error_message': 'Respuesta inválida de Azul'}

    def create_checkout_sale(
        self,
        order_number: str,
        amount: Decimal,
        currency: str = 'DOP',
        customer_email: str = '',
        metadata: dict = None,
    ) -> dict:
        """Crear una venta directa en Azul.

        Retorna dict con:
        - success: bool
        - txn_number: str (ID de transacción Azul)
        - auth_code: str (código de autorización)
        - response_code: str
        - error_message: str si falla
        """
        metadata = metadata or {}
        currency_code = AZUL_CURRENCY_CODES.get(currency.upper(), '214')
        amount_str = str(int(amount * 100))

        payload = {
            **self._auth(),
            'typeService': 'JSON',
            'orderNumber': order_number[:20],
            'amount': amount_str,
            'currency': currency_code,
            'customerEmail': customer_email,
            'customFields': json.dumps({
                'tenant_id': metadata.get('tenant_id', ''),
                'user_id': metadata.get('user_id', ''),
                'plan_id': metadata.get('plan_id', ''),
                'source': 'subscription_checkout',
            }),
        }

        data = self._post('/sales', payload)
        return self._parse_checkout_response(data, amount, currency)

    def verify_transaction(self, order_number: str) -> dict:
        """Verificar estado de una transacción."""
        payload = {
            **self._auth(),
            'typeService': 'JSON',
            'orderNumber': order_number[:20],
        }
        data = self._post('/verify', payload)
        response_code = data.get('responseCode', '99')
        return {
            'success': response_code == '00',
            'response_code': response_code,
            'txn_number': data.get('txnNumber', ''),
            'auth_code': data.get('authCode', ''),
            'iso_response': data.get('IsoResponse', ''),
            'raw': data,
        }

    def void_transaction(self, txn_number: str, amount: Optional[Decimal] = None) -> dict:
        """Anular o reembolsar una transacción."""
        payload = {
            **self._auth(),
            'typeService': 'JSON',
            'orderNumber': f'VOID-{txn_number[:12]}',
            'txnNumber': txn_number,
        }
        if amount is not None:
            payload['amount'] = str(int(amount * 100))
        data = self._post('/void', payload)
        return self._parse_checkout_response(data, amount or Decimal('0'), 'DOP')

    def _parse_checkout_response(self, data: dict, amount: Decimal, currency: str) -> dict:
        if data.get('success') is False and data.get('error_message'):
            return {
                'success': False,
                'error': data['error_message'],
            }

        response_code = data.get('responseCode', '99')
        txn_number = data.get('txnNumber', '')
        auth_code = data.get('authCode', '')

        if response_code == '00':
            logger.info('AzulService sale approved txn=%s auth=%s', txn_number, auth_code)
            return {
                'success': True,
                'txn_number': txn_number,
                'auth_code': auth_code,
                'response_code': response_code,
                'amount': float(amount),
                'currency': currency,
                'raw': data,
            }

        error_msg = ERROR_MAP.get(response_code, data.get('IsoResponse', f'Código {response_code}'))
        logger.warning('AzulService sale denied code=%s txn=%s', response_code, txn_number)
        return {
            'success': False,
            'response_code': response_code,
            'error': error_msg,
            'txn_number': txn_number,
        }

    @staticmethod
    def create_payment_record(
        user, tenant, amount: Decimal, txn_number: str, order_number: str,
        plan=None, months: int = 1,
    ):
        """Crear registro de Payment en payments_api."""
        provider = PaymentProvider.objects.filter(name='azul').first()
        if not provider:
            logger.warning('Azul PaymentProvider not found — skipping Payment record')
            return None
        payment = Payment.objects.create(
            user=user,
            tenant=tenant,
            provider=provider,
            amount=amount,
            currency='DOP',
            status='completed',
            provider_payment_id=txn_number or '',
            metadata={
                'azul_order_number': order_number or '',
                'plan_id': str(plan.id) if plan else '',
                'months': months,
                'source': 'azul_checkout',
            },
        )
        logger.info('Azul Payment record created id=%s user=%s amount=%s', payment.id, user.id, amount)
        return payment


class StripeService:
    def __init__(self):
        if not stripe:
            raise Exception("Stripe library not installed. Run: pip install stripe")
        self.stripe = stripe
        provider = PaymentProvider.objects.filter(name='stripe', is_active=True).first()
        if provider:
            self.stripe.api_key = provider.get_api_key()
    
    def create_customer(self, user):
        """Crear cliente en Stripe"""
        try:
            customer = self.stripe.Customer.create(
                email=user.email,
                name=user.full_name,
                metadata={'user_id': user.id}
            )
            return customer
        except Exception as e:
            raise Exception(f"Error creating Stripe customer: {str(e)}")
    
    def create_subscription_payment(self, user, plan_id):
        """Crear pago para suscripción"""
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)
            
            # Crear customer si no existe
            customer = self.create_customer(user)
            
            # Crear payment intent
            payment_intent = self.stripe.PaymentIntent.create(
                amount=int(plan.price * 100),  # Stripe usa centavos
                currency='usd',
                customer=customer.id,
                metadata={
                    'user_id': user.id,
                    'plan_id': plan.id,
                    'type': 'subscription'
                }
            )
            
            # Crear registro de pago
            payment = Payment.objects.create(
                user=user,
                provider=PaymentProvider.objects.get(name='stripe'),
                amount=plan.price,
                provider_payment_id=payment_intent.id,
                provider_customer_id=customer.id,
                metadata={
                    'plan_id': plan.id,
                    'plan_name': plan.name
                }
            )
            
            return {
                'payment_id': payment.id,
                'client_secret': payment_intent.client_secret,
                'amount': plan.price
            }
            
        except Exception as e:
            raise Exception(f"Error creating subscription payment: {str(e)}")

class OnboardingService:
    @staticmethod
    def complete_subscription_purchase(payment_id):
        """Completar proceso de compra y crear tenant automáticamente"""
        try:
            payment = Payment.objects.get(id=payment_id)
            
            if payment.status != 'completed':
                raise Exception("Payment not completed")
            
            user = payment.user
            plan_id = payment.metadata.get('plan_id')
            plan = SubscriptionPlan.objects.get(id=plan_id)
            
            # 1. Crear tenant automáticamente
            tenant = Tenant.objects.create(
                name=f"{user.full_name}'s Barbershop",
                owner=user.email,
                is_active=True
            )
            
            # 2. Asignar tenant al usuario
            user.tenant = tenant
            user.save()
            
            # 3. Crear suscripción
            subscription = UserSubscription.objects.create(
                user=user,
                plan=plan,
                is_active=True,
                auto_renew=True
            )
            
            # 4. Vincular pago con suscripción
            payment.subscription = subscription
            payment.save()
            
            # 5. Asignar rol Client-Admin
            from apps.roles_api.models import Role, UserRole
            from apps.roles_api.default_permissions import ensure_role_default_permissions
            client_admin_role = Role.objects.get(name='Client-Admin')
            ensure_role_default_permissions(client_admin_role)
            UserRole.objects.get_or_create(
                user=user,
                role=client_admin_role,
                tenant=tenant
            )
            
            return {
                'tenant': tenant,
                'subscription': subscription,
                'success': True
            }
            
        except Exception as e:
            raise Exception(f"Error completing onboarding: {str(e)}")

class NotificationService:
    @staticmethod
    def send_welcome_email(user, tenant):
        """Enviar email de bienvenida"""
        from apps.notifications_api.models import NotificationTemplate, Notification
        template = NotificationTemplate.objects.filter(
            Q(notification_type='welcome'),
            Q(type='email'),
            Q(tenant=tenant) | Q(tenant__isnull=True),
            is_active=True
        ).first()
        if template:
            notification = Notification.objects.create(
                recipient=user,
                template=template,
                subject=template.subject or f"¡Bienvenido a Auron Suite!",
                message=template.body,
                metadata={'tenant_id': str(tenant.id), 'user_name': user.full_name or user.email}
            )
            notification.send()
            logger.info("Welcome email sent user_id=%s tenant_id=%s notification_id=%s", user.id, tenant.id, notification.id)
        else:
            logger.warning("No active welcome email template found")
    
    @staticmethod
    def send_payment_confirmation(user, payment):
        """Enviar confirmación de pago"""
        from apps.notifications_api.models import NotificationTemplate, Notification
        template = NotificationTemplate.objects.filter(
            Q(notification_type='payment_received'),
            Q(type='email'),
            Q(tenant=user.tenant) | Q(tenant__isnull=True),
            is_active=True
        ).first()
        if template:
            notification = Notification.objects.create(
                recipient=user,
                template=template,
                subject=template.subject or "Pago recibido",
                message=template.body,
                metadata={
                    'payment_id': str(payment.id),
                    'amount': str(payment.amount),
                    'user_name': user.full_name or user.email
                }
            )
            notification.send()
            logger.info("Payment confirmation sent user_id=%s payment_id=%s notification_id=%s", user.id, payment.id, notification.id)
        else:
            logger.warning("No active payment_received email template found")
    
    @staticmethod
    def send_subscription_expiry_warning(user, subscription):
        """Enviar advertencia de expiración"""
        from apps.notifications_api.models import NotificationTemplate, Notification
        template = NotificationTemplate.objects.filter(
            Q(notification_type='subscription_expiring'),
            Q(type='email'),
            Q(tenant=user.tenant) | Q(tenant__isnull=True),
            is_active=True
        ).first()
        if template:
            notification = Notification.objects.create(
                recipient=user,
                template=template,
                subject=template.subject or "Suscripción próxima a vencer",
                message=template.body,
                metadata={
                    'subscription_id': str(subscription.id),
                    'plan_name': subscription.plan.name if subscription.plan else 'N/A',
                    'user_name': user.full_name or user.email
                }
            )
            notification.send()
            logger.info("Subscription expiry warning sent user_id=%s subscription_id=%s notification_id=%s", user.id, subscription.id, notification.id)
        else:
            logger.warning("No active subscription_expiring email template found")
