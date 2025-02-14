from hyvbase.main import HyvBase
import asyncio
from datetime import datetime

async def main():
    hyv = HyvBase()
    
    # Create an autonomous crypto agent
    agent = await hyv.create_autonomous_agent(
        agent_type="dex",
        name="CryptoAgent",
        tools=["starknet", "dex"],
        personality_config={
            "name": "Alex",
            "role": "Crypto Operations Specialist",
            "traits": ["precise", "security-focused", "helpful"],
            "expertise": ["Token Swaps", "Crypto Transfers", "DeFi Operations"],
            "speaking_style": "Professional and clear",
            "language_tone": "formal"
        },
        autonomous_config={
            "market_monitoring": True,
            "auto_trading": False,
            "monitoring_interval": 60,
            "risk_limits": {
                "max_trade_size": 1.0,
                "max_daily_trades": 5
            }
        }
    )

    print("\nCryptoAgent is ready! Type 'exit' to quit, 'memory <query>' to search history")
    print("Example: 'memory ETH trades' or 'memory recent conversations'\n")

    async def handle_command(cmd: str):
        """Process user input and store in vector memory"""
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
        
        # If it's a transaction-like command, store it
        if any(kw in cmd.lower() for kw in ["swap", "trade", "transfer", "buy", "sell"]):
            await hyv.store_transaction(
                agent_name="CryptoAgent",
                transaction_data={
                    "type": cmd.split()[0].lower(),  # First word as transaction type
                    "description": cmd,
                    "response": response,
                    "status": "processed",
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        return response

    async def search_memory(query: str):
        """Search both chat and transaction history"""
        # Get both chat and transaction history
        chats = await hyv.query_chat_history(
            query=query,
            agent_name="CryptoAgent",
            k=5
        )
        
        txns = await hyv.query_transactions(
            query=query,
            agent_name="CryptoAgent",
            k=3
        )

        # Format and return results
        results = []
        if chats:
            results.append("\nRelevant Conversations:")
            for chat in chats:
                results.append(f"{chat['metadata']['role']}: {chat['metadata']['message']}")
        
        if txns:
            results.append("\nRelevant Transactions:")
            for tx in txns:
                tx_data = tx['metadata']['transaction']
                results.append(f"- {tx_data['description']}")
                if tx_data.get('response'):
                    results.append(f"  Response: {tx_data['response']}")
                if tx_data.get('quote'):
                    results.append(f"  Quote: {tx_data['quote']}")

        return "\n".join(results) if results else "No relevant history found."

    # Main interaction loop
    while True:
        try:
            cmd = input("You: ").strip()
            if cmd.lower() == 'exit':
                break

            if cmd.lower().startswith('memory'):
                query = cmd[7:].strip()  # Remove 'memory ' from the query
                if query:
                    results = await search_memory(query)
                    print(results)
                else:
                    print("Please specify what to search for, e.g., 'memory ETH trades'")
            else:
                await handle_command(cmd)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {str(e)}")
            # Store error in memory for debugging
            await hyv.store_chat_memory(
                agent_name="CryptoAgent",
                message=f"Error occurred: {str(e)}",
                role="system"
            )

    # Graceful shutdown
    print("\nShutting down CryptoAgent...")

if __name__ == "__main__":
    asyncio.run(main()) 