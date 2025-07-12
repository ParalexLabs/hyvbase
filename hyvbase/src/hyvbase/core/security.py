"""Enterprise-Grade Security Manager for HyvBase

Multi-layer security system with transaction validation, risk assessment,
audit logging, and compliance frameworks.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import secrets
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from .types import SecurityLevel, SecurityResult, Transaction, TransactionResult
from .config import SecurityConfig

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk assessment levels"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    CRITICAL = "critical"


class PolicyType(Enum):
    """Security policy types"""
    TRANSACTION_LIMIT = "transaction_limit"
    RATE_LIMIT = "rate_limit"
    IP_RESTRICTION = "ip_restriction"
    TIME_RESTRICTION = "time_restriction"
    AMOUNT_RESTRICTION = "amount_restriction"
    FREQUENCY_RESTRICTION = "frequency_restriction"
    GEOGRAPHIC_RESTRICTION = "geographic_restriction"
    CUSTOM = "custom"


@dataclass
class TransactionPolicy:
    """Transaction security policy"""
    id: str
    name: str
    policy_type: PolicyType
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class RiskAssessment:
    """Risk assessment result"""
    risk_level: RiskLevel
    risk_score: float  # 0-100
    risk_factors: List[str]
    recommendations: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityEvent:
    """Security event for audit logging"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    severity: str = "INFO"
    message: str = ""
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    source_ip: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class EncryptionManager:
    """Encryption and key management"""
    
    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key or self._generate_master_key()
        self.cipher_suite = self._create_cipher_suite()
    
    def _generate_master_key(self) -> str:
        """Generate a new master key"""
        return Fernet.generate_key().decode()
    
    def _create_cipher_suite(self) -> Fernet:
        """Create cipher suite from master key"""
        return Fernet(self.master_key.encode())
    
    def encrypt(self, data: str) -> str:
        """Encrypt data"""
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt data"""
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
    
    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """Encrypt dictionary data"""
        json_str = json.dumps(data)
        return self.encrypt(json_str)
    
    def decrypt_dict(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt dictionary data"""
        json_str = self.decrypt(encrypted_data)
        return json.loads(json_str)
    
    def create_secure_hash(self, data: str) -> str:
        """Create secure hash"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def create_hmac(self, data: str, secret: str) -> str:
        """Create HMAC signature"""
        return hmac.new(
            secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def verify_hmac(self, data: str, signature: str, secret: str) -> bool:
        """Verify HMAC signature"""
        expected_signature = self.create_hmac(data, secret)
        return hmac.compare_digest(signature, expected_signature)


class RateLimiter:
    """Advanced rate limiting with sliding window"""
    
    def __init__(self):
        self.windows: Dict[str, List[float]] = {}
        self.cleanup_interval = 60  # seconds
        self.last_cleanup = time.time()
    
    def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        """Check if action is allowed within rate limit"""
        current_time = time.time()
        
        # Cleanup old entries periodically
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries()
            self.last_cleanup = current_time
        
        # Initialize key if not exists
        if key not in self.windows:
            self.windows[key] = []
        
        # Remove old entries for this key
        window_start = current_time - window_seconds
        self.windows[key] = [
            timestamp for timestamp in self.windows[key]
            if timestamp > window_start
        ]
        
        # Check if under limit
        if len(self.windows[key]) < limit:
            self.windows[key].append(current_time)
            return True
        
        return False
    
    def _cleanup_old_entries(self):
        """Remove old entries from all windows"""
        current_time = time.time()
        for key in list(self.windows.keys()):
            # Remove entries older than 1 hour
            self.windows[key] = [
                timestamp for timestamp in self.windows[key]
                if current_time - timestamp < 3600
            ]
            
            # Remove empty windows
            if not self.windows[key]:
                del self.windows[key]
    
    def get_remaining_time(self, key: str, limit: int, window_seconds: int) -> float:
        """Get remaining time until next allowed action"""
        if key not in self.windows or len(self.windows[key]) < limit:
            return 0.0
        
        oldest_entry = min(self.windows[key])
        return max(0.0, window_seconds - (time.time() - oldest_entry))


class AuditLogger:
    """Security audit logging system"""
    
    def __init__(self, log_file: Optional[Path] = None):
        self.log_file = log_file or Path.home() / ".hyvbase" / "audit.log"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.events: List[SecurityEvent] = []
        self.max_events_in_memory = 1000
    
    async def log_event(self, event: SecurityEvent) -> None:
        """Log security event"""
        self.events.append(event)
        
        # Persist to file
        await self._persist_event(event)
        
        # Cleanup old events from memory
        if len(self.events) > self.max_events_in_memory:
            self.events = self.events[-self.max_events_in_memory:]
        
        # Alert on critical events
        if event.severity in ["CRITICAL", "HIGH"]:
            await self._send_alert(event)
    
    async def _persist_event(self, event: SecurityEvent) -> None:
        """Persist event to file"""
        try:
            event_data = {
                "id": event.id,
                "event_type": event.event_type,
                "severity": event.severity,
                "message": event.message,
                "user_id": event.user_id,
                "agent_id": event.agent_id,
                "source_ip": event.source_ip,
                "metadata": event.metadata,
                "timestamp": event.timestamp.isoformat()
            }
            
            with open(self.log_file, "a") as f:
                f.write(json.dumps(event_data) + "\n")
                
        except Exception as e:
            logger.error(f"Failed to persist audit event: {e}")
    
    async def _send_alert(self, event: SecurityEvent) -> None:
        """Send alert for critical events"""
        # TODO: Implement alerting (email, Slack, etc.)
        logger.critical(f"Security Alert: {event.message}")
    
    def get_events(self, 
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None,
                   event_type: Optional[str] = None,
                   severity: Optional[str] = None) -> List[SecurityEvent]:
        """Get filtered security events"""
        filtered_events = self.events
        
        if start_time:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]
        
        if end_time:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]
        
        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]
        
        if severity:
            filtered_events = [e for e in filtered_events if e.severity == severity]
        
        return filtered_events


class SecurityManager:
    """Comprehensive security management system"""
    
    def __init__(self, 
                 security_level: SecurityLevel = SecurityLevel.MEDIUM,
                 policies: List[TransactionPolicy] = None,
                 config: Optional[SecurityConfig] = None):
        self.security_level = security_level
        self.policies = policies or []
        self.config = config or SecurityConfig()
        
        # Initialize components
        self.encryption_manager = EncryptionManager(self.config.encryption_key)
        self.rate_limiter = RateLimiter()
        self.audit_logger = AuditLogger()
        
        # Security state
        self.blocked_ips: Set[str] = set(self.config.blocked_ips)
        self.allowed_ips: Set[str] = set(self.config.allowed_ips)
        self.suspicious_activities: Dict[str, List[datetime]] = {}
        
        # Load default policies
        self._load_default_policies()
    
    def _load_default_policies(self) -> None:
        """Load default security policies"""
        default_policies = [
            TransactionPolicy(
                id="default_transaction_limit",
                name="Default Transaction Limit",
                policy_type=PolicyType.TRANSACTION_LIMIT,
                parameters={
                    "max_value_usd": 10000,
                    "max_value_eth": 5.0,
                    "max_daily_volume": 50000
                },
                description="Default transaction value limits"
            ),
            TransactionPolicy(
                id="default_rate_limit",
                name="Default Rate Limit",
                policy_type=PolicyType.RATE_LIMIT,
                parameters={
                    "max_requests_per_minute": 60,
                    "max_transactions_per_hour": 10
                },
                description="Default rate limiting"
            ),
            TransactionPolicy(
                id="time_restriction",
                name="Time-based Restrictions",
                policy_type=PolicyType.TIME_RESTRICTION,
                parameters={
                    "allowed_hours": list(range(6, 23)),  # 6 AM to 11 PM
                    "timezone": "UTC"
                },
                description="Restrict operations to business hours"
            )
        ]
        
        for policy in default_policies:
            if not any(p.id == policy.id for p in self.policies):
                self.policies.append(policy)
    
    async def validate_operation(self, 
                               operation_type: str,
                               data: Dict[str, Any],
                               agent_context: Dict[str, Any]) -> SecurityResult:
        """Comprehensive operation validation"""
        start_time = time.time()
        
        try:
            # Initialize validation result
            result = SecurityResult(
                approved=True,
                risk_score=0.0,
                policies_checked=[],
                violations=[],
                recommendations=[]
            )
            
            # Log security event
            await self.audit_logger.log_event(SecurityEvent(
                event_type="operation_validation",
                severity="INFO",
                message=f"Validating {operation_type} operation",
                agent_id=agent_context.get("agent_id"),
                metadata={"operation_type": operation_type, "data": data}
            ))
            
            # 1. IP-based validation
            await self._validate_ip_restrictions(result, agent_context)
            
            # 2. Rate limiting validation
            await self._validate_rate_limits(result, operation_type, agent_context)
            
            # 3. Transaction-specific validation
            if operation_type in ["trade", "transfer", "swap"]:
                await self._validate_transaction(result, data, agent_context)
            
            # 4. Time-based restrictions
            await self._validate_time_restrictions(result, operation_type)
            
            # 5. Risk assessment
            risk_assessment = await self._assess_risk(operation_type, data, agent_context)
            result.risk_score = risk_assessment.risk_score
            result.recommendations.extend(risk_assessment.recommendations)
            
            # 6. Policy enforcement
            await self._enforce_policies(result, operation_type, data, agent_context)
            
            # Final approval decision
            result.approved = (
                len(result.violations) == 0 and
                result.risk_score < self._get_risk_threshold()
            )
            
            # Log result
            await self.audit_logger.log_event(SecurityEvent(
                event_type="operation_validation_complete",
                severity="INFO" if result.approved else "WARNING",
                message=f"Operation {'approved' if result.approved else 'rejected'}",
                agent_id=agent_context.get("agent_id"),
                metadata={
                    "approved": result.approved,
                    "risk_score": result.risk_score,
                    "violations": result.violations,
                    "execution_time": time.time() - start_time
                }
            ))
            
            return result
            
        except Exception as e:
            await self.audit_logger.log_event(SecurityEvent(
                event_type="validation_error",
                severity="ERROR",
                message=f"Security validation failed: {str(e)}",
                agent_id=agent_context.get("agent_id"),
                metadata={"error": str(e)}
            ))
            
            return SecurityResult(
                approved=False,
                risk_score=100.0,
                policies_checked=[],
                violations=[f"Validation error: {str(e)}"],
                recommendations=["Review security configuration"]
            )
    
    async def _validate_ip_restrictions(self, result: SecurityResult, context: Dict[str, Any]) -> None:
        """Validate IP-based restrictions"""
        source_ip = context.get("source_ip")
        if not source_ip:
            return
        
        result.policies_checked.append("ip_restrictions")
        
        # Check blocked IPs
        if source_ip in self.blocked_ips:
            result.violations.append(f"IP {source_ip} is blocked")
            return
        
        # Check allowed IPs (if configured)
        if self.allowed_ips and source_ip not in self.allowed_ips:
            result.violations.append(f"IP {source_ip} is not in allowed list")
    
    async def _validate_rate_limits(self, result: SecurityResult, operation_type: str, context: Dict[str, Any]) -> None:
        """Validate rate limiting"""
        result.policies_checked.append("rate_limits")
        
        # Get rate limit configuration
        rate_config = self.config.rate_limits.get(operation_type, self.config.rate_limits.get("general"))
        if not rate_config:
            return
        
        # Create rate limit key
        agent_id = context.get("agent_id", "unknown")
        rate_key = f"{agent_id}:{operation_type}"
        
        # Check rate limit
        if not self.rate_limiter.is_allowed(
            rate_key,
            rate_config["requests_per_minute"],
            60  # 1 minute window
        ):
            remaining_time = self.rate_limiter.get_remaining_time(
                rate_key,
                rate_config["requests_per_minute"],
                60
            )
            result.violations.append(
                f"Rate limit exceeded for {operation_type}. "
                f"Try again in {remaining_time:.1f} seconds"
            )
    
    async def _validate_transaction(self, result: SecurityResult, data: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Validate transaction-specific rules"""
        result.policies_checked.append("transaction_validation")
        
        # Check transaction value limits
        amount = data.get("amount", 0)
        token = data.get("token", "").upper()
        
        if token in self.config.max_transaction_value:
            max_value = self.config.max_transaction_value[token]
            if amount > max_value:
                result.violations.append(
                    f"Transaction amount {amount} {token} exceeds limit {max_value}"
                )
        
        # Check for suspicious patterns
        await self._check_suspicious_patterns(result, data, context)
    
    async def _validate_time_restrictions(self, result: SecurityResult, operation_type: str) -> None:
        """Validate time-based restrictions"""
        result.policies_checked.append("time_restrictions")
        
        # Find time restriction policy
        time_policy = next(
            (p for p in self.policies if p.policy_type == PolicyType.TIME_RESTRICTION),
            None
        )
        
        if not time_policy or not time_policy.enabled:
            return
        
        current_hour = datetime.now().hour
        allowed_hours = time_policy.parameters.get("allowed_hours", list(range(24)))
        
        if current_hour not in allowed_hours:
            result.violations.append(
                f"Operation not allowed at hour {current_hour}. "
                f"Allowed hours: {allowed_hours}"
            )
    
    async def _assess_risk(self, operation_type: str, data: Dict[str, Any], context: Dict[str, Any]) -> RiskAssessment:
        """Comprehensive risk assessment"""
        risk_factors = []
        risk_score = 0.0
        
        # Base risk by operation type
        operation_risk = {
            "trade": 30,
            "transfer": 25,
            "swap": 20,
            "post": 10,
            "read": 5
        }
        risk_score += operation_risk.get(operation_type, 15)
        
        # Amount-based risk
        amount = data.get("amount", 0)
        if amount > 1000:
            risk_score += 20
            risk_factors.append("High transaction amount")
        elif amount > 100:
            risk_score += 10
            risk_factors.append("Medium transaction amount")
        
        # Time-based risk
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 22:
            risk_score += 15
            risk_factors.append("Off-hours operation")
        
        # Frequency-based risk
        agent_id = context.get("agent_id", "unknown")
        if agent_id in self.suspicious_activities:
            recent_activities = len([
                activity for activity in self.suspicious_activities[agent_id]
                if activity > datetime.now() - timedelta(hours=1)
            ])
            if recent_activities > 10:
                risk_score += 30
                risk_factors.append("High frequency activity")
        
        # Determine risk level
        if risk_score >= 80:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 60:
            risk_level = RiskLevel.VERY_HIGH
        elif risk_score >= 40:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 20:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        # Generate recommendations
        recommendations = []
        if risk_score > 50:
            recommendations.append("Consider additional verification")
        if risk_score > 70:
            recommendations.append("Manual review recommended")
        if risk_score > 90:
            recommendations.append("Block operation and investigate")
        
        return RiskAssessment(
            risk_level=risk_level,
            risk_score=risk_score,
            risk_factors=risk_factors,
            recommendations=recommendations
        )
    
    async def _enforce_policies(self, result: SecurityResult, operation_type: str, data: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Enforce security policies"""
        for policy in self.policies:
            if not policy.enabled:
                continue
            
            result.policies_checked.append(policy.name)
            
            try:
                await self._enforce_single_policy(policy, result, operation_type, data, context)
            except Exception as e:
                logger.error(f"Error enforcing policy {policy.name}: {e}")
                result.violations.append(f"Policy enforcement error: {policy.name}")
    
    async def _enforce_single_policy(self, policy: TransactionPolicy, result: SecurityResult, 
                                   operation_type: str, data: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Enforce a single policy"""
        if policy.policy_type == PolicyType.TRANSACTION_LIMIT:
            await self._enforce_transaction_limit_policy(policy, result, data)
        elif policy.policy_type == PolicyType.AMOUNT_RESTRICTION:
            await self._enforce_amount_restriction_policy(policy, result, data)
        elif policy.policy_type == PolicyType.FREQUENCY_RESTRICTION:
            await self._enforce_frequency_restriction_policy(policy, result, context)
        # Add more policy types as needed
    
    async def _enforce_transaction_limit_policy(self, policy: TransactionPolicy, result: SecurityResult, data: Dict[str, Any]) -> None:
        """Enforce transaction limit policy"""
        max_value_usd = policy.parameters.get("max_value_usd", float('inf'))
        amount = data.get("amount", 0)
        
        # TODO: Convert amount to USD for comparison
        # For now, assume direct comparison
        if amount > max_value_usd:
            result.violations.append(
                f"Transaction exceeds policy limit: {amount} > {max_value_usd}"
            )
    
    async def _enforce_amount_restriction_policy(self, policy: TransactionPolicy, result: SecurityResult, data: Dict[str, Any]) -> None:
        """Enforce amount restriction policy"""
        min_amount = policy.parameters.get("min_amount", 0)
        max_amount = policy.parameters.get("max_amount", float('inf'))
        amount = data.get("amount", 0)
        
        if amount < min_amount:
            result.violations.append(f"Amount {amount} below minimum {min_amount}")
        
        if amount > max_amount:
            result.violations.append(f"Amount {amount} exceeds maximum {max_amount}")
    
    async def _enforce_frequency_restriction_policy(self, policy: TransactionPolicy, result: SecurityResult, context: Dict[str, Any]) -> None:
        """Enforce frequency restriction policy"""
        max_operations_per_hour = policy.parameters.get("max_operations_per_hour", 100)
        agent_id = context.get("agent_id", "unknown")
        
        # Track activity
        if agent_id not in self.suspicious_activities:
            self.suspicious_activities[agent_id] = []
        
        # Clean old activities
        one_hour_ago = datetime.now() - timedelta(hours=1)
        self.suspicious_activities[agent_id] = [
            activity for activity in self.suspicious_activities[agent_id]
            if activity > one_hour_ago
        ]
        
        # Check frequency
        if len(self.suspicious_activities[agent_id]) >= max_operations_per_hour:
            result.violations.append(
                f"Frequency limit exceeded: {len(self.suspicious_activities[agent_id])} operations in last hour"
            )
        
        # Add current activity
        self.suspicious_activities[agent_id].append(datetime.now())
    
    async def _check_suspicious_patterns(self, result: SecurityResult, data: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Check for suspicious transaction patterns"""
        # Round number amounts (potential bot activity)
        amount = data.get("amount", 0)
        if amount > 0 and amount == int(amount) and amount % 10 == 0:
            result.recommendations.append("Round number amount detected - possible automated activity")
        
        # Rapid succession of identical transactions
        # TODO: Implement transaction history tracking
        
        # Unusual token combinations
        token_from = data.get("token_from", "").upper()
        token_to = data.get("token_to", "").upper()
        
        if token_from == token_to:
            result.violations.append("Cannot swap token to itself")
    
    def _get_risk_threshold(self) -> float:
        """Get risk threshold based on security level"""
        thresholds = {
            SecurityLevel.LOW: 90.0,
            SecurityLevel.MEDIUM: 70.0,
            SecurityLevel.HIGH: 50.0,
            SecurityLevel.CRITICAL: 30.0
        }
        return thresholds.get(self.security_level, 70.0)
    
    def add_policy(self, policy: TransactionPolicy) -> None:
        """Add a new security policy"""
        self.policies.append(policy)
        logger.info(f"Added security policy: {policy.name}")
    
    def remove_policy(self, policy_id: str) -> bool:
        """Remove a security policy"""
        for i, policy in enumerate(self.policies):
            if policy.id == policy_id:
                del self.policies[i]
                logger.info(f"Removed security policy: {policy.name}")
                return True
        return False
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics"""
        return {
            "security_level": self.security_level.value,
            "active_policies": len([p for p in self.policies if p.enabled]),
            "blocked_ips": len(self.blocked_ips),
            "allowed_ips": len(self.allowed_ips),
            "suspicious_activities": len(self.suspicious_activities),
            "recent_events": len(self.audit_logger.events)
        }
    
    async def generate_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        recent_events = self.audit_logger.get_events(
            start_time=datetime.now() - timedelta(days=1)
        )
        
        return {
            "timestamp": datetime.now().isoformat(),
            "security_level": self.security_level.value,
            "policies": [
                {
                    "name": p.name,
                    "type": p.policy_type.value,
                    "enabled": p.enabled
                }
                for p in self.policies
            ],
            "metrics": self.get_security_metrics(),
            "recent_events": [
                {
                    "type": e.event_type,
                    "severity": e.severity,
                    "message": e.message,
                    "timestamp": e.timestamp.isoformat()
                }
                for e in recent_events[-10:]  # Last 10 events
            ]
        }


# Factory functions for common security configurations
def create_development_security() -> SecurityManager:
    """Create development security configuration"""
    return SecurityManager(
        security_level=SecurityLevel.LOW,
        policies=[
            TransactionPolicy(
                id="dev_limits",
                name="Development Limits",
                policy_type=PolicyType.TRANSACTION_LIMIT,
                parameters={"max_value_usd": 100},
                description="Low limits for development"
            )
        ]
    )


def create_production_security() -> SecurityManager:
    """Create production security configuration"""
    return SecurityManager(
        security_level=SecurityLevel.HIGH,
        policies=[
            TransactionPolicy(
                id="prod_limits",
                name="Production Limits",
                policy_type=PolicyType.TRANSACTION_LIMIT,
                parameters={"max_value_usd": 10000},
                description="Production transaction limits"
            ),
            TransactionPolicy(
                id="prod_frequency",
                name="Production Frequency Limits",
                policy_type=PolicyType.FREQUENCY_RESTRICTION,
                parameters={"max_operations_per_hour": 50},
                description="Production frequency limits"
            )
        ]
    )
