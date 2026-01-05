# pylint: disable=line-too-long,useless-suppression
# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------

"""
Data models for workflow agents.
"""

from pydantic import BaseModel, Field


class ServiceSelectionResult(BaseModel):
    """Structured response for service selection."""
    model_config = {"extra": "forbid"} 
    
    IsComplete: bool = Field(
        ..., 
        description="True when a unique service has been selected."
    )
    ServiceId: str = Field(
        ..., 
        description="Identifier of the selected service."
    )
    ServiceName: str = Field(
        ..., 
        description="Human-friendly name of the selected service."
    )
    UserMessage: str = Field(
        ..., 
        description="Message to the user (question or confirmation)."
    )


class BalanceResult(BaseModel):
    """Balance information response."""
    model_config = {"extra": "forbid"}
    
    Balance: float = Field(
        ...,
        description="Available balance."
    )
    Currency: str = Field(
        ...,
        description="Currency code (e.g., S/.)"
    )
    ErrorMessage: str = Field(
        ...,
        description="Present when the tool call failed."
    )


class PaymentConfirmationResult(BaseModel):
    """Payment confirmation response."""
    model_config = {"extra": "forbid"}
    
    IsComplete: bool = Field(
        ...,
        description="True when confirmation flow is finished (confirmed or cancelled)."
    )
    Confirmed: bool = Field(
        ...,
        description="True if the user confirmed the payment."
    )
    Amount: float = Field(
        ...,
        description="Payment amount; 0 if not yet provided."
    )
    ServiceId: str = Field(
        ...,
        description="Echo of the selected service id."
    )
    UserMessage: str = Field(
        ...,
        description="Message to the user (prompt/confirmation)."
    )


class PaymentExecutionResult(BaseModel):
    """Payment execution result."""
    model_config = {"extra": "forbid"}
    
    ReceiptId: str = Field(
        ...,
        description="Receipt identifier."
    )
    ReceiptDetails: str = Field(
        ...,
        description="Receipt details."
    )
    ErrorMessage: str = Field(
        ...,
        description="Present when the tool call failed."
    )

