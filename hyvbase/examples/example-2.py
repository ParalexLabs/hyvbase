"""
Example 2: Advanced StarkNet Trading with Dynamic Gas Management and Memory Optimization

This example demonstrates:
1. Dynamic gas price management
2. Memory optimization
3. Autonomous market monitoring
4. Natural language command processing
5. Error handling and retries
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
from hyvbase.main import HyvBase
from hyvbase.config import HyvBaseConfig

async def main():
    # Initialize HyvBase with custom memory configuration
    config = HyvBaseConfig(
        features={
            'vector_db': True  # Enable vector database
        },
        tool_configs={
            'memory': {
                'max_cache_size': 2000,      # Store more items in cache
                'cache_ttl': 7200,           # Keep items for 2 hours
                'cleanup_interval': 600,      # Clean up every 10 minutes
            },
            'twitter': {
                'rate_limit': 60,
                'retry_count': 3
            },
            'telegram': {
                'rate_limit': 30,
                'retry_count': 3
            },
            'starknet': {
                'rate_limit': 30,
                'retry_count': 3
            }
        }
    )
    hyv = HyvBase(config)
    
    # Create agent with autonomous capabilities
    agent = await hyv.create_autonomous_agent(
        agent_type="dex",
        name="TradingAgent",
        tools=["starknet", "dex"],
        personality_config={
            "name": "TradingBot",
            "role": "Advanced trading assistant",
            "traits": ["analytical", "cautious", "efficient"],
            "expertise": ["DeFi", "trading", "market analysis"]
        },
        autonomous_config={
            "market_monitoring": True,
            "auto_trading": False,  # Set to True to enable automated trading
            "monitoring_interval": 30,  # Check market every 30 seconds
            "risk_limits": {
                "max_trade_size": 0.5,  # Maximum 0.5 ETH per trade
                "max_daily_trades": 3,   # Maximum 3 trades per day
                "min_profit_threshold": 0.02  # 2% minimum profit
            }
        }
    )

    try:
        # Run the agent with monitoring and natural language support
        await hyv.run_agent_with_monitoring("TradingAgent")
    except KeyboardInterrupt:
        print("\nGracefully shutting down...")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Run the example
    asyncio.run(main())
