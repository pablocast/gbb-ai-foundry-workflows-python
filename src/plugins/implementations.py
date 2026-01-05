# pylint: disable=line-too-long,useless-suppression
# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------

"""
Payment Plugin for Azure AI Projects Agents
Provides functions for managing service payments, bills, and account balances.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Annotated
import uuid
from pydantic import BaseModel, Field

class ServiceInfo(BaseModel):
    """Information about a service."""
    model_config = {"extra": "forbid"}
    
    id: str = Field(default="", description="Service identifier")
    name: str = Field(default="", description="Service name")
    category: str = Field(default="", description="Service category")


class AccountInfo(BaseModel):
    """Information about a customer account."""
    model_config = {"extra": "forbid"}
    
    id: str = Field(default="", description="Account identifier")
    balance: float = Field(default=0.0, description="Account balance")
    currency: str = Field(default="S/.", description="Currency code")


class BalanceInfo(BaseModel):
    """Balance information response."""
    model_config = {"extra": "forbid"}
    
    balance: float = Field(description="Account balance")
    currency: str = Field(default="S/.", description="Currency code")
    error_message: str = Field(default="", description="Error message if any")


class PaymentResult(BaseModel):
    """Result of a payment operation."""
    model_config = {"extra": "forbid"}
    
    receipt_id: str = Field(default="", description="Receipt identifier")
    receipt_details: str = Field(default="", description="Receipt details")
    error_message: str = Field(default="", description="Error message if any")


class ReceiptInfo(BaseModel):
    """Receipt information."""
    model_config = {"extra": "forbid"}
    
    receipt_id: str = Field(default="", description="Receipt identifier")
    account_id: str = Field(default="", description="Account identifier")
    service_id: str = Field(default="", description="Service identifier")
    service_name: str = Field(default="", description="Service name")
    amount: float = Field(default=0.0, description="Payment amount")
    currency: str = Field(default="S/.", description="Currency code")
    timestamp: str = Field(default="", description="Timestamp of payment")


class BillInfo(BaseModel):
    """Bill information."""
    model_config = {"extra": "forbid"}
    
    bill_id: str = Field(default="", description="Bill identifier")
    customer_id: str = Field(default="", description="Customer identifier")
    service_id: str = Field(default="", description="Service identifier")
    service_name: str = Field(default="", description="Service name")
    amount: float = Field(default=0.0, description="Bill amount")
    currency: str = Field(default="S/.", description="Currency code")
    due_date: str = Field(default="", description="Due date")
    period: str = Field(default="", description="Billing period")
    status: str = Field(default="", description="Bill status (Pendiente, Vencido, Pagado)")
    error_message: str = Field(default="", description="Error message if any")


class PaymentPlugin:
    """Plugin for managing service payments."""
    
    def __init__(self):
        # Customer favorite services mapping
        self._customer_favorites: Dict[str, List[str]] = {
            "cust-1": ["SVC001", "SVC002", "SVC004"],
            "cust-2": ["SVC003", "SVC005"],
            "cust-3": ["SVC001", "SVC003", "SVC004", "SVC005"],
        }
        
        # Available services
        self._services: Dict[str, ServiceInfo] = {
            "SVC001": ServiceInfo(id="SVC001", name="Luz del Sur", category="Electricidad"),
            "SVC002": ServiceInfo(id="SVC002", name="Sedapal", category="Agua"),
            "SVC003": ServiceInfo(id="SVC003", name="Claro Móvil", category="Telefonía"),
            "SVC004": ServiceInfo(id="SVC004", name="Netflix", category="Streaming"),
            "SVC005": ServiceInfo(id="SVC005", name="Movistar Hogar", category="Internet"),
        }
        
        # Customer accounts
        self._accounts: Dict[str, AccountInfo] = {
            "acct-123": AccountInfo(id="acct-123", balance=20.50, currency="S/."),
            "acct-124": AccountInfo(id="acct-124", balance=250.00, currency="S/."),
        }
        
        # Latest bills
        now = datetime.now()
        self._latest_bills: Dict[str, BillInfo] = {
            "cust-1:SVC001": BillInfo(
                bill_id="BILL-001", customer_id="cust-1", service_id="SVC001", 
                service_name="Luz del Sur", amount=85.50, currency="S/.",
                due_date=(now + timedelta(days=15)).isoformat(),
                period="Noviembre 2025", status="Pendiente"
            ),
            "cust-1:SVC002": BillInfo(
                bill_id="BILL-002", customer_id="cust-1", service_id="SVC002",
                service_name="Sedapal", amount=42.30, currency="S/.",
                due_date=(now + timedelta(days=10)).isoformat(),
                period="Noviembre 2025", status="Pendiente"
            ),
            "cust-1:SVC004": BillInfo(
                bill_id="BILL-003", customer_id="cust-1", service_id="SVC004",
                service_name="Netflix", amount=44.90, currency="S/.",
                due_date=(now + timedelta(days=5)).isoformat(),
                period="Diciembre 2025", status="Pendiente"
            ),
            "cust-2:SVC003": BillInfo(
                bill_id="BILL-004", customer_id="cust-2", service_id="SVC003",
                service_name="Claro Móvil", amount=59.90, currency="S/.",
                due_date=(now + timedelta(days=8)).isoformat(),
                period="Diciembre 2025", status="Pendiente"
            ),
            "cust-2:SVC005": BillInfo(
                bill_id="BILL-005", customer_id="cust-2", service_id="SVC005",
                service_name="Movistar Hogar", amount=120.00, currency="S/.",
                due_date=(now + timedelta(days=20)).isoformat(),
                period="Diciembre 2025", status="Pendiente"
            ),
            "cust-3:SVC001": BillInfo(
                bill_id="BILL-006", customer_id="cust-3", service_id="SVC001",
                service_name="Luz del Sur", amount=150.75, currency="S/.",
                due_date=(now + timedelta(days=-2)).isoformat(),
                period="Noviembre 2025", status="Vencido"
            ),
            "cust-3:SVC003": BillInfo(
                bill_id="BILL-007", customer_id="cust-3", service_id="SVC003",
                service_name="Claro Móvil", amount=39.90, currency="S/.",
                due_date=(now + timedelta(days=12)).isoformat(),
                period="Diciembre 2025", status="Pendiente"
            ),
        }
        
        # Receipts (populated after payments)
        self._receipts: Dict[str, ReceiptInfo] = {}
    
    def _trace(self, function_name: str):
        """Print function trace for debugging."""
        print(f"\033[95m\nFUNCTION: {function_name}\033[0m")
    
    def list_favorite_services(
        self,
        customer_id: Annotated[str, "Customer identifier"]
    ) -> List[ServiceInfo]:
        """List favorite services for a customer."""
        self._trace("list_favorite_services")
        
        if customer_id in self._customer_favorites:
            favorite_ids = self._customer_favorites[customer_id]
            return [
                self._services[svc_id] 
                for svc_id in favorite_ids 
                if svc_id in self._services
            ]
        
        return []
    
    def get_balance(
        self,
        account_id: Annotated[str, "Account identifier"]
    ) -> BalanceInfo:
        """Get the balance of an account."""
        self._trace("get_balance")
        
        if account_id in self._accounts:
            account = self._accounts[account_id]
            return BalanceInfo(
                balance=account.balance,
                currency=account.currency,
                error_message=""
            )
        
        return BalanceInfo(
            balance=0.0,
            currency="S/.",
            error_message=f"Account {account_id} not found."
        )
    
    def pay_service(
        self,
        account_id: Annotated[str, "Account identifier"],
        service_id: Annotated[str, "Service identifier"],
        amount: Annotated[float, "Payment amount"]
    ) -> PaymentResult:
        """Execute a payment for a service."""
        self._trace("pay_service")
        
        # Validate account
        if account_id not in self._accounts:
            return PaymentResult(
                receipt_id="",
                receipt_details="",
                error_message=f"Account {account_id} not found."
            )
        
        account = self._accounts[account_id]
        
        # Check balance
        if account.balance < amount:
            return PaymentResult(
                receipt_id="",
                receipt_details="",
                error_message="Insufficient funds."
            )
        
        # Validate service
        if service_id not in self._services:
            return PaymentResult(
                receipt_id="",
                receipt_details="",
                error_message=f"Service {service_id} not found."
            )
        
        service = self._services[service_id]
        
        # Process payment
        account.balance -= amount
        receipt_id = f"RCP-{uuid.uuid4().hex[:12].upper()}"
        timestamp = datetime.utcnow()
        
        receipt = ReceiptInfo(
            receipt_id=receipt_id,
            account_id=account_id,
            service_id=service_id,
            service_name=service.name,
            amount=amount,
            currency=account.currency,
            timestamp=timestamp.isoformat()
        )
        
        self._receipts[receipt_id] = receipt
        
        return PaymentResult(
            receipt_id=receipt_id,
            receipt_details=f"Pago de {amount:.2f} {account.currency} a {service.name} realizado exitosamente. Fecha: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            error_message=""
        )
    
    def get_latest_bill(
        self,
        customer_id: Annotated[str, "Customer identifier"],
        service_id: Annotated[str, "Service identifier"]
    ) -> BillInfo:
        """Get the latest bill for a customer and service."""
        self._trace("get_latest_bill")
        
        key = f"{customer_id}:{service_id}"
        
        if key in self._latest_bills:
            return self._latest_bills[key]
        
        # Check if service exists
        if service_id not in self._services:
            return BillInfo(
                error_message=f"Servicio {service_id} no encontrado."
            )
        
        service = self._services[service_id]
        return BillInfo(
            service_id=service_id,
            service_name=service.name,
            error_message=f"No se encontró factura pendiente para {service.name}."
        )