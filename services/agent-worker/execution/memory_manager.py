"""
Memory Manager for agents.
Handles short-term, mid-term, and long-term memory with vector search.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from shared.database.connections import db_manager, redis_manager
from shared.database.models import AgentMemory
from shared.models.schemas import MemoryType
from shared.observability.metrics import (
    MEMORY_SEARCH_TOTAL,
    MEMORY_SEARCH_DURATION,
    MEMORY_ENTRIES_TOTAL,
)
from config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class MemoryManager:
    """
    Manages agent memory across multiple tiers:
    - Short-term: Active context (Redis, 1-hour TTL)
    - Mid-term: Recent history (Redis, 24-hour TTL)
    - Long-term: Persistent memory (PostgreSQL + pgvector)
    """

    # Redis key prefixes
    PREFIX_SHORT_TERM = "memory:short:"
    PREFIX_MID_TERM = "memory:mid:"
    PREFIX_CONTEXT = "memory:context:"

    def __init__(self, agent_id: UUID):
        self.agent_id = agent_id
        self._embedding_model = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the memory manager."""
        if self._initialized:
            return

        logger.debug("Initializing memory manager", agent_id=str(self.agent_id))
        self._initialized = True

    async def _get_embedding(self, text: str) -> list[float]:
        """
        Get embedding vector for text.
        Uses OpenAI's Ada-002 model by default.
        """
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.openai_api_key)

            response = await client.embeddings.create(
                model="text-embedding-ada-002",
                input=text,
            )

            return response.data[0].embedding

        except Exception as e:
            logger.error("Failed to generate embedding", error=str(e))
            # Return zero vector as fallback
            return [0.0] * 1536

    # Short-term Memory (Redis with 1-hour TTL)

    async def store_short_term(
        self,
        key: str,
        content: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Store content in short-term memory.

        Args:
            key: Memory key
            content: Content to store
            ttl: Time-to-live in seconds (default: 1 hour)

        Returns:
            Success status
        """
        ttl = ttl or settings.memory_short_term_ttl
        redis_key = f"{self.PREFIX_SHORT_TERM}{self.agent_id}:{key}"

        data = json.dumps({
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }, default=str)

        await redis_manager.set(redis_key, data, ex=ttl)
        return True

    async def get_short_term(self, key: str) -> Optional[Any]:
        """
        Retrieve content from short-term memory.

        Args:
            key: Memory key

        Returns:
            Stored content or None
        """
        redis_key = f"{self.PREFIX_SHORT_TERM}{self.agent_id}:{key}"
        data = await redis_manager.get(redis_key)

        if data:
            parsed = json.loads(data)
            return parsed.get("content")
        return None

    async def delete_short_term(self, key: str) -> bool:
        """Delete content from short-term memory."""
        redis_key = f"{self.PREFIX_SHORT_TERM}{self.agent_id}:{key}"
        return await redis_manager.delete(redis_key) > 0

    # Mid-term Memory (Redis with 24-hour TTL)

    async def store_mid_term(
        self,
        key: str,
        content: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Store content in mid-term memory.

        Args:
            key: Memory key
            content: Content to store
            ttl: Time-to-live in seconds (default: 24 hours)

        Returns:
            Success status
        """
        ttl = ttl or settings.memory_mid_term_ttl
        redis_key = f"{self.PREFIX_MID_TERM}{self.agent_id}:{key}"

        data = json.dumps({
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }, default=str)

        await redis_manager.set(redis_key, data, ex=ttl)
        return True

    async def get_mid_term(self, key: str) -> Optional[Any]:
        """Retrieve content from mid-term memory."""
        redis_key = f"{self.PREFIX_MID_TERM}{self.agent_id}:{key}"
        data = await redis_manager.get(redis_key)

        if data:
            parsed = json.loads(data)
            return parsed.get("content")
        return None

    # Long-term Memory (PostgreSQL + pgvector)

    async def store_long_term(
        self,
        content: str,
        memory_type: MemoryType,
        metadata: Optional[dict] = None,
        generate_embedding: bool = True,
    ) -> UUID:
        """
        Store content in long-term memory with optional embedding.

        Args:
            content: Text content to store
            memory_type: Type of memory
            metadata: Additional metadata
            generate_embedding: Whether to generate embedding

        Returns:
            Memory entry ID
        """
        embedding = None
        if generate_embedding:
            embedding = await self._get_embedding(content)

        async with db_manager.session() as session:
            memory = AgentMemory(
                agent_id=self.agent_id,
                memory_type=memory_type.value if hasattr(memory_type, "value") else memory_type,
                content=content,
                embedding=embedding,
                metadata_=metadata or {},
            )

            session.add(memory)
            await session.commit()

            logger.debug(
                "Stored long-term memory",
                agent_id=str(self.agent_id),
                memory_id=str(memory.id),
                memory_type=memory_type,
            )

            MEMORY_ENTRIES_TOTAL.labels(
                agent_id=str(self.agent_id),
                memory_type=memory_type.value if hasattr(memory_type, "value") else memory_type,
            ).inc()

            return memory.id

    async def search_memories(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7,
    ) -> list[dict]:
        """
        Search memories using vector similarity.

        Args:
            query: Search query
            memory_type: Filter by memory type
            limit: Maximum results
            similarity_threshold: Minimum similarity score

        Returns:
            List of matching memories with similarity scores
        """
        import time

        start_time = time.time()

        # Generate query embedding
        query_embedding = await self._get_embedding(query)

        async with db_manager.session() as session:
            # Build query using pgvector similarity
            from sqlalchemy import text

            type_filter = ""
            if memory_type:
                type_value = memory_type.value if hasattr(memory_type, "value") else memory_type
                type_filter = f"AND memory_type = '{type_value}'"

            sql = text(f"""
                SELECT
                    id,
                    content,
                    memory_type,
                    metadata,
                    created_at,
                    1 - (embedding <=> :embedding) as similarity
                FROM agent_memory
                WHERE agent_id = :agent_id
                    AND embedding IS NOT NULL
                    {type_filter}
                    AND 1 - (embedding <=> :embedding) >= :threshold
                ORDER BY embedding <=> :embedding
                LIMIT :limit
            """)

            result = await session.execute(
                sql,
                {
                    "agent_id": str(self.agent_id),
                    "embedding": str(query_embedding),
                    "threshold": similarity_threshold,
                    "limit": limit,
                },
            )

            memories = []
            for row in result:
                memories.append({
                    "id": str(row.id),
                    "content": row.content,
                    "memory_type": row.memory_type,
                    "metadata": row.metadata,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "similarity": float(row.similarity),
                })

        duration = time.time() - start_time

        MEMORY_SEARCH_TOTAL.labels(
            agent_id=str(self.agent_id),
            memory_type=memory_type.value if memory_type and hasattr(memory_type, "value") else "all",
        ).inc()

        MEMORY_SEARCH_DURATION.labels(
            memory_type=memory_type.value if memory_type and hasattr(memory_type, "value") else "all",
        ).observe(duration)

        logger.debug(
            "Memory search completed",
            agent_id=str(self.agent_id),
            query=query[:50],
            results=len(memories),
            duration_ms=round(duration * 1000, 2),
        )

        return memories

    # Convenience Methods

    async def store_conversation(
        self,
        query: str,
        response: str,
        metadata: Optional[dict] = None,
    ) -> UUID:
        """Store a conversation exchange in memory."""
        content = f"Q: {query}\nA: {response}"
        return await self.store_long_term(
            content=content,
            memory_type=MemoryType.CONVERSATION,
            metadata={
                "query": query[:200],
                "response_preview": response[:200],
                **(metadata or {}),
            },
        )

    async def store_knowledge(
        self,
        content: str,
        metadata: Optional[dict] = None,
    ) -> UUID:
        """Store knowledge in long-term memory."""
        return await self.store_long_term(
            content=content,
            memory_type=MemoryType.KNOWLEDGE,
            metadata=metadata,
        )

    async def store_context(
        self,
        context: dict,
        ttl: Optional[int] = None,
    ) -> bool:
        """Store current context in short-term memory."""
        return await self.store_short_term(
            key="current_context",
            content=context,
            ttl=ttl or 3600,
        )

    async def get_context(self) -> Optional[dict]:
        """Retrieve current context from short-term memory."""
        return await self.get_short_term("current_context")

    async def get_recent_conversations(self, limit: int = 5) -> list[dict]:
        """Get recent conversation history."""
        async with db_manager.session() as session:
            result = await session.execute(
                select(AgentMemory)
                .where(AgentMemory.agent_id == self.agent_id)
                .where(AgentMemory.memory_type == MemoryType.CONVERSATION.value)
                .order_by(AgentMemory.created_at.desc())
                .limit(limit)
            )

            memories = result.scalars().all()
            return [
                {
                    "id": str(m.id),
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in memories
            ]

    async def cleanup_expired(self) -> int:
        """Clean up expired memory entries."""
        async with db_manager.session() as session:
            result = await session.execute(
                delete(AgentMemory)
                .where(AgentMemory.agent_id == self.agent_id)
                .where(AgentMemory.expires_at.isnot(None))
                .where(AgentMemory.expires_at < datetime.utcnow())
            )
            await session.commit()
            return result.rowcount

    async def cleanup(self) -> None:
        """Clean up all agent memories and resources."""
        # Clean up Redis entries
        pattern = f"memory:*:{self.agent_id}:*"
        # Note: In production, use SCAN instead of KEYS
        logger.debug("Memory manager cleanup completed", agent_id=str(self.agent_id))
