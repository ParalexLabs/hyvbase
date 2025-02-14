# HyvBase Documentation

HyvBase is a framework for building intelligent agents that can interact with StarkNet blockchain and social media platforms. It provides a simple way to create automated trading and social media management solutions.

## Installation

```bash
pip install hyvbase
```

Required Python version: >=3.8

## Quick Start

1. Create a `.env` file with your credentials:

```env
# StarkNet Configuration
STARKNET_PRIVATE_KEY=your_private_key
STARKNET_ACCOUNT=your_account_address

# Social Media APIs
TWITTER_CLIENT_ID=your_client_id
TWITTER_CLIENT_SECRET=your_client_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_SECRET=your_access_secret

TELEGRAM_BOT_TOKEN=your_bot_token

# OpenAI API (for agent intelligence)
OPENAI_API_KEY=your_openai_key
```

## Basic Usage

### Creating a Crypto Trading Agent

```python
from hyvbase.main import HyvBase
import asyncio

async def main():
    # Initialize HyvBase
    hyv = HyvBase()
    
    # Create a DEX agent
    agent = await hyv.create_agent(
        agent_type="dex",
        name="CryptoTrader",
        tools=["starknet", "dex"],
        personality_config={
            "name": "Alex",
            "role": "Crypto Trader",
            "traits": ["precise", "helpful"],
            "expertise": ["Token Swaps", "Transfers"]
        }
    )

    # Example commands:
    # Get quote
    quote = await agent.process_command("What's the price of 0.1 ETH in USDC?")
    print(quote)

    # Execute swap
    swap = await agent.process_command("swap 0.1 ETH to USDC")
    print(swap)

    # Send tokens
    transfer = await agent.process_command("send 100 USDC to 0x123...")
    print(transfer)

if __name__ == "__main__":
    asyncio.run(main())
```

### Creating a Social Media Agent

```python
async def main():
    hyv = HyvBase()
    
    # Create social media agent
    agent = await hyv.create_agent(
        agent_type="social",
        name="SocialManager",
        tools=["twitter", "telegram"],
        personality_config={
            "name": "Sam",
            "role": "Social Media Manager",
            "traits": ["engaging", "professional"],
            "expertise": ["Community Management"]
        }
    )

    # Post to Twitter
    tweet = await agent.process_command("post tweet: Hello from HyvBase! #Crypto")
    
    # Send Telegram message
    telegram = await agent.process_command("send telegram: Important update from HyvBase")
```

## Advanced Usage with Memory

HyvBase includes vector database integration for storing and querying conversation and transaction history:

```python
async def main():
    hyv = HyvBase()
    
    # Create agent with memory capabilities
    agent = await hyv.create_autonomous_agent(
        agent_type="dex",
        name="CryptoAgent",
        tools=["starknet", "dex"],
        personality_config={
            "name": "Alex",
            "role": "Crypto Operations Specialist",
            "traits": ["precise", "security-focused"],
            "expertise": ["Token Swaps", "DeFi Operations"]
        }
    )

    async def handle_command(cmd: str):
        # Store user message
        await hyv.store_chat_memory(
            agent_name="CryptoAgent",
            message=cmd,
            role="user"
        )
        
        # Get agent's response
        response = await agent.process_command(cmd)
        print(f"\nAgent: {response}\n")
        
        # Store agent's response
        await hyv.store_chat_memory(
            agent_name="CryptoAgent",
            message=response,
            role="agent"
        )
        
        # Store transactions
        if any(kw in cmd.lower() for kw in ["swap", "trade", "transfer"]):
            await hyv.store_transaction(
                agent_name="CryptoAgent",
                transaction_data={
                    "type": cmd.split()[0].lower(),
                    "description": cmd,
                    "response": response,
                    "timestamp": datetime.now().isoformat()
                }
            )

    # Search memory example
    results = await hyv.query_chat_history(
        query="recent ETH trades",
        agent_name="CryptoAgent",
        k=5
    )
```

## Supported Operations

### StarkNet Operations
- Token swaps via AVNU DEX
- Token transfers
- Price quotes
- Transaction monitoring

Supported tokens:
- ETH
- USDC
- USDT
- STARK

### Social Media Operations
- Twitter:
  - Post tweets
  - Read timeline
  - Engage with mentions
  
- Telegram:
  - Send messages
  - Manage group chats
  - Handle commands

### Vector Memory Features
- Store and query chat history
- Track transaction history
- Semantic search capabilities
- Conversation context maintenance

## Best Practices

1. **Error Handling**
```python
try:
    result = await agent.process_command("swap 0.1 ETH to USDC")
    print(result)
except Exception as e:
    print(f"Error: {str(e)}")
```

2. **Memory Management**
```python
# Store important interactions
await hyv.store_chat_memory(
    agent_name="CryptoAgent",
    message="Important message",
    role="user"
)

# Query past interactions
past_trades = await hyv.query_transactions(
    query="ETH trades last week",
    agent_name="CryptoAgent"
)
```

3. **Gas Management for StarkNet**
- Default gas settings are optimized for most operations
- Adjust if needed in your configuration:
```python
config = HyvBaseConfig(
    l1_max_amount=1000,  # Amount of L1 gas units
    l1_max_price_per_unit=25000  # Gas price in Gwei
)
```

## License

HyvBase is licensed under the MIT License. 