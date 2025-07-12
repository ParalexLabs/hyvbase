"""Workflow Engine for HyvBase

Visual workflow creation and execution system for complex multi-step operations.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from .types import WorkflowDefinition, Workflow, WorkflowStep, AgentResponse

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class StepStatus(Enum):
    """Workflow step status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowExecutionContext:
    """Workflow execution context"""
    workflow_id: str
    variables: Dict[str, Any] = field(default_factory=dict)
    step_results: Dict[str, Any] = field(default_factory=dict)
    error_count: int = 0
    retry_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class WorkflowEngine:
    """Workflow execution engine"""
    
    def __init__(self):
        self.workflows: Dict[str, Workflow] = {}
        self.definitions: Dict[str, WorkflowDefinition] = {}
        self.active_executions: Dict[str, asyncio.Task] = {}
        self.step_handlers: Dict[str, Callable] = {}
        
        # Built-in step handlers
        self._register_builtin_handlers()
    
    def _register_builtin_handlers(self) -> None:
        """Register built-in step handlers"""
        self.step_handlers.update({
            "delay": self._handle_delay_step,
            "condition": self._handle_condition_step,
            "loop": self._handle_loop_step,
            "parallel": self._handle_parallel_step,
            "http_request": self._handle_http_request_step,
            "crypto_trade": self._handle_crypto_trade_step,
            "social_post": self._handle_social_post_step,
        })
    
    def register_step_handler(self, step_type: str, handler: Callable) -> None:
        """Register custom step handler"""
        self.step_handlers[step_type] = handler
        logger.info(f"Registered step handler: {step_type}")
    
    def create_workflow_definition(self, 
                                 name: str,
                                 description: str,
                                 steps: List[Dict[str, Any]],
                                 triggers: List[str] = None,
                                 variables: Dict[str, Any] = None) -> WorkflowDefinition:
        """Create workflow definition"""
        workflow_id = str(uuid.uuid4())
        
        # Convert step dictionaries to WorkflowStep objects
        workflow_steps = []
        for step_data in steps:
            step = WorkflowStep(
                id=step_data.get("id", str(uuid.uuid4())),
                name=step_data["name"],
                tool=step_data["tool"],
                parameters=step_data.get("parameters", {}),
                conditions=step_data.get("conditions", {}),
                retry_policy=step_data.get("retry_policy", {})
            )
            workflow_steps.append(step)
        
        definition = WorkflowDefinition(
            id=workflow_id,
            name=name,
            description=description,
            steps=workflow_steps,
            triggers=triggers or [],
            variables=variables or {}
        )
        
        self.definitions[workflow_id] = definition
        return definition
    
    async def execute_workflow(self, definition_id: str, 
                             input_variables: Dict[str, Any] = None) -> Workflow:
        """Execute workflow from definition"""
        definition = self.definitions.get(definition_id)
        if not definition:
            raise ValueError(f"Workflow definition {definition_id} not found")
        
        # Create workflow instance
        workflow = Workflow(
            id=str(uuid.uuid4()),
            definition=definition,
            status=WorkflowStatus.PENDING.value,
            variables=input_variables or {}
        )
        
        self.workflows[workflow.id] = workflow
        
        # Start execution
        execution_task = asyncio.create_task(
            self._execute_workflow_async(workflow)
        )
        self.active_executions[workflow.id] = execution_task
        
        return workflow
    
    async def _execute_workflow_async(self, workflow: Workflow) -> None:
        """Execute workflow asynchronously"""
        context = WorkflowExecutionContext(
            workflow_id=workflow.id,
            variables=workflow.variables.copy(),
            started_at=datetime.now()
        )
        
        try:
            workflow.status = WorkflowStatus.RUNNING.value
            workflow.started_at = context.started_at
            
            logger.info(f"Starting workflow execution: {workflow.definition.name}")
            
            # Execute steps sequentially
            for i, step in enumerate(workflow.definition.steps):
                workflow.current_step = i
                
                try:
                    # Check conditions
                    if not await self._check_step_conditions(step, context):
                        logger.info(f"Skipping step {step.name} due to conditions")
                        continue
                    
                    # Execute step
                    result = await self._execute_step(step, context)
                    
                    # Store result
                    context.step_results[step.id] = result
                    workflow.results.append(result)
                    
                    logger.info(f"Completed step: {step.name}")
                    
                except Exception as e:
                    logger.error(f"Step {step.name} failed: {e}")
                    
                    # Handle retry logic
                    max_retries = step.retry_policy.get("max_retries", 0)
                    if context.retry_count < max_retries:
                        context.retry_count += 1
                        logger.info(f"Retrying step {step.name} ({context.retry_count}/{max_retries})")
                        # Retry the same step
                        i -= 1
                        continue
                    else:
                        # Step failed permanently
                        workflow.status = WorkflowStatus.FAILED.value
                        workflow.error = str(e)
                        workflow.completed_at = datetime.now()
                        return
            
            # Workflow completed successfully
            workflow.status = WorkflowStatus.COMPLETED.value
            workflow.completed_at = datetime.now()
            context.completed_at = workflow.completed_at
            
            logger.info(f"Workflow completed: {workflow.definition.name}")
            
        except asyncio.CancelledError:
            workflow.status = WorkflowStatus.CANCELLED.value
            workflow.completed_at = datetime.now()
            logger.info(f"Workflow cancelled: {workflow.definition.name}")
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED.value
            workflow.error = str(e)
            workflow.completed_at = datetime.now()
            logger.error(f"Workflow failed: {workflow.definition.name} - {e}")
        
        finally:
            # Cleanup
            if workflow.id in self.active_executions:
                del self.active_executions[workflow.id]
    
    async def _check_step_conditions(self, step: WorkflowStep, context: WorkflowExecutionContext) -> bool:
        """Check if step conditions are met"""
        if not step.conditions:
            return True
        
        # Simple condition evaluation
        for condition_type, condition_value in step.conditions.items():
            if condition_type == "variable_equals":
                var_name = condition_value["variable"]
                expected_value = condition_value["value"]
                actual_value = context.variables.get(var_name)
                if actual_value != expected_value:
                    return False
            
            elif condition_type == "previous_step_success":
                previous_step_id = condition_value
                previous_result = context.step_results.get(previous_step_id)
                if not previous_result or not previous_result.get("success", False):
                    return False
        
        return True
    
    async def _execute_step(self, step: WorkflowStep, context: WorkflowExecutionContext) -> Dict[str, Any]:
        """Execute individual step"""
        logger.info(f"Executing step: {step.name} ({step.tool})")
        
        # Get step handler
        handler = self.step_handlers.get(step.tool)
        if not handler:
            raise ValueError(f"No handler found for step tool: {step.tool}")
        
        # Execute step with handler
        try:
            result = await handler(step, context)
            return {
                "success": True,
                "result": result,
                "step_id": step.id,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "step_id": step.id,
                "timestamp": datetime.now().isoformat()
            }
    
    # Built-in step handlers
    async def _handle_delay_step(self, step: WorkflowStep, context: WorkflowExecutionContext) -> Any:
        """Handle delay step"""
        delay_seconds = step.parameters.get("seconds", 1)
        await asyncio.sleep(delay_seconds)
        return f"Delayed for {delay_seconds} seconds"
    
    async def _handle_condition_step(self, step: WorkflowStep, context: WorkflowExecutionContext) -> Any:
        """Handle conditional logic step"""
        condition = step.parameters.get("condition")
        true_action = step.parameters.get("true_action")
        false_action = step.parameters.get("false_action")
        
        # Evaluate condition (simplified)
        condition_result = eval(condition, {"context": context})
        
        if condition_result:
            return true_action
        else:
            return false_action
    
    async def _handle_loop_step(self, step: WorkflowStep, context: WorkflowExecutionContext) -> Any:
        """Handle loop step"""
        items = step.parameters.get("items", [])
        sub_steps = step.parameters.get("steps", [])
        results = []
        
        for item in items:
            # Set loop variable
            context.variables["loop_item"] = item
            
            # Execute sub-steps
            for sub_step_data in sub_steps:
                sub_step = WorkflowStep(
                    id=str(uuid.uuid4()),
                    name=sub_step_data["name"],
                    tool=sub_step_data["tool"],
                    parameters=sub_step_data.get("parameters", {})
                )
                sub_result = await self._execute_step(sub_step, context)
                results.append(sub_result)
        
        return results
    
    async def _handle_parallel_step(self, step: WorkflowStep, context: WorkflowExecutionContext) -> Any:
        """Handle parallel execution step"""
        sub_steps_data = step.parameters.get("steps", [])
        
        # Create sub-steps
        sub_steps = []
        for sub_step_data in sub_steps_data:
            sub_step = WorkflowStep(
                id=str(uuid.uuid4()),
                name=sub_step_data["name"],
                tool=sub_step_data["tool"],
                parameters=sub_step_data.get("parameters", {})
            )
            sub_steps.append(sub_step)
        
        # Execute in parallel
        tasks = [self._execute_step(sub_step, context) for sub_step in sub_steps]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    async def _handle_http_request_step(self, step: WorkflowStep, context: WorkflowExecutionContext) -> Any:
        """Handle HTTP request step"""
        import aiohttp
        
        url = step.parameters.get("url")
        method = step.parameters.get("method", "GET")
        headers = step.parameters.get("headers", {})
        data = step.parameters.get("data")
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, json=data) as response:
                result = await response.json()
                return {
                    "status": response.status,
                    "data": result
                }
    
    async def _handle_crypto_trade_step(self, step: WorkflowStep, context: WorkflowExecutionContext) -> Any:
        """Handle crypto trading step"""
        # This would integrate with the actual crypto tools
        action = step.parameters.get("action")  # buy, sell, swap
        token_from = step.parameters.get("token_from")
        token_to = step.parameters.get("token_to")
        amount = step.parameters.get("amount")
        
        # Placeholder implementation
        return {
            "action": action,
            "token_from": token_from,
            "token_to": token_to,
            "amount": amount,
            "status": "simulated"
        }
    
    async def _handle_social_post_step(self, step: WorkflowStep, context: WorkflowExecutionContext) -> Any:
        """Handle social media posting step"""
        platform = step.parameters.get("platform")  # twitter, telegram, discord
        content = step.parameters.get("content")
        
        # Placeholder implementation
        return {
            "platform": platform,
            "content": content,
            "status": "simulated"
        }
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow by ID"""
        return self.workflows.get(workflow_id)
    
    def get_workflow_status(self, workflow_id: str) -> Optional[str]:
        """Get workflow status"""
        workflow = self.workflows.get(workflow_id)
        return workflow.status if workflow else None
    
    def list_workflows(self) -> List[Workflow]:
        """List all workflows"""
        return list(self.workflows.values())
    
    def list_definitions(self) -> List[WorkflowDefinition]:
        """List all workflow definitions"""
        return list(self.definitions.values())
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel running workflow"""
        if workflow_id in self.active_executions:
            task = self.active_executions[workflow_id]
            task.cancel()
            
            # Update workflow status
            workflow = self.workflows.get(workflow_id)
            if workflow:
                workflow.status = WorkflowStatus.CANCELLED.value
                workflow.completed_at = datetime.now()
            
            return True
        return False
    
    async def pause_workflow(self, workflow_id: str) -> bool:
        """Pause workflow execution"""
        # TODO: Implement workflow pausing
        workflow = self.workflows.get(workflow_id)
        if workflow:
            workflow.status = WorkflowStatus.PAUSED.value
            return True
        return False
    
    async def resume_workflow(self, workflow_id: str) -> bool:
        """Resume paused workflow"""
        # TODO: Implement workflow resuming
        workflow = self.workflows.get(workflow_id)
        if workflow and workflow.status == WorkflowStatus.PAUSED.value:
            workflow.status = WorkflowStatus.RUNNING.value
            return True
        return False
    
    def export_workflow_definition(self, definition_id: str) -> str:
        """Export workflow definition as JSON"""
        definition = self.definitions.get(definition_id)
        if not definition:
            raise ValueError(f"Workflow definition {definition_id} not found")
        
        # Convert to dictionary for JSON serialization
        definition_dict = {
            "id": definition.id,
            "name": definition.name,
            "description": definition.description,
            "steps": [
                {
                    "id": step.id,
                    "name": step.name,
                    "tool": step.tool,
                    "parameters": step.parameters,
                    "conditions": step.conditions,
                    "retry_policy": step.retry_policy
                }
                for step in definition.steps
            ],
            "triggers": definition.triggers,
            "variables": definition.variables,
            "metadata": definition.metadata
        }
        
        return json.dumps(definition_dict, indent=2)
    
    def import_workflow_definition(self, json_data: str) -> WorkflowDefinition:
        """Import workflow definition from JSON"""
        definition_dict = json.loads(json_data)
        
        # Convert step dictionaries back to WorkflowStep objects
        steps = []
        for step_data in definition_dict["steps"]:
            step = WorkflowStep(
                id=step_data["id"],
                name=step_data["name"],
                tool=step_data["tool"],
                parameters=step_data.get("parameters", {}),
                conditions=step_data.get("conditions", {}),
                retry_policy=step_data.get("retry_policy", {})
            )
            steps.append(step)
        
        definition = WorkflowDefinition(
            id=definition_dict["id"],
            name=definition_dict["name"],
            description=definition_dict["description"],
            steps=steps,
            triggers=definition_dict.get("triggers", []),
            variables=definition_dict.get("variables", {}),
            metadata=definition_dict.get("metadata", {})
        )
        
        self.definitions[definition.id] = definition
        return definition


