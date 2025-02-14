from typing import Optional, Dict, Any
from langchain_community.utilities import GoogleSearchAPIWrapper, WikipediaAPIWrapper
from langchain.tools import Tool
from .base import SwarmBaseTool

class GoogleSearchTool(SwarmBaseTool):
    """Tool for performing Google searches."""
    
    name: str = "google_search"
    description: str = "Search Google for recent results on a given query"
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__()
        self.search = GoogleSearchAPIWrapper(google_api_key=api_key)
        
    async def _arun(self, query: str) -> str:
        """Run Google search asynchronously."""
        return await self.search.arun(query)

class DuckDuckGoTool(SwarmBaseTool):
    """Tool for performing DuckDuckGo searches."""
    
    name: str = "duckduckgo_search"
    description: str = "Search DuckDuckGo for web results on a given query"
    
    async def _arun(self, query: str) -> str:
        """Run DuckDuckGo search asynchronously."""
        from duckduckgo_search import ddg
        results = await ddg(query, max_results=5)
        return "\n".join(f"{r['title']}: {r['link']}" for r in results)

class WikipediaSearchTool(SwarmBaseTool):
    """Tool for searching Wikipedia articles."""
    
    name: str = "wikipedia"
    description: str = "Search Wikipedia articles for detailed information"
    
    def __init__(self):
        super().__init__()
        self.wiki = WikipediaAPIWrapper()
        
    async def _arun(self, query: str) -> str:
        """Search Wikipedia asynchronously."""
        return await self.wiki.arun(query)

class ArxivSearchTool(SwarmBaseTool):
    """Tool for searching academic papers on arXiv."""
    
    name: str = "arxiv"
    description: str = "Search academic papers on arXiv for scientific research"
    
    async def _arun(self, query: str) -> str:
        """Search arXiv asynchronously."""
        import arxiv
        search = arxiv.Search(query=query, max_results=5)
        results = await search.get()
        return "\n\n".join(
            f"Title: {r.title}\nAuthors: {', '.join(r.authors)}\nURL: {r.pdf_url}"
            for r in results
        ) 