from typing import Optional, Dict, Any
from .base import SwarmBaseTool

class PythonREPLTool(SwarmBaseTool):
    """Tool for executing Python code."""
    
    name: str = "python_repl"
    description: str = "Execute Python code and return the result"
    
    async def _arun(self, code: str) -> str:
        """Execute Python code in a safe environment."""
        try:
            # Create a restricted globals dictionary
            restricted_globals = {
                "__builtins__": {
                    name: getattr(__builtins__, name)
                    for name in ["abs", "all", "any", "len", "max", "min", "range", "round", "sum"]
                }
            }
            
            # Execute code in restricted environment
            local_dict = {}
            exec(code, restricted_globals, local_dict)
            
            # Get the last expression's value
            if "_" in local_dict:
                return str(local_dict["_"])
            return "Code executed successfully"
        except Exception as e:
            return f"Error: {str(e)}"

class GitHubTool(SwarmBaseTool):
    """Tool for interacting with GitHub repositories."""
    
    name: str = "github"
    description: str = "Search and interact with GitHub repositories"
    
    def __init__(self, access_token: Optional[str] = None):
        super().__init__()
        self.access_token = access_token
        
    async def _arun(self, query: str) -> str:
        """Search GitHub repositories."""
        from github import Github
        g = Github(self.access_token)
        
        try:
            repos = g.search_repositories(query, sort="stars", order="desc")
            return "\n".join(
                f"{repo.full_name}: {repo.description} (Stars: {repo.stargazers_count})"
                for repo in repos[:5]
            )
        except Exception as e:
            return f"Error: {str(e)}" 