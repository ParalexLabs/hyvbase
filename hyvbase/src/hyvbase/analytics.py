from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

@dataclass
class TransactionMetrics:
    timestamp: datetime
    operation: str
    success: bool
    gas_used: int
    duration: float
    error: Optional[str] = None

class OperationAnalytics:
    def __init__(self):
        self.metrics: List[TransactionMetrics] = []
        
    def add_metric(self, metric: TransactionMetrics):
        self.metrics.append(metric)
        
    def get_success_rate(self) -> float:
        if not self.metrics:
            return 0.0
        successful = sum(1 for m in self.metrics if m.success)
        return successful / len(self.metrics)
        
    def get_average_gas(self) -> float:
        if not self.metrics:
            return 0.0
        return sum(m.gas_used for m in self.metrics) / len(self.metrics) 