"""
Comprehensive Example: StarkNet Tool Integration with Unified Agent System

This example demonstrates how to integrate the Modern StarkNet Tool Adapter
with the unified HyvBase framework, showing various usage patterns and capabilities.
"""

import asyncio
import json
import os
from typing import Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.hyvbase.tools.adapters.starknet_adapter import ModernStarkNetTool, StarkNetToolRegistry
from src.hyvbase.core.types import AgentResponse, ToolCapability


class StarkNetAgentDemo:
    """Demo class showcasing StarkNet tool integration with unified agent system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.starknet_tool = None
        self.conversation_history = []
        
    async def initialize(self):
        """Initialize the StarkNet agent"""
        print("🚀 Initializing StarkNet Agent...")
        
        # Validate configuration
        valid, message = StarkNetToolRegistry.validate_config(self.config)
        if not valid:
            raise ValueError(f"Configuration error: {message}")
        
        # Create and initialize the StarkNet tool
        self.starknet_tool = StarkNetToolRegistry.create_tool(self.config)
        await self.starknet_tool.initialize()
        
        print("✅ StarkNet Agent initialized successfully!")
        print(f"📍 Account: {self.config['account_address'][:10]}...")
        print(f"🌐 Network: {self.config.get('network', 'mainnet')}")
        
    async def process_command(self, command: str) -> AgentResponse:
        """Process a command and return the response"""
        if not self.starknet_tool:
            raise RuntimeError("Agent not initialized")
        
        print(f"\n🔄 Processing command: {command}")
        
        # Record the command
        self.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "type": "command",
            "content": command
        })
        
        # Execute the command
        response = await self.starknet_tool.execute(command)
        
        # Record the response
        self.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "type": "response",
            "content": response.model_dump() if hasattr(response, 'model_dump') else str(response)
        })
        
        return response
    
    async def demo_dex_operations(self):
        """Demonstrate DEX operations"""
        print("\n" + "="*60)
        print("🏦 DEX OPERATIONS DEMO")
        print("="*60)
        
        # Get price quote
        print("\n1. Getting price quote for ETH/USDC...")
        response = await self.process_command("quote ETH USDC 1.0")
        self._display_response(response)
        
        # Get another quote with different amount
        print("\n2. Getting price quote for larger amount...")
        response = await self.process_command("quote ETH USDC 10.0")
        self._display_response(response)
        
        # Simulate a swap (this would normally require confirmation)
        print("\n3. Simulating token swap...")
        print("⚠️  Note: This would normally require user confirmation for safety")
        # response = await self.process_command("swap ETH USDC 0.1")
        # self._display_response(response)
        
    async def demo_balance_queries(self):
        """Demonstrate balance queries"""
        print("\n" + "="*60)
        print("💰 BALANCE QUERIES DEMO")
        print("="*60)
        
        # Check ETH balance
        print("\n1. Checking ETH balance...")
        response = await self.process_command("balance ETH")
        self._display_response(response)
        
        # Check USDC balance
        print("\n2. Checking USDC balance...")
        response = await self.process_command("balance USDC")
        self._display_response(response)
        
        # Check default balance (ETH)
        print("\n3. Checking default balance...")
        response = await self.process_command("balance")
        self._display_response(response)
    
    async def demo_status_queries(self):
        """Demonstrate status queries"""
        print("\n" + "="*60)
        print("ℹ️  STATUS QUERIES DEMO")
        print("="*60)
        
        # Get tool status
        print("\n1. Getting tool status...")
        response = await self.process_command("status")
        self._display_response(response)
        
        # Get capabilities
        print("\n2. Tool capabilities:")
        capabilities = self.starknet_tool.get_capabilities()
        for capability in capabilities:
            print(f"   ✓ {capability.value}")
        
        # Get help text
        print("\n3. Available commands:")
        help_text = self.starknet_tool.get_help_text()
        print(help_text)
    
    async def demo_transfer_operations(self):
        """Demonstrate transfer operations (simulation only)"""
        print("\n" + "="*60)
        print("💸 TRANSFER OPERATIONS DEMO (SIMULATION)")
        print("="*60)
        
        # Simulate token transfer
        print("\n1. Simulating ETH transfer...")
        print("⚠️  Note: This is a simulation - no actual transfer will occur")
        
        # In a real scenario, you would use a test address
        test_address = "0x1234567890abcdef1234567890abcdef12345678"
        
        # Validate the command first
        command = f"transfer ETH 0.01 {test_address}"
        is_valid = self.starknet_tool.validate_command(command)
        
        if is_valid:
            print(f"✅ Command validation passed: {command}")
            print("📝 In production, this would:")
            print(f"   • Transfer 0.01 ETH to {test_address[:10]}...")
            print(f"   • Return transaction hash")
            print(f"   • Provide block explorer link")
        else:
            print("❌ Command validation failed")
    
    async def demo_error_handling(self):
        """Demonstrate error handling"""
        print("\n" + "="*60)
        print("🚨 ERROR HANDLING DEMO")
        print("="*60)
        
        # Test invalid command
        print("\n1. Testing invalid command...")
        response = await self.process_command("invalid_command")
        self._display_response(response)
        
        # Test malformed command
        print("\n2. Testing malformed transfer command...")
        response = await self.process_command("transfer ETH")
        self._display_response(response)
        
        # Test empty command
        print("\n3. Testing empty command...")
        response = await self.process_command("")
        self._display_response(response)
    
    async def demo_conversation_flow(self):
        """Demonstrate a realistic conversation flow"""
        print("\n" + "="*60)
        print("💬 CONVERSATION FLOW DEMO")
        print("="*60)
        
        # Simulate a user conversation
        commands = [
            "status",
            "balance ETH",
            "quote ETH USDC 1.0",
            "balance USDC",
            "quote USDC ETH 1000"
        ]
        
        for i, command in enumerate(commands, 1):
            print(f"\n{i}. User: {command}")
            response = await self.process_command(command)
            
            if response.success:
                print(f"   Agent: {response.message}")
                if response.data:
                    print(f"   Data: {json.dumps(response.data, indent=2)}")
            else:
                print(f"   Agent: Error - {response.error}")
    
    def _display_response(self, response: AgentResponse):
        """Display a formatted response"""
        if response.success:
            print(f"✅ {response.message}")
            if response.data:
                print(f"📊 Data: {json.dumps(response.data, indent=2)}")
        else:
            print(f"❌ Error: {response.error}")
            if response.metadata:
                print(f"🔍 Metadata: {json.dumps(response.metadata, indent=2)}")
    
    async def save_conversation_history(self, filename: str = None):
        """Save conversation history to file"""
        if not filename:
            filename = f"starknet_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.conversation_history, f, indent=2)
        
        print(f"💾 Conversation history saved to {filename}")
    
    async def run_comprehensive_demo(self):
        """Run the comprehensive demo"""
        print("🎯 Starting Comprehensive StarkNet Tool Demo")
        print("="*60)
        
        try:
            # Initialize the agent
            await self.initialize()
            
            # Run all demo sections
            await self.demo_status_queries()
            await self.demo_balance_queries()
            await self.demo_dex_operations()
            await self.demo_transfer_operations()
            await self.demo_error_handling()
            await self.demo_conversation_flow()
            
            # Save conversation history
            await self.save_conversation_history()
            
            print("\n" + "="*60)
            print("🎉 Demo completed successfully!")
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ Demo failed with error: {e}")
            raise


async def main():
    """Main function to run the demo"""
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
    
    # Create and run the demo
    demo = StarkNetAgentDemo(config)
    await demo.run_comprehensive_demo()


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())
