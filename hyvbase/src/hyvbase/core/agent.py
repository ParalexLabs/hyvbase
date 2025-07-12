"""Unified HyvBase Agent Architecture

The ONE agent class that does everything - crypto trading, social media, 
analytics, and more through a unified, extensible interface.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import logging

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from .types import (
    AgentType, AgentStatus, AgentResponse, ToolCapability, 
    SecurityLevel, MemoryStrategy, AgentProtocol
)
from .plugin import PluginManager, BaseTool
from .security import SecurityManager, TransactionPolicy
from .observability import ObservabilityManager
from .memory import AdvancedMemoryManager
from .config import HyvBaseConfig

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM configuration"""
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout: float = 30.0
    api_key: Optional[str] = None
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentConfig:
    """Comprehensive agent configuration"""
    # Core settings
    agent_type: AgentType
    name: str
    description: str = ""
    
    # LLM configuration
    llm_config: LLMConfig = field(default_factory=LLMConfig)
    
    # Tool configuration
    enabled_tools: List[str] = field(default_factory=list)
    tool_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Security configuration
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    transaction_policies: List[TransactionPolicy] = field(default_factory=list)
    max_transaction_value: Optional[float] = None
    
    # Memory configuration
    memory_strategy: MemoryStrategy = MemoryStrategy.HYBRID
    memory_ttl: int = 3600  # 1 hour
    max_memory_size: int = 1000
    
    # Performance settings
    max_concurrent_operations: int = 5
    timeout: float = 30.0
    retry_attempts: int = 3
    
    # Personality and behavior
    personality: Dict[str, Any] = field(default_factory=dict)
    system_prompt: Optional[str] = None
    
    # Feature flags
    features: Dict[str, bool] = field(default_factory=dict)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


class HyvBaseAgent:
    """
    The unified HyvBase agent - handles all operations through a single,
    powerful interface. This is the core of the entire framework.
    """
    
    def __init__(self, config: AgentConfig, global_config: Optional[HyvBaseConfig] = None):
        self.config = config
        self.global_config = global_config or HyvBaseConfig()
        self.id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.status = AgentStatus.IDLE
        
        # Core components
        self.llm: Optional[BaseChatModel] = None
        self.plugin_manager: Optional[PluginManager] = None
        self.security_manager: Optional[SecurityManager] = None
        self.observability: Optional[ObservabilityManager] = None
        self.memory_manager: Optional[AdvancedMemoryManager] = None
        
        # Runtime state
        self.active_operations: Dict[str, asyncio.Task] = {}
        self.operation_history: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Any] = {}
        
        # Initialize components
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize all agent components"""
        if self._initialized:
            return
            
        try:
            self.status = AgentStatus.PROCESSING
            
            # Initialize LLM
            self.llm = self._create_llm()
            
            # Initialize plugin manager
            self.plugin_manager = PluginManager(self.global_config)
            await self.plugin_manager.initialize()
            
            # Load configured tools
            await self._load_tools()
            
            # Initialize security manager
            self.security_manager = SecurityManager(
                self.config.security_level,
                self.config.transaction_policies
            )
            
            # Initialize observability
            self.observability = ObservabilityManager(
                agent_id=self.id,
                agent_name=self.config.name
            )
            
            # Initialize memory manager
            self.memory_manager = AdvancedMemoryManager(
                strategy=self.config.memory_strategy,
                ttl=self.config.memory_ttl,
                max_size=self.config.max_memory_size
            )
            await self.memory_manager.initialize()
            
            self._initialized = True
            self.status = AgentStatus.IDLE
            
            logger.info(f"Agent {self.config.name} initialized successfully")
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"Failed to initialize agent {self.config.name}: {e}")
            raise
    
    def _create_llm(self) -> BaseChatModel:
        """Create and configure LLM"""
        llm_config = self.config.llm_config
        
        if llm_config.model.startswith("gpt"):
            return ChatOpenAI(
                model=llm_config.model,
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens,
                timeout=llm_config.timeout,
                openai_api_key=llm_config.api_key,
                **llm_config.custom_params
            )
        else:
            # Support for other LLM providers can be added here
            raise ValueError(f"Unsupported LLM model: {llm_config.model}")
    
    async def _load_tools(self) -> None:
        """Load and configure tools"""
        if not self.plugin_manager:
            raise RuntimeError("Plugin manager not initialized")
            
        for tool_name in self.config.enabled_tools:
            tool_config = self.config.tool_configs.get(tool_name, {})
            await self.plugin_manager.load_tool(tool_name, tool_config)
    
    async def process(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """
        Universal processing method - handles any input and returns standardized response
        """
        if not self._initialized:
            await self.initialize()
            
        operation_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            self.status = AgentStatus.PROCESSING
            
            # Track operation
            if self.observability:
                await self.observability.track_operation_start(
                    operation_id=operation_id,
                    operation_type="process",
                    input_data=input_data,
                    context=context
                )
            
            # Parse and validate input
            parsed_input = await self._parse_input(input_data, context)
            
            # Security validation
            if self.security_manager:
                security_result = await self.security_manager.validate_operation(
                    operation_type="process",
                    data=parsed_input,
                    agent_context={"agent_id": self.id, "agent_type": self.config.agent_type}
                )
                
                if not security_result.approved:
                    return AgentResponse(
                        success=False,
                        error=f"Security validation failed: {security_result.violations}",
                        metadata={"security_result": security_result}
                    )
            
            # Execute the operation
            response = await self._execute_operation(parsed_input, context)
            
            # Store in memory
            if self.memory_manager:
                await self.memory_manager.store_interaction(
                    input_data=input_data,
                    response=response,
                    context=context
                )
            
            # Track successful completion
            execution_time = time.time() - start_time
            response.execution_time = execution_time
            
            if self.observability:
                await self.observability.track_operation_complete(
                    operation_id=operation_id,
                    success=response.success,
                    execution_time=execution_time,
                    response=response
                )
            
            self.status = AgentStatus.IDLE
            return response
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_response = AgentResponse(
                success=False,
                error=str(e),
                metadata={"operation_id": operation_id, "execution_time": execution_time}
            )
            
            if self.observability:
                await self.observability.track_operation_error(
                    operation_id=operation_id,
                    error=str(e),
                    execution_time=execution_time
                )
            
            self.status = AgentStatus.ERROR
            logger.error(f"Operation failed for agent {self.config.name}: {e}")
            return error_response
    
    async def _parse_input(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Parse input data into structured format"""
        if isinstance(input_data, str):
            # Use LLM to parse natural language
            return await self._parse_natural_language(input_data, context)
        elif isinstance(input_data, dict):
            return input_data
        else:
            return {"raw_input": input_data, "type": type(input_data).__name__}
    
    async def _parse_natural_language(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Parse natural language using LLM"""
        system_prompt = self._get_system_prompt()
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
        
        if context:
            messages.insert(1, {"role": "system", "content": f"Context: {context}"})
        
        response = await self.llm.ainvoke(messages)
        
        # Try to parse as JSON, fallback to text
        try:
            import json
            return json.loads(response.content)
        except:
            return {
                "intent": "conversation",
                "text": text,
                "llm_response": response.content
            }
    
    def _get_system_prompt(self) -> str:
        """Get system prompt based on agent type and configuration"""
        if self.config.system_prompt:
            return self.config.system_prompt
            
        base_prompt = f"""You are {self.config.name}, a {self.config.agent_type.value} agent.
        
        Available capabilities: {self.get_capabilities()}
        
        Parse user input and return a JSON object with:
        - intent: The user's intention (trade, transfer, post, analyze, etc.)
        - action: Specific action to take
        - parameters: Parameters for the action
        - metadata: Additional context
        
        Example responses:
        {{"intent": "trade", "action": "swap", "parameters": {{"from": "ETH", "to": "USDC", "amount": 1.0}}}}
        {{"intent": "social", "action": "post", "parameters": {{"platform": "twitter", "content": "Hello world!"}}}}
        """
        
        return base_prompt
    
    async def _execute_operation(self, parsed_input: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Execute the parsed operation"""
        intent = parsed_input.get("intent", "conversation")
        action = parsed_input.get("action", "")
        parameters = parsed_input.get("parameters", {})
        
        # Route to appropriate handler
        if intent == "trade" or intent == "crypto":
            return await self._handle_crypto_operation(action, parameters, context)
        elif intent == "social":
            return await self._handle_social_operation(action, parameters, context)
        elif intent == "analyze":
            return await self._handle_analysis_operation(action, parameters, context)
        elif intent == "workflow":
            return await self._handle_workflow_operation(action, parameters, context)
        else:
            return await self._handle_conversation(parsed_input, context)
    
    async def _handle_crypto_operation(self, action: str, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Handle cryptocurrency operations"""
        if not self.plugin_manager:
            return AgentResponse(success=False, error="Plugin manager not initialized")
        
        # Get appropriate crypto tool
        crypto_tools = self.plugin_manager.get_tools_by_capability(ToolCapability.BLOCKCHAIN_WRITE)
        if not crypto_tools:
            return AgentResponse(success=False, error="No crypto tools available")
        
        tool = crypto_tools[0]  # Use first available tool
        
        # Execute the operation
        command = f"{action} {' '.join(str(v) for v in parameters.values())}"
        return await tool.execute(command, **parameters)
    
    async def _handle_social_operation(self, action: str, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Handle social media operations"""
        if not self.plugin_manager:
            return AgentResponse(success=False, error="Plugin manager not initialized")
        
        # Get appropriate social tool
        social_tools = self.plugin_manager.get_tools_by_capability(ToolCapability.SOCIAL_WRITE)
        if not social_tools:
            return AgentResponse(success=False, error="No social tools available")
        
        tool = social_tools[0]  # Use first available tool
        
        # Execute the operation
        command = f"{action} {' '.join(str(v) for v in parameters.values())}"
        return await tool.execute(command, **parameters)
    
    async def _handle_analysis_operation(self, action: str, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Handle analysis operations"""
        # Use LLM for analysis
        analysis_prompt = f"Analyze the following data and provide insights: {parameters}"
        
        messages = [
            {"role": "system", "content": "You are a data analyst. Provide clear, actionable insights."},
            {"role": "user", "content": analysis_prompt}
        ]
        
        response = await self.llm.ainvoke(messages)
        
        return AgentResponse(
            success=True,
            data={"analysis": response.content},
            message="Analysis completed"
        )
    
    async def _handle_workflow_operation(self, action: str, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Handle workflow operations"""
        # TODO: Implement workflow handling
        return AgentResponse(
            success=False,
            error="Workflow operations not yet implemented"
        )
    
    async def _handle_conversation(self, parsed_input: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Handle general conversation"""
        text = parsed_input.get("text", "")
        
        # Get conversation history from memory
        conversation_context = ""
        if self.memory_manager:
            recent_interactions = await self.memory_manager.get_recent_interactions(limit=5)
            conversation_context = "\n".join([
                f"User: {interaction.get('input', '')}\nAgent: {interaction.get('response', '')}"
                for interaction in recent_interactions
            ])
        
        # Create conversational prompt
        messages = [
            {"role": "system", "content": self._get_conversation_prompt()},
            {"role": "system", "content": f"Recent conversation:\n{conversation_context}"},
            {"role": "user", "content": text}
        ]
        
        response = await self.llm.ainvoke(messages)
        
        return AgentResponse(
            success=True,
            data={"response": response.content},
            message=response.content
        )
    
    def _get_conversation_prompt(self) -> str:
        """Get conversation prompt based on agent configuration"""
        personality = self.config.personality
        
        prompt = f"""You are {self.config.name}, a {self.config.agent_type.value}.
        
        Personality traits: {personality.get('traits', [])}
        Expertise: {personality.get('expertise', [])}
        
        Engage in helpful, professional conversation while staying in character.
        If users ask about capabilities, mention: {self.get_capabilities()}
        """
        
        return prompt
    
    def get_capabilities(self) -> List[ToolCapability]:
        """Get all capabilities of this agent"""
        if not self.plugin_manager:
            return []
        
        capabilities = set()
        for tool in self.plugin_manager.get_all_tools():
            capabilities.update(tool.get_capabilities())
        
        return list(capabilities)
    
    def get_status(self) -> AgentStatus:
        """Get current agent status"""
        return self.status
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        if not self.observability:
            return {}
        
        return await self.observability.get_metrics()
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the agent"""
        try:
            self.status = AgentStatus.STOPPED
            
            # Cancel active operations
            for task in self.active_operations.values():
                if not task.done():
                    task.cancel()
            
            # Wait for operations to complete
            if self.active_operations:
                await asyncio.gather(
                    *self.active_operations.values(),
                    return_exceptions=True
                )
            
            # Shutdown components
            if self.memory_manager:
                await self.memory_manager.shutdown()
            
            if self.observability:
                await self.observability.shutdown()
            
            logger.info(f"Agent {self.config.name} shut down successfully")
            
        except Exception as e:
            logger.error(f"Error during agent shutdown: {e}")
            raise


# Factory function for easier agent creation
def create_agent(
    agent_type: AgentType,
    name: str,
    **kwargs
) -> HyvBaseAgent:
    """Create a pre-configured agent"""
    config = AgentConfig(
        agent_type=agent_type,
        name=name,
        **kwargs
    )
    
    return HyvBaseAgent(config)


# Pre-configured agent types
def create_crypto_trader(name: str = "CryptoTrader", **kwargs) -> HyvBaseAgent:
    """Create a crypto trading agent"""
    return create_agent(
        AgentType.CRYPTO_TRADER,
        name,
        enabled_tools=["starknet", "avnu_dex", "market_data"],
        security_level=SecurityLevel.HIGH,
        **kwargs
    )


def create_social_manager(name: str = "SocialManager", **kwargs) -> HyvBaseAgent:
    """Create a social media management agent"""
    return create_agent(
        AgentType.SOCIAL_MANAGER,
        name,
        enabled_tools=["twitter", "telegram", "discord"],
        security_level=SecurityLevel.MEDIUM,
        **kwargs
    )
