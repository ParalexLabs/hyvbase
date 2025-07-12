"""Example usage of Modern StarkNet Tool Adapter"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.hyvbase.tools.adapters.starknet_adapter import ModernStarkNetTool, StarkNetToolRegistry

async def main():
    # Configuration from environment variables
    config = {
        "private_key": os.getenv("STARKNET_PRIVATE_KEY"),
        "account_address": os.getenv("STARKNET_ACCOUNT_ADDRESS"),
        "rpc_url": os.getenv("STARKNET_RPC_URL", "https://starknet-mainnet.public.blastapi.io"),
        "network": os.getenv("STARKNET_NETWORK", "mainnet"),
        "max_fee": int(os.getenv("STARKNET_MAX_FEE", "1000000000000000")),
        "timeout": int(os.getenv("STARKNET_TIMEOUT", "30")),
        "retry_attempts": int(os.getenv("STARKNET_RETRY_ATTEMPTS", "3"))
    }
    
    # Check if required environment variables are set
    if not config["private_key"] or not config["account_address"]:
        print("❌ Error: Please set STARKNET_PRIVATE_KEY and STARKNET_ACCOUNT_ADDRESS environment variables")
        print("You can copy .env.example to .env and fill in your credentials")
        return
    
    # Validate configuration
    valid, message = StarkNetToolRegistry.validate_config(config)
    if not valid:
        print(f"Configuration error: {message}")
        return
    
    # Create the StarkNet tool
    starknet_tool = StarkNetToolRegistry.create_tool(config)
    
    # Initialize the tool
    await starknet_tool.initialize()
    
    # Execute various commands
    responses = []

    # Example DEX operation: Get price quote
    response = await starknet_tool.execute("quote ETH USDC 1.0")
    responses.append(response)
    
    # Example token transfer
    response = await starknet_tool.execute("transfer ETH 0.5 0xabcdef1234567890abcdef1234567890abcdef12")
    responses.append(response)
    
    # Example balance query
    response = await starknet_tool.execute("balance ETH")
    responses.append(response)
    
    for response in responses:
        if response.success:
            print(f"Success: {response.message}")
            print(f"Data: {response.data}")
        else:
            print(f"Error: {response.error}")

if __name__ == "__main__":
    asyncio.run(main())
