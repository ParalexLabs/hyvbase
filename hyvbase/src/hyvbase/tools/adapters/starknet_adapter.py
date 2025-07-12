"""StarkNet Tool Adapter for Unified HyvBase Framework

Adapts existing StarkNet tools to work with the new plugin architecture
while preserving all original functionality.
"""

from typing import Dict, List, Optional, Any
import asyncio
import json
from datetime import datetime

from ...core.plugin import BaseTool
from ...core.types import AgentResponse, ToolCapability
from ..crypto.starknet import StarknetTool
from ..crypto.starknet_dex import StarknetDEXTool  
from ..crypto.starknet_transfer import StarknetTransferTool
from ..crypto.starknet_nft import StarknetNFTTool


class ModernStarkNetTool(BaseTool):
    """Modern StarkNet tool adapter for the unified framework"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.name = "StarkNetTool"
        self.config = config or {}
        
        # Initialize legacy StarkNet tool
        self.starknet_tool = StarknetTool(
            private_key=self.config.get("private_key"),
            account_address=self.config.get("account_address"),
            rpc_url=self.config.get("rpc_url", "https://starknet-mainnet.public.blastapi.io")
        )
        
        # Initialize specialized tools
        self.dex_tool = None
        self.transfer_tool = None
        self.nft_tool = None
        
    async def initialize(self) -> None:
        """Initialize the tool and its components"""
        try:
            # Initialize base StarkNet tool
            await asyncio.get_event_loop().run_in_executor(
                None, self.starknet_tool._initialize
            )
            
            # Initialize specialized tools
            self.dex_tool = StarknetDEXTool(self.starknet_tool)
            self.transfer_tool = StarknetTransferTool(self.starknet_tool)
            self.nft_tool = StarknetNFTTool(self.starknet_tool)
            
            self.initialized = True
            
        except Exception as e:
            raise RuntimeError(f"Failed to initialize StarkNet tool: {e}")
    
    async def execute(self, command: str, **kwargs) -> AgentResponse:
        """Execute StarkNet commands with unified response format"""
        if not self.initialized:
            await self.initialize()
        
        try:
            # Parse command
            parts = command.strip().split()
            if not parts:
                return AgentResponse(
                    success=False,
                    error="Empty command",
                    metadata={"tool": "starknet"}
                )
            
            action = parts[0].lower()
            
            # Route to appropriate handler
            if action in ["swap", "quote"]:
                return await self._handle_dex_operation(command)
            elif action in ["transfer", "send"]:
                return await self._handle_transfer_operation(command)
            elif action in ["mint", "nft"]:
                return await self._handle_nft_operation(command)
            elif action in ["balance", "get_balance"]:
                return await self._handle_balance_query(parts)
            elif action in ["status", "info"]:
                return await self._handle_status_query()
            else:
                return AgentResponse(
                    success=False,
                    error=f"Unknown action: {action}",
                    metadata={"tool": "starknet", "available_actions": [
                        "swap", "quote", "transfer", "send", "balance", "status"
                    ]}
                )
                
        except Exception as e:
            return AgentResponse(
                success=False,
                error=str(e),
                metadata={"tool": "starknet", "command": command}
            )
    
    async def _handle_dex_operation(self, command: str) -> AgentResponse:
        """Handle DEX operations (swap/quote)"""
        try:
            result = await self.dex_tool._arun(command)
            
            # Try to parse as JSON for structured data
            try:
                data = json.loads(result)
                return AgentResponse(
                    success=True,
                    data=data,
                    message=f"DEX operation completed: {command}",
                    metadata={"tool": "starknet_dex", "operation_type": "dex"}
                )
            except json.JSONDecodeError:
                # Return as string if not JSON
                return AgentResponse(
                    success=True,
                    data={"result": result},
                    message=result,
                    metadata={"tool": "starknet_dex", "operation_type": "dex"}
                )
                
        except Exception as e:
            return AgentResponse(
                success=False,
                error=f"DEX operation failed: {str(e)}",
                metadata={"tool": "starknet_dex", "command": command}
            )
    
    async def _handle_transfer_operation(self, command: str) -> AgentResponse:
        """Handle token transfer operations"""
        try:
            # Parse transfer command: "transfer TOKEN AMOUNT TO_ADDRESS"
            parts = command.split()
            if len(parts) < 4:
                return AgentResponse(
                    success=False,
                    error="Invalid transfer format. Use: transfer TOKEN AMOUNT TO_ADDRESS",
                    metadata={"tool": "starknet_transfer"}
                )
            
            token = parts[1].upper()
            amount = float(parts[2])
            to_address = parts[3]
            
            result = await self.transfer_tool.transfer_token(
                token=token,
                amount=amount,
                to_address=to_address
            )
            
            return AgentResponse(
                success=True,
                data={
                    "transaction_hash": result,
                    "token": token,
                    "amount": amount,
                    "to_address": to_address,
                    "explorer_url": f"https://starkscan.co/tx/{result}"
                },
                message=f"Successfully transferred {amount} {token} to {to_address[:10]}...",
                metadata={"tool": "starknet_transfer", "operation_type": "transfer"}
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                error=f"Transfer failed: {str(e)}",
                metadata={"tool": "starknet_transfer", "command": command}
            )
    
    async def _handle_nft_operation(self, command: str) -> AgentResponse:
        """Handle NFT operations"""
        try:
            result = await self.nft_tool._arun(command)
            
            return AgentResponse(
                success=True,
                data={"result": result},
                message=f"NFT operation completed: {command}",
                metadata={"tool": "starknet_nft", "operation_type": "nft"}
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                error=f"NFT operation failed: {str(e)}",
                metadata={"tool": "starknet_nft", "command": command}
            )
    
    async def _handle_balance_query(self, parts: List[str]) -> AgentResponse:
        """Handle balance queries"""
        try:
            if len(parts) > 1:
                token = parts[1].upper()
            else:
                token = "ETH"  # Default to ETH
            
            # Use the base StarkNet tool to get balance
            balance = await asyncio.get_event_loop().run_in_executor(
                None, self.starknet_tool.get_balance, token
            )
            
            return AgentResponse(
                success=True,
                data={
                    "token": token,
                    "balance": balance,
                    "account": self.starknet_tool.config.account_address
                },
                message=f"Balance: {balance} {token}",
                metadata={"tool": "starknet", "operation_type": "balance_query"}
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                error=f"Balance query failed: {str(e)}",
                metadata={"tool": "starknet", "operation_type": "balance_query"}
            )
    
    async def _handle_status_query(self) -> AgentResponse:
        """Handle status queries"""
        try:
            status_info = {
                "account_address": self.starknet_tool.config.account_address,
                "network": "StarkNet Mainnet",
                "rpc_url": self.starknet_tool.config.rpc_url,
                "initialized": self.initialized,
                "tools_available": {
                    "dex": self.dex_tool is not None,
                    "transfer": self.transfer_tool is not None,
                    "nft": self.nft_tool is not None
                },
                "timestamp": datetime.now().isoformat()
            }
            
            return AgentResponse(
                success=True,
                data=status_info,
                message="StarkNet tool status retrieved",
                metadata={"tool": "starknet", "operation_type": "status"}
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                error=f"Status query failed: {str(e)}",
                metadata={"tool": "starknet", "operation_type": "status"}
            )
    
    def get_capabilities(self) -> List[ToolCapability]:
        """Get tool capabilities"""
        return [
            ToolCapability.BLOCKCHAIN_READ,
            ToolCapability.BLOCKCHAIN_WRITE,
            ToolCapability.MARKET_DATA,
            ToolCapability.AUTOMATION
        ]
    
    def validate_command(self, command: str) -> bool:
        """Validate if command is supported"""
        if not command or not command.strip():
            return False
        
        action = command.strip().split()[0].lower()
        supported_actions = [
            "swap", "quote", "transfer", "send", "balance", 
            "get_balance", "status", "info", "mint", "nft"
        ]
        
        return action in supported_actions
    
    def get_help_text(self) -> str:
        """Get help text for the tool"""
        return """
