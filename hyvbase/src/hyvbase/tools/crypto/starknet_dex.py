from typing import Optional, List, Tuple, Dict, Any
from decimal import Decimal
from langchain.tools import BaseTool
from .base import StarknetTool
from .dex_config import DEXRegistry, DEXConfig
import json
from .avnu_client import AVNUClient, AVNUConfig

class StarknetDEXTool(BaseTool):
    """Tool for interacting with AVNU DEX"""
    
    name: str = "starknet_dex"
    description: str = """Execute operations on AVNU DEX. Available commands:
    - quote <token_from> <token_to> <amount>
    - swap <token_from> <token_to> <amount>
    Example: 'swap ETH USDC 0.1'"""
    
    MAX_PRICE_IMPACT = 5.0  # 5% max price impact
    
    starknet_tool: StarknetTool = None
    dex_registry: DEXRegistry = None
    avnu_client: Optional[AVNUClient] = None
    
    def __init__(self, starknet_tool: StarknetTool):
        """Initialize AVNU DEX tool"""
        super().__init__()
        # Initialize StarknetTool first
        if not starknet_tool.client or not starknet_tool.account:
            starknet_tool._initialize()
        self.starknet_tool = starknet_tool
        self.dex_registry = DEXRegistry()
        self.avnu_client = AVNUClient(starknet_tool=self.starknet_tool)
    
    def _run(self, command: str) -> str:
        """Sync version - raises NotImplementedError to enforce async usage"""
        raise NotImplementedError("StarknetDEXTool only supports async operations. Use arun() instead.")
    
    def _validate_inputs(self, token_from: str, token_to: str, amount: float) -> Tuple[bool, str]:
        """Validate input parameters"""
        try:
            # Check tokens exist
            if token_from not in self.dex_registry.tokens:
                return False, f"Token {token_from} is not supported"
            if token_to not in self.dex_registry.tokens:
                return False, f"Token {token_to} is not supported"
            
            # Check amount is positive
            if amount <= 0:
                return False, "Amount must be greater than 0"
            
            # Validate trade parameters
            return self.dex_registry.validate_trade(token_from, token_to, amount)
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def _calculate_price_impact(self, quote_amount: float, market_price: float) -> float:
        """Calculate price impact percentage"""
        try:
            if market_price == 0 or quote_amount == 0:
                return 0.0  # Return 0 instead of inf for better UX
            impact = abs((quote_amount - market_price) / market_price * 100)
            return min(impact, 100.0)  # Cap at 100%
        except Exception:
            return 0.0  # Return 0 on calculation errors
    
    async def _arun(self, command: str) -> str:
        """Execute DEX operation"""
        try:
            parts = command.lower().split()
            if len(parts) < 4:
                return "Invalid command format. Use: <action> <token_from> <token_to> <amount>"
            
            action = parts[0]
            token_from = parts[1].upper()
            token_to = parts[2].upper()
            
            try:
                amount = float(parts[3])
            except ValueError:
                return f"Invalid amount: {parts[3]}"
            
            # Validate inputs
            valid, message = self._validate_inputs(token_from, token_to, amount)
            if not valid:
                return message
            
            if action == "quote":
                return await self._get_quote(token_from, token_to, amount)
            elif action == "swap":
                return await self._execute_swap(token_from, token_to, amount)
            else:
                return f"Unsupported action: {action}. Use 'quote' or 'swap'"
                
        except Exception as e:
            return f"Error executing DEX operation: {str(e)}"
    
    async def _get_quote(self, token_from: str, token_to: str, amount: float) -> str:
        """Get quote from DEX"""
        try:
            token_from_config = self.dex_registry.tokens[token_from]
            token_to_config = self.dex_registry.tokens[token_to]
            
            # Convert amount to wei
            amount_wei = int(amount * (10 ** token_from_config.decimals))
            
            # Get quote from AVNU
            try:
                quote_data = self.avnu_client.get_quotes(
                    int(token_from_config.address, 16),
                    int(token_to_config.address, 16),
                    amount_wei
                )
                quote_id = quote_data["quoteId"]
                
                # Extract amounts from quote
                buy_amount = int(quote_data.get("buyAmount", "0"), 16)
                sell_amount = int(quote_data.get("sellAmount", "0"), 16)
                
            except Exception as e:
                return f"Failed to get quote: {str(e)}"
            
            # Build transaction to get final quote
            try:
                tx_data = self.avnu_client.build_transaction(
                    quote_id,
                    int(self.starknet_tool.config.account_address, 16),
                    self.dex_registry.dex.max_slippage
                )
                
                # Calculate output amount
                output_amount = buy_amount / (10 ** token_to_config.decimals)
                input_amount = sell_amount / (10 ** token_from_config.decimals)
                
                # Get market price from quote data
                market_price = float(quote_data.get("marketPrice", 0))
                
                # Calculate rate and price impact
                rate = output_amount / input_amount if input_amount else 0
                price_impact = self._calculate_price_impact(
                    rate,
                    market_price
                )
                
                quote_info = {
                    "input": f"{input_amount} {token_from}",
                    "output": f"{output_amount:.6f} {token_to}",
                    "rate": f"1 {token_from} = {rate:.6f} {token_to}",
                    "price_impact": f"{price_impact}%",
                    "slippage": f"{self.dex_registry.dex.max_slippage}%",
                    "warning": "High price impact!" if price_impact > self.MAX_PRICE_IMPACT else None
                }
                
                return json.dumps(quote_info, indent=2)
                
            except Exception as e:
                return f"Failed to process quote: {str(e)}"
            
        except Exception as e:
            return f"Error getting quote: {str(e)}"
    
    async def _execute_swap(self, token_from: str, token_to: str, amount: float) -> str:
        """Execute swap on DEX"""
        try:
            # First get a quote to check price impact
            quote_result = await self._get_quote(token_from, token_to, amount)
            quote_info = json.loads(quote_result)
            
            # Check price impact
            price_impact = float(quote_info["price_impact"].rstrip("%"))
            if price_impact > self.MAX_PRICE_IMPACT:
                return f"Swap aborted: Price impact too high ({price_impact}%)"
            
            token_from_config = self.dex_registry.tokens[token_from]
            token_to_config = self.dex_registry.tokens[token_to]
            
            # Convert amount to wei
            amount_wei = int(amount * (10 ** token_from_config.decimals))
            
            try:
                # Get full quote data
                quote_data = self.avnu_client.get_quotes(
                    int(token_from_config.address, 16),
                    int(token_to_config.address, 16),
                    amount_wei
                )
                quote_id = quote_data["quoteId"]
                
                # Build transaction with quote
                tx_data = self.avnu_client.build_transaction(
                    quote_id,
                    int(self.starknet_tool.config.account_address, 16),
                    self.dex_registry.dex.max_slippage
                )
                
                # Prepare calls
                calls = await self.avnu_client.prepare_swap_calls(
                    int(token_from_config.address, 16),
                    amount_wei,
                    tx_data
                )
                
                # Execute transaction
                transaction = await self.starknet_tool.sign_transaction(calls)
                tx_hash = await self.starknet_tool.send_transaction(transaction)
                
                return (
                    f"Successfully initiated swap on AVNU:\n"
                    f"Input: {quote_info['input']}\n"
                    f"Expected output: {quote_info['output']}\n"
                    f"Price impact: {quote_info['price_impact']}\n"
                    f"Transaction hash: {tx_hash}"
                )
            except Exception as e:
                return f"Failed to execute swap: {str(e)}"
            
        except Exception as e:
            return f"Error executing swap: {str(e)}" 