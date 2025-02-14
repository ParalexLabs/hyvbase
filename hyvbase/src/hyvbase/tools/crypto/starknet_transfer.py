from typing import Optional, Dict, Any
from langchain.tools import BaseTool
from .base import StarknetTool
from pydantic import Field

class StarknetTransferTool(BaseTool):
    """Tool for token transfers on StarkNet"""
    
    name: str = "starknet_transfer"
    description: str = "Transfer tokens on StarkNet"
    starknet: StarknetTool = Field(description="StarkNet client tool")
    
    def __init__(self, starknet_tool: StarknetTool):
        super().__init__(starknet=starknet_tool)
        
    def _run(self, command: str) -> str:
        """Synchronous run - required by BaseTool"""
        raise NotImplementedError("Use async version")
        
    async def _arun(self, command: str) -> str:
        """Execute transfer operations"""
        try:
            # Parse command
            parts = command.split()
            action = parts[0]
            
            if action == "transfer":
                amount = float(parts[1])
                token = parts[2]
                to_address = parts[3]
                return await self.transfer_token(token, amount, to_address)
            elif action == "balance":
                token = parts[1]
                return await self.get_balance(token)
            else:
                return f"Unknown action: {action}"
                
        except Exception as e:
            return f"Transfer error: {str(e)}"
            
    async def transfer_token(self, token: str, amount: float, to_address: str) -> str:
        """Transfer tokens to an address"""
        try:
            # Use the starknet client to execute the transfer
            tx = await self.starknet.execute_transfer(
                token=token,
                amount=amount,
                recipient=to_address
            )
            return f"Transfer successful. Transaction: {tx}"
        except Exception as e:
            raise Exception(f"Transfer failed: {str(e)}")
        
    async def get_balance(self, token: str) -> str:
        """Get token balance"""
        try:
            balance = await self.starknet.get_balance(token)
            return f"Balance of {token}: {balance}"
        except Exception as e:
            raise Exception(f"Failed to get balance: {str(e)}") 