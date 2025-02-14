from typing import Any, Dict, Optional
from langchain.tools import BaseTool as LangChainBaseTool
from pydantic import BaseModel, Field
from functools import wraps
from typing import Callable, TypeVar

class SwarmBaseTool(LangChainBaseTool):
    """Base class for all SwarmBase tools."""
    
    name: str = Field(description="The unique name of the tool")
    description: str = Field(description="Detailed description of what the tool does")
    
    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        """Async implementation of the tool."""
        raise NotImplementedError("Async run not implemented")

    def _run(self, *args: Any, **kwargs: Any) -> str:
        """Sync implementation of the tool."""
        raise NotImplementedError("Sync run not implemented")

T = TypeVar('T')

def handle_operation_errors(operation_name: str):
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_msg = f"{operation_name} failed: {str(e)}"
                return error_msg
        return wrapper
    return decorator 