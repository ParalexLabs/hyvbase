"""Advanced Observability and Monitoring for HyvBase

Comprehensive monitoring, metrics collection, distributed tracing,
and alerting system for production-grade deployments.
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """Individual metric data point"""
    name: str
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OperationTrace:
    """Distributed tracing for operations"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: str = "pending"  # pending, success, error
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Real-time metrics collection and aggregation"""
    
    def __init__(self, max_metrics: int = 10000):
        self.metrics: deque = deque(maxlen=max_metrics)
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment counter metric"""
        with self._lock:
            key = self._create_key(name, tags)
            self.counters[key] += value
            self._store_metric(Metric(name, value, tags or {}))
    
    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Set gauge metric"""
        with self._lock:
            key = self._create_key(name, tags)
            self.gauges[key] = value
            self._store_metric(Metric(name, value, tags or {}))
    
    def histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record histogram value"""
        with self._lock:
            key = self._create_key(name, tags)
            self.histograms[key].append(value)
            self._store_metric(Metric(name, value, tags or {}))
    
    def timer(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record timing metric"""
        with self._lock:
            key = self._create_key(name, tags)
            self.timers[key].append(duration)
            self._store_metric(Metric(name, duration, tags or {}))
    
    def _create_key(self, name: str, tags: Optional[Dict[str, str]]) -> str:
        """Create unique key for metric"""
        if not tags:
            return name
        
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}:{tag_str}"
    
    def _store_metric(self, metric: Metric) -> None:
        """Store metric in buffer"""
        self.metrics.append(metric)
    
    def get_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """Get counter value"""
        key = self._create_key(name, tags)
        return self.counters.get(key, 0.0)
    
    def get_gauge(self, name: str, tags: Optional[Dict[str, str]] = None) -> Optional[float]:
        """Get gauge value"""
        key = self._create_key(name, tags)
        return self.gauges.get(key)
    
    def get_histogram_stats(self, name: str, tags: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get histogram statistics"""
        key = self._create_key(name, tags)
        values = self.histograms.get(key, [])
        
        if not values:
            return {}
        
        sorted_values = sorted(values)
        length = len(sorted_values)
        
        return {
            "count": length,
            "min": min(sorted_values),
            "max": max(sorted_values),
            "mean": sum(sorted_values) / length,
            "p50": sorted_values[int(length * 0.5)],
            "p95": sorted_values[int(length * 0.95)],
            "p99": sorted_values[int(length * 0.99)]
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics summary"""
        with self._lock:
            return {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {k: self.get_histogram_stats("", {}) for k in self.histograms.keys()},
                "timers": {k: self.get_histogram_stats("", {}) for k in self.timers.keys()}
            }
    
    def reset(self) -> None:
        """Reset all metrics"""
        with self._lock:
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()
            self.timers.clear()
            self.metrics.clear()


class DistributedTracer:
    """Distributed tracing system"""
    
    def __init__(self, service_name: str, sample_rate: float = 0.1):
        self.service_name = service_name
        self.sample_rate = sample_rate
        self.active_traces: Dict[str, OperationTrace] = {}
        self.completed_traces: deque = deque(maxlen=1000)
        self._lock = threading.Lock()
    
    def start_trace(self, operation_name: str, parent_span_id: Optional[str] = None) -> OperationTrace:
        """Start a new trace"""
        import uuid
        
        trace = OperationTrace(
            trace_id=str(uuid.uuid4()),
            span_id=str(uuid.uuid4()),
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=datetime.now(),
            tags={"service": self.service_name}
        )
        
        with self._lock:
            self.active_traces[trace.span_id] = trace
        
        return trace
    
    def finish_trace(self, span_id: str, status: str = "success", error: Optional[str] = None) -> None:
        """Finish a trace"""
        with self._lock:
            trace = self.active_traces.pop(span_id, None)
            
            if trace:
                trace.end_time = datetime.now()
                trace.duration_ms = (trace.end_time - trace.start_time).total_seconds() * 1000
                trace.status = status
                
                if error:
                    trace.logs.append({
                        "level": "error",
                        "message": error,
                        "timestamp": datetime.now().isoformat()
                    })
                
                self.completed_traces.append(trace)
    
    def add_log(self, span_id: str, level: str, message: str, **kwargs) -> None:
        """Add log to trace"""
        with self._lock:
            trace = self.active_traces.get(span_id)
            if trace:
                trace.logs.append({
                    "level": level,
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                    **kwargs
                })
    
    def add_tag(self, span_id: str, key: str, value: str) -> None:
        """Add tag to trace"""
        with self._lock:
            trace = self.active_traces.get(span_id)
            if trace:
                trace.tags[key] = value
    
    def get_trace(self, span_id: str) -> Optional[OperationTrace]:
        """Get active trace"""
        return self.active_traces.get(span_id)
    
    def get_completed_traces(self, limit: int = 100) -> List[OperationTrace]:
        """Get completed traces"""
        with self._lock:
            return list(self.completed_traces)[-limit:]


class AlertManager:
    """Alert management and notification system"""
    
    def __init__(self):
        self.alert_rules: List[Dict[str, Any]] = []
        self.alert_channels: List[Callable] = []
        self.alert_history: deque = deque(maxlen=1000)
        self.suppression_rules: Dict[str, datetime] = {}
    
    def add_alert_rule(self, name: str, condition: Callable[[Dict[str, Any]], bool], 
                      severity: str = "warning", cooldown_minutes: int = 5) -> None:
        """Add alert rule"""
        self.alert_rules.append({
            "name": name,
            "condition": condition,
            "severity": severity,
            "cooldown_minutes": cooldown_minutes
        })
    
    def add_alert_channel(self, channel: Callable[[Dict[str, Any]], None]) -> None:
        """Add alert notification channel"""
        self.alert_channels.append(channel)
    
    async def check_alerts(self, metrics: Dict[str, Any]) -> None:
        """Check alert conditions and trigger notifications"""
        current_time = datetime.now()
        
        for rule in self.alert_rules:
            try:
                # Check suppression
                suppression_key = f"{rule['name']}"
                if suppression_key in self.suppression_rules:
                    if current_time < self.suppression_rules[suppression_key]:
                        continue  # Still in cooldown
                
                # Check condition
                if rule["condition"](metrics):
                    alert = {
                        "name": rule["name"],
                        "severity": rule["severity"],
                        "message": f"Alert triggered: {rule['name']}",
                        "timestamp": current_time.isoformat(),
                        "metrics": metrics
                    }
                    
                    # Send notifications
                    await self._send_alert(alert)
                    
                    # Add to history
                    self.alert_history.append(alert)
                    
                    # Set suppression
                    self.suppression_rules[suppression_key] = (
                        current_time + timedelta(minutes=rule["cooldown_minutes"])
                    )
                    
            except Exception as e:
                logger.error(f"Error checking alert rule {rule['name']}: {e}")
    
    async def _send_alert(self, alert: Dict[str, Any]) -> None:
        """Send alert through all channels"""
        for channel in self.alert_channels:
            try:
                if asyncio.iscoroutinefunction(channel):
                    await channel(alert)
                else:
                    channel(alert)
            except Exception as e:
                logger.error(f"Error sending alert through channel: {e}")


class HealthChecker:
    """Health check system"""
    
    def __init__(self):
        self.health_checks: Dict[str, Callable] = {}
        self.health_status: Dict[str, Dict[str, Any]] = {}
        self.last_check_time: Dict[str, datetime] = {}
    
    def register_health_check(self, name: str, check_func: Callable) -> None:
        """Register a health check"""
        self.health_checks[name] = check_func
    
    async def run_health_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        overall_status = "healthy"
        results = {}
        
        for name, check_func in self.health_checks.items():
            try:
                start_time = time.time()
                
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                
                execution_time = (time.time() - start_time) * 1000
                
                if isinstance(result, bool):
                    status = "healthy" if result else "unhealthy"
                    details = {}
                elif isinstance(result, dict):
                    status = result.get("status", "healthy")
                    details = result.get("details", {})
                else:
                    status = "healthy"
                    details = {"result": str(result)}
                
                results[name] = {
                    "status": status,
                    "execution_time_ms": execution_time,
                    "details": details,
                    "timestamp": datetime.now().isoformat()
                }
                
                if status != "healthy":
                    overall_status = "unhealthy"
                
                self.health_status[name] = results[name]
                self.last_check_time[name] = datetime.now()
                
            except Exception as e:
                results[name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                overall_status = "unhealthy"
        
        return {
            "status": overall_status,
            "checks": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        return {
            "status": self.health_status,
            "last_check_times": {
                name: time.isoformat() for name, time in self.last_check_time.items()
            }
        }


class ObservabilityManager:
    """Comprehensive observability management"""
    
    def __init__(self, agent_id: str, agent_name: str, config: Optional[Dict[str, Any]] = None):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.config = config or {}
        
        # Initialize components
        self.metrics = MetricsCollector()
        self.tracer = DistributedTracer(service_name=f"hyvbase-{agent_name}")
        self.alerts = AlertManager()
        self.health = HealthChecker()
        
        # Performance tracking
        self.operation_times: Dict[str, List[float]] = defaultdict(list)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.success_counts: Dict[str, int] = defaultdict(int)
        
        # Setup default alerts
        self._setup_default_alerts()
        
        # Setup default health checks
        self._setup_default_health_checks()
        
        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
    
    def _setup_default_alerts(self) -> None:
        """Setup default alert rules"""
        # High error rate alert
        self.alerts.add_alert_rule(
            name="high_error_rate",
            condition=lambda m: self._calculate_error_rate() > 0.1,  # 10% error rate
            severity="warning",
            cooldown_minutes=5
        )
        
        # Slow operation alert
        self.alerts.add_alert_rule(
            name="slow_operations",
            condition=lambda m: self._get_avg_operation_time() > 30000,  # 30 seconds
            severity="warning",
            cooldown_minutes=10
        )
        
        # Memory usage alert (placeholder)
        self.alerts.add_alert_rule(
            name="high_memory_usage",
            condition=lambda m: False,  # TODO: Implement memory monitoring
            severity="critical",
            cooldown_minutes=15
        )
    
    def _setup_default_health_checks(self) -> None:
        """Setup default health checks"""
        # Basic connectivity check
        self.health.register_health_check(
            "agent_status",
            lambda: {"status": "healthy", "details": {"agent_id": self.agent_id}}
        )
        
        # Metrics collection check
        self.health.register_health_check(
            "metrics_collection",
            lambda: len(self.metrics.metrics) > 0
        )
    
    async def track_operation_start(self, operation_id: str, operation_type: str, 
                                  input_data: Any, context: Optional[Dict[str, Any]] = None) -> OperationTrace:
        """Track operation start"""
        # Create trace
        trace = self.tracer.start_trace(f"{operation_type}_{operation_id}")
        
        # Add tags
        self.tracer.add_tag(trace.span_id, "operation_id", operation_id)
        self.tracer.add_tag(trace.span_id, "operation_type", operation_type)
        self.tracer.add_tag(trace.span_id, "agent_id", self.agent_id)
        
        # Record metrics
        self.metrics.counter(f"operations.{operation_type}.started", tags={"agent_id": self.agent_id})
        
        # Log
        self.tracer.add_log(
            trace.span_id, 
            "info", 
            f"Operation {operation_type} started",
            operation_id=operation_id
        )
        
        return trace
    
    async def track_operation_complete(self, operation_id: str, success: bool, 
                                     execution_time: float, response: Any) -> None:
        """Track operation completion"""
        # Find trace by operation_id (simplified - in real implementation, maintain mapping)
        # For now, we'll create a new metric entry
        
        operation_type = "unknown"  # In real implementation, maintain operation context
        
        # Record metrics
        if success:
            self.metrics.counter(f"operations.{operation_type}.success", tags={"agent_id": self.agent_id})
            self.success_counts[operation_type] += 1
        else:
            self.metrics.counter(f"operations.{operation_type}.error", tags={"agent_id": self.agent_id})
            self.error_counts[operation_type] += 1
        
        # Record timing
        self.metrics.timer(f"operations.{operation_type}.duration", execution_time * 1000, 
                          tags={"agent_id": self.agent_id})
        self.operation_times[operation_type].append(execution_time * 1000)
        
        # Keep only recent operation times
        if len(self.operation_times[operation_type]) > 100:
            self.operation_times[operation_type] = self.operation_times[operation_type][-100:]
    
    async def track_operation_error(self, operation_id: str, error: str, execution_time: float) -> None:
        """Track operation error"""
        # Record error metrics
        self.metrics.counter("operations.error", tags={
            "agent_id": self.agent_id,
            "error_type": type(error).__name__ if isinstance(error, Exception) else "unknown"
        })
        
        # Record timing even for errors
        self.metrics.timer("operations.error.duration", execution_time * 1000, 
                          tags={"agent_id": self.agent_id})
    
    def _calculate_error_rate(self) -> float:
        """Calculate current error rate"""
        total_success = sum(self.success_counts.values())
        total_errors = sum(self.error_counts.values())
        total_operations = total_success + total_errors
        
        if total_operations == 0:
            return 0.0
        
        return total_errors / total_operations
    
    def _get_avg_operation_time(self) -> float:
        """Get average operation time across all operations"""
        all_times = []
        for times in self.operation_times.values():
            all_times.extend(times)
        
        if not all_times:
            return 0.0
        
        return sum(all_times) / len(all_times)
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics"""
        base_metrics = self.metrics.get_all_metrics()
        
        # Add derived metrics
        base_metrics["derived"] = {
            "error_rate": self._calculate_error_rate(),
            "avg_operation_time_ms": self._get_avg_operation_time(),
            "total_operations": sum(self.success_counts.values()) + sum(self.error_counts.values()),
            "active_traces": len(self.tracer.active_traces),
            "completed_traces": len(self.tracer.completed_traces)
        }
        
        return base_metrics
    
    async def start_monitoring(self) -> None:
        """Start background monitoring tasks"""
        # Metrics collection task
        self._background_tasks.append(
            asyncio.create_task(self._metrics_collection_loop())
        )
        
        # Alert checking task
        self._background_tasks.append(
            asyncio.create_task(self._alert_checking_loop())
        )
        
        # Health check task
        self._background_tasks.append(
            asyncio.create_task(self._health_check_loop())
        )
    
    async def _metrics_collection_loop(self) -> None:
        """Background metrics collection"""
        while not self._shutdown_event.is_set():
            try:
                # Collect system metrics
                # TODO: Add system resource monitoring
                
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(30)
    
    async def _alert_checking_loop(self) -> None:
        """Background alert checking"""
        while not self._shutdown_event.is_set():
            try:
                metrics = await self.get_metrics()
                await self.alerts.check_alerts(metrics)
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alert checking loop: {e}")
                await asyncio.sleep(60)
    
    async def _health_check_loop(self) -> None:
        """Background health checking"""
        while not self._shutdown_event.is_set():
            try:
                await self.health.run_health_checks()
                
                await asyncio.sleep(120)  # Check every 2 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(120)
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        metrics = await self.get_metrics()
        health_status = await self.health.run_health_checks()
        recent_traces = self.tracer.get_completed_traces(20)
        
        return {
            "agent_info": {
                "agent_id": self.agent_id,
                "agent_name": self.agent_name,
                "uptime": "unknown"  # TODO: Track uptime
            },
            "metrics": metrics,
            "health": health_status,
            "traces": [
                {
                    "trace_id": trace.trace_id,
                    "operation_name": trace.operation_name,
                    "duration_ms": trace.duration_ms,
                    "status": trace.status,
                    "timestamp": trace.start_time.isoformat()
                }
                for trace in recent_traces
            ],
            "alerts": list(self.alerts.alert_history)[-10:],  # Last 10 alerts
            "timestamp": datetime.now().isoformat()
        }
    
    async def export_metrics(self, format: str = "prometheus") -> str:
        """Export metrics in specified format"""
        metrics = await self.get_metrics()
        
        if format == "prometheus":
            return self._export_prometheus_format(metrics)
        elif format == "json":
            return json.dumps(metrics, default=str, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_prometheus_format(self, metrics: Dict[str, Any]) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        # Counters
        for name, value in metrics.get("counters", {}).items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        
        # Gauges
        for name, value in metrics.get("gauges", {}).items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        
        return "\n".join(lines)
    
    async def shutdown(self) -> None:
        """Shutdown observability manager"""
        self._shutdown_event.set()
        
        # Cancel background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        logger.info(f"Observability manager for {self.agent_name} shut down")


# Utility functions for common observability patterns
def create_timer_context(metrics_collector: MetricsCollector, metric_name: str, 
                        tags: Optional[Dict[str, str]] = None):
    """Context manager for timing operations"""
    class TimerContext:
        def __init__(self):
            self.start_time = None
        
        def __enter__(self):
            self.start_time = time.time()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.start_time:
                duration = (time.time() - self.start_time) * 1000
                metrics_collector.timer(metric_name, duration, tags)
    
    return TimerContext()


async def trace_async_operation(tracer: DistributedTracer, operation_name: str):
    """Decorator for tracing async operations"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            trace = tracer.start_trace(operation_name)
            try:
                result = await func(*args, **kwargs)
                tracer.finish_trace(trace.span_id, "success")
                return result
            except Exception as e:
                tracer.finish_trace(trace.span_id, "error", str(e))
                raise
        return wrapper
    return decorator
