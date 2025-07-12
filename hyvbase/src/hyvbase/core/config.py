"""Advanced Configuration System for HyvBase

Comprehensive configuration management with environment-specific settings,
feature flags, and runtime configuration updates.
"""

import os
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import yaml
import json

from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings

from .types import SecurityLevel, MemoryStrategy

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class DatabaseConfig:
    """Database configuration"""
    url: str = "sqlite:///hyvbase.db"
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False
    backup_enabled: bool = True
    backup_interval: int = 3600  # seconds


@dataclass
class RedisConfig:
    """Redis configuration"""
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    max_connections: int = 10
    decode_responses: bool = True


@dataclass
class SecurityConfig:
    """Security configuration"""
    default_security_level: SecurityLevel = SecurityLevel.MEDIUM
    encryption_key: Optional[str] = None
    jwt_secret: Optional[str] = None
    session_timeout: int = 3600  # seconds
    
    # Transaction limits
    max_transaction_value: Dict[str, float] = field(default_factory=lambda: {
        "ETH": 10.0,
        "USDC": 10000.0,
        "USDT": 10000.0,
        "STARK": 1000.0
    })
    
    # Rate limiting
    rate_limits: Dict[str, Dict[str, int]] = field(default_factory=lambda: {
        "crypto": {"requests_per_minute": 30, "burst": 50},
        "social": {"requests_per_minute": 60, "burst": 100},
        "general": {"requests_per_minute": 100, "burst": 200}
    })
    
    # IP restrictions
    allowed_ips: List[str] = field(default_factory=list)
    blocked_ips: List[str] = field(default_factory=list)
    
    # Audit settings
    audit_enabled: bool = True
    audit_retention_days: int = 90


@dataclass
class PerformanceConfig:
    """Performance configuration"""
    max_concurrent_operations: int = 10
    default_timeout: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Memory settings
    memory_strategy: MemoryStrategy = MemoryStrategy.HYBRID
    memory_ttl: int = 3600
    max_memory_size: int = 10000
    
    # Caching
    cache_enabled: bool = True
    cache_ttl: int = 300
    cache_max_size: int = 1000
    
    # Connection pooling
    connection_pool_size: int = 10
    connection_timeout: float = 10.0


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    file_path: str = "logs/hyvbase.log"
    file_max_size: str = "10MB"
    file_backup_count: int = 5
    
    # Structured logging
    structured_logging: bool = True
    log_format: str = "json"
    
    # External logging
    external_logging: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration"""
    metrics_enabled: bool = True
    metrics_port: int = 8080
    metrics_path: str = "/metrics"
    
    # Tracing
    tracing_enabled: bool = True
    tracing_sample_rate: float = 0.1
    
    # Health checks
    health_check_enabled: bool = True
    health_check_port: int = 8081
    health_check_path: str = "/health"
    
    # Alerting
    alerting_enabled: bool = True
    alert_channels: List[str] = field(default_factory=list)


class HyvBaseConfig(BaseSettings):
    """Main HyvBase configuration"""
    
    # Environment
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    
    # API Keys and Credentials
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    
    # Blockchain credentials
    starknet_private_key: Optional[str] = Field(None, env="STARKNET_PRIVATE_KEY")
    starknet_account: Optional[str] = Field(None, env="STARKNET_ACCOUNT")
    starknet_rpc_url: str = Field("https://starknet-mainnet.public.blastapi.io", env="STARKNET_RPC_URL")
    
    ethereum_private_key: Optional[str] = Field(None, env="ETHEREUM_PRIVATE_KEY")
    ethereum_rpc_url: str = Field("https://mainnet.infura.io/v3/YOUR_KEY", env="ETHEREUM_RPC_URL")
    
    solana_private_key: Optional[str] = Field(None, env="SOLANA_PRIVATE_KEY")
    solana_rpc_url: str = Field("https://api.mainnet-beta.solana.com", env="SOLANA_RPC_URL")
    
    # Social media credentials
    twitter_api_key: Optional[str] = Field(None, env="TWITTER_API_KEY")
    twitter_api_secret: Optional[str] = Field(None, env="TWITTER_API_SECRET")
    twitter_access_token: Optional[str] = Field(None, env="TWITTER_ACCESS_TOKEN")
    twitter_access_secret: Optional[str] = Field(None, env="TWITTER_ACCESS_SECRET")
    twitter_bearer_token: Optional[str] = Field(None, env="TWITTER_BEARER_TOKEN")
    
    telegram_bot_token: Optional[str] = Field(None, env="TELEGRAM_BOT_TOKEN")
    discord_bot_token: Optional[str] = Field(None, env="DISCORD_BOT_TOKEN")
    
    # Component configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    # Feature flags
    features: Dict[str, bool] = field(default_factory=lambda: {
        "advanced_trading": True,
        "social_automation": True,
        "analytics": True,
        "workflows": True,
        "plugins": True,
        "monitoring": True,
        "security_audit": True,
        "multi_chain": True,
        "ai_insights": True,
        "backup_recovery": True
    })
    
    # Plugin configuration
    plugin_directories: List[str] = field(default_factory=lambda: [
        "~/.hyvbase/plugins",
        "./plugins"
    ])
    
    # Network configurations
    networks: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "starknet": {
            "mainnet": {
                "rpc_url": "https://starknet-mainnet.public.blastapi.io",
                "explorer_url": "https://starkscan.co"
            },
            "testnet": {
                "rpc_url": "https://starknet-goerli.public.blastapi.io",
                "explorer_url": "https://testnet.starkscan.co"
            }
        },
        "ethereum": {
            "mainnet": {
                "rpc_url": "https://mainnet.infura.io/v3/YOUR_KEY",
                "explorer_url": "https://etherscan.io"
            },
            "goerli": {
                "rpc_url": "https://goerli.infura.io/v3/YOUR_KEY",
                "explorer_url": "https://goerli.etherscan.io"
            }
        }
    })
    
    # Tool configurations
    tool_configs: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "starknet": {
            "timeout": 30.0,
            "max_retries": 3,
            "gas_multiplier": 1.5
        },
        "twitter": {
            "timeout": 15.0,
            "max_retries": 2,
            "rate_limit": 60
        },
        "telegram": {
            "timeout": 10.0,
            "max_retries": 3,
            "rate_limit": 30
        }
    })
    
    # Custom user configurations
    user_configs: Dict[str, Any] = field(default_factory=dict)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    @validator('environment')
    def validate_environment(cls, v):
        if isinstance(v, str):
            return Environment(v.lower())
        return v
    
    @validator('plugin_directories')
    def expand_plugin_directories(cls, v):
        return [os.path.expanduser(path) for path in v]
    
    def get_network_config(self, network: str, chain_type: str = "mainnet") -> Dict[str, Any]:
        """Get network configuration"""
        return self.networks.get(network, {}).get(chain_type, {})
    
    def get_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """Get tool-specific configuration"""
        return self.tool_configs.get(tool_name, {})
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled"""
        return self.features.get(feature_name, False)
    
    def update_feature(self, feature_name: str, enabled: bool) -> None:
        """Update feature flag"""
        self.features[feature_name] = enabled
        logger.info(f"Feature {feature_name} {'enabled' if enabled else 'disabled'}")
    
    def get_credential(self, service: str, credential_type: str) -> Optional[str]:
        """Get credential safely"""
        attr_name = f"{service}_{credential_type}"
        return getattr(self, attr_name, None)
    
    def validate_credentials(self) -> Dict[str, bool]:
        """Validate that required credentials are present"""
        validation_results = {}
        
        # OpenAI
        validation_results['openai'] = bool(self.openai_api_key)
        
        # StarkNet
        validation_results['starknet'] = bool(
            self.starknet_private_key and self.starknet_account
        )
        
        # Social media
        validation_results['twitter'] = bool(
            self.twitter_api_key and self.twitter_api_secret
        )
        validation_results['telegram'] = bool(self.telegram_bot_token)
        validation_results['discord'] = bool(self.discord_bot_token)
        
        return validation_results
    
    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> 'HyvBaseConfig':
        """Load configuration from file"""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        if config_path.suffix.lower() == '.yaml' or config_path.suffix.lower() == '.yml':
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
        elif config_path.suffix.lower() == '.json':
            with open(config_path, 'r') as f:
                config_data = json.load(f)
        else:
            raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")
        
        return cls(**config_data)
    
    def save_to_file(self, config_path: Union[str, Path]) -> None:
        """Save configuration to file"""
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        config_dict = self.dict()
        
        if config_path.suffix.lower() == '.yaml' or config_path.suffix.lower() == '.yml':
            with open(config_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False)
        elif config_path.suffix.lower() == '.json':
            with open(config_path, 'w') as f:
                json.dump(config_dict, f, indent=2)
        else:
            raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")
    
    def create_environment_config(self, env: Environment) -> 'HyvBaseConfig':
        """Create environment-specific configuration"""
        config_dict = self.dict()
        
        # Environment-specific overrides
        if env == Environment.DEVELOPMENT:
            config_dict.update({
                'debug': True,
                'logging': {'level': 'DEBUG'},
                'security': {'audit_enabled': False},
                'performance': {'max_concurrent_operations': 5}
            })
        elif env == Environment.PRODUCTION:
            config_dict.update({
                'debug': False,
                'logging': {'level': 'INFO'},
                'security': {'audit_enabled': True},
                'performance': {'max_concurrent_operations': 20}
            })
        elif env == Environment.TESTING:
            config_dict.update({
                'debug': True,
                'logging': {'level': 'DEBUG'},
                'database': {'url': 'sqlite:///:memory:'},
                'performance': {'max_concurrent_operations': 2}
            })
        
        config_dict['environment'] = env
        return HyvBaseConfig(**config_dict)


class ConfigManager:
    """Configuration manager for runtime updates"""
    
    def __init__(self, config: HyvBaseConfig):
        self.config = config
        self._watchers: List[callable] = []
    
    def add_watcher(self, callback: callable) -> None:
        """Add configuration change watcher"""
        self._watchers.append(callback)
    
    def remove_watcher(self, callback: callable) -> None:
        """Remove configuration change watcher"""
        if callback in self._watchers:
            self._watchers.remove(callback)
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration and notify watchers"""
        for key, value in updates.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # Notify watchers
        for watcher in self._watchers:
            try:
                watcher(self.config, updates)
            except Exception as e:
                logger.error(f"Error in config watcher: {e}")
    
    def reload_from_file(self, config_path: Union[str, Path]) -> None:
        """Reload configuration from file"""
        new_config = HyvBaseConfig.from_file(config_path)
        self.config = new_config
        
        # Notify watchers
        for watcher in self._watchers:
            try:
                watcher(self.config, {"reloaded": True})
            except Exception as e:
                logger.error(f"Error in config watcher: {e}")


# Global configuration instance
_global_config: Optional[HyvBaseConfig] = None


def get_config() -> HyvBaseConfig:
    """Get global configuration instance"""
    global _global_config
    if _global_config is None:
        _global_config = HyvBaseConfig()
    return _global_config


def set_config(config: HyvBaseConfig) -> None:
    """Set global configuration instance"""
    global _global_config
    _global_config = config


def load_config(config_path: Optional[Union[str, Path]] = None) -> HyvBaseConfig:
    """Load configuration from file or environment"""
    if config_path:
        config = HyvBaseConfig.from_file(config_path)
    else:
        config = HyvBaseConfig()
    
    set_config(config)
    return config


# Environment-specific configuration factories
def create_development_config() -> HyvBaseConfig:
    """Create development configuration"""
    return HyvBaseConfig().create_environment_config(Environment.DEVELOPMENT)


def create_production_config() -> HyvBaseConfig:
    """Create production configuration"""
    return HyvBaseConfig().create_environment_config(Environment.PRODUCTION)


def create_testing_config() -> HyvBaseConfig:
    """Create testing configuration"""
    return HyvBaseConfig().create_environment_config(Environment.TESTING)