StarkNet Tool Commands:

DEX Operations:
- quote ETH USDC 1.0          # Get price quote
- swap ETH USDC 1.0           # Execute token swap

Transfer Operations:
- transfer ETH 0.5 0x123...   # Transfer tokens
- send USDC 100 0x456...      # Send tokens (alias)

Query Operations:
- balance ETH                 # Get token balance
- balance                     # Get ETH balance (default)
- status                      # Get tool status

NFT Operations:
- mint collection_address     # Mint NFT
- nft info token_id          # Get NFT info

Supported tokens: ETH, USDC, USDT, STARK
"""


class StarkNetToolRegistry:
    """Registry for StarkNet tools and utilities"""
    
    @staticmethod
    def create_tool(config: Dict[str, Any]) -> ModernStarkNetTool:
        """Factory method to create StarkNet tool"""
        return ModernStarkNetTool(config)
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> tuple[bool, str]:
        """Validate StarkNet configuration"""
        required_fields = ["private_key", "account_address"]
        
        for field in required_fields:
            if field not in config or not config[field]:
                return False, f"Missing required field: {field}"
        
        # Validate address format
        account_address = config["account_address"]
        if not account_address.startswith("0x") or len(account_address) != 66:
            return False, "Invalid account address format"
        
        return True, "Configuration valid"
    
    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """Get default configuration template"""
        return {
            "private_key": "",  # Required
            "account_address": "",  # Required
            "rpc_url": "https://starknet-mainnet.public.blastapi.io",
            "network": "mainnet",
            "max_fee": 1000000000000000,  # 0.001 ETH in wei
            "timeout": 30,
            "retry_attempts": 3
        }
