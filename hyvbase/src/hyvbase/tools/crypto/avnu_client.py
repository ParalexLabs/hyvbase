from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from .base import StarknetTool
import requests
from starknet_py.net.client_models import Call
from starknet_py.hash.selector import get_selector_from_name
from ...helpers.common import get_random_proxy

class AVNUConfig(BaseModel):
    """Configuration for AVNU client"""
    API_URL: str = "https://starknet.api.avnu.fi/swap/v1"
    CONTRACT: int = 0x04270219d365d6b017231b52e92b3fb5d7c8378b05e9abc97724537a80e93b0f
    SLIPPAGE_PCT: float = 1.0
    REFERRAL_FEES: int = 0x06365F8bc49887969AF68A27A5885270171ad0C18570EEAF4Fd53b162eb4A48C

class AVNUClient:
    """Client for interacting with AVNU API"""
    
    def __init__(self, starknet_tool: StarknetTool):
        self.starknet_tool = starknet_tool
        self.config = AVNUConfig()
        self.CONTRACT = self.config.CONTRACT  # Store contract address for easier access
        self._token_contracts = {}  # Cache for token contracts
    
    async def _get_token_contract(self, token_address: int):
        """Get or create token contract instance (awaits contract creation)"""
        if token_address not in self._token_contracts:
            self._token_contracts[token_address] = await self.starknet_tool.get_contract(token_address)
        return self._token_contracts[token_address]
    
    def get_quotes(self, from_token: int, to_token: int, amount: int) -> Dict[str, Any]:
        """Get quotes from AVNU"""
        url = f"{self.config.API_URL}/quotes"
        fees = hex(self.config.REFERRAL_FEES)

        params = {
            "sellTokenAddress": hex(from_token),
            "buyTokenAddress": hex(to_token),
            "sellAmount": hex(amount),
            # "integratorFees": hex(2),
            # "integratorFeeRecipient": fees,
            "excludeSources": "Ekubo",
        }

        proxies = get_random_proxy()
        response = requests.get(url, params=params, proxies=proxies)
        response_data = response.json()
        
        # Return full quote data instead of just quoteId
        return response_data[0]
    
    def build_transaction(self, quote_id: str, recipient: int, slippage: float) -> Dict[str, Any]:
        """Build transaction from quote"""
        url = f"{self.config.API_URL}/build"
        data = {
            "quoteId": quote_id,
            "takerAddress": hex(recipient),
            "slippage": float(slippage / 100),
        }

        proxies = get_random_proxy()
        response = requests.post(url, json=data, proxies=proxies)
        response_data = response.json()

        return response_data
    
    async def prepare_swap_calls(self, from_token: int, amount: int, transaction_data: Dict[str, Any]) -> List[Call]:
        """Prepare approval and swap calls"""
        try:
            # Get contract for approval
            approve_contract = await self._get_token_contract(from_token)
            
            # Manually create the approval call with proper uint256 handling
            approve_call = Call(
                to_addr=approve_contract.address,
                selector=get_selector_from_name("approve"),
                calldata=[self.CONTRACT, amount, 0]  # Flat list: spender, amount_low, amount_high
            )
            
            # Validate transaction data
            if "calldata" not in transaction_data:
                raise ValueError("Missing calldata in transaction")
            if "entrypoint" not in transaction_data:
                raise ValueError("Missing entrypoint in transaction")
                
            # Convert calldata strings to integers
            call_data = [
                int(item, 16) if isinstance(item, str) and item.startswith("0x") else int(item)
                for item in transaction_data["calldata"]
            ]
            
            # Prepare swap call
            swap_call = Call(
                to_addr=self.CONTRACT,
                selector=get_selector_from_name(transaction_data["entrypoint"]),
                calldata=call_data,
            )
            
            return [approve_call, swap_call]
            
        except Exception as e:
            raise ValueError(f"Failed to prepare swap calls: {str(e)}") 