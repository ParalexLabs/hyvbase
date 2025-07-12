"""Advanced Memory Management System for HyvBase

Supports multi-tier storage strategies including short-term buffer,
long-term VectorStore, in-memory cache, and permanent storage.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque

import numpy as np
from langchain_core.memory import BaseMemory
from vectrs.database import VectorDBManager, VectorDatabase
from vectrs.database.vectrbase import SimilarityMetric, IndexType

from .types import MemoryStrategy

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """Individual memory entry"""
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    expired: bool = False


class InMemoryCache:
    """Ultra-fast in-memory cache for recent operations"""
    
    def __init__(self, max_size: int = 1000):
        self.cache: deque = deque(maxlen=max_size)
        self._lock = asyncio.Lock()
    
    async def set(self, key: str, value: Any) -> None:
        """Set cache value"""
        async with self._lock:
            self.cache.appendleft((key, value))
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cache value"""
        async with self._lock:
            for cache_key, cache_value in self.cache:
                if cache_key == key:
                    return cache_value
        return None


class RedisMemory(BaseMemory):
    """Short-term memory using Redis"""
    
    def __init__(self, max_items: int = 1000, ttl: int = 3600):
        super().__init__(max_items)
        self.ttl = ttl
        self._store: Dict[str, MemoryEntry] = {}
        
    async def add(self, data: Dict[str, Any], **kwargs) -> None:
        """Add data to memory"""
        entry_id = f"entry_{str(len(self._store) + 1)}"
        self._store[entry_id] = MemoryEntry(datetime.now(), data)
        
        if len(self._store) > self.max_items:
            self._cleanup()
    
    async def query(self, query: str) -> List[Dict[str, Any]]:
        """Query memory"""
        # Very basic text search
        return [
            entry.data for entry in self._store.values()
            if query.lower() in str(entry.data).lower()
        ]
    
    def _cleanup(self):
        """Cleanup stale entries"""
        expired_items = len(self._store) - self.max_items
        if expired_items > 0:
            keys_to_remove = list(self._store.keys())[:expired_items]
            for key in keys_to_remove:
                del self._store[key]


class VectorMemory(BaseMemory):
    """Long-term memory using vector database"""
    
    def __init__(self):
        self.db_manager = VectorDBManager()
        self.chat_memory: VectorDatabase = self.db_manager.create_database(
            dim=1536, space=SimilarityMetric.COSINE, max_elements=100000, index_type=IndexType.HNSW
        )
    
    async def add(self, data: Dict[str, Any], embedding: np.ndarray, **kwargs) -> None:
        """Add data to vector memory with embedding"""
        entry_id = f"entry_{datetime.now().timestamp()}"
        self.chat_memory.add(embedding, entry_id, data)
    
    async def query(self, embedding: np.ndarray, k: int = 5) -> List[Dict[str, Any]]:
        """Query memory using semantic search"""
        labels, distances = self.chat_memory.knn_query(embedding, k=k)
        results = []
        for label in labels[0]:
            results.append(self.chat_memory.get_metadata(f"vector_{label}"))
        return results

    async def similarity_search(self, query_vector: np.ndarray, **kwargs) -> List[Dict[str, Any]]:
        """Similarity search in vector memory"""
        labels, distances = self.db_manager.query_database(self.chat_memory, query_vector, top_k=5)
        return [self.chat_memory.get_metadata(l) for l in labels]


class AdvancedMemoryManager:
    """Multi-tier memory management"""
    
    def __init__(self, strategy: MemoryStrategy = MemoryStrategy.HYBRID, ttl: int = 3600, max_size: int = 10000):
        self.strategy = strategy
        self.ttl = ttl
        self.max_size = max_size
        
        # Init storage layers
        self.cache = InMemoryCache(max_size=int(max_size * 0.1))
        self.redis_memory = RedisMemory(max_items=int(max_size * 0.3), ttl=ttl)
        self.vector_memory = VectorMemory()
        
        # Async cleanup task
        self._shutdown_event = asyncio.Event()
        self._background_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize memory manager"""
        self._background_task = asyncio.create_task(self._background_cleanup())
    
    async def store_interaction(self, input_data: Any, response: Any, context: Optional[Dict[str, Any]] = None) -> None:
        """Store an interaction in memory"""
        # Placeholder
        pass
    
    async def get_recent_interactions(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent interactions"""
        return []
    
    async def _background_cleanup(self) -> None:
        """Background cleanup task"""
        while not self._shutdown_event.is_set():
            await asyncio.sleep(self.ttl)
            
            # Perform cleanup operations
            # TODO: Implement actual cleanup logic
            logger.debug("Memory cleanup executed")
    
    async def shutdown(self) -> None:
        """Shutdown memory manager and cleanup"""
        if self._background_task:
            self._shutdown_event.set()
            await self._background_task
        logger.info("Memory manager shut down")


# Utility functions for advanced memory operations
def create_memory_manager(config: Dict[str, Any]) -> AdvancedMemoryManager:
    """Factory function for creating a memory manager"""
    strategy = config.get("strategy", MemoryStrategy.HYBRID)
    ttl = config.get("ttl", 3600)
    max_size = config.get("max_size", 10000)
    
    return AdvancedMemoryManager(strategy=strategy, ttl=ttl, max_size=max_size)
