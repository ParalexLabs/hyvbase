from typing import Optional, Dict, Any, List, ClassVar
from pydantic import BaseModel, Field
from ratelimit import limits, sleep_and_retry
import asyncio
from langchain.memory import ConversationBufferMemory
from langchain_core.callbacks import AsyncCallbackManager
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from ..base import SwarmBaseTool
from starknet_py.net.client import Client
from starknet_py.net.models import StarknetChainId
from starknet_py.contract import Contract
from starknet_py.net.account.account import Account
from starknet_py.net.full_node_client import FullNodeClient
import json
import tweepy
import time
from datetime import datetime

class SocialAuthConfig(BaseModel):
    """Base configuration for social media authentication."""
    rate_limit: int = 60  # requests per minute
    retry_count: int = 3
    timeout: int = 10
    memory_key: str = "chat_history"
    analytics_enabled: bool = True

class SocialAnalytics(BaseModel):
    """Analytics tracking for social media tools."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    rate_limit_hits: int = 0

class BaseSocialTool(SwarmBaseTool):
    """Enhanced base class for all social media tools."""
    
    auth_config: SocialAuthConfig = Field(default_factory=SocialAuthConfig)
    llm: Optional[Any] = None
    callback_manager: AsyncCallbackManager = Field(
        default_factory=lambda: AsyncCallbackManager([])
    )
    memory: ConversationBufferMemory = Field(
        default_factory=lambda: ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
    )
    webhook_handlers: List[Any] = Field(default_factory=list)
    analytics: SocialAnalytics = Field(default_factory=SocialAnalytics)
    
    def model_post_init(self, __context) -> None:
        """Post-initialization setup."""
        self._setup_rate_limiting()
        self._setup_chains()
        self._setup_webhooks()
        
    async def _retry_operation(self, operation, *args, **kwargs):
        """Retry operation placeholder; simply calls the operation once.
        Expand this as needed for real retry logic.
        """
        return await operation(*args, **kwargs)
        
    def _setup_chains(self):
        """Setup LangChain chains for content generation and analysis."""
        if not self.llm:
            return
            
        # Content generation chain
        content_template = """
        Generate social media content for {platform} with the following requirements:
        Topic: {topic}
        Tone: {tone}
        Length: {length}
        Previous context: {context}
        
        Content:
        """
        
        self.content_chain = LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                input_variables=["platform", "topic", "tone", "length", "context"],
                template=content_template
            ),
            memory=self.memory,
            callback_manager=self.callback_manager
        )
        
        # Sentiment analysis chain
        sentiment_template = """
        Analyze the sentiment and engagement potential of this social media content:
        Platform: {platform}
        Content: {content}
        
        Provide analysis in terms of:
        1. Overall sentiment (positive/negative/neutral)
        2. Engagement potential
        3. Key themes
        4. Improvement suggestions
        
        Analysis:
        """
        
        self.sentiment_chain = LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                input_variables=["platform", "content"],
                template=sentiment_template
            ),
            callback_manager=self.callback_manager
        )
        
    def _setup_rate_limiting(self):
        """Placeholder for rate limiting setup."""
        pass
        
    def _setup_webhooks(self):
        """Placeholder for webhook setup."""
        pass

class TwitterAuthConfig(SocialAuthConfig):
    """Twitter-specific authentication configuration."""
    api_key: str
    api_secret: str
    access_token: str
    access_token_secret: str
    tweet_rate_limit: int = 300  # Twitter API v2 rate limit
    monitor_keywords: Optional[List[str]] = None

class TwitterTool(BaseSocialTool):
    """Enhanced Twitter tool with LangChain integration."""
    
    name: str = "twitter"
    description: str = "Advanced Twitter operations with AI-powered features"
    auth_config: TwitterAuthConfig

    class Config:
        extra = "allow"

    def _authenticate(self):
        """Authenticate with Twitter API."""
        auth = tweepy.OAuthHandler(
            self.auth_config.api_key,
            self.auth_config.api_secret
        )
        auth.set_access_token(
            self.auth_config.access_token,
            self.auth_config.access_token_secret
        )
        return tweepy.API(auth)

    def __init__(
        self,
        auth_config: TwitterAuthConfig,
        llm: Optional[Any] = None,
        callback_manager: Optional[AsyncCallbackManager] = None
    ):
        super().__init__(auth_config=auth_config, llm=llm, callback_manager=callback_manager)
        self.api = self._authenticate()
        self.client = tweepy.Client(
            consumer_key=auth_config.api_key,
            consumer_secret=auth_config.api_secret,
            access_token=auth_config.access_token,
            access_token_secret=auth_config.access_token_secret
        )
        self._setup_twitter_chains()
        
    def _setup_twitter_chains(self):
        """Setup Twitter-specific LangChain chains."""
        if not self.llm:
            return
            
        # Thread generation chain
        thread_template = """
        Create a Twitter thread about {topic} with the following requirements:
        Style: {style}
        Number of tweets: {num_tweets}
        Include hashtags: {include_hashtags}
        Previous engagement context: {context}
        
        Format each tweet with a number and stay within character limits.
        Thread:
        """
        
        self.thread_chain = LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                input_variables=["topic", "style", "num_tweets", "include_hashtags", "context"],
                template=thread_template
            ),
            memory=self.memory,
            callback_manager=self.callback_manager
        )
        
        # Engagement optimization chain
        engagement_template = """
        Analyze this tweet for optimal engagement:
        Tweet: {tweet}
        Current time: {current_time}
        Target audience: {target_audience}
        Previous engagement data: {engagement_data}
        
        Provide:
        1. Best posting time
        2. Hashtag recommendations
        3. Content improvement suggestions
        4. Engagement prediction
        
        Analysis:
        """
        
        self.engagement_chain = LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                input_variables=["tweet", "current_time", "target_audience", "engagement_data"],
                template=engagement_template
            ),
            callback_manager=self.callback_manager
        )
        
    async def _arun(self, command: str) -> str:
        """
        Process a Twitter command from an AI agent in JSON format.
        
        Expected JSON formats:
          For tweeting:
              {
                  "action": "tweet",
                  "content": "Your tweet text here"
              }
          (You can expand this as needed.)
        """
        try:
            data = json.loads(command)
        except Exception as e:
            return f"Unable to parse command as JSON: {str(e)}"
        
        action = data.get("action")
        if action == "tweet":
            content = data.get("content")
            if not content:
                return "Missing 'content' for tweet action."
            # Run the synchronous Tweepy call in an executor
            loop = asyncio.get_running_loop()
            try:
                result = await loop.run_in_executor(None, self.api.update_status, content)
                tweet_id = result if isinstance(result, int) else getattr(result, "id", "unknown")
                return f"Tweet sent successfully! (id: {tweet_id})"
            except Exception as e:
                return f"Error sending tweet: {str(e)}"
        else:
            return f"Unknown action: {action}"

    # You can add other dedicated API methods for Twitter as needed.

class StarkNetTool(SwarmBaseTool):
    """Tool for interacting with StarkNet."""
    
    name: str = "starknet"
    description: str = "Execute operations on StarkNet blockchain"
    
    # Declare fields
    client: Any = None
    account: Any = None
    abis: Dict[str, Any] = {}
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(
        self,
        private_key: str,
        account_address: str,
        rpc_url: str = "https://starknet-mainnet.public.blastapi.io"
    ):
        super().__init__()
        self.client = FullNodeClient(node_url=rpc_url)
        self.account = Account(
            address=account_address,
            client=self.client,
            key_pair=private_key,
            chain=StarknetChainId.MAINNET
        )
        self._load_abis()
    
    def _load_abis(self):
        """Load contract ABIs."""
        # Add ABI loading logic here
        pass
        
    async def _arun(self, command: str) -> str:
        """Execute StarkNet operations."""
        try:
            cmd = json.loads(command)
            action = cmd.get("action")
            
            if action == "get_balance":
                address = cmd.get("address")
                # Use the correct ETH contract and method
                eth_contract = "0x049d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7"
                try:
                    # Get balance from storage
                    storage_key = self._get_balance_key(address)
                    result = await self.client.get_storage_at(
                        contract_address=eth_contract,
                        key=storage_key,
                        block_number="latest"
                    )
                    return f"Balance: {result}"
                except Exception as e:
                    return f"Failed to get balance: {str(e)}"
            
            return f"Unknown action: {action}"
        except Exception as e:
            return f"Error: {str(e)}"
            
    def _get_balance_key(self, address: str) -> int:
        """Calculate storage key for balance mapping."""
        # Remove '0x' prefix if present
        clean_address = address.replace('0x', '')
        # Convert to integer
        addr_int = int(clean_address, 16)
        # Calculate storage key using mapping formula
        storage_key = addr_int
        return storage_key

class StarkNetDEXTool(SwarmBaseTool):
    """Tool for interacting with StarkNet DEXes."""
    
    name: str = "starknet_dex"
    description: str = "Execute swaps and provide liquidity on StarkNet DEXes"
    
    DEX_CONTRACTS: ClassVar[Dict[str, Dict[str, Any]]] = {
        "jediswap": {
            "address": "0x...",  # JediSwap contract address
            "abi": {...}  # JediSwap ABI
        },
        "myswap": {
            "address": "0x...",  # MySwap contract address
            "abi": {...}  # MySwap ABI
        },
        "10kswap": {
            "address": "0x...",  # 10kSwap contract address
            "abi": {...}  # 10kSwap ABI
        }
    }
    
    def __init__(self, starknet_tool: StarkNetTool):
        super().__init__()
        self.starknet = starknet_tool
        self.dex_contracts = {}
        self._load_contracts()
        
    def _load_contracts(self):
        """Load DEX contract interfaces."""
        for dex_name, config in self.DEX_CONTRACTS.items():
            self.dex_contracts[dex_name] = Contract(
                address=config["address"],
                abi=config["abi"],
                client=self.starknet.client
            )
    
    async def _arun(self, command: str) -> str:
        """Execute DEX operations via a simple space-separated command interface.
        Example: "jediswap swap TOKEN1 TOKEN2 100.0"
        """
        try:
            cmd_parts = command.split(" ")
            dex = cmd_parts[0]
            action = cmd_parts[1]
            params = cmd_parts[2:]
            
            if dex not in self.dex_contracts:
                return f"Unsupported DEX: {dex}"
                
            if action == "swap":
                return await self._swap(
                    dex,
                    token_in=params[0],
                    token_out=params[1],
                    amount=float(params[2])
                )
            elif action == "add_liquidity":
                return await self._add_liquidity(
                    dex,
                    token_a=params[0],
                    token_b=params[1],
                    amount_a=float(params[2]),
                    amount_b=float(params[3])
                )
            else:
                return f"Unknown action: {action}"
        except Exception as e:
            return f"Error: {str(e)}"
            
    async def _swap(
        self,
        dex: str,
        token_in: str,
        token_out: str,
        amount: float
    ) -> str:
        """Execute a swap on specified DEX."""
        contract = self.dex_contracts[dex]
        
        # Prepare swap call
        swap_call = contract.functions["swap"].prepare(
            token_in=token_in,
            token_out=token_out,
            amount=amount
        )
        
        # Execute transaction
        tx = await self.starknet.account.execute(swap_call)
        receipt = await tx.wait_for_acceptance()
        
        return f"Swap executed: {receipt.transaction_hash}"

class StarkNetNFTTool(SwarmBaseTool):
    """Tool for interacting with StarkNet NFTs."""
    
    name: str = "starknet_nft"
    description: str = "Interact with NFTs on StarkNet"
    
    def __init__(self, starknet_tool: StarkNetTool):
        super().__init__()
        self.starknet = starknet_tool
        
    async def _arun(self, command: str) -> str:
        """Execute NFT operations."""
        try:
            cmd_parts = command.split(" ")
            action = cmd_parts[0]
            params = cmd_parts[1:]
            
            if action == "mint":
                return await self._mint_nft(
                    contract=params[0],
                    token_id=int(params[1])
                )
            elif action == "transfer":
                return await self._transfer_nft(
                    contract=params[0],
                    token_id=int(params[1]),
                    to_address=params[2]
                )
            else:
                return f"Unknown action: {action}"
        except Exception as e:
            return f"Error: {str(e)}" 