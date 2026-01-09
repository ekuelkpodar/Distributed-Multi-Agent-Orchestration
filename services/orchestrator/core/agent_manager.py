"""
Agent Manager for the Orchestrator Service.
Handles agent lifecycle management, registration, and health monitoring.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from shared.database.models import Agent, AgentPool, AgentPoolMembership
from shared.models.schemas import (
    AgentType,
    AgentStatus,
    AgentSpawnRequest,
    AgentSpawnResponse,
    AgentCapabilities,
    AgentConfig,
)
from shared.events.producers import event_producer
from shared.observability.metrics import AGENT_SPAWNED_TOTAL, AGENT_ACTIVE

logger = structlog.get_logger()


class AgentManager:
    """
    Manages agent lifecycle and registration.
    Handles spawning, health monitoring, and graceful shutdown.
    """

    def __init__(
        self,
        heartbeat_interval: int = 30,
        heartbeat_timeout: int = 90,
        max_agents: int = 100,
    ):
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.max_agents = max_agents
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the agent manager and health monitoring."""
        logger.info("Starting agent manager")
        self._running = True
        self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())

    async def stop(self) -> None:
        """Stop the agent manager gracefully."""
        logger.info("Stopping agent manager")
        self._running = False
        if self._health_monitor_task:
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass

    async def spawn_agent(
        self,
        session: AsyncSession,
        request: AgentSpawnRequest,
    ) -> AgentSpawnResponse:
        """
        Spawn a new agent with the given configuration.

        Args:
            session: Database session
            request: Agent spawn request

        Returns:
            AgentSpawnResponse with the new agent ID
        """
        logger.info(
            "Spawning new agent",
            agent_type=request.agent_type,
            name=request.name,
        )

        # Check agent limits
        active_count = await self._count_active_agents(session)
        if active_count >= self.max_agents:
            logger.warning("Agent limit reached", max_agents=self.max_agents)
            raise ValueError(f"Maximum agent limit ({self.max_agents}) reached")

        # Generate agent name if not provided
        agent_name = request.name or f"{request.agent_type.value}-{uuid4().hex[:8]}"

        # Build capabilities
        capabilities = AgentCapabilities(
            skills=request.capabilities or [],
            max_concurrent_tasks=request.config.get("max_concurrent_tasks", 5) if request.config else 5,
        )

        # Build config
        config = AgentConfig(**(request.config or {}))

        # Create agent record
        agent = Agent(
            name=agent_name,
            type=request.agent_type.value if hasattr(request.agent_type, "value") else request.agent_type,
            status=AgentStatus.STARTING.value,
            capabilities=capabilities.model_dump(),
            config=config.model_dump(),
            parent_id=request.parent_id,
            last_heartbeat=datetime.utcnow(),
        )

        session.add(agent)
        await session.flush()

        # Add to appropriate pool
        await self._assign_to_pool(session, agent)

        await session.commit()

        # Publish spawn event
        await event_producer.publish_agent_spawned(
            agent_id=agent.id,
            agent_type=agent.type,
            agent_name=agent.name,
        )

        # Update metrics
        AGENT_SPAWNED_TOTAL.labels(
            agent_type=agent.type,
            pool="default",
        ).inc()

        AGENT_ACTIVE.labels(
            agent_type=agent.type,
            status=AgentStatus.STARTING.value,
        ).inc()

        logger.info(
            "Agent spawned successfully",
            agent_id=str(agent.id),
            agent_name=agent.name,
            agent_type=agent.type,
        )

        return AgentSpawnResponse(
            agent_id=agent.id,
            status=AgentStatus.STARTING,
            message=f"Agent {agent_name} spawned successfully",
        )

    async def get_agent(
        self,
        session: AsyncSession,
        agent_id: UUID,
    ) -> Optional[Agent]:
        """Get agent by ID."""
        result = await session.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        return result.scalar_one_or_none()

    async def get_agents(
        self,
        session: AsyncSession,
        agent_type: Optional[AgentType] = None,
        status: Optional[AgentStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Agent]:
        """Get agents with optional filtering."""
        query = select(Agent)

        if agent_type:
            type_value = agent_type.value if hasattr(agent_type, "value") else agent_type
            query = query.where(Agent.type == type_value)

        if status:
            status_value = status.value if hasattr(status, "value") else status
            query = query.where(Agent.status == status_value)

        query = query.order_by(Agent.created_at.desc()).limit(limit).offset(offset)

        result = await session.execute(query)
        return list(result.scalars().all())

    async def update_agent_status(
        self,
        session: AsyncSession,
        agent_id: UUID,
        status: AgentStatus,
    ) -> Optional[Agent]:
        """Update agent status."""
        agent = await self.get_agent(session, agent_id)
        if not agent:
            return None

        old_status = agent.status
        agent.status = status.value if hasattr(status, "value") else status
        agent.updated_at = datetime.utcnow()

        if status in (AgentStatus.IDLE, AgentStatus.BUSY):
            agent.last_heartbeat = datetime.utcnow()

        await session.commit()

        # Update metrics
        AGENT_ACTIVE.labels(
            agent_type=agent.type,
            status=old_status,
        ).dec()
        AGENT_ACTIVE.labels(
            agent_type=agent.type,
            status=status.value if hasattr(status, "value") else status,
        ).inc()

        logger.info(
            "Agent status updated",
            agent_id=str(agent_id),
            old_status=old_status,
            new_status=status,
        )

        return agent

    async def record_heartbeat(
        self,
        session: AsyncSession,
        agent_id: UUID,
        metrics: Optional[dict] = None,
    ) -> bool:
        """Record agent heartbeat."""
        result = await session.execute(
            update(Agent)
            .where(Agent.id == agent_id)
            .values(
                last_heartbeat=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

        if result.rowcount == 0:
            return False

        await session.commit()

        # Publish heartbeat event
        agent = await self.get_agent(session, agent_id)
        if agent:
            await event_producer.publish_agent_heartbeat(
                agent_id=agent_id,
                status=AgentStatus(agent.status),
                metrics=metrics,
            )

        return True

    async def terminate_agent(
        self,
        session: AsyncSession,
        agent_id: UUID,
        reason: str = "normal",
    ) -> bool:
        """Terminate an agent gracefully."""
        agent = await self.get_agent(session, agent_id)
        if not agent:
            return False

        logger.info(
            "Terminating agent",
            agent_id=str(agent_id),
            reason=reason,
        )

        old_status = agent.status
        agent.status = AgentStatus.OFFLINE.value
        agent.updated_at = datetime.utcnow()

        await session.commit()

        # Publish stop event
        await event_producer.publish_agent_stopped(
            agent_id=agent_id,
            reason=reason,
        )

        # Update metrics
        AGENT_ACTIVE.labels(
            agent_type=agent.type,
            status=old_status,
        ).dec()

        return True

    async def get_available_agent(
        self,
        session: AsyncSession,
        agent_type: Optional[AgentType] = None,
        required_capabilities: Optional[list[str]] = None,
    ) -> Optional[Agent]:
        """
        Get an available agent for task assignment.
        Uses load balancing to distribute work evenly.
        """
        query = select(Agent).where(Agent.status == AgentStatus.IDLE.value)

        if agent_type:
            type_value = agent_type.value if hasattr(agent_type, "value") else agent_type
            query = query.where(Agent.type == type_value)

        # Order by last heartbeat to prefer recently active agents
        query = query.order_by(Agent.last_heartbeat.desc()).limit(1)

        result = await session.execute(query)
        agent = result.scalar_one_or_none()

        if agent and required_capabilities:
            agent_caps = agent.capabilities.get("skills", [])
            if not all(cap in agent_caps for cap in required_capabilities):
                return None

        return agent

    async def _assign_to_pool(
        self,
        session: AsyncSession,
        agent: Agent,
    ) -> None:
        """Assign agent to an appropriate pool."""
        # Find matching pool
        result = await session.execute(
            select(AgentPool).where(AgentPool.agent_type == agent.type)
        )
        pool = result.scalar_one_or_none()

        if pool:
            membership = AgentPoolMembership(
                agent_id=agent.id,
                pool_id=pool.id,
            )
            session.add(membership)

    async def _count_active_agents(self, session: AsyncSession) -> int:
        """Count currently active agents."""
        result = await session.execute(
            select(Agent).where(
                Agent.status.in_(["idle", "busy", "starting"])
            )
        )
        return len(result.scalars().all())

    async def _health_monitor_loop(self) -> None:
        """Background task to monitor agent health."""
        logger.info("Starting agent health monitor")

        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self._check_agent_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Health monitor error", error=str(e))

    async def _check_agent_health(self) -> None:
        """Check health of all agents and mark stale ones as offline."""
        from shared.database.connections import db_manager

        timeout_threshold = datetime.utcnow() - timedelta(seconds=self.heartbeat_timeout)

        async with db_manager.session() as session:
            # Find agents with stale heartbeats
            result = await session.execute(
                select(Agent).where(
                    and_(
                        Agent.status.in_(["idle", "busy"]),
                        Agent.last_heartbeat < timeout_threshold,
                    )
                )
            )

            stale_agents = result.scalars().all()

            for agent in stale_agents:
                logger.warning(
                    "Agent heartbeat timeout",
                    agent_id=str(agent.id),
                    last_heartbeat=agent.last_heartbeat.isoformat(),
                )

                old_status = agent.status
                agent.status = AgentStatus.OFFLINE.value
                agent.updated_at = datetime.utcnow()

                # Publish failure event
                await event_producer.publish_agent_stopped(
                    agent_id=agent.id,
                    reason="heartbeat_timeout",
                )

                # Update metrics
                AGENT_ACTIVE.labels(
                    agent_type=agent.type,
                    status=old_status,
                ).dec()

            if stale_agents:
                await session.commit()
                logger.info(
                    "Marked stale agents as offline",
                    count=len(stale_agents),
                )
