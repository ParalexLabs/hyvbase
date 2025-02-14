from typing import List, Type
from langchain.tools import BaseTool

from .base import SwarmBaseTool
from .search import (
    GoogleSearchTool,
    DuckDuckGoTool,
    WikipediaSearchTool,
    ArxivSearchTool
)
from .social import (
    TwitterTool,
    TelegramTool
)
from .crypto import (
    StarknetTool,
    StarknetDEXTool,
    # SolanaTool,
    # SolanaSPLTool,
    # SolanaMarketTool,
)
# Temporarily comment out Solana imports until we fix the dependencies
# from .crypto.solana import SolanaTool, SolanaSPLTool, SolanaMarketTool

def get_all_tools() -> List[Type[BaseTool]]:
    """Get all available tools."""
    return [
        GoogleSearchTool(),
        DuckDuckGoTool(),
        WikipediaSearchTool(),
        ArxivSearchTool(),
        TwitterTool(),
        TelegramTool(),
        # Note: StarknetTool and StarknetDEXTool need to be instantiated with parameters
        # They should be instantiated where needed, not here
    ]

__all__ = [
    "SwarmBaseTool",
    "GoogleSearchTool",
    "DuckDuckGoTool",
    "WikipediaSearchTool",
    "ArxivSearchTool",
    "TwitterTool",
    "TelegramTool",
    "StarknetTool",
    "StarknetDEXTool",
    # Temporarily comment out Solana tools
    # "SolanaTool",
    # "SolanaSPLTool",
    # "SolanaMarketTool",
    "get_all_tools"
] 