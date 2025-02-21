"""Natural language processing utilities for HyvBase."""

import re
from typing import Tuple, Dict, Any, Optional, List

class CommandParser:
    """Parser for natural language commands in HyvBase."""
    
    def __init__(self):
        self.patterns = {
            'memory': [
                r'(?:show|view|check|get)\s+(?:memory|history)',
                r'(?:show|view|check|get)\s+(?:chat|conversation|messages)',
                r'(?:recent|latest)\s+(?:trades|transactions|activity)',
            ],
            'trade': [
                r'(?:buy|sell|swap|trade)\s+([\d.]+)\s*(\w+)(?:\s+(?:for|to|with)\s+(\w+))?',
            ],
            'quote': [
                r'(?:price|quote|rate|value)\s+(?:of\s+)?(\w+)(?:\s+(?:in|to|for)\s+(\w+))?',
                r'how\s+much\s+is\s+(\w+)(?:\s+(?:in|to|for)\s+(\w+))?',
                r'what\'s\s+the\s+price\s+of\s+(\w+)(?:\s+(?:in|to|for)\s+(\w+))?',
            ],
            'monitor': [
                r'(?:monitor|watch|track)\s+(?:market|prices)?',
                r'(?:start|enable|begin)\s+(?:monitoring|watching|tracking)',
                r'(?:stop|disable|end)\s+(?:monitoring|watching|tracking)',
            ],
            'exit': [
                r'(?:exit|quit|bye|goodbye)',
            ],
            'help': [
                r'(?:help|assist|guide|support)',
                r'what\s+can\s+you\s+do',
                r'show\s+commands',
            ],
        }
        
        # Default values
        self.default_quote_token = 'USDC'
        self.supported_tokens = ['ETH', 'USDC', 'USDT', 'STARK']
        
    def normalize_token(self, token: str) -> str:
        """Normalize token names to standard format."""
        token = token.upper()
        if token in self.supported_tokens:
            return token
        # Add any token name normalization rules here
        return token
        
    def parse_command(self, cmd: str) -> Tuple[str, Dict[str, Any]]:
        """Parse natural language command into structured format.
        
        Args:
            cmd: Natural language command string
            
        Returns:
            Tuple of (structured_command, metadata)
        """
        cmd = cmd.lower().strip()
        
        # Help command
        for pattern in self.patterns['help']:
            if re.search(pattern, cmd):
                return 'help', {'type': 'help'}
        
        # Memory commands
        if any(re.search(pattern, cmd) for pattern in self.patterns['memory']):
            if any(x in cmd for x in ['chat', 'conversation', 'messages']):
                return 'memory chat', {'type': 'memory', 'subtype': 'chat'}
            return 'memory recent', {'type': 'memory', 'subtype': 'transactions'}
        
        # Trading commands
        for pattern in self.patterns['trade']:
            match = re.search(pattern, cmd)
            if match:
                amount, token1, token2 = match.groups()
                token1 = self.normalize_token(token1)
                token2 = self.normalize_token(token2) if token2 else self.default_quote_token
                
                action = 'buy' if 'buy' in cmd else 'sell'
                if action == 'sell':
                    return f"swap {token1} {token2} {amount}", {
                        'type': 'trade',
                        'action': 'sell',
                        'amount': float(amount),
                        'token_in': token1,
                        'token_out': token2
                    }
                else:
                    return f"swap {token2} {token1} {amount}", {
                        'type': 'trade',
                        'action': 'buy',
                        'amount': float(amount),
                        'token_in': token2,
                        'token_out': token1
                    }
        
        # Quote commands
        for pattern in self.patterns['quote']:
            match = re.search(pattern, cmd)
            if match:
                token1, token2 = match.groups()
                token1 = self.normalize_token(token1)
                token2 = self.normalize_token(token2) if token2 else self.default_quote_token
                return f"quote {token1} {token2} 1", {
                    'type': 'quote',
                    'token': token1,
                    'quote_in': token2
                }
        
        # Monitoring commands
        for pattern in self.patterns['monitor']:
            if re.search(pattern, cmd):
                if 'start' in cmd or 'enable' in cmd:
                    return 'auto on', {'type': 'monitor', 'action': 'start'}
                elif 'stop' in cmd or 'disable' in cmd:
                    return 'auto off', {'type': 'monitor', 'action': 'stop'}
                return 'monitor', {'type': 'monitor', 'action': 'check'}
        
        # Exit commands
        for pattern in self.patterns['exit']:
            if re.search(pattern, cmd):
                return 'exit', {'type': 'exit'}
        
        # If no pattern matches, return the original command
        return cmd, {'type': 'unknown'}
    
    def get_help(self) -> str:
        """Get help message with available commands."""
        return """
Available commands:
1. Memory & History:
   - "show recent memory" or "view transactions"
   - "show chat history" or "view messages"

2. Trading:
   - "sell 0.4 STARK for USDC"
   - "buy 0.1 ETH"
   - "swap 1 ETH to USDC"

3. Price Quotes:
   - "what's the price of ETH?"
   - "quote STARK in USDC"
   - "how much is ETH worth?"

4. Market Monitoring:
   - "start monitoring"
   - "stop monitoring"
   - "check market status"

5. System:
   - "help" - Show this message
   - "exit" or "quit" - Close the application
"""

def create_parser() -> CommandParser:
    """Create and return a new CommandParser instance."""
    return CommandParser() 