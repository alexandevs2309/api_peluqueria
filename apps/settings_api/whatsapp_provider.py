import os
import requests
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class WhatsAppProvider(ABC):
    """Interfaz abstracta para proveedores de WhatsApp"""

    @abstractmethod
    def create_instance(self, instance_name: str, token: str = None) -> dict:
        """Crea una nueva instancia en la pasarela y devuelve el código QR si aplica"""
        pass

    @abstractmethod
    def get_status(self, instance_name: str) -> str:
        """Obtiene el estado de conexión de la instancia (connected, disconnected, connecting)"""
        pass

    @abstractmethod
    def delete_instance(self, instance_name: str) -> bool:
        """Elimina una instancia en la pasarela"""
        pass

    @abstractmethod
    def send_message(self, instance_name: str, token: str, to_phone: str, message: str) -> str:
        """Envía un mensaje de texto a través de la instancia"""
        pass

    @abstractmethod
    def set_webhook(self, instance_name: str, webhook_url: str) -> bool:
        """Configura el webhook para eventos de la instancia"""
        pass


class EvolutionApiProvider(WhatsAppProvider):
    """Implementación de pasarela WhatsApp usando Evolution API (autohospedada)"""

    def __init__(self):
        self.base_url = os.getenv("EVOLUTION_API_URL", "http://localhost:8080").rstrip("/")
        self.global_token = os.getenv("EVOLUTION_API_TOKEN", "")

    def _get_headers(self, instance_token: str = None) -> dict:
        headers = {
            "Content-Type": "application/json",
        }
        if instance_token:
            headers["apikey"] = instance_token
        elif self.global_token:
            headers["apikey"] = self.global_token
        return headers

    def create_instance(self, instance_name: str, token: str = None) -> dict:
        """Crea una instancia y obtiene el QR si no está conectada"""
        url = f"{self.base_url}/instance/create"
        payload = {
            "instanceName": instance_name,
            "token": token,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS"
        }
        try:
            logger.info("EvolutionAPI: Creating instance %s", instance_name)
            response = requests.post(url, json=payload, headers=self._get_headers(), timeout=15)
            
            # Si la instancia ya existe, la eliminamos y reintentamos la creación
            if response.status_code == 403 and "already in use" in response.text:
                logger.warning("EvolutionAPI: Instance %s already exists. Deleting and recreating...", instance_name)
                deleted = self.delete_instance(instance_name)
                logger.info("EvolutionAPI: Deletion result for %s: %s", instance_name, deleted)
                import time
                time.sleep(1.5)  # Evitar condiciones de carrera en base de datos
                response = requests.post(url, json=payload, headers=self._get_headers(), timeout=15)

            if response.status_code in (200, 201):
                data = response.json()
                # La estructura de Evolution API retorna info de qr
                qrcode_data = data.get("qrcode", {})
                
                # Evolution API v2 retorna 'hash' como string con la apikey directamente
                hash_data = data.get("hash")
                api_key = token
                if isinstance(hash_data, dict):
                    api_key = hash_data.get("apikey") or token
                elif isinstance(hash_data, str):
                    api_key = hash_data
                
                return {
                    "success": True,
                    "instance_name": instance_name,
                    "token": api_key,
                    "qrcode_base64": qrcode_data.get("base64") if qrcode_data else None,
                    "qrcode_code": qrcode_data.get("code") if qrcode_data else None,
                    "status": "connecting"
                }
            logger.error("EvolutionAPI: Failed to create instance %s. Status: %s, Body: %s", 
                         instance_name, response.status_code, response.text)
            return {"success": False, "error": f"Status code: {response.status_code}"}
        except Exception as e:
            logger.error("EvolutionAPI: Error creating instance %s: %s", instance_name, str(e))
            return {"success": False, "error": str(e)}

    def get_status(self, instance_name: str) -> str:
        """Verifica si la instancia está conectada"""
        url = f"{self.base_url}/instance/connectionState/{instance_name}"
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                state = response.json().get("instance", {}).get("state")
                if state == "open":
                    return "connected"
                elif state in ("connecting", "connecting_chat"):
                    return "connecting"
            return "disconnected"
        except Exception as e:
            logger.error("EvolutionAPI: Error checking state for %s: %s", instance_name, str(e))
            return "disconnected"

    def delete_instance(self, instance_name: str) -> bool:
        """Elimina la instancia de Evolution API"""
        # Primero intentamos logout, luego delete
        logout_url = f"{self.base_url}/instance/logout/{instance_name}"
        delete_url = f"{self.base_url}/instance/delete/{instance_name}"
        try:
            # Logout
            requests.post(logout_url, headers=self._get_headers(), timeout=10)
            # Delete
            resp = requests.delete(delete_url, headers=self._get_headers(), timeout=10)
            return resp.status_code in (200, 201)
        except Exception as e:
            logger.error("EvolutionAPI: Error deleting instance %s: %s", instance_name, str(e))
            return False

    def send_message(self, instance_name: str, token: str, to_phone: str, message: str) -> str:
        """Envía mensaje de texto"""
        url = f"{self.base_url}/message/sendText/{instance_name}"
        
        # Limpiar el número de cualquier carácter no numérico
        import re
        clean_phone = re.sub(r'\D', '', to_phone)
        # Si tiene 10 dígitos (RD/US), prepender el código de país '1'
        if len(clean_phone) == 10:
            clean_phone = '1' + clean_phone
        
        payload = {
            "number": clean_phone,
            "text": message,
            "options": {
                "delay": 1000,
                "presence": "composing"
            }
        }
        try:
            logger.info("EvolutionAPI: Sending message to %s via %s", clean_phone, instance_name)
            response = requests.post(url, json=payload, headers=self._get_headers(token), timeout=15)
            if response.status_code in (200, 201):
                data = response.json()
                return data.get("key", {}).get("id") or "success"
            raise Exception(f"Failed sending message. Status: {response.status_code}, Body: {response.text}")
        except Exception as e:
            logger.error("EvolutionAPI: Error sending message via %s to %s: %s", instance_name, clean_phone, str(e))
            raise e

    def set_webhook(self, instance_name: str, webhook_url: str) -> bool:
        """Configura el webhook para recibir actualizaciones de conexión"""
        url = f"{self.base_url}/webhook/set/{instance_name}"
        payload = {
            "enabled": True,
            "url": webhook_url,
            "events": [
                "CONNECTION_UPDATE"
            ]
        }
        try:
            response = requests.post(url, json=payload, headers=self._get_headers(), timeout=10)
            return response.status_code in (200, 201)
        except Exception as e:
            logger.error("EvolutionAPI: Error setting webhook for %s: %s", instance_name, str(e))
            return False


def get_whatsapp_provider() -> WhatsAppProvider:
    """Retorna el proveedor activo. Modular por diseño."""
    # Podría configurarse mediante variables de entorno si hubiesen más proveedores
    return EvolutionApiProvider()
