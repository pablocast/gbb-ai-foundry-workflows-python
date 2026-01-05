# pylint: disable=line-too-long,useless-suppression
# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------

"""
Multi-agent workflow demonstration with service payment processing.
"""

import os
import asyncio
from dotenv import load_dotenv
from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient

# Import modules
from agents.factory import AgentFactory
from agents.models import (
    ServiceSelectionResult,
    BalanceResult,
    PaymentConfirmationResult,
    PaymentExecutionResult
)
from plugins.foundry_wrappers import (
    list_favorite_services_tool,
    get_balance_tool,
    pay_service_tool,
    get_latest_bill_tool,
    handle_tool_call
)
from workflows.runner import WorkflowRunner

load_dotenv()

runner =  WorkflowRunner({
        "list_favorite_services": lambda customer_id: handle_tool_call(
            "list_favorite_services", 
            {"customer_id": customer_id}
        ),
        "get_balance": lambda account_id: handle_tool_call(
            "get_balance", 
            {"account_id": account_id}
        ),
        "pay_service": lambda account_id, service_id, amount: handle_tool_call(
            "pay_service", 
            {"account_id": account_id, "service_id": service_id, "amount": amount}
        ),
        "get_latest_bill": lambda customer_id, service_id: handle_tool_call(
            "get_latest_bill", 
            {"customer_id": customer_id, "service_id": service_id}
        ),
    }
)


async def main():
    """Main entry point for the workflow demonstration."""
    
    endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    model_deployment = os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"]
    
    async with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=endpoint, credential=credential) as project_client,
        project_client.get_openai_client() as openai_client,
    ):
        # Create registries
        schemas_registry = {
            "ServiceSelectionResult": ServiceSelectionResult,
            "BalanceResult": BalanceResult,
            "PaymentConfirmationResult": PaymentConfirmationResult,
            "PaymentExecutionResult": PaymentExecutionResult
        }

        tools_registry = {
            "ListFavoriteServices": list_favorite_services_tool,
            "GetBalance": get_balance_tool,
            "PayService": pay_service_tool,
            "GetLatestBill": get_latest_bill_tool,
        }

        # Create factory
        factory = AgentFactory(
            model_deployment, 
            schemas_registry, 
            tools_registry
        )
        
        # Create Agents in Microsoft Foundry Project
        await factory.create_all_agents_from_config(
            project_client,
            agent_names=["ServiceSelectionAgent", "GetBalanceAgent", "LatestBillAndConfirmationAgent", "PayServiceAgent"],
            config_file="service_agents.yaml"
        )

        # Create workflow
        workflow = await factory.create_workflow(
            project_client,
            workflow_name="service-payment-workflow",
            workflow_file="service-payment-workflow.yaml"
        )
        
        # Create conversation
        conversation = await openai_client.conversations.create()
        print(f"Created conversation (id: {conversation.id})")
        

        # Interactive session
        print("\nStarting interactive session. Type 'quit' to exit.\n")
        
        while True:
            user_input = input("\033[92mINPUT: \033[97m").strip()
            
            if user_input.lower() == 'quit':
                print("Exiting interactive session.")
                break
            
            if not user_input:
                continue
            
            # Execute workflow
            await runner.execute_async(
                openai_client, 
                conversation.id, 
                workflow.name, 
                user_input
            )
            
            print()


if __name__ == "__main__":
    asyncio.run(main())