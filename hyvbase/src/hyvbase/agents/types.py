from typing import List, Optional, Dict, Any
from langchain.agents import (
    AgentExecutor,
    ConversationalChatAgent,
    create_react_agent,
    create_structured_chat_agent,
)
from langchain_core.memory import BaseMemory
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManager
from langchain_core.outputs import LLMResult
from ..tools import get_all_tools
from langchain_openai import ChatOpenAI

class ZeroShotAgent:
    """Zero-shot agent that uses natural language to determine actions."""
    
    def __init__(
        self,
        llm: BaseChatModel,
        tools: Optional[List[BaseTool]] = None,
        memory: Optional[BaseMemory] = None,
        **kwargs: Any
    ):
        tools = tools or get_all_tools()
        super().__init__(llm=llm, tools=tools, memory=memory, **kwargs)

class ReActAgent:
    """ReAct (Reasoning and Acting) agent."""
    
    def __init__(
        self,
        llm: BaseChatModel,
        tools: Optional[List[BaseTool]] = None,
        memory: Optional[BaseMemory] = None,
        **kwargs: Any
    ):
        tools = tools or get_all_tools()
        self.agent = create_react_agent(llm, tools, **kwargs)
        self.executor = AgentExecutor.from_agent_and_tools(
            agent=self.agent,
            tools=tools,
            memory=memory,
            verbose=True
        )

class ConversationalAgent:
    """A conversational agent that can use tools and maintain memory"""
    
    def __init__(
        self,
        llm: BaseChatModel,
        tools: List[BaseTool],
        memory: Optional[BaseMemory] = None,
        system_message: str = "",
        verbose: bool = True
    ):
        """Initialize the agent"""
        # Create the underlying agent with better prompting
        base_prompt = """You are a helpful trading assistant. When users want to trade, always use the starknet_dex tool with the following format:
        - For quotes: quote avnu <token_from> <token_to> <amount>
        - For swaps: swap avnu <token_from> <token_to> <amount>
        
        Available tokens: ETH, USDC, USDT, STARK
        Example commands:
        - quote avnu STARK USDC 2
        - swap avnu ETH USDC 0.1
        
        Always correct token names (e.g., 'strak' should be 'STARK')."""
        
        system_message = base_prompt + "\n" + system_message
        
        agent = ConversationalChatAgent.from_llm_and_tools(
            llm=llm,
            tools=tools,
            system_message=system_message
        )
        
        # Create the executor
        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=tools,
            memory=memory,
            verbose=verbose,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
    
    async def arun(self, input_text: str) -> str:
        """Run the agent asynchronously"""
        try:
            # Use ainvoke instead of arun
            result = await self.agent_executor.ainvoke(
                {"input": input_text},
                config={"callbacks": None}  # Disable default callbacks
            )
            
            # Handle both output formats
            if isinstance(result, dict):
                return result.get("output", result.get("response", "No response generated"))
            return str(result)
            
        except Exception as e:
            return f"Error executing agent: {str(e)}"
    
    def run(self, input_text: str) -> str:
        """Run the agent synchronously"""
        try:
            # Use invoke instead of run
            result = self.agent_executor.invoke(
                {"input": input_text},
                config={"callbacks": None}  # Disable default callbacks
            )
            return result.get("output", "No response generated")
        except Exception as e:
            return f"Error executing agent: {str(e)}"

# Add other agent types similarly... 