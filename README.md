# HyvBase 🚀

HyvBase is an intelligent agent framework for StarkNet and social media automation. Built with Python, it provides a simple way to create automated trading and social media management solutions.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## Features ✨

- **StarkNet Integration**: Swap tokens and execute transfers via AVNU DEX
- **Social Media Management**: Twitter and Telegram automation
- **Vector Memory**: Store and query conversation and transaction history
- **Intelligent Agents**: GPT-powered agents for natural interaction

## Quick Installation 🛠️

```bash
pip install hyvbase
```

Required: Python >=3.8

## Basic Example 📝

```python
from hyvbase.main import HyvBase
import asyncio

async def main():
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

    # Get price quote
    quote = await agent.process_command("What's the price of 0.1 ETH in USDC?")
    print(quote)

    # Execute swap
    swap = await agent.process_command("swap 0.1 ETH to USDC")
    print(swap)

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration 🔧

Create a `.env` file:

```env
# StarkNet
STARKNET_PRIVATE_KEY=your_private_key
STARKNET_ACCOUNT=your_account_address

# Social Media
TWITTER_CLIENT_ID=your_client_id
TWITTER_CLIENT_SECRET=your_client_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_SECRET=your_access_secret

TELEGRAM_BOT_TOKEN=your_bot_token

# OpenAI (for agent intelligence)
OPENAI_API_KEY=your_openai_key
```

## Supported Operations 🔥

### StarkNet
- Token swaps via AVNU DEX
- Token transfers
- Price quotes
- Transaction monitoring

Supported tokens: ETH, USDC, USDT, STARK

### Social Media
- Twitter: Post tweets, read timeline, engage with mentions
- Telegram: Send messages, manage groups, handle commands

### Memory Features
- Store and query chat history
- Track transaction history
- Semantic search capabilities

## Documentation 📚

For detailed documentation and examples, check out our [Documentation](DOCUMENTATION.md).

## Contributing 🤝

We welcome contributions! Please check our [Contributing Guidelines](CONTRIBUTING.md).

## License 📄

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

