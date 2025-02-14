from typing import Optional, Dict, Any, List
from github import Github, GithubException
from langchain.tools import BaseTool
from ..base import SwarmBaseTool

class GitHubTool(SwarmBaseTool):
    """Tool for GitHub interactions based on LangChain's GitHubAPIWrapper."""
    
    name: str = "github"
    description: str = "Interact with GitHub repositories, issues, and pull requests"
    
    def __init__(self, access_token: str):
        super().__init__()
        self.client = Github(access_token)
        
    async def _arun(self, command: str) -> str:
        """Execute GitHub operations."""
        try:
            cmd_parts = command.split(" ", 2)
            action = cmd_parts[0]
            
            if action == "search":
                query = cmd_parts[1]
                return await self.search_repositories(query)
                
            elif action == "create_issue":
                repo_name, title_and_body = cmd_parts[1], cmd_parts[2].split("|")
                return await self.create_issue(repo_name, title_and_body[0], title_and_body[1])
                
            elif action == "list_pulls":
                repo_name = cmd_parts[1]
                return await self.list_pull_requests(repo_name)
                
            else:
                return f"Unknown action: {action}"
        except Exception as e:
            return f"Error: {str(e)}"
            
    async def search_repositories(
        self,
        query: str,
        sort: str = "stars",
        order: str = "desc"
    ) -> List[Dict]:
        """Search GitHub repositories."""
        try:
            repos = self.client.search_repositories(
                query=query,
                sort=sort,
                order=order
            )
            return [
                {
                    "name": repo.full_name,
                    "description": repo.description,
                    "stars": repo.stargazers_count,
                    "url": repo.html_url
                }
                for repo in repos[:5]
            ]
        except GithubException as e:
            return f"Search failed: {str(e)}"

    async def create_issue(
        self,
        repo_name: str,
        title: str,
        body: str,
        labels: Optional[List[str]] = None
    ) -> str:
        """Create a new issue in a repository."""
        try:
            repo = self.client.get_repo(repo_name)
            issue = repo.create_issue(
                title=title,
                body=body,
                labels=labels
            )
            return f"Issue created: {issue.html_url}"
        except GithubException as e:
            return f"Failed to create issue: {str(e)}" 