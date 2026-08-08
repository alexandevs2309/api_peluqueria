from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


@dataclass
class PaymentResult:
    success: bool
    transaction_id: str
    authorization_code: str
    status: str
    amount: Decimal
    currency: str
    error_message: Optional[str] = None
    raw_response: Optional[dict] = None


@dataclass
class PaymentProviderConfig:
    merchant_id: str = ''
    terminal_id: str = ''
    api_key: str = ''
    webhook_secret: str = ''
    sandbox: bool = True
    currency: str = 'DOP'


class PaymentProvider(ABC):
    """Interfaz abstracta para proveedores de pago presencial (POS)."""

    @abstractmethod
    def charge(self, amount: Decimal, currency: str, metadata: dict = None) -> PaymentResult:
        pass

    @abstractmethod
    def refund(self, transaction_id: str, amount: Optional[Decimal] = None) -> PaymentResult:
        pass

    @abstractmethod
    def get_status(self, transaction_id: str) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass
