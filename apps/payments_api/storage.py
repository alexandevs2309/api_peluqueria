"""
Almacenamiento de comprobantes de pago manual.

Los comprobantes (transfers bancarios, depósitos, capturas) viven FUERA de
MEDIA_ROOT y sin URL pública (base_url=None): nunca son servidos por
django.views.static.serve en DEBUG/producción. El único punto de acceso es el
endpoint de descarga protegido (apps.payments_api.views.manual_proof_download).
"""
import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PaymentProofStorage(FileSystemStorage):
    """FileSystemStorage dedicado, con ubicación configurable."""

    def __init__(self, location=None, base_url=None, *args, **kwargs):
        location = location or getattr(settings, 'PROOF_STORAGE_ROOT', None)
        super().__init__(location=location, base_url=None, *args, **kwargs)
        if self.base_location:
            os.makedirs(self.base_location, exist_ok=True)