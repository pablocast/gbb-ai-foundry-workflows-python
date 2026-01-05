# pylint: disable=line-too-long,useless-suppression
# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------

"""
Function Tools wrapper
Wraps plugin methods as FunctionTool objects for Azure AI Projects agents.
"""

from azure.ai.projects.models import FunctionTool
from plugins.implementations import PaymentPlugin

# Create plugin instance
payment_plugin = PaymentPlugin()

# List Favorite Services Tool
list_favorite_services_tool = FunctionTool(
    name="list_favorite_services",
    parameters={
        "type": "object",
        "properties": {
            "customer_id": {
                "type": "string",
                "description": "Customer identifier",
            },
        },
        "required": ["customer_id"],
        "additionalProperties": False,
    },
    description="List favorite services for a customer.",
    strict=True,
)


# Get Balance Tool
get_balance_tool = FunctionTool(
    name="get_balance",
    parameters={
        "type": "object",
        "properties": {
            "account_id": {
                "type": "string",
                "description": "Account identifier",
            },
        },
        "required": ["account_id"],
        "additionalProperties": False,
    },
    description="Get the balance of an account.",
    strict=True,
)


# Pay Service Tool
pay_service_tool = FunctionTool(
    name="pay_service",
    parameters={
        "type": "object",
        "properties": {
            "account_id": {
                "type": "string",
                "description": "Account identifier",
            },
            "service_id": {
                "type": "string",
                "description": "Service identifier",
            },
            "amount": {
                "type": "number",
                "description": "Payment amount",
            },
        },
        "required": ["account_id", "service_id", "amount"],
        "additionalProperties": False,
    },
    description="Execute a payment for a service.",
    strict=True,
)


# Get Latest Bill Tool
get_latest_bill_tool = FunctionTool(
    name="get_latest_bill",
    parameters={
        "type": "object",
        "properties": {
            "customer_id": {
                "type": "string",
                "description": "Customer identifier",
            },
            "service_id": {
                "type": "string",
                "description": "Service identifier",
            },
        },
        "required": ["customer_id", "service_id"],
        "additionalProperties": False,
    },
    description="Get the latest bill for a customer and service.",
    strict=True,
)


# Tool execution handler
def handle_tool_call(tool_name: str, arguments: dict):
    """
    Execute the appropriate plugin function based on tool name.
    
    Args:
        tool_name: Name of the tool to execute
        arguments: Dictionary of arguments for the tool
        
    Returns:
        Result from the plugin function
    """
    if tool_name == "list_favorite_services":
        return payment_plugin.list_favorite_services(
            customer_id=arguments["customer_id"]
        )
    elif tool_name == "get_balance":
        return payment_plugin.get_balance(
            account_id=arguments["account_id"]
        )
    elif tool_name == "pay_service":
        return payment_plugin.pay_service(
            account_id=arguments["account_id"],
            service_id=arguments["service_id"],
            amount=arguments["amount"]
        )
    elif tool_name == "get_latest_bill":
        return payment_plugin.get_latest_bill(
            customer_id=arguments["customer_id"],
            service_id=arguments["service_id"]
        )
    else:
        raise ValueError(f"Unknown tool: {tool_name}")

