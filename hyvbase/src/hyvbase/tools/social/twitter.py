from typing import Optional, Dict, Any, List
import tweepy
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_core.callbacks import AsyncCallbackManager
from .base import BaseSocialTool, SocialAuthConfig
import time
from datetime import datetime
import asyncio
import webbrowser
from urllib.parse import parse_qs, urlparse
import os
from requests_oauthlib import OAuth2Session
import hashlib
import base64
import secrets

# Allow OAuth2 HTTP for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

class TwitterAuthConfig(SocialAuthConfig):
    """Twitter-specific authentication configuration."""
    client_id: str
    client_secret: str
    callback_url: str = "http://127.0.0.1:8000/callback"
    tweet_rate_limit: int = 300
    scopes: List[str] = ["tweet.read", "tweet.write", "users.read", "offline.access"]
    access_token: Optional[str] = None

def generate_pkce():
    """Generate PKCE code verifier and challenge."""
    code_verifier = secrets.token_urlsafe(32)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip('=')
    return code_verifier, code_challenge

class TwitterTool(BaseSocialTool):
    """Enhanced Twitter tool with LangChain integration."""
    
    name: str = "twitter"
    description: str = "Advanced Twitter operations with AI-powered features"
    auth_config: TwitterAuthConfig

    class Config:
        extra = "allow"

    def __init__(
        self,
        auth_config: TwitterAuthConfig,
        llm: Optional[Any] = None,
        callback_manager: Optional[AsyncCallbackManager] = None
    ):
        callback_manager = callback_manager or AsyncCallbackManager([])
        super().__init__(auth_config=auth_config, llm=llm, callback_manager=callback_manager)
        
        if auth_config.access_token:
            # Use existing access token if available
            self.client = tweepy.Client(
                access_token=auth_config.access_token,
                consumer_key=auth_config.client_id,
                consumer_secret=auth_config.client_secret,
                wait_on_rate_limit=True
            )
        else:
            # Get new access token through OAuth flow
            # Generate PKCE codes
            code_verifier, code_challenge = generate_pkce()
            
            # Create OAuth2 session
            self.oauth = OAuth2Session(
                auth_config.client_id,
                redirect_uri=auth_config.callback_url,
                scope=auth_config.scopes
            )
            
            # Get authorization URL with PKCE
            auth_url, state = self.oauth.authorization_url(
                'https://twitter.com/i/oauth2/authorize',
                code_challenge=code_challenge,
                code_challenge_method='S256'
            )
            
            print("\nPlease authorize the app:")
            print(auth_url)
            
            # Start local server to get the authorization code
            from http.server import HTTPServer, BaseHTTPRequestHandler
            import threading
            
            class CallbackHandler(BaseHTTPRequestHandler):
                oauth_response = None
                
                def do_GET(self):
                    CallbackHandler.oauth_response = self.path
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b"Authorization successful! You can close this window.")
                    
                def log_message(self, format, *args):
                    pass
            
            # Start server
            server = HTTPServer(('localhost', 8000), CallbackHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            
            # Open browser for authorization
            webbrowser.open(auth_url)
            
            # Wait for the callback
            while not CallbackHandler.oauth_response:
                pass
            
            # Stop server
            server.shutdown()
            server.server_close()
            
            # Parse the response
            callback_url = f"http://127.0.0.1:8000{CallbackHandler.oauth_response}"
            
            try:
                # Fetch token using the callback response
                token = self.oauth.fetch_token(
                    'https://api.twitter.com/2/oauth2/token',
                    authorization_response=callback_url,
                    client_secret=auth_config.client_secret,
                    code_verifier=code_verifier
                )
                
                print("\nAccess token obtained successfully!")
                
                # Initialize client with user context
                self.client = tweepy.Client(
                    access_token=token["access_token"],
                    consumer_key=auth_config.client_id,
                    consumer_secret=auth_config.client_secret,
                    wait_on_rate_limit=True
                )
                
            except Exception as e:
                print(f"\nError getting access token: {str(e)}")
                raise
        
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
        """Asynchronously process a command."""
        if command.startswith("tweet "):
            tweet_content = command[len("tweet "):]
            loop = asyncio.get_running_loop()
            try:
                # Use v2 API with user context
                result = await loop.run_in_executor(
                    None,
                    lambda: self.client.create_tweet(text=tweet_content)
                )
                return f"Tweet sent successfully! (id: {result.data['id']})"
            except Exception as e:
                return f"Failed to send tweet: {str(e)}"
        return f"Command not recognized: {command}"
        
    async def _execute_command(self, command: str) -> str:
        """Execute Twitter command with enhanced functionality."""
        cmd_parts = command.split(" ", 2)
        action = cmd_parts[0]
        
        actions = {
            "tweet": self.post_tweet,
            "thread": self.create_thread,
            "analyze": self.analyze_tweet,
            "monitor": self.monitor_keywords,
            "engage": self.auto_engage,
            "schedule": self.schedule_tweet,
            "trend": self.analyze_trends
        }
        
        if action not in actions:
            return f"Unknown action: {action}"
            
        return await actions[action](*cmd_parts[1:])
        
    async def create_thread(
        self,
        topic: str,
        style: str = "informative",
        num_tweets: int = 5,
        include_hashtags: bool = True
    ) -> str:
        """Create an AI-generated Twitter thread."""
        try:
            context = self.memory.load_memory_variables({})
            
            thread_content = await self.thread_chain.arun({
                "topic": topic,
                "style": style,
                "num_tweets": num_tweets,
                "include_hashtags": include_hashtags,
                "context": context.get(self.auth_config.memory_key, "")
            })
            
            # Parse and post thread
            tweets = self._parse_thread_content(thread_content)
            thread_ids = []
            
            for i, tweet in enumerate(tweets):
                if i == 0:
                    response = await self.post_tweet(tweet)
                    thread_ids.append(response.data["id"])
                else:
                    response = await self.post_tweet(
                        tweet,
                        reply_to=thread_ids[-1]
                    )
                    thread_ids.append(response.data["id"])
                    
            return f"Thread posted successfully. First tweet: {thread_ids[0]}"
        except Exception as e:
            return f"Failed to create thread: {str(e)}"
            
    async def analyze_tweet(
        self,
        tweet_text: str,
        target_audience: Optional[str] = None
    ) -> Dict:
        """Analyze tweet for engagement optimization."""
        try:
            engagement_data = await self._get_historical_engagement()
            
            analysis = await self.engagement_chain.arun({
                "tweet": tweet_text,
                "current_time": datetime.now().isoformat(),
                "target_audience": target_audience or "general",
                "engagement_data": engagement_data
            })
            
            return self._parse_engagement_analysis(analysis)
        except Exception as e:
            return f"Failed to analyze tweet: {str(e)}"
            
    async def auto_engage(
        self,
        keywords: List[str],
        engagement_type: str = "like,retweet,reply",
        max_engagements: int = 10
    ) -> str:
        """Automatically engage with relevant tweets."""
        try:
            engaged = 0
            async for tweet in self._search_relevant_tweets(keywords):
                if engaged >= max_engagements:
                    break
                    
                # Analyze tweet for engagement worthiness
                should_engage = await self._should_engage_with_tweet(tweet)
                if should_engage:
                    await self._perform_engagement(
                        tweet,
                        engagement_type.split(",")
                    )
                    engaged += 1
                    
            return f"Engaged with {engaged} tweets"
        except Exception as e:
            return f"Auto-engagement failed: {str(e)}" 