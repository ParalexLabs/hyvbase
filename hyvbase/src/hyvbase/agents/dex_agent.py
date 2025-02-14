from typing import List, Optional, Dict, Any
from langchain.schema import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from langchain.memory import ConversationBufferMemory
from .personality import AgentPersonality
from ..tools.crypto import StarknetDEXTool
import json
import traceback
from datetime import datetime

class DEXAgent:
    """Agent for natural DEX interactions using LLM"""
    
    def __init__(
        self,
        llm: BaseChatModel,
        dex_tool: Dict[str, Any],  # Changed to accept dict of tools
        personality: Optional[AgentPersonality] = None,
        memory: Optional[ConversationBufferMemory] = None
    ):
        self.llm = llm
        # Store tools separately
        self.swap_tool = dex_tool["swap"]
        self.transfer_tool = dex_tool["transfer"]
        self.nft_tool = dex_tool["nft"]
        self.memory = memory
        self.personality = personality or AgentPersonality(
            name="Alex",
            role="DEX Trading Specialist",
            traits=["helpful", "precise"],
            expertise=["DEX Trading", "Token Swaps", "Token Transfers"]
        )
        
        # Track pending operations
        self.pending_trade = None
        
        # System prompt for command parsing
        self.system_prompt = f"""You are {self.personality.name}, a {self.personality.role}.
Your task is to understand user trading and transfer intentions and convert them to structured commands.

Available commands:
1. Quote: Get price quote for token swap
   Format: {{"action": "quote", "token_from": "X", "token_to": "Y", "amount": Z}}

2. Trade: Execute token swap
   Format: {{"action": "trade", "token_from": "X", "token_to": "Y", "amount": Z}}

3. Transfer: Send tokens to an address
   Format: {{"action": "transfer", "token": "X", "amount": Z, "to_address": "address"}}

4. Confirm: Respond to operation confirmation
   Format: {{"action": "confirm", "confirmed": true/false}}

Supported tokens: ETH, USDC, USDT, STARK

When users are responding to a confirmation:
- ONLY these responses should be interpreted as {{"action": "confirm", "confirmed": true}}:
  * "yes"
  * "yeah"
  * "sure"
  * "ok"
  * "go ahead"
  * "proceed"
  * "do it"
  * "confirm"
  * "execute"
  * "approved"

- ALL OTHER responses should be interpreted as {{"action": "confirm", "confirmed": false}}

Examples:
User: "send 0.5 STARK to 0x123..."
Response: {{"action": "transfer", "token": "STARK", "amount": 0.5, "to_address": "0x123..."}}

User: "What's the price of 2 STARK in USDC?"
Response: {{"action": "quote", "token_from": "STARK", "token_to": "USDC", "amount": 2.0}}

Always respond with a valid JSON command object. If you don't understand the request, respond with:
{{"action": "confirm", "confirmed": false}}

I can also analyze market conditions and provide insights. When users ask about:
- Market updates or conditions
- Price analysis
- Trading suggestions
- General market questions

Format for market analysis response:
{{"action": "market_analysis", "query": "user's question"}}

Example:
User: "How's the market looking?"
Response: {{"action": "market_analysis", "query": "current_market_overview"}}

User: "What's happening with ETH?"
Response: {{"action": "market_analysis", "query": "eth_analysis"}}
"""

    async def parse_command(self, user_input: str) -> Dict[str, Any]:
        """Use LLM to parse natural language into structured command"""
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_input)
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            # Use json.loads instead of eval for safety
            command = json.loads(response.content)
            
            # Convert string "true"/"false" to boolean if needed
            if command.get('action') == 'confirm':
                if isinstance(command.get('confirmed'), str):
                    command['confirmed'] = command['confirmed'].lower() == 'true'
                    
            return command
        except json.JSONDecodeError:
            return {"error": "Failed to parse LLM response as JSON"}
        except Exception as e:
            return {"error": f"Failed to parse command: {str(e)}"}

    async def process_command(self, command: str) -> str:
        """Process user command or engage in conversation"""
        try:
            # First check for system commands
            command = command.strip().lower()
            if command.startswith('auto'):
                if 'on' in command:
                    self.autonomous_mode = True
                    return "Autonomous mode enabled. I'll monitor the market and suggest trades."
                elif 'off' in command:
                    self.autonomous_mode = False
                    return "Autonomous mode disabled. I'll only respond to your commands."
                
            # For other commands, use LLM parsing
            parsed = await self.parse_command(command)
            
            if parsed["action"] == "market_analysis":
                return await self._handle_market_analysis(parsed["query"])
                
            elif parsed["action"] == "transfer":
                # Use transfer tool with proper method call
                try:
                    print(f"\nInitiating transfer of {parsed['amount']} {parsed['token']} to {parsed['to_address']}")
                    result = await self.transfer_tool.transfer_token(
                        token=parsed["token"],
                        amount=parsed["amount"],
                        to_address=parsed["to_address"]
                    )
                    print(f"\nTransaction submitted successfully!")
                    print(f"View on Starkscan: https://starkscan.co/tx/{result.split('0x')[1]}")
                    return f"Transfer initiated: {result}"
                except Exception as e:
                    return f"Transfer failed: {str(e)}"
                
            elif parsed["action"] == "quote":
                # Use swap tool for quotes
                quote = await self.swap_tool._arun(
                    f"quote {parsed['token_from']} {parsed['token_to']} {parsed['amount']}"
                )
                print(f"\nQuote for trading {parsed['amount']} {parsed['token_from']} to {parsed['token_to']}:")
                print(quote)
                return "Quote provided above"
            
            elif parsed["action"] == "trade":
                # Use swap tool for trades
                quote = await self.swap_tool._arun(
                    f"quote {parsed['token_from']} {parsed['token_to']} {parsed['amount']}"
                )
                print(f"\nQuote for trading {parsed['amount']} {parsed['token_from']} to {parsed['token_to']}:")
                print(quote)
                
                self.pending_trade = {
                    'token_from': parsed['token_from'],
                    'token_to': parsed['token_to'],
                    'amount': parsed['amount']
                }
                
                return "Would you like to proceed with this trade? (yes/no)"
            
            elif parsed["action"] == "confirm":
                # Handle confirmations for pending trades
                if self.pending_trade:
                    if parsed['confirmed']:
                        try:
                            result = await self.swap_tool._arun(
                                f"swap {self.pending_trade['token_from']} {self.pending_trade['token_to']} {self.pending_trade['amount']}"
                            )
                            self.pending_trade = None
                            return result
                        except Exception as e:
                            self.pending_trade = None
                            return f"Failed to execute swap: {str(e)}"
                    else:
                        self.pending_trade = None
                        return "Trade cancelled"
            
            else:
                # Handle as conversation if not a specific command
                return await self._handle_conversation(command)
                
        except Exception as e:
            return f"Error: {str(e)}"
            
    async def _handle_market_analysis(self, query: str) -> str:
        """Handle market analysis queries"""
        try:
            # Get current market data
            eth_price = await self.swap_tool._arun("quote ETH USDC 1")
            stark_price = await self.swap_tool._arun("quote STARK USDC 1")
            
            # Format market data for analysis
            market_data = {
                "ETH": eth_price,
                "STARK": stark_price,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            
            # Create analysis prompt
            analysis_prompt = f"""
            Current market conditions:
            ETH/USDC: {market_data['ETH']}
            STARK/USDC: {market_data['STARK']}
            
            User query: {query}
            
            Provide a concise but informative analysis of the market conditions,
            focusing on relevant aspects to the user's query. Include price trends,
            notable patterns, and potential implications if applicable.
            """
            
            # Get analysis from LLM
            response = await self.llm.ainvoke([{
                "role": "system",
                "content": "You are a crypto market analyst. Provide clear, actionable insights."
            }, {
                "role": "user",
                "content": analysis_prompt
            }])
            
            return response.content
            
        except Exception as e:
            return "I apologize, I'm having trouble analyzing the market data right now."
            
    async def _handle_conversation(self, user_input: str) -> str:
        """Handle general conversation"""
        try:
            messages = [{
                "role": "system",
                "content": f"""You are {self.personality.name}, a {self.personality.role}.
                Engage in natural conversation about crypto markets and trading.
                Provide helpful, informative responses while maintaining professionalism.
                """
            }, {
                "role": "user",
                "content": user_input
            }]
            
            response = await self.llm.ainvoke(messages)
            return response.content
            
        except Exception as e:
            return "I apologize, I'm having trouble processing your request." 