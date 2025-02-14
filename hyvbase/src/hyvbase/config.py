from pydantic_settings import BaseSettings
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import os

# Load .env file first
load_dotenv()

class HyvBaseConfig(BaseSettings):
    """Global configuration for HyvBase."""
    
    # API Keys
    openai_api_key: Optional[str] = None
    starknet_private_key: Optional[str] = None
    starknet_account: Optional[str] = None
    twitter_client_id: Optional[str] = None
    twitter_client_secret: Optional[str] = None
    twitter_callback_url: Optional[str] = "http://127.0.0.1:8000/callback"
    twitter_bearer_token: Optional[str] = None
    twitter_api_key: Optional[str] = None
    twitter_api_secret: Optional[str] = None
    twitter_access_token: Optional[str] = None
    twitter_access_secret: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    
    # Network configurations
    rpc_urls: Dict[str, str] = {
        "starknet": "https://starknet-mainnet.public.blastapi.io"
    }
    
    # Tool configurations
    tool_configs: Dict[str, Dict[str, Any]] = {
        "twitter": {
            "rate_limit": 60,
            "retry_count": 3
        },
        "telegram": {
            "rate_limit": 30,
            "retry_count": 3
        },
        "starknet": {
            "rate_limit": 30,
            "retry_count": 3
        }
    }
    
    # Retry configurations
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 10.0
    
    # Rate limiting
    rate_limits: Dict[str, int] = {
        "social": 60,  # requests per minute
        "blockchain": 30
    }
    
    # Feature flags
    features: Dict[str, bool] = {
        "analytics": True,
        "auto_retry": True,
        "simulation": True,
        "vector_db": True  # Enable/disable vector database functionality
    }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False  # Allow case-insensitive env var names
        
        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            return (
                init_settings,
                env_settings,
                file_secret_settings,
            ) 