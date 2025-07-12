# StarkNet Tool Adapter Examples

This directory contains comprehensive examples showing how to integrate the StarkNet tools with the unified HyvBase framework.

## Files Overview

### 1. `starknet_adapter.py`
The main adapter file that bridges the existing StarkNet tools with the new unified framework. Located at `src/hyvbase/tools/adapters/starknet_adapter.py`.

**Key Features:**
- Unified command interface for all StarkNet operations
- Async/await support for all operations
- Structured response format with `AgentResponse`
- Error handling and validation
- Support for DEX, transfer, NFT, and balance operations

### 2. `starknet_tool_example.py`
A simple example demonstrating basic usage of the StarkNet tool adapter.

**Usage:**
```bash
cd hyvbase/examples
cp .env.example .env  # Fill in your credentials
python starknet_tool_example.py
```

### 3. `starknet_unified_agent_example.py`
A comprehensive demo showcasing full integration with the unified agent system.

**Features:**
- Complete workflow demonstrations
- Error handling examples
- Conversation flow simulation
- Response formatting
- History tracking

**Usage:**
```bash
cd hyvbase/examples
cp .env.example .env  # Fill in your credentials
python starknet_unified_agent_example.py
```

### 4. `test_starknet_tool.py`
A test script for validating the tool adapter functionality without requiring actual network connections.

**Usage:**
```bash
cd hyvbase/examples
cp .env.example .env  # Optional: Fill in your credentials for full testing
python test_starknet_tool.py
```

**Interactive Mode:**
The test script includes an interactive mode where you can test command validation and get help text.

### 5. `starknet_config.example.json`
Configuration template showing all available options for the StarkNet tool (alternative to .env).

### 6. `.env.example`
Environment variables template for configuration.

**Usage:**
1. Copy to `.env`: `cp .env.example .env`
2. Fill in your actual credentials
3. Environment variables are automatically loaded

## Configuration

### Environment Variables (Recommended)
All examples use environment variables for configuration. Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required environment variables:
- `STARKNET_PRIVATE_KEY` - Your StarkNet private key
- `STARKNET_ACCOUNT_ADDRESS` - Your StarkNet account address
- `STARKNET_RPC_URL` - StarkNet RPC endpoint (optional, defaults to public endpoint)

Optional environment variables:
- `STARKNET_NETWORK` - Network name (mainnet/testnet)
- `STARKNET_MAX_FEE` - Maximum transaction fee
- `STARKNET_TIMEOUT` - Request timeout in seconds
- `STARKNET_RETRY_ATTEMPTS` - Number of retry attempts

### Direct Configuration (Alternative)
You can also configure directly in code:
```python
config = {
    "private_key": "0x123456789abcdef...",
    "account_address": "0xabcdef1234567890...",
    "rpc_url": "https://starknet-mainnet.public.blastapi.io"
}
```

## Supported Commands

### DEX Operations
- `quote ETH USDC 1.0` - Get price quote for token swap
- `swap ETH USDC 1.0` - Execute token swap

### Transfer Operations
- `transfer ETH 0.5 0x123...` - Transfer tokens to address
- `send USDC 100 0x456...` - Send tokens (alias for transfer)

### Query Operations
- `balance ETH` - Get token balance
- `balance` - Get ETH balance (default)
- `status` - Get tool status and info

### NFT Operations
- `mint collection_address` - Mint NFT
- `nft info token_id` - Get NFT information

## Safety Features

### Validation
- Command syntax validation
- Configuration validation
- Address format validation
- Amount validation

### Error Handling
- Graceful error responses
- Detailed error messages
- Metadata for debugging
- Structured error format

### Security
- Private key protection
- Transaction confirmation prompts
- Maximum transfer limits
- Whitelist address support

## Response Format

All operations return a structured `AgentResponse`:

```python
class AgentResponse:
    success: bool
    data: Optional[Dict[str, Any]]
    message: str
    error: Optional[str]
    metadata: Optional[Dict[str, Any]]
```

### Success Response Example
```python
AgentResponse(
    success=True,
    data={
        "token": "ETH",
        "balance": "1.5",
        "account": "0xabcdef..."
    },
    message="Balance: 1.5 ETH",
    metadata={"tool": "starknet", "operation_type": "balance_query"}
)
```

### Error Response Example
```python
AgentResponse(
    success=False,
    error="Invalid command format",
    metadata={"tool": "starknet", "command": "invalid_command"}
)
```

## Integration with Unified Framework

### Tool Registration
```python
from hyvbase.tools.adapters.starknet_adapter import StarkNetToolRegistry

# Create tool
config = {...}
tool = StarkNetToolRegistry.create_tool(config)

# Initialize
await tool.initialize()

# Execute commands
response = await tool.execute("balance ETH")
```

### Agent Integration
```python
from hyvbase.core.agent import UnifiedAgent
from hyvbase.tools.adapters.starknet_adapter import ModernStarkNetTool

agent = UnifiedAgent()
starknet_tool = ModernStarkNetTool(config)
agent.register_tool("starknet", starknet_tool)

# Use through agent
response = await agent.execute("starknet balance ETH")
```

## Development

### Running Tests
```bash
# Run the test suite
python test_starknet_tool.py

# Run comprehensive demo
python starknet_unified_agent_example.py
```

### Adding New Commands
1. Add command validation to `validate_command()`
2. Add routing logic to `execute()`
3. Implement handler method (e.g., `_handle_new_operation()`)
4. Update help text in `get_help_text()`

### Extending Functionality
The adapter is designed to be extensible:
- Add new operation types
- Integrate additional StarkNet tools
- Add custom validation logic
- Implement custom response formatting

## Security Considerations

1. **Private Key Management**: Never hardcode private keys
2. **Network Safety**: Validate all network operations
3. **Amount Limits**: Implement reasonable transfer limits
4. **Address Validation**: Always validate addresses before operations
5. **Confirmation Prompts**: Require confirmation for destructive operations

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Configuration Errors**: Check your `starknet_config.json`
3. **Network Issues**: Verify RPC URL and connectivity
4. **Permission Errors**: Check private key and account permissions

### Debug Mode

Enable debug mode by setting environment variable:
```bash
export HYVBASE_DEBUG=1
```

This will provide detailed logging for troubleshooting.

## Contributing

When adding new features:
1. Follow the existing patterns
2. Add comprehensive tests
3. Update documentation
4. Ensure backward compatibility
5. Add example usage

## License

This code is part of the HyvBase project and follows the project's license terms.
