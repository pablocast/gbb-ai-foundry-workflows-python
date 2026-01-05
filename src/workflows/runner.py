# pylint: disable=line-too-long,useless-suppression
# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------

"""
Workflow Runner for Azure AI Projects
Handles workflow execution with client-side function execution.
"""

import json
from typing import Dict, Callable, List, Optional
from azure.ai.projects.models import ResponseStreamEventType, ItemType


def notify(message: str, color: str = "cyan"):
    """Print colored console output."""
    colors = {
        "cyan": "\033[96m",
        "yellow": "\033[93m",
        "darkgray": "\033[90m",
        "darkyellow": "\033[33m",
        "white": "\033[97m",
        "green": "\033[92m",
        "darkgreen": "\033[32m",
        "magenta": "\033[95m",
        "reset": "\033[0m"
    }
    color_code = colors.get(color.lower(), colors["cyan"])
    print(f"{color_code}{message}{colors['reset']}")


class WorkflowRunner:
    """Workflow runner that executes functions client-side and submits results."""
    
    def __init__(self, function_map: Dict[str, Callable]):
        """
        Initialize workflow runner with function implementations.
        
        Args:
            function_map: Dictionary mapping function names to callable implementations
        """
        self.function_map = function_map
    
    async def execute_async(self, openai_client, conversation_id: str, workflow_name: str, user_input: str):
        """
        Execute workflow with function execution loop.
        
        Args:
            openai_client: The OpenAI client for responses
            conversation_id: The conversation ID
            workflow_name: Name of the workflow agent
            user_input: User input message
        """
        is_complete = False
        current_input = user_input
        tool_outputs = None
        
        while not is_complete:
            # Monitor the workflow and collect function calls
            function_calls = await self.monitor_workflow_async(
                openai_client, 
                conversation_id, 
                workflow_name,
                current_input,
                tool_outputs
            )
            
            if function_calls:
                # notify("\nWORKFLOW: Yield (function calls detected)\n", "darkyellow")
                
                # Execute functions and prepare outputs
                tool_outputs = []
                for func_call in function_calls:
                    result = self.invoke_function(func_call['name'], func_call['arguments'])
                    tool_outputs.append({
                        "type": "function_call_output",
                        "call_id": func_call['call_id'],
                        "output": json.dumps(result)
                    })
                
                # Next iteration will submit these outputs
                current_input = ""  # Empty input to continue conversation
                # notify("WORKFLOW: Resume (submitting function results)\n", "darkyellow")
            else:
                is_complete = True
        
        # notify("\nWORKFLOW: Done!\n", "cyan")
    
    async def monitor_workflow_async(
        self, 
        openai_client, 
        conversation_id: str,
        workflow_name: str,
        user_input: str,
        tool_outputs: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Monitor workflow execution and collect function calls.
        
        Returns:
            List of function calls that need to be executed, empty if workflow is complete
        """
        # Build request parameters
        request_params = {
            "conversation": conversation_id,
            "extra_body": {"agent": {"name": workflow_name, "type": "agent_reference"}},
            "stream": True,
            "metadata": {"x-ms-debug-mode-enabled": "1"},
        }
        
        # Add input or tool outputs
        if tool_outputs:
            request_params["input"] = tool_outputs
        else:
            request_params["input"] = user_input
        
        # Create the response stream
        stream = await openai_client.responses.create(**request_params)
        
        has_streamed = False
        message_id = None
        pending_function_calls = []
        
        async for event in stream:
            # Workflow action events
            if event.type == ResponseStreamEventType.RESPONSE_OUTPUT_ITEM_ADDED:
                if hasattr(event.item, 'type') and event.item.type == ItemType.WORKFLOW_ACTION:
                    #notify(f"ACTION ENTER #{event.item.action_id}", "darkgray")
                    pass 

                # New agent message
                elif hasattr(event.item, 'role') and event.item.role == 'assistant':
                    if event.item.id != message_id:
                        if has_streamed:
                            print()
                        
                        message_id = event.item.id
                        has_streamed = False
                        
                        # Get agent name
                        agent_name = "ASSISTANT"
                        if hasattr(event.item, 'created_by') and event.item.created_by:
                            agent_info = event.item.created_by.get('agent', {})
                            agent_name = agent_info.get('name', 'ASSISTANT').upper()
                        
                        notify(f"\n{agent_name}:", "cyan")
                        # notify(f"[{message_id}]", "darkgray")
                
                # Function/tool calls
                elif hasattr(event.item, 'type') and event.item.type == 'function_call':
                    notify(f"Calling tool: {event.item.name}", "white")
                    # notify(f"[{event.item.call_id}]", "darkgray")
            
            # Action completed
            elif event.type == ResponseStreamEventType.RESPONSE_OUTPUT_ITEM_DONE:
                if hasattr(event.item, 'type') and event.item.type == ItemType.WORKFLOW_ACTION:
                    # notify(f"ACTION EXIT #{event.item.action_id} [{event.item.status}]", "darkgray")
                    pass 

                # Collect completed function calls with full arguments
                elif hasattr(event.item, 'type') and event.item.type == 'function_call' and event.item.status == 'completed':
                    pending_function_calls.append({
                        'call_id': event.item.call_id,
                        'name': event.item.name,
                        'arguments': event.item.arguments
                    })
            
            # Text streaming
            elif event.type == ResponseStreamEventType.RESPONSE_OUTPUT_TEXT_DELTA:
                print(event.delta, end="", flush=True)
                has_streamed = True
            
            elif event.type == ResponseStreamEventType.RESPONSE_OUTPUT_TEXT_DONE:
                if event.text and not has_streamed:
                    print(event.text, end="", flush=True)
                    has_streamed = True
            
            # Activity events
            elif event.type == "response.activity":
                notify("\nACTIVITY:", "cyan")
                notify(event.activity.strip(), "yellow")
            
            # Response complete
            elif event.type == ResponseStreamEventType.RESPONSE_COMPLETED:
                if has_streamed:
                    print()
                
                if hasattr(event.response, 'usage') and event.response.usage:
                    usage = event.response.usage
                    notify(
                        f"[Tokens Total: {usage.total_tokens}, Input: {usage.input_tokens}, Output: {usage.output_tokens}]",
                        "darkgray"
                    )
        
        return pending_function_calls
    
    def invoke_function(self, function_name: str, arguments: dict):
        """
        Invoke a function from the function map (equivalent to C# InvokeFunctionAsync).
        
        Args:
            function_name: Name of the function to invoke
            arguments: Function arguments
            
        Returns:
            Function result
        """
        notify(f"INPUT - Executing Function: {function_name}", "magenta")
        
        if function_name not in self.function_map:
            raise ValueError(f"Function {function_name} not found in function map")
        
        function_impl = self.function_map[function_name]
        
        # Parse arguments if string
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        
        # Execute function
        result = function_impl(**arguments)
        
        # Convert Pydantic models to dict
        if hasattr(result, 'model_dump'):
            result = result.model_dump()
        elif isinstance(result, list) and len(result) > 0 and hasattr(result[0], 'model_dump'):
            result = [item.model_dump() for item in result]
        
        return result