from typing import Any, Dict
import wolframalpha
from .base import SwarmBaseTool

class WolframAlphaTool(SwarmBaseTool):
    """Tool for complex mathematical computations using WolframAlpha."""
    
    name: str = "wolfram_alpha"
    description: str = "Solve complex mathematical problems, equations, and computations"
    
    def __init__(self, api_key: str):
        super().__init__()
        self.client = wolframalpha.Client(api_key)
        
    async def _arun(self, query: str) -> str:
        """Compute result using WolframAlpha."""
        res = self.client.query(query)
        try:
            return next(res.results).text
        except StopIteration:
            return "No results found"

class PythonCalculatorTool(SwarmBaseTool):
    """Tool for basic mathematical calculations using Python."""
    
    name: str = "calculator"
    description: str = "Perform basic mathematical calculations"
    
    async def _arun(self, expression: str) -> str:
        """Evaluate mathematical expression."""
        try:
            # Safely evaluate mathematical expression
            allowed_names = {"abs": abs, "round": round}
            code = compile(expression, "<string>", "eval")
            for name in code.co_names:
                if name not in allowed_names:
                    raise NameError(f"Use of {name} not allowed")
            return str(eval(code, {"__builtins__": {}}, allowed_names))
        except Exception as e:
            return f"Error: {str(e)}" 