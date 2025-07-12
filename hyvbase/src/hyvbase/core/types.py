"""Core type definitions for HyvBase framework"""

from typing import Dict, List, Optional, Any, Union, Protocol, TypeVar, Generic
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid


class AgentType(Enum):
    """Agent types supported by HyvBase"""
    CRYPTO_TRADER = "crypto_trader"
    SOCIAL_MANAGER = "social_manager"
    MARKET_ANALYST = "market_analyst"
    PORTFOLIO_MANAGER = "portfolio_manager"
    ARBITRAGE_BOT = "arbitrage_bot"
    CONTENT_CREATOR = "content_creator"
    COMMUNITY_MODERATOR = "community_moderator"
    CUSTOM = "custom"


class AgentStatus(Enum):
    """Agent execution status"""
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING = "waiting"
    ERROR = "error"
    PAUSED = "paused"
    STOPPED = "stopped"


class ToolCapability(Enum):
    """Tool capabilities"""
    BLOCKCHAIN_READ = "blockchain_read"
    BLOCKCHAIN_WRITE = "blockchain_write"
    SOCIAL_READ = "social_read"
    SOCIAL_WRITE = "social_write"
    MARKET_DATA = "market_data"
    ANALYTICS = "analytics"
    AUTOMATION = "automation"
    AI_INFERENCE = "ai_inference"


class SecurityLevel(Enum):
    """Security levels for operations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MemoryStrategy(Enum):
    """Memory storage strategies"""
    CACHE_ONLY = "cache_only"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    PERMANENT = "permanent"
    HYBRID = "hybrid"


@dataclass
class AgentResponse:
    """Standardized agent response"""
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    execution_time: Optional[float] = None


@dataclass
class Transaction:
    """Blockchain transaction definition"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chain: str = ""
    from_address: str = ""
    to_address: str = ""
    value: float = 0.0
    token: str = ""
    gas_limit: Optional[int] = None
    gas_price: Optional[float] = None
    data: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TransactionResult:
    """Transaction execution result"""
    transaction_id: str
    success: bool
    hash: Optional[str] = None
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SecurityResult:
    """Security validation result"""
    approved: bool
    risk_score: float
    policies_checked: List[str]
    violations: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowStep:
    """Individual workflow step"""
    id: str
    name: str
    tool: str
    parameters: Dict[str, Any]
    conditions: Dict[str, Any] = field(default_factory=dict)
    retry_policy: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowDefinition:
    """Workflow definition"""
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    triggers: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Workflow:
    """Workflow execution instance"""
    id: str
    definition: WorkflowDefinition
    status: str = "pending"
    current_step: int = 0
    variables: Dict[str, Any] = field(default_factory=dict)
    results: List[Any] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


# Protocol definitions for better type safety
class ToolProtocol(Protocol):
    """Protocol for tools"""
    async def execute(self, command: str, **kwargs) -> AgentResponse:
        ...
    
    def get_capabilities(self) -> List[ToolCapability]:
        ...
    
    def validate_command(self, command: str) -> bool:
        ...


class AgentProtocol(Protocol):
    """Protocol for agents"""
    async def process(self, input_data: Any) -> AgentResponse:
        ...
    
    def get_status(self) -> AgentStatus:
        ...
    
    def get_capabilities(self) -> List[ToolCapability]:
        ...


# Generic types
T = TypeVar('T')
ResponseType = TypeVar('ResponseType', bound=AgentResponse)