# Workflow builder utilities
class WorkflowBuilder:
    """Fluent interface for building workflows"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.steps: List[Dict[str, Any]] = []
        self.variables: Dict[str, Any] = {}
        self.triggers: List[str] = []
    
    def add_step(self, name: str, tool: str, parameters: Dict[str, Any] = None, 
                conditions: Dict[str, Any] = None, retry_policy: Dict[str, Any] = None) -> 'WorkflowBuilder':
        """Add step to workflow"""
        step = {
            "id": str(uuid.uuid4()),
            "name": name,
            "tool": tool,
            "parameters": parameters or {},
            "conditions": conditions or {},
            "retry_policy": retry_policy or {}
        }
        self.steps.append(step)
        return self
    
    def add_delay(self, seconds: float, name: str = None) -> 'WorkflowBuilder':
        """Add delay step"""
        return self.add_step(
            name=name or f"Delay {seconds}s",
            tool="delay",
            parameters={"seconds": seconds}
        )
    
    def add_crypto_trade(self, action: str, token_from: str, token_to: str, amount: float, name: str = None) -> 'WorkflowBuilder':
        """Add crypto trading step"""
        return self.add_step(
            name=name or f"{action.title()} {amount} {token_from}",
            tool="crypto_trade",
            parameters={
                "action": action,
                "token_from": token_from,
                "token_to": token_to,
                "amount": amount
            }
        )
    
    def add_social_post(self, platform: str, content: str, name: str = None) -> 'WorkflowBuilder':
        """Add social media posting step"""
        return self.add_step(
            name=name or f"Post to {platform}",
            tool="social_post",
            parameters={
                "platform": platform,
                "content": content
            }
        )
    
    def add_condition(self, condition: str, true_action: Any, false_action: Any, name: str = None) -> 'WorkflowBuilder':
        """Add conditional step"""
        return self.add_step(
            name=name or "Conditional Logic",
            tool="condition",
            parameters={
                "condition": condition,
                "true_action": true_action,
                "false_action": false_action
            }
        )
    
    def set_variables(self, variables: Dict[str, Any]) -> 'WorkflowBuilder':
        """Set workflow variables"""
        self.variables.update(variables)
        return self
    
    def add_trigger(self, trigger: str) -> 'WorkflowBuilder':
        """Add workflow trigger"""
        self.triggers.append(trigger)
        return self
    
    def build(self, engine: WorkflowEngine) -> WorkflowDefinition:
        """Build workflow definition"""
        return engine.create_workflow_definition(
            name=self.name,
            description=self.description,
            steps=self.steps,
            triggers=self.triggers,
            variables=self.variables
        )


# Example workflow templates
def create_arbitrage_workflow(engine: WorkflowEngine) -> WorkflowDefinition:
    """Create arbitrage trading workflow"""
    return (WorkflowBuilder("Arbitrage Trading", "Automated arbitrage between DEXs")
            .add_step("Check Price Difference", "crypto_trade", {"action": "check_arbitrage"})
            .add_condition("price_diff > 0.01", "execute_arbitrage", "wait")
            .add_crypto_trade("buy", "ETH", "USDC", 1.0, "Buy ETH")
            .add_crypto_trade("sell", "ETH", "USDC", 1.0, "Sell ETH")
            .add_social_post("twitter", "Arbitrage opportunity executed!", "Tweet Success")
            .build(engine))


def create_social_campaign_workflow(engine: WorkflowEngine) -> WorkflowDefinition:
    """Create social media campaign workflow"""
    return (WorkflowBuilder("Social Campaign", "Automated social media campaign")
            .add_social_post("twitter", "🚀 New trading opportunity discovered!")
            .add_delay(3600)  # Wait 1 hour
            .add_social_post("telegram", "Updates available in our community channel")
            .add_delay(7200)  # Wait 2 hours
            .add_social_post("discord", "Join our discussion about market trends")
            .build(engine))
