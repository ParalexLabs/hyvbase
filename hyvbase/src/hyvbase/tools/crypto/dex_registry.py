class DEXRegistry:
    """Registry of DEX contracts and tokens"""
    
    def __init__(self, is_testnet: bool = False):
        self.is_testnet = is_testnet
        
        # Mainnet addresses (verified 2024-03-15)
        self.tokens = {
            "ETH": TokenConfig(
                name="ETH",
                symbol="ETH",
                decimals=18,
                address="0x049d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7"
            ),
            "USDC": TokenConfig(
                name="USDC",
                symbol="USDC",
                decimals=6,
                address="0x053c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8"
            ),
            "STARK": TokenConfig(
                name="STARK",
                symbol="STARK",
                decimals=18,
                address="0x04718f5a0fc34cc1af16a1cdee98ffb20c31f5cd61d6ab07201858f4287c938d"
            )
        }
        
        # AVNU mainnet contract (verified)
        self.dex = DEXConfig(
            name="AVNU",
            contract_address="0x04270219d365d6b017231b52e92b3fb5d7c8378b05e9abc97724537a80e93b0f",
            max_slippage=1.0
        ) 