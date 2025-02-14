from hyvbase.main import HyvBase
import asyncio

async def main():
    swarm = HyvBase()
    
    # Create a comprehensive crypto agent
    await swarm.create_agent(
        agent_type="dex",
        name="CryptoAgent",
        tools=["starknet", "dex"],
        personality_config={
            "name": "Alex",
            "role": "Crypto Operations Specialist",
            "traits": ["precise", "security-focused", "helpful"],
            "expertise": [
                "Token Swaps",
                "Crypto Transfers",
                "NFT Operations",
                "DeFi Operations"
            ],
            "speaking_style": "Professional and clear",
            "language_tone": "formal"
        }
    )
    
    # Run the agent
    await swarm.run_agent("CryptoAgent")

if __name__ == "__main__":
    asyncio.run(main()) 