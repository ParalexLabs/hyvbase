from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class TransactionMetrics:
    """Metrics for a single transaction"""
    timestamp: datetime
    transaction_type: str
    amount: float
    gas_used: float
    success: bool
    execution_time: float
    slippage: float = 0.0
    mev_protected: bool = True

class OperationAnalytics:
    """Analytics for tracking operations and performance"""
    
    def __init__(self):
        self.interactions: List[Dict[str, Any]] = []
        self.success_count: int = 0
        self.total_count: int = 0
        self.transactions: List[TransactionMetrics] = []
    
    def log_interaction(self, command: str, response: str, timestamp: datetime) -> None:
        """Log an interaction with the agent"""
        self.interactions.append({
            "command": command,
            "response": response,
            "timestamp": timestamp
        })
    
    def log_trade(self, success: bool) -> None:
        """Log a trade result"""
        self.total_count += 1
        if success:
            self.success_count += 1
    
    def log_transaction(self, metrics: TransactionMetrics) -> None:
        """Log a transaction with detailed metrics"""
        self.transactions.append(metrics)
        self.log_trade(metrics.success)
    
    def get_success_rate(self) -> float:
        """Get the success rate of trades"""
        if self.total_count == 0:
            return 0.0
        return self.success_count / self.total_count
    
    def get_recent_interactions(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent interactions"""
        return self.interactions[-limit:]
    
    def get_transaction_summary(self) -> Dict[str, Any]:
        """Get summary of all transactions"""
        if not self.transactions:
            return {
                "total_transactions": 0,
                "success_rate": 0.0,
                "average_gas": 0.0,
                "average_slippage": 0.0,
                "mev_protection_rate": 100.0
            }
        
        successful = [t for t in self.transactions if t.success]
        return {
            "total_transactions": len(self.transactions),
            "success_rate": len(successful) / len(self.transactions) * 100,
            "average_gas": sum(t.gas_used for t in self.transactions) / len(self.transactions),
            "average_slippage": sum(t.slippage for t in self.transactions) / len(self.transactions),
            "mev_protection_rate": sum(1 for t in self.transactions if t.mev_protected) / len(self.transactions) * 100
        }

__all__ = ['OperationAnalytics', 'TransactionMetrics'] 