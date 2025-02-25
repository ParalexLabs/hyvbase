from typing import Optional, Dict, Any, List, Union
from hyvbase.agents.personality import AgentPersonality
from hyvbase.tools.crypto import (
    StarknetTool, 
    StarknetDEXTool,
    StarknetTransferTool,
    StarknetNFTTool
)
from hyvbase.tools.social import TwitterTool, TelegramTool
from hyvbase.agents.dex_agent import DEXAgent
from hyvbase.agents.types import ZeroShotAgent, ReActAgent, ConversationalAgent
from hyvbase.analytics import OperationAnalytics
from hyvbase.config import HyvBaseConfig
from hyvbase.utils.nlp import create_parser
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.memory import ConversationBufferMemory
from dotenv import load_dotenv
import asyncio
import os
from pathlib import Path
from hyvbase.tools.social.twitter import TwitterAuthConfig
from datetime import datetime
from vectrs.database import VectorDBManager
from vectrs.database.vectrbase import SimilarityMetric, IndexType
import numpy as np
import logging
import time

# Disable OpenAI and httpx logging
logging.getLogger('openai').setLevel(logging.ERROR)
logging.getLogger('httpx').setLevel(logging.ERROR)

class HyvBase:
    """
    Main class for initializing and managing HyvBase functionality.
    Provides access to various tools and agents for blockchain and social media operations.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize HyvBase with optional configuration"""
        # Load environment variables
        load_dotenv()
        
        self.config = HyvBaseConfig() if not config else config
        self.analytics = OperationAnalytics()
        self.agents = {}
        self.tools = {}
        self.active_tasks = {}  # Store background tasks
        
        # Initialize OpenAI components
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize vector database if enabled
        self.use_vector_db = self.config.features.get('vector_db', True)  # Default to True for backward compatibility
        self.vector_dbs = {}
        
        if self.use_vector_db:
            # Create data directory if it doesn't exist
            self.data_dir = Path.home() / ".hyvbase" / "data"
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize vector database
            os.environ["VECTRS_DB_PATH"] = str(self.data_dir / "vector_store.db")
            self.db_manager = VectorDBManager()
            self._init_vector_db()

        self.memory_cache = {}
        self.memory_config = {
            'max_cache_size': 1000,  # Maximum number of items in cache
            'cache_ttl': 3600,  # Time to live for cache items in seconds
            'cleanup_interval': 300,  # Cleanup interval in seconds
        }
        self._start_memory_cleanup()

    def _init_vector_db(self):
        """Initialize default vector databases for chat history and transactions"""
        if not self.use_vector_db:
            return
            
        # Create chat history database
        chat_history_db_id = self.db_manager.create_database(
            dim=1536,  # OpenAI embedding dimension
            space=SimilarityMetric.COSINE,
            max_elements=100000,
            index_type=IndexType.HNSW
        )
        self.vector_dbs['chat_history'] = self.db_manager.get_database(chat_history_db_id)
        
        # Create transaction history database
        transaction_history_db_id = self.db_manager.create_database(
            dim=1536,  # OpenAI embedding dimension
            space=SimilarityMetric.COSINE,
            max_elements=100000,
            index_type=IndexType.HNSW
        )
        self.vector_dbs['transaction_history'] = self.db_manager.get_database(transaction_history_db_id)

    def create_llm(self, model: str = "gpt-4", temperature: float = 0.7) -> ChatOpenAI:
        """Create a language model instance"""
        return ChatOpenAI(
            temperature=temperature,
            model=model,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )

    def create_memory(self, memory_type: str = "buffer") -> ConversationBufferMemory:
        """Create a memory instance"""
        return ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

    def create_personality(
        self,
        name: str,
        role: str,
        traits: List[str],
        expertise: List[str],
        **kwargs
    ) -> AgentPersonality:
        """Create an agent personality"""
        return AgentPersonality(
            name=name,
            role=role,
            traits=traits,
            expertise=expertise,
            **kwargs
        )

    async def create_tools(self, tool_types: List[str]) -> Dict[str, Any]:
        """Create specified tools"""
        tools = {}
        
        for tool_type in tool_types:
            if tool_type == "starknet":
                tools["starknet"] = StarknetTool(
                    private_key=os.getenv("STARKNET_PRIVATE_KEY"),
                    account_address=os.getenv("STARKNET_ACCOUNT"),
                    rpc_url=os.getenv("STARKNET_RPC_URL")
                )
            elif tool_type == "dex":
                if "starknet" not in tools:
                    tools["starknet"] = await self.create_tools(["starknet"])
                starknet_tool = tools["starknet"]
                tools["dex"] = {
                    "swap": StarknetDEXTool(starknet_tool=starknet_tool),
                    "transfer": StarknetTransferTool(starknet_tool=starknet_tool),
                    "nft": StarknetNFTTool(starknet_tool=starknet_tool)
                }
            elif tool_type == "twitter":
                tools["twitter"] = TwitterTool(
                    auth_config=TwitterAuthConfig(
                        client_id=os.getenv("TWITTER_CLIENT_ID"),
                        client_secret=os.getenv("TWITTER_CLIENT_SECRET"),
                        api_key=os.getenv("TWITTER_API_KEY"),
                        api_secret=os.getenv("TWITTER_API_SECRET"),
                        access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
                        access_secret=os.getenv("TWITTER_ACCESS_SECRET")
                    )
                )
            elif tool_type == "telegram":
                tools["telegram"] = TelegramTool(
                    token=os.getenv("TELEGRAM_BOT_TOKEN")
                )

        return tools

    async def create_agent(
        self,
        agent_type: str,
        name: str,
        tools: List[str],
        personality_config: Dict[str, Any],
        model: str = "gpt-4",
        temperature: float = 0.7
    ) -> Union[ZeroShotAgent, ReActAgent, ConversationalAgent, DEXAgent]:
        """Create an agent of specified type with tools and personality"""
        
        # Create components
        llm = self.create_llm(model, temperature)
        memory = self.create_memory()
        personality = self.create_personality(**personality_config)
        tools_dict = await self.create_tools(tools)

        # Create appropriate agent type
        if agent_type == "dex":
            if "dex" not in tools_dict:
                tools_dict = await self.create_tools(["starknet", "dex"])
            agent = DEXAgent(
                llm=llm,
                dex_tool=tools_dict["dex"],
                personality=personality,
                memory=memory
            )
        elif agent_type == "zeroshot":
            agent = ZeroShotAgent(
                llm=llm,
                tools=list(tools_dict.values()),
                memory=memory
            )
        elif agent_type == "react":
            agent = ReActAgent(
                llm=llm,
                tools=list(tools_dict.values()),
                memory=memory
            )
        elif agent_type == "conversational":
            agent = ConversationalAgent(
                llm=llm,
                tools=list(tools_dict.values()),
                memory=memory,
                system_message=personality.get_system_prompt()
            )
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

        self.agents[name] = agent
        return agent

    async def create_autonomous_agent(
        self,
        agent_type: str,
        name: str,
        tools: List[str],
        personality_config: Dict[str, Any],
        autonomous_config: Optional[Dict[str, Any]] = None,
        model: str = "gpt-4",
        temperature: float = 0.7
    ) -> Any:
        """Create an agent with autonomous capabilities"""
        
        # Create base agent
        agent = await self.create_agent(
            agent_type=agent_type,
            name=name,
            tools=tools,
            personality_config=personality_config,
            model=model,
            temperature=temperature
        )
        
        # Add autonomous capabilities
        agent.autonomous_mode = False
        agent.autonomous_config = autonomous_config or {
            "market_monitoring": True,
            "auto_trading": False,  # Default to false for safety
            "monitoring_interval": 60,  # seconds
            "risk_limits": {
                "max_trade_size": 1.0,
                "max_daily_trades": 5
            }
        }
        
        return agent

    async def run_agent(self, agent_name: str):
        """Run an interactive session with the specified agent"""
        agent = self.agents.get(agent_name)
        if not agent:
            raise ValueError(f"Agent {agent_name} not found")

        print(f"\nAgent {agent_name} is ready!")
        print("Type 'exit' to quit\n")

        while True:
            try:
                command = input("You: ").strip()
                if command.lower() == 'exit':
                    break

                if hasattr(agent, "process_command"):
                    response = await agent.process_command(command)
                else:
                    response = await agent.arun(command)
                print(f"\nAgent: {response}\n")

            except KeyboardInterrupt:
                print("\nGracefully shutting down...")
                break
            except Exception as e:
                print(f"\nError: {str(e)}\n")

    async def run_agent_with_monitoring(self, agent_name: str):
        """Run agent with autonomous monitoring capabilities"""
        agent = self.agents.get(agent_name)
        if not agent:
            raise ValueError(f"Agent {agent_name} not found")

        # Initialize command parser
        self.cmd_parser = create_parser()

        # Start monitoring task
        monitoring_task = asyncio.create_task(
            self._autonomous_monitoring(agent)
        )
        self.active_tasks[f"{agent_name}_monitoring"] = monitoring_task

        print(f"\nAgent {agent_name} is ready!")
        print(self.cmd_parser.get_help())

        while True:
            try:
                command = input("\nWhat would you like to do? ").strip()
                
                # Parse natural language into structured command
                parsed_cmd, cmd_info = self.cmd_parser.parse_command(command)
                
                if parsed_cmd == 'exit':
                    print("\nGoodbye!")
                    break
                elif parsed_cmd == 'help':
                    print(self.cmd_parser.get_help())
                    continue
                elif parsed_cmd == 'auto on':
                    agent.autonomous_mode = True
                    print(f"\nAgent: Autonomous mode enabled. I'll monitor the market and suggest trades.")
                elif parsed_cmd == 'auto off':
                    agent.autonomous_mode = False
                    print(f"\nAgent: Autonomous mode disabled. I'll only respond to your commands.")
                elif parsed_cmd == 'monitor':
                    await self._market_update(agent)
                elif parsed_cmd.startswith('memory'):
                    if cmd_info['subtype'] == 'chat':
                        await self._show_chat_history(agent_name)
                    else:
                        await self._show_transaction_history(agent_name)
                else:
                    response = await agent.process_command(parsed_cmd)
                    print(f"\nAgent: {response}\n")
                    
                    # Store the interaction in memory
                    await self.store_chat_memory(agent_name, command, "user")
                    await self.store_chat_memory(agent_name, response, "agent")
                    
                    # Store transaction if it's a trade
                    if cmd_info.get('type') == 'trade':
                        await self.store_transaction(agent_name, {
                            'type': cmd_info['action'],
                            'token_in': cmd_info['token_in'],
                            'token_out': cmd_info['token_out'],
                            'amount': cmd_info['amount'],
                            'response': response,
                            'timestamp': datetime.now().isoformat()
                        })
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\nError: {str(e)}\n")
                await self.store_chat_memory(agent_name, str(e), "error")

        # Cleanup
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass

    async def _autonomous_monitoring(self, agent):
        """Background market monitoring and analysis with memory optimization"""
        while True:
            try:
                if getattr(agent, 'autonomous_mode', False):
                    # Get market update
                    market_data = await self._market_update(agent)
                    
                    if market_data:
                        # Store market data in memory
                        await self.store_transaction(agent.name, {
                            'type': 'market_update',
                            'data': market_data
                        })
                    
                    if agent.autonomous_config.get("auto_trading"):
                        await self._analyze_trading_opportunity(agent)
                    
                interval = agent.autonomous_config.get("monitoring_interval", 60)
                await asyncio.sleep(interval)
                
            except Exception as e:
                await asyncio.sleep(60)

    async def _market_update(self, agent):
        """Get and display market update"""
        try:
            # Get market data using the agent's swap tool
            eth_price = await agent.swap_tool._arun("quote ETH USDC 1")
            stark_price = await agent.swap_tool._arun("quote STARK USDC 1")
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{timestamp}] Market Update:")
            print(f"ETH/USDC: {eth_price}")
            print(f"STARK/USDC: {stark_price}")
            
            return {
                "ETH": eth_price,
                "STARK": stark_price,
                "timestamp": timestamp
            }
            
        except Exception as e:
            return None

    async def _analyze_trading_opportunity(self, agent):
        """Analyze market for trading opportunities"""
        try:
            market_data = await self._market_update(agent)
            if not market_data:
                return
                
            analysis = f"""
            Current market conditions:
            - ETH/USDC: {market_data['ETH']}
            - STARK/USDC: {market_data['STARK']}
            """
            
            suggestion = await agent.llm.ainvoke([{
                "role": "system",
                "content": "You are a trading analyst. Analyze the market data and suggest if any action should be taken. Respond with TRADE or HOLD."
            }, {
                "role": "user",
                "content": analysis
            }])
            
            if "TRADE" in suggestion.content:
                print(f"\n[{market_data['timestamp']}] Trading opportunity detected!")
                # Implement auto-trading logic here if needed
                
        except Exception as e:
            pass

    async def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text using OpenAI API"""
        try:
            # Get the full embedding vector from OpenAI
            response = await self.embeddings.aembed_query(text)
            
            if isinstance(response, dict) and 'data' in response:
                # Extract embedding from response if it's in a dict
                embedding_data = response['data'][0]['embedding']
                embedding = np.array(embedding_data, dtype=np.float32)
            else:
                # Try direct conversion
                embedding = np.array(response, dtype=np.float32)
            
            # Verify dimensions and reshape
            if embedding.size != 1536:
                return np.zeros((1, 1536), dtype=np.float32)
            
            # Ensure 2D shape (1, 1536)
            if len(embedding.shape) == 1:
                embedding = embedding.reshape(1, -1)
                
            return embedding
            
        except Exception as e:
            return np.zeros((1, 1536), dtype=np.float32)

    async def store_chat_memory(self, agent_name: str, message: str, role: str, embedding: Optional[np.ndarray] = None):
        """Store chat message in vector database"""
        if not self.use_vector_db:
            return
            
        if not embedding:
            # If no embedding provided, use OpenAI to create one
            embedding = await self._get_embedding(message)
        
        if embedding.shape != (1, 1536):
            return
            
        metadata = {
            "agent": agent_name,
            "role": role,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        vector_id = f"{agent_name}_{datetime.now().timestamp()}"
        try:
            # Extract 1D array for storage
            self.vector_dbs['chat_history'].add(
                embedding[0],  # Get the 1D array from the 2D embedding
                vector_id,
                metadata
            )
        except Exception as e:
            pass

    async def store_transaction(self, agent_name: str, transaction_data: Dict[str, Any], embedding: Optional[np.ndarray] = None):
        """Store transaction in vector database"""
        if not self.use_vector_db:
            return
            
        if not embedding:
            # Create embedding from transaction description or data
            desc = f"Transaction: {transaction_data.get('type', 'unknown')} - {transaction_data.get('description', '')}"
            embedding = await self._get_embedding(desc)
        
        if embedding.shape != (1, 1536):
            return
            
        # Add quote information if available
        if 'response' in transaction_data:
            try:
                # Try to extract quote information from response
                if 'quote' in transaction_data['response'].lower():
                    transaction_data['quote'] = transaction_data['response']
            except:
                pass
        
        metadata = {
            "agent": agent_name,
            "transaction": transaction_data,
            "timestamp": datetime.now().isoformat()
        }
        
        vector_id = f"{agent_name}_{datetime.now().timestamp()}"
        try:
            # Extract 1D array for storage
            self.vector_dbs['transaction_history'].add(
                embedding[0],  # Get the 1D array from the 2D embedding
                vector_id,
                metadata
            )
        except Exception as e:
            pass

    async def query_chat_history(self, query: str, agent_name: Optional[str] = None, k: int = 5) -> List[Dict[str, Any]]:
        """Query chat history using semantic search"""
        if not self.use_vector_db:
            return []
            
        embedding = await self._get_embedding(query)
        
        if embedding.shape != (1, 1536):
            return []
            
        # Set ef parameter for better recall (typically 2-3x k)
        self.vector_dbs['chat_history'].set_ef(k * 3)
        
        try:
            # Query similar vectors
            labels, distances = self.vector_dbs['chat_history'].knn_query(embedding, k=k)
            
            results = []
            for label, distance in zip(labels[0], distances[0]):
                # Get metadata for this vector
                vector_id = f"vector_{label}"  # This is a temporary ID, actual results will come from metadata
                metadata = self.vector_dbs['chat_history'].get_metadata(vector_id)
                if metadata:
                    results.append({
                        'metadata': metadata,
                        'distance': float(distance)
                    })
            
            # Filter by agent if specified
            if agent_name:
                results = [r for r in results if r['metadata']['agent'] == agent_name]
                
            return results
        except Exception as e:
            return []

    async def query_transactions(self, query: str, agent_name: Optional[str] = None, k: int = 5) -> List[Dict[str, Any]]:
        """Query transaction history using semantic search"""
        if not self.use_vector_db:
            return []
            
        embedding = await self._get_embedding(query)
        
        if embedding.shape != (1, 1536):
            return []
            
        # Set ef parameter for better recall (typically 2-3x k)
        self.vector_dbs['transaction_history'].set_ef(k * 3)
        
        try:
            # Query similar vectors
            labels, distances = self.vector_dbs['transaction_history'].knn_query(embedding, k=k)
            
            results = []
            for label, distance in zip(labels[0], distances[0]):
                # Get metadata for this vector
                vector_id = f"vector_{label}"  # This is a temporary ID, actual results will come from metadata
                metadata = self.vector_dbs['transaction_history'].get_metadata(vector_id)
                if metadata:
                    results.append({
                        'metadata': metadata,
                        'distance': float(distance)
                    })
            
            # Filter by agent if specified
            if agent_name:
                results = [r for r in results if r['metadata']['agent'] == agent_name]
                
            return results
        except Exception as e:
            return []

    def _start_memory_cleanup(self):
        """Start background memory cleanup task"""
        async def cleanup_task():
            while True:
                try:
                    await self._cleanup_memory()
                    await asyncio.sleep(self.memory_config['cleanup_interval'])
                except Exception:
                    await asyncio.sleep(60)  # Retry after a minute if cleanup fails
        
        asyncio.create_task(cleanup_task())

    async def _cleanup_memory(self):
        """Clean up expired cache items"""
        current_time = time.time()
        expired_keys = []
        
        for key, item in self.memory_cache.items():
            if current_time - item['timestamp'] > self.memory_config['cache_ttl']:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.memory_cache[key]

        # If still over limit, remove oldest items
        while len(self.memory_cache) > self.memory_config['max_cache_size']:
            oldest_key = min(self.memory_cache.items(), key=lambda x: x[1]['timestamp'])[0]
            del self.memory_cache[oldest_key]

    async def store_chat_memory(self, agent_name: str, message: str, role: str):
        """Store chat message in memory cache"""
        key = f"{agent_name}:{role}:{int(time.time())}"
        self.memory_cache[key] = {
            'message': message,
            'timestamp': time.time(),
            'type': 'chat'
        }
        
        # Trigger cleanup if cache is getting too large
        if len(self.memory_cache) >= self.memory_config['max_cache_size']:
            await self._cleanup_memory()

    async def store_transaction(self, agent_name: str, tx_data: dict):
        """Store transaction data in memory cache"""
        key = f"{agent_name}:tx:{int(time.time())}"
        self.memory_cache[key] = {
            'data': tx_data,
            'timestamp': time.time(),
            'type': 'transaction'
        }
        
        # Trigger cleanup if cache is getting too large
        if len(self.memory_cache) >= self.memory_config['max_cache_size']:
            await self._cleanup_memory()

    async def query_memory(self, query: str, memory_type: str = None, time_range: int = None) -> List[Dict]:
        """Query memory cache with filters"""
        current_time = time.time()
        results = []
        
        for item in self.memory_cache.values():
            # Apply time range filter if specified
            if time_range and (current_time - item['timestamp']) > time_range:
                continue
                
            # Apply type filter if specified
            if memory_type and item.get('type') != memory_type:
                continue
                
            # Simple text search in message/data
            content = item.get('message') or str(item.get('data'))
            if query.lower() in content.lower():
                results.append(item)
        
        return results

    async def _show_chat_history(self, agent_name: str, limit: int = 5):
        """Show recent chat history"""
        recent_chats = await self.query_chat_history(
            query="recent messages",
            agent_name=agent_name,
            k=limit
        )
        if recent_chats:
            print("\nRecent chat history:")
            for chat in recent_chats:
                metadata = chat['metadata']
                print(f"\n{metadata['role'].capitalize()}: {metadata['message']}")
                print(f"Time: {metadata['timestamp']}")
        else:
            print("\nNo recent chat history found")

    async def _show_transaction_history(self, agent_name: str, limit: int = 5):
        """Show recent transaction history"""
        recent_trades = await self.query_transactions(
            query="recent trades",
            agent_name=agent_name,
            k=limit
        )
        if recent_trades:
            print("\nRecent transactions:")
            for trade in recent_trades:
                metadata = trade['metadata']
                tx_data = metadata['transaction']
                print(f"\nType: {tx_data['type']}")
                if 'token_in' in tx_data:
                    print(f"Token In: {tx_data['token_in']}")
                    print(f"Token Out: {tx_data['token_out']}")
                    print(f"Amount: {tx_data['amount']}")
                if 'result' in tx_data:
                    print(f"Result: {tx_data['result']}")
                print(f"Time: {tx_data['timestamp']}")
        else:
            print("\nNo recent transactions found")

if __name__ == "__main__":
    print("HyvBase framework loaded. Import and use HyvBase class to create agents.") 