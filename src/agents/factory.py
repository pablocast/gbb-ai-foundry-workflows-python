# pylint: disable=line-too-long,useless-suppression
# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------

"""
Generic Agent Factory for creating AI agents from configurations.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml
from azure.ai.projects.models import (
    PromptAgentDefinition,
    WorkflowAgentDefinition,
    StructuredInputDefinition,
    PromptAgentDefinitionText,
    ResponseTextFormatConfigurationJsonSchema
)


class AgentFactory:
    """Generic factory for creating AI agents from YAML configurations."""
    
    def __init__(self, model_deployment_name: str, schemas_registry: Dict[str, Any], tools_registry: Dict[str, Any]):
        """
        Initialize agent factory.
        
        Args:
            model_deployment_name: Name of the AI model deployment
            schemas_registry: Dictionary mapping schema names to Pydantic models
            tools_registry: Dictionary mapping tool names to FunctionTool instances
        """
        self.model_deployment_name = model_deployment_name
        self.schemas_registry = schemas_registry
        self.tools_registry = tools_registry
    
    @staticmethod
    def load_agent_configs(config_file: str = "service_agents.yaml") -> Dict[str, Any]:
        """
        Load agent configurations from YAML file.
        
        Args:
            config_file: Name of the YAML configuration file
            
        Returns:
            Dictionary with 'agents' and 'schemas' from the config
        """
        config_path = Path(__file__).parent.parent.parent / "workflows" / "agents" / config_file
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return config
    
    async def create_agent_from_config(
        self,
        project_client,
        agent_name: str,
        config_file: str = "service_agents.yaml"
    ):
        """
        Create an agent from YAML configuration.
        
        Args:
            project_client: Azure AI Project client
            agent_name: Name of the agent to create (must exist in config)
            config_file: Name of the YAML configuration file
            
        Returns:
            Created agent version
        """
        # Load configuration
        config = self.load_agent_configs(config_file)
        agents_config = config.get('agents', {})
        
        if agent_name not in agents_config:
            raise ValueError(f"Agent '{agent_name}' not found in configuration file")
        
        agent_config = agents_config[agent_name]
        
        # Extract configuration
        instructions = agent_config.get('instructions', '')
        output_schema_name = agent_config.get('output_schema')
        tools = agent_config.get('tools', [])
        structured_inputs_config = agent_config.get('structured_inputs', {})
        
        # Create the agent
        return await self.create_agent(
            project_client=project_client,
            agent_name=agent_name,
            instructions=instructions,
            output_schema_name=output_schema_name,
            tools=tools,
            structured_inputs=structured_inputs_config
        )
    
    async def create_all_agents_from_config(
        self,
        project_client,
        config_file: str = "service_agents.yaml",
        agent_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create multiple agents from YAML configuration.
        
        Args:
            project_client: Azure AI Project client
            config_file: Name of the YAML configuration file
            agent_names: List of agent names to create. If None, creates all agents in config
            
        Returns:
            Dictionary mapping agent names to created agent versions
        """
        config = self.load_agent_configs(config_file)
        agents_config = config.get('agents', {})
        
        # Determine which agents to create
        if agent_names is None:
            agent_names = list(agents_config.keys())
        
        created_agents = {}
        for agent_name in agent_names:
            agent = await self.create_agent_from_config(
                project_client,
                agent_name,
                config_file
            )
            created_agents[agent_name] = agent
        
        return created_agents
    
    async def create_agent(
        self, 
        project_client, 
        agent_name: str,
        instructions: str,
        output_schema_name: str,
        tools: Optional[list] = None,
        structured_inputs: Optional[Dict[str, Any]] = None
    ):
        """
        Create a prompt agent with the given configuration.
        
        Args:
            project_client: Azure AI Project client
            agent_name: Name of the agent
            instructions: Agent instructions/prompt
            output_schema_name: Name of the output schema (must be in schemas_registry)
            tools: List of tool names (must be in tools_registry)
            structured_inputs: Dictionary of structured input definitions
            
        Returns:
            Created agent version
        """
        # Build structured inputs
        inputs = {}
        if structured_inputs:
            for input_name, input_config in structured_inputs.items():
                inputs[input_name] = StructuredInputDefinition(
                    required=input_config.get('required', False),
                    description=input_config.get('description', ''),
                )
        
        # Get output schema
        if output_schema_name not in self.schemas_registry:
            raise ValueError(f"Schema '{output_schema_name}' not found in schemas registry")
        
        schema_model = self.schemas_registry[output_schema_name]
        
        # Build tools list
        agent_tools = []
        if tools:
            for tool_name in tools:
                if tool_name not in self.tools_registry:
                    raise ValueError(f"Tool '{tool_name}' not found in tools registry")
                agent_tools.append(self.tools_registry[tool_name])
        
        # Create agent
        agent = await project_client.agents.create_version(
            agent_name=agent_name,
            definition=PromptAgentDefinition(
                model=self.model_deployment_name,
                instructions=instructions,
                structured_inputs=inputs if inputs else None,
                text=PromptAgentDefinitionText(
                    format=ResponseTextFormatConfigurationJsonSchema(
                        name=output_schema_name,
                        schema=schema_model.model_json_schema()
                    )
                ),
                tools=agent_tools if agent_tools else None
            ),
        )
        
        print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")
        return agent
    
    async def create_workflow(
        self, 
        project_client, 
        workflow_name: str,
        workflow_file: str
    ):
        """
        Create a workflow agent from YAML file.
        
        Args:
            project_client: Azure AI Project client
            workflow_name: Name of the workflow agent
            workflow_file: Name of the workflow YAML file
            
        Returns:
            Created workflow agent version
        """
        workflow_path = Path(__file__).parent.parent.parent / "workflows" / workflow_file
        
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow_yaml = f.read()
        
        workflow = await project_client.agents.create_version(
            agent_name=workflow_name,
            definition=WorkflowAgentDefinition(workflow=workflow_yaml),
        )
        
        print(f"Workflow created (id: {workflow.id}, name: {workflow.name}, version: {workflow.version})")
        return workflow