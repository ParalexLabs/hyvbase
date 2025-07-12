#!/usr/bin/env python3
"""
Simple test script for StarkNet Tool Adapter

This script provides a quick way to test the StarkNet tool adapter
without running the full comprehensive demo.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.hyvbase.tools.adapters.starknet_adapter import ModernStarkNetTool, StarkNetToolRegistry


async def test_configuration():
    """Test configuration validation"""
    print("Testing configuration validation...")
    
    # Test valid configuration from environment
    valid_config = {
        "private_key": os.getenv("STARKNET_PRIVATE_KEY", "0x123456789abcdef123456789abcdef123456789abcdef123456789abcdef123456"),
        "account_address": os.getenv("STARKNET_ACCOUNT_ADDRESS", "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    }
    
    valid, message = StarkNetToolRegistry.validate_config(valid_config)
    print(f"✅ Valid config test: {valid} - {message}")
    
    # Test invalid configuration
    invalid_config = {
        "private_key": "0x123"  # Missing account_address
    }
    
    valid, message = StarkNetToolRegistry.validate_config(invalid_config)
    print(f"❌ Invalid config test: {valid} - {message}")


async def test_tool_creation():
    """Test tool creation and basic functionality"""
    print("\nTesting tool creation...")
    
    config = {
        "private_key": os.getenv("STARKNET_PRIVATE_KEY", "0x123456789abcdef123456789abcdef123456789abcdef123456789abcdef123456"),
        "account_address": os.getenv("STARKNET_ACCOUNT_ADDRESS", "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"),
        "rpc_url": os.getenv("STARKNET_RPC_URL", "https://starknet-mainnet.public.blastapi.io")
    }
    
    try:
        # Create the tool
        tool = StarkNetToolRegistry.create_tool(config)
        print(f"✅ Tool created: {tool.name}")
        
        # Test capabilities
        capabilities = tool.get_capabilities()
        print(f"✅ Capabilities: {[cap.value for cap in capabilities]}")
        
        # Test command validation
        valid_commands = ["balance ETH", "quote ETH USDC 1.0", "status"]
        invalid_commands = ["invalid_command", "", "transfer"]
        
        for cmd in valid_commands:
            is_valid = tool.validate_command(cmd)
            print(f"✅ Valid command '{cmd}': {is_valid}")
        
        for cmd in invalid_commands:
            is_valid = tool.validate_command(cmd)
            print(f"❌ Invalid command '{cmd}': {is_valid}")
        
        # Test help text
        help_text = tool.get_help_text()
        print(f"✅ Help text available: {len(help_text)} characters")
        
    except Exception as e:
        print(f"❌ Tool creation failed: {e}")


async def test_command_execution():
    """Test command execution (without actual network calls)"""
    print("\nTesting command execution...")
    
    config = {
        "private_key": os.getenv("STARKNET_PRIVATE_KEY", "0x123456789abcdef123456789abcdef123456789abcdef123456789abcdef123456"),
        "account_address": os.getenv("STARKNET_ACCOUNT_ADDRESS", "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"),
        "rpc_url": os.getenv("STARKNET_RPC_URL", "https://starknet-mainnet.public.blastapi.io")
    }
    
    try:
        tool = StarkNetToolRegistry.create_tool(config)
        
        # Test error handling for uninitialized tool
        response = await tool.execute("status")
        print(f"Response type: {type(response)}")
        print(f"Response success: {response.success}")
        print(f"Response message: {response.message if response.success else response.error}")
        
        # Note: We don't actually initialize the tool here to avoid network calls
        print("⚠️  Note: Actual network operations require valid StarkNet credentials")
        
    except Exception as e:
        print(f"❌ Command execution test failed: {e}")


async def interactive_mode():
    """Interactive mode for testing commands"""
    print("\nEntering interactive mode...")
    print("Type 'help' for available commands or 'exit' to quit")
    
    config = {
        "private_key": os.getenv("STARKNET_PRIVATE_KEY", "0x123456789abcdef123456789abcdef123456789abcdef123456789abcdef123456"),
        "account_address": os.getenv("STARKNET_ACCOUNT_ADDRESS", "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"),
        "rpc_url": os.getenv("STARKNET_RPC_URL", "https://starknet-mainnet.public.blastapi.io")
    }
    
    tool = StarkNetToolRegistry.create_tool(config)
    
    while True:
        try:
            command = input("\n> ").strip()
            
            if command.lower() in ['exit', 'quit']:
                break
            elif command.lower() == 'help':
                print(tool.get_help_text())
            elif command.lower() == 'validate':
                test_cmd = input("Enter command to validate: ").strip()
                is_valid = tool.validate_command(test_cmd)
                print(f"Command '{test_cmd}' is {'valid' if is_valid else 'invalid'}")
            elif command:
                # Just validate the command (don't execute to avoid network calls)
                is_valid = tool.validate_command(command)
                if is_valid:
                    print(f"✅ Command '{command}' is valid")
                    print("⚠️  Note: Actual execution requires valid StarkNet credentials")
                else:
                    print(f"❌ Command '{command}' is invalid")
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")


async def main():
    """Main test function"""
    print("🧪 StarkNet Tool Adapter Test Suite")
    print("=" * 50)
    
    await test_configuration()
    await test_tool_creation()
    await test_command_execution()
    
    # Ask if user wants interactive mode
    try:
        choice = input("\nDo you want to enter interactive mode? (y/n): ").lower().strip()
        if choice.startswith('y'):
            await interactive_mode()
    except KeyboardInterrupt:
        print("\nExiting...")
    
    print("\n🎉 Test suite completed!")


if __name__ == "__main__":
    asyncio.run(main())
