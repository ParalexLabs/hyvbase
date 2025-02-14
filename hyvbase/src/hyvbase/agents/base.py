from typing import List, Optional, Dict, Any, Union, Tuple
from langchain.agents import AgentExecutor, BaseSingleActionAgent
from langchain.schema import AgentAction, AgentFinish, BaseMemory
from langchain.callbacks.manager import CallbackManagerForChainRun
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import re

class SwarmBaseAgent(BaseSingleActionAgent):
    """Base agent class for SwarmBase integrations."""
    
    tools: List[BaseTool]
    memory: Optional[BaseMemory] = None
    
    @property
    def input_keys(self) -> List[str]:
        return ["input"]
        
    def plan(
        self,
        intermediate_steps: List[Tuple[AgentAction, str]],
        callbacks: CallbackManagerForChainRun = None,
        **kwargs: Any,
    ) -> Union[AgentAction, AgentFinish]:
        """Plan the next action based on observations."""
        raise NotImplementedError
        
    async def aplan(
        self,
        intermediate_steps: List[Tuple[AgentAction, str]],
        callbacks: CallbackManagerForChainRun = None,
        **kwargs: Any,
    ) -> Union[AgentAction, AgentFinish]:
        """Async version of plan."""
        raise NotImplementedError

class CryptoAgent(SwarmBaseAgent):
    """Specialized agent for crypto operations."""
    
    def __init__(
        self,
        tools: List[BaseTool],
        memory: Optional[BaseMemory] = None,
        allowed_chains: List[str] = None,
        max_transaction_value: float = None
    ):
        super().__init__()
        self.tools = tools
        self.memory = memory
        self.allowed_chains = allowed_chains or ["starknet", "solana"]
        self.max_transaction_value = max_transaction_value
        
    def parse_command(self, command: str) -> Dict[str, Any]:
        """Parse command string into structured format."""
        # Example: "swap jediswap ETH USDC 0.1"
        parts = command.split()
        if not parts:
            raise ValueError("Empty command")
            
        action = parts[0]
        if action == "swap":
            return {
                "action": "swap",
                "dex": parts[1],
                "token_in": parts[2],
                "token_out": parts[3],
                "amount": float(parts[4])
            }
        # Add more command parsers...
        
    def validate_transaction(self, parsed_command: Dict[str, Any]) -> bool:
        """Validate transaction against safety constraints."""
        if "amount" in parsed_command:
            if self.max_transaction_value and parsed_command["amount"] > self.max_transaction_value:
                return False
        return True
        
    async def aplan(
        self,
        intermediate_steps: List[Tuple[AgentAction, str]],
        callbacks: CallbackManagerForChainRun = None,
        **kwargs: Any,
    ) -> Union[AgentAction, AgentFinish]:
        """Plan next action based on previous steps and input."""
        
        # Get input
        user_input = kwargs.get("input", "")
        
        # Check if we should finish
        if user_input.lower() in ["done", "stop", "finish"]:
            return AgentFinish(
                return_values={"output": "Task completed"},
                log="Agent finished by user request"
            )
            
        try:
            # Parse and validate command
            parsed_command = self.parse_command(user_input)
            if not self.validate_transaction(parsed_command):
                return AgentFinish(
                    return_values={"output": "Transaction validation failed"},
                    log="Transaction exceeded safety limits"
                )
                
            # Find appropriate tool
            tool_name = parsed_command["action"]
            tool = next((t for t in self.tools if t.name == tool_name), None)
            
            if not tool:
                return AgentFinish(
                    return_values={"output": f"No tool found for action: {tool_name}"},
                    log=f"Missing tool: {tool_name}"
                )
                
            # Create action
            return AgentAction(
                tool=tool.name,
                tool_input=user_input,
                log=f"Using {tool.name} to execute: {user_input}"
            )
            
        except Exception as e:
            return AgentFinish(
                return_values={"output": f"Error: {str(e)}"},
                log=f"Error during planning: {str(e)}"
            )

class SwarmAgent(BaseSingleActionAgent):
    """Base agent class that combines all LangChain capabilities."""
    
    tools: List[BaseTool]
    memory: Optional[BaseMemory] = None
    llm: Any
    
    @property
    def input_keys(self) -> List[str]:
        return ["input"]
        
    async def plan(
        self,
        intermediate_steps: List[Tuple[AgentAction, str]],
        callbacks: Optional[CallbackManagerForChainRun] = None,
        **kwargs: Any,
    ) -> Union[AgentAction, AgentFinish]:
        """Plan next action based on previous steps."""
        raise NotImplementedError
        
    async def aplan(
        self,
        intermediate_steps: List[Tuple[AgentAction, str]],
        callbacks: Optional[CallbackManagerForChainRun] = None,
        **kwargs: Any,
    ) -> Union[AgentAction, AgentFinish]:
        """Async version of plan."""
        raise NotImplementedError 