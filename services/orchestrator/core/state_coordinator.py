"""
State Coordinator for the Orchestrator Service.
Handles distributed state management, locking, and synchronization.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

import redis.asyncio as redis
import structlog

from shared.database.connections import redis_manager
from shared.events.producers import event_producer

logger = structlog.get_logger()


class StateCoordinator:
    """
    Manages distributed state across the agent orchestration platform.
    Uses Redis for hot state and distributed locking.
    """

    # Key prefixes
    PREFIX_AGENT_STATE = "agent:state:"
    PREFIX_TASK_STATE = "task:state:"
    PREFIX_SESSION = "session:"
    PREFIX_LOCK = "lock:"
    PREFIX_COUNTER = "counter:"

    # TTL values (in seconds)
    TTL_SHORT_TERM = 3600  # 1 hour
    TTL_MID_TERM = 86400  # 24 hours
    TTL_SESSION = 1800  # 30 minutes
    TTL_LOCK = 30  # 30 seconds default lock

    def __init__(self):
        self._redis: Optional[redis.Redis] = None

    @property
    def redis(self) -> redis.Redis:
        """Get Redis client."""
        if self._redis is None:
            self._redis = redis_manager.client
        return self._redis

    # Agent State Management

    async def get_agent_state(self, agent_id: UUID) -> Optional[dict]:
        """Get agent state from Redis."""
        key = f"{self.PREFIX_AGENT_STATE}{agent_id}"
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def set_agent_state(
        self,
        agent_id: UUID,
        state: dict,
        ttl: int = TTL_SHORT_TERM,
    ) -> bool:
        """Set agent state in Redis."""
        key = f"{self.PREFIX_AGENT_STATE}{agent_id}"
        data = json.dumps(state, default=str)
        await self.redis.set(key, data, ex=ttl)

        # Publish state update event
        await event_producer.publish_state_update(
            agent_id=agent_id,
            state_key="agent_state",
            state_value=state,
        )

        return True

    async def update_agent_state(
        self,
        agent_id: UUID,
        updates: dict,
    ) -> dict:
        """Update specific fields in agent state."""
        current = await self.get_agent_state(agent_id) or {}
        current.update(updates)
        current["updated_at"] = datetime.utcnow().isoformat()
        await self.set_agent_state(agent_id, current)
        return current

    async def delete_agent_state(self, agent_id: UUID) -> bool:
        """Delete agent state from Redis."""
        key = f"{self.PREFIX_AGENT_STATE}{agent_id}"
        return await self.redis.delete(key) > 0

    # Task State Management

    async def get_task_state(self, task_id: UUID) -> Optional[dict]:
        """Get task state from Redis."""
        key = f"{self.PREFIX_TASK_STATE}{task_id}"
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def set_task_state(
        self,
        task_id: UUID,
        state: dict,
        ttl: int = TTL_SHORT_TERM,
    ) -> bool:
        """Set task state in Redis."""
        key = f"{self.PREFIX_TASK_STATE}{task_id}"
        data = json.dumps(state, default=str)
        await self.redis.set(key, data, ex=ttl)
        return True

    async def update_task_progress(
        self,
        task_id: UUID,
        progress: float,
        message: Optional[str] = None,
    ) -> dict:
        """Update task progress in Redis."""
        state = await self.get_task_state(task_id) or {}
        state["progress"] = progress
        if message:
            state["progress_message"] = message
        state["updated_at"] = datetime.utcnow().isoformat()
        await self.set_task_state(task_id, state)
        return state

    # Session Management

    async def create_session(
        self,
        session_id: str,
        data: dict,
        ttl: int = TTL_SESSION,
    ) -> bool:
        """Create a new session."""
        key = f"{self.PREFIX_SESSION}{session_id}"
        session_data = {
            **data,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(seconds=ttl)).isoformat(),
        }
        await self.redis.set(key, json.dumps(session_data, default=str), ex=ttl)
        return True

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data."""
        key = f"{self.PREFIX_SESSION}{session_id}"
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def extend_session(self, session_id: str, ttl: int = TTL_SESSION) -> bool:
        """Extend session TTL."""
        key = f"{self.PREFIX_SESSION}{session_id}"
        return await self.redis.expire(key, ttl)

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        key = f"{self.PREFIX_SESSION}{session_id}"
        return await self.redis.delete(key) > 0

    # Distributed Locking

    async def acquire_lock(
        self,
        lock_name: str,
        timeout: int = TTL_LOCK,
        blocking: bool = True,
        blocking_timeout: float = 5.0,
    ) -> Optional[Any]:
        """
        Acquire a distributed lock.

        Args:
            lock_name: Name of the lock
            timeout: Lock expiration in seconds
            blocking: Whether to block waiting for lock
            blocking_timeout: How long to wait for lock

        Returns:
            Lock object if acquired, None otherwise
        """
        key = f"{self.PREFIX_LOCK}{lock_name}"
        lock = self.redis.lock(
            key,
            timeout=timeout,
            blocking=blocking,
            blocking_timeout=blocking_timeout,
        )

        try:
            acquired = await lock.acquire()
            if acquired:
                logger.debug("Lock acquired", lock_name=lock_name)
                return lock
            return None
        except Exception as e:
            logger.error("Failed to acquire lock", lock_name=lock_name, error=str(e))
            return None

    async def release_lock(self, lock: Any) -> bool:
        """Release a distributed lock."""
        try:
            await lock.release()
            logger.debug("Lock released")
            return True
        except Exception as lock_err:
            logger.warning("Attempted to release unowned lock", error=str(lock_err))
            return False

    async def with_lock(
        self,
        lock_name: str,
        callback,
        timeout: int = TTL_LOCK,
    ):
        """
        Execute callback while holding a lock.

        Args:
            lock_name: Name of the lock
            callback: Async function to execute
            timeout: Lock timeout

        Returns:
            Result of callback, or None if lock not acquired
        """
        lock = await self.acquire_lock(lock_name, timeout=timeout)
        if not lock:
            return None

        try:
            if asyncio.iscoroutinefunction(callback):
                return await callback()
            return callback()
        finally:
            await self.release_lock(lock)

    # Leader Election

    async def try_become_leader(
        self,
        service_id: str,
        ttl: int = 30,
    ) -> bool:
        """
        Attempt to become the leader for a service.
        Uses Redis atomic SET NX for leader election.
        """
        key = f"{self.PREFIX_LOCK}leader:{service_id}"
        leader_id = f"{service_id}:{datetime.utcnow().timestamp()}"

        # Try to set ourselves as leader (only if key doesn't exist)
        result = await self.redis.set(key, leader_id, ex=ttl, nx=True)

        if result:
            logger.info("Became leader", service_id=service_id)
            return True

        return False

    async def renew_leadership(self, service_id: str, ttl: int = 30) -> bool:
        """Renew leadership by extending TTL."""
        key = f"{self.PREFIX_LOCK}leader:{service_id}"
        return await self.redis.expire(key, ttl)

    async def resign_leadership(self, service_id: str) -> bool:
        """Resign leadership."""
        key = f"{self.PREFIX_LOCK}leader:{service_id}"
        result = await self.redis.delete(key)
        if result:
            logger.info("Resigned leadership", service_id=service_id)
        return result > 0

    async def get_leader(self, service_id: str) -> Optional[str]:
        """Get current leader ID."""
        key = f"{self.PREFIX_LOCK}leader:{service_id}"
        return await self.redis.get(key)

    # Counters and Rate Limiting

    async def increment_counter(
        self,
        counter_name: str,
        amount: int = 1,
        ttl: Optional[int] = None,
    ) -> int:
        """Increment a counter and return new value."""
        key = f"{self.PREFIX_COUNTER}{counter_name}"
        value = await self.redis.incrby(key, amount)
        if ttl:
            await self.redis.expire(key, ttl)
        return value

    async def get_counter(self, counter_name: str) -> int:
        """Get counter value."""
        key = f"{self.PREFIX_COUNTER}{counter_name}"
        value = await self.redis.get(key)
        return int(value) if value else 0

    async def reset_counter(self, counter_name: str) -> bool:
        """Reset a counter to zero."""
        key = f"{self.PREFIX_COUNTER}{counter_name}"
        return await self.redis.delete(key) > 0

    async def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window: int,
    ) -> tuple[bool, int]:
        """
        Check if request is within rate limit.

        Args:
            identifier: Unique identifier (e.g., client ID)
            limit: Maximum requests allowed
            window: Time window in seconds

        Returns:
            Tuple of (allowed, remaining_requests)
        """
        key = f"ratelimit:{identifier}"
        current = await self.increment_counter(key, ttl=window)

        if current == 1:
            # First request, set expiry
            await self.redis.expire(key, window)

        remaining = max(0, limit - current)
        allowed = current <= limit

        return allowed, remaining

    # Pub/Sub for Real-time Updates

    async def publish(self, channel: str, message: dict) -> int:
        """Publish a message to a channel."""
        data = json.dumps(message, default=str)
        return await self.redis.publish(channel, data)

    async def subscribe(self, *channels: str):
        """Subscribe to channels and yield messages."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(*channels)

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield {
                        "channel": message["channel"],
                        "data": json.loads(message["data"]),
                    }
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.close()

    # Batch Operations

    async def get_multiple_states(
        self,
        prefix: str,
        ids: list[UUID],
    ) -> dict[UUID, dict]:
        """Get multiple states in a single operation."""
        if not ids:
            return {}

        keys = [f"{prefix}{id}" for id in ids]
        values = await self.redis.mget(keys)

        result = {}
        for id, value in zip(ids, values):
            if value:
                result[id] = json.loads(value)

        return result

    async def set_multiple_states(
        self,
        prefix: str,
        states: dict[UUID, dict],
        ttl: int = TTL_SHORT_TERM,
    ) -> bool:
        """Set multiple states in a single operation."""
        if not states:
            return True

        pipeline = self.redis.pipeline()
        for id, state in states.items():
            key = f"{prefix}{id}"
            data = json.dumps(state, default=str)
            pipeline.set(key, data, ex=ttl)

        await pipeline.execute()
        return True


# Global state coordinator instance
state_coordinator = StateCoordinator()
