from typing import Optional, Dict, Any, Tuple, List
import re

class CommandParser:
    """Natural language command parser for trading commands"""
    
    def __init__(self, supported_tokens: List[str]):
        self.supported_tokens = [t.upper() for t in supported_tokens]
        
    def validate_token(self, token: str) -> Tuple[bool, str]:
        """Validate a token symbol"""
        token = token.upper()
        if token not in self.supported_tokens:
            return False, f"Invalid token: {token}. Supported tokens: {', '.join(self.supported_tokens)}"
        return True, token

    def parse_command(self, command: str) -> Dict[str, Any]:
        """Parse a natural language command into structured format"""
        command = command.lower().strip()
        
        # Common phrases that mean "yes"
        yes_phrases = [
            'yes', 'y', 'yeah', 'sure', 'ok', 'go ahead', 'proceed', 'confirm',
            'do it', 'lets do it', "let's do it", 'execute', 'approved'
        ]
        
        # Common phrases that mean "no"
        no_phrases = [
            'no', 'n', 'nah', 'cancel', 'stop', 'abort', 'nope', 
            'not now', 'not right now', 'maybe later', 'negative',
            'dont', "don't", 'do not', 'reject'
        ]
        
        # Check for variations of yes/no responses
        for phrase in yes_phrases:
            if phrase in command:
                return {
                    'action': 'confirm',
                    'confirmed': True
                }
                
        for phrase in no_phrases:
            if phrase in command:
                return {
                    'action': 'confirm',
                    'confirmed': False
                }

        # Quote patterns
        quote_match = re.match(
            r'(?:quote|get quote for|what is the price for|price for|check price for)\s+'
            r'(?:(\d+\.?\d*)\s+)?(\w+)(?:\s+to\s+|\s+)(\w+)(?:\s+(\d+\.?\d*))?', 
            command
        )
        if quote_match:
            groups = quote_match.groups()
            amount = float(groups[0] or groups[3])  # Amount could be at start or end
            token_from = groups[1].upper()
            token_to = groups[2].upper()
            
            valid, msg_or_token = self.validate_token(token_from)
            if not valid:
                return {'error': msg_or_token}
            
            valid, msg_or_token = self.validate_token(token_to)
            if not valid:
                return {'error': msg_or_token}
            
            return {
                'action': 'quote',
                'token_from': token_from,
                'token_to': token_to,
                'amount': amount
            }

        # Sell/Buy patterns
        trade_match = re.match(
            r'(?:i want to |please |can you |)?'
            r'(sell|buy)\s+'
            r'(?:about |around |approximately |)?'
            r'(\d+\.?\d*)\s+'
            r'(?:worth of |)?'
            r'(\w+)', 
            command
        )
        if trade_match:
            action, amount, token = trade_match.groups()
            amount = float(amount)
            
            valid, msg_or_token = self.validate_token(token)
            if not valid:
                return {'error': msg_or_token}
            
            return {
                'action': action,
                'token': token,
                'amount': amount
            }

        # Trade patterns
        trade_match = re.match(
            r'(?:i want to |please |can you |)?'
            r'(?:trade|swap|exchange)\s+'
            r'(\d+\.?\d*)\s+'
            r'(\w+)'
            r'(?:\s+for|\s+to|\s+into)\s+'
            r'(\w+)', 
            command
        )
        if trade_match:
            amount, token_from, token_to = trade_match.groups()
            amount = float(amount)
            
            valid, msg_or_token = self.validate_token(token_from)
            if not valid:
                return {'error': msg_or_token}
                
            valid, msg_or_token = self.validate_token(token_to)
            if not valid:
                return {'error': msg_or_token}
            
            return {
                'action': 'trade',
                'token_from': token_from,
                'token_to': token_to,
                'amount': amount
            }

        return {'error': 'Command not recognized'} 