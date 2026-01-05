# pylint: disable=line-too-long,useless-suppression
# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------

"""
Payment Service Workflow - Code-based implementation
Converted from declarative YAML workflow using Microsoft Agent Framework
"""

import os
import asyncio
from typing import List
from dotenv import load_dotenv
from azure.identity.aio import DefaultAzureCredential
from agent_framework import (
    ChatAgent,
    ChatMessage,
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    WorkflowOutputEvent,
    WorkflowStatusEvent,
    WorkflowRunState,
    handler,
)
from agent_framework_azure_ai import AzureAIAgentClient
from typing_extensions import Never

from agents.models import (
    ServiceSelectionResult,
    BalanceResult,
    PaymentConfirmationResult,
    PaymentExecutionResult
)
from foundry_wrappers.payment_tools import (
    list_favorite_services_tool,
    get_balance_tool,
    pay_service_tool,
    get_latest_bill_tool,
)

load_dotenv()


# Workflow State - equivalent to Local variables in YAML
class WorkflowState:
    """Holds the workflow state across executors."""
    def __init__(self):
        self.user_message: str = ""
        self.customer_id: str = "cust-1"
        self.account_id: str = "acct-123"
        self.service_selection: ServiceSelectionResult | None = None
        self.balance: BalanceResult | None = None
        self.confirmation: PaymentConfirmationResult | None = None
        self.payment: PaymentExecutionResult | None = None


# Executor 1: Service Selection Agent
class ServiceSelectionExecutor(Executor):
    """Executor for service selection using ServiceSelectionAgent."""
    
    agent: ChatAgent
    state: WorkflowState
    
    def __init__(self, agent: ChatAgent, state: WorkflowState, id="select_service"):
        self.agent = agent
        self.state = state
        super().__init__(id=id)
    
    @handler
    async def handle_start(self, message: str, ctx: WorkflowContext[WorkflowState]) -> None:
        """Handle initial user message and select service."""
        self.state.user_message = message
        
        # Build conversation with structured inputs
        messages: List[ChatMessage] = [
            ChatMessage(role="user", text=message)
        ]
        
        # Loop until service is selected (externalLoop equivalent)
        while True:
            response = await self.agent.run(
                messages,
                arguments={"CustomerId": self.state.customer_id}
            )
            
            # Parse structured output
            # Note: In practice, you'd parse the JSON response from response.messages[-1].contents[-1].text
            # For this example, assume the agent returns ServiceSelectionResult
            
            print(f"ServiceSelectionAgent: {response.messages[-1].contents[-1].text}")
            messages.extend(response.messages)
            
            # Check if complete (simplified - actual implementation needs JSON parsing)
            # self.state.service_selection = parse_service_selection(response)
            # if self.state.service_selection.IsComplete:
            #     break
            
            # For demo, break after first iteration
            break
        
        # Forward state to next executor
        await ctx.send_message(self.state)


# Executor 2: Get Balance Agent
class GetBalanceExecutor(Executor):
    """Executor for retrieving account balance."""
    
    agent: ChatAgent
    
    def __init__(self, agent: ChatAgent, id="get_balance"):
        self.agent = agent
        super().__init__(id=id)
    
    @handler
    async def handle_balance_check(self, state: WorkflowState, ctx: WorkflowContext[WorkflowState]) -> None:
        """Get account balance."""
        response = await self.agent.run(
            [],
            arguments={"AccountId": state.account_id}
        )
        
        print(f"GetBalanceAgent: {response.messages[-1].contents[-1].text}")
        
        # Parse balance result
        # state.balance = parse_balance(response)
        
        await ctx.send_message(state)


# Executor 3: Confirmation Agent
class ConfirmationExecutor(Executor):
    """Executor for payment confirmation."""
    
    agent: ChatAgent
    
    def __init__(self, agent: ChatAgent, id="confirm_payment"):
        self.agent = agent
        super().__init__(id=id)
    
    @handler
    async def handle_confirmation(self, state: WorkflowState, ctx: WorkflowContext[WorkflowState]) -> None:
        """Confirm payment with user."""
        if state.service_selection is None or state.balance is None:
            await ctx.yield_output("Error: Missing required data")
            return
        
        # Loop until confirmation is complete (externalLoop equivalent)
        messages: List[ChatMessage] = []
        
        while True:
            response = await self.agent.run(
                messages,
                arguments={
                    "CustomerId": state.customer_id,
                    "ServiceId": state.service_selection.ServiceId,
                    "ServiceName": state.service_selection.ServiceName,
                    "Balance": state.balance.Balance,
                    "Currency": state.balance.Currency
                }
            )
            
            print(f"ConfirmationAgent: {response.messages[-1].contents[-1].text}")
            messages.extend(response.messages)
            
            # Parse confirmation result
            # state.confirmation = parse_confirmation(response)
            # if state.confirmation.IsComplete:
            #     break
            
            # For demo, break after first iteration
            break
        
        await ctx.send_message(state)


# Executor 4: Decision Logic
class DecisionExecutor(Executor):
    """Executor for payment decision logic (ConditionGroup equivalent)."""
    
    def __init__(self, id="decision"):
        super().__init__(id=id)
    
    @handler
    async def handle_decision(self, state: WorkflowState, ctx: WorkflowContext[WorkflowState, str]) -> None:
        """Make decision based on confirmation."""
        if state.confirmation is None:
            await ctx.yield_output("Error: No confirmation data")
            return
        
        # Case: Cancelled
        if not state.confirmation.Confirmed:
            await ctx.yield_output("Entendido, no realizo el pago. ¿Quieres pagar otro servicio?")
            return
        
        # Case: Confirmed
        if state.confirmation.Confirmed:
            # Validate amount
            if state.confirmation.Amount <= 0:
                await ctx.yield_output("El monto debe ser mayor que 0. No se pudo procesar el pago.")
                return
            
            # Check insufficient funds
            if state.balance and state.confirmation.Amount > state.balance.Balance:
                message = (
                    f"❌ Fondos insuficientes: El monto a pagar "
                    f"({state.confirmation.Amount} {state.balance.Currency}) \n"
                    f"es mayor que tu saldo disponible "
                    f"({state.balance.Balance} {state.balance.Currency}).\n"
                    f"No se realizó el pago. ¿Deseas pagar otro servicio?"
                )
                await ctx.yield_output(message)
                return
            
            # All validation passed - proceed to payment
            await ctx.send_message(state)


# Executor 5: Payment Execution
class PaymentExecutor(Executor):
    """Executor for payment execution."""
    
    agent: ChatAgent
    
    def __init__(self, agent: ChatAgent, id="pay"):
        self.agent = agent
        super().__init__(id=id)
    
    @handler
    async def handle_payment(self, state: WorkflowState, ctx: WorkflowContext[Never, str]) -> None:
        """Execute the payment."""
        if state.confirmation is None or state.service_selection is None:
            await ctx.yield_output("Error: Missing payment data")
            return
        
        response = await self.agent.run(
            [],
            arguments={
                "AccountId": state.account_id,
                "ServiceId": state.service_selection.ServiceId,
                "Amount": state.confirmation.Amount
            }
        )
        
        print(f"PaymentAgent: {response.messages[-1].contents[-1].text}")
        
        # Parse payment result
        # state.payment = parse_payment(response)
        
        receipt_message = (
            f"✅ Pago confirmado — ReceiptId: {state.payment.ReceiptId if state.payment else 'N/A'}\n"
            f"{state.payment.ReceiptDetails if state.payment else ''}\n"
            f"¿Deseas realizar otro pago?"
        )
        
        await ctx.yield_output(receipt_message)


async def main():
    """Build and run the payment workflow."""
    
    endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    model_deployment = os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"]
    
    # Initialize workflow state
    state = WorkflowState()
    
    async with (
        DefaultAzureCredential() as credential,
        # Create agents
        ChatAgent(
            chat_client=AzureAIAgentClient(
                project_endpoint=endpoint,
                model_deployment_name=model_deployment,
                async_credential=credential,
                agent_name="ServiceSelectionAgent",
            ),
            instructions="""Eres un asistente de pagos.
            Ayuda al usuario a seleccionar un servicio favorito para pagar.
            Usa la herramienta list_favorite_services para mostrar opciones.""",
            tools=[list_favorite_services_tool],
        ) as service_agent,
        ChatAgent(
            chat_client=AzureAIAgentClient(
                project_endpoint=endpoint,
                model_deployment_name=model_deployment,
                async_credential=credential,
                agent_name="GetBalanceAgent",
            ),
            instructions="Recupera el balance de la cuenta usando get_balance.",
            tools=[get_balance_tool],
        ) as balance_agent,
        ChatAgent(
            chat_client=AzureAIAgentClient(
                project_endpoint=endpoint,
                model_deployment_name=model_deployment,
                async_credential=credential,
                agent_name="LatestBillAndConfirmationAgent",
            ),
            instructions="Obtén la factura más reciente y confirma el pago con el usuario.",
            tools=[get_latest_bill_tool],
        ) as confirmation_agent,
        ChatAgent(
            chat_client=AzureAIAgentClient(
                project_endpoint=endpoint,
                model_deployment_name=model_deployment,
                async_credential=credential,
                agent_name="PayServiceAgent",
            ),
            instructions="Ejecuta el pago del servicio usando pay_service.",
            tools=[pay_service_tool],
        ) as payment_agent
    ):
        # Create executors
        service_executor = ServiceSelectionExecutor(service_agent, state)
        balance_executor = GetBalanceExecutor(balance_agent)
        confirmation_executor = ConfirmationExecutor(confirmation_agent)
        decision_executor = DecisionExecutor()
        payment_executor = PaymentExecutor(payment_agent)
        
        # Build workflow graph
        workflow = (
            WorkflowBuilder()
            .set_start_executor(service_executor)
            .add_edge(service_executor, balance_executor)
            .add_edge(balance_executor, confirmation_executor)
            .add_edge(confirmation_executor, decision_executor)
            .add_edge(decision_executor, payment_executor)
            .build()
        )
        
        # Run workflow with streaming
        print("\nStarting payment workflow...\n")
        
        async for event in workflow.run_stream("cuales son mis servicios favoritos"):
            if isinstance(event, WorkflowStatusEvent):
                if event.state == WorkflowRunState.IDLE:
                    print(f"\nWorkflow State: IDLE")
            elif isinstance(event, WorkflowOutputEvent):
                print(f"\n🎉 Workflow Output: {event.data}")
                break
        
        # Allow cleanup
        await asyncio.sleep(1.0)


if __name__ == "__main__":
    asyncio.run(main())
