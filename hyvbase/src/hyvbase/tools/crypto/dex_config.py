from dataclasses import dataclass
from typing import Dict, Tuple

@dataclass
class TokenConfig:
    """Token configuration"""
    symbol: str
    address: str
    decimals: int

@dataclass
class DEXConfig:
    """DEX configuration"""
    name: str
    address: str
    supported_tokens: Dict[str, TokenConfig]
    min_amount: float = 0.0001
    max_amount: float = 100.0
    max_slippage: float = 1.0

class DEXRegistry:
    """Registry for AVNU DEX configuration"""
    
    def __init__(self):
        # Define supported tokens
        self.tokens = {
            "ETH": TokenConfig(
                symbol="ETH",
                address="0x049d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7",
                decimals=18
            ),
            "USDC": TokenConfig(
                symbol="USDC",
                address="0x053c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8",
                decimals=6
            ),
            "USDT": TokenConfig(
                symbol="USDT",
                address="0x068f5c6a61780768455de69077e07e89787839bf8166decfbf92b645209c0fb8",
                decimals=6
            ),
            "STARK": TokenConfig(
                symbol="STARK",
                address="0x04718f5a0fc34cc1af16a1cdee98ffb20c31f5cd61d6ab07201858f4287c938d",
                decimals=18
            )
        }

        # Configure AVNU
        self.dex = DEXConfig(
            name="AVNU",
            address="0x04270219d365d6b017231b52e92b3fb5d7c8378b05e9abc97724537a80e93b0f",
            supported_tokens=self.tokens,
            min_amount=0.0001,
            max_amount=100.0,
            max_slippage=1.0
        )
    
    def is_supported_token(self, token_symbol: str) -> bool:
        """Check if token is supported"""
        return token_symbol.upper() in self.tokens
    
    def validate_trade(self, token_from: str, token_to: str, amount: float) -> Tuple[bool, str]:
        """Validate a trade against constraints"""
        if not self.is_supported_token(token_from):
            return False, f"Token {token_from} is not supported"
            
        if not self.is_supported_token(token_to):
            return False, f"Token {token_to} is not supported"
            
        if amount < self.dex.min_amount:
            return False, f"Amount {amount} is below minimum {self.dex.min_amount}"
            
        if amount > self.dex.max_amount:
            return False, f"Amount {amount} is above maximum {self.dex.max_amount}"
            
        return True, "Trade is valid" 