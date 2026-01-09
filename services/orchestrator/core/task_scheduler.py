"""
Task Scheduler for the Orchestrator Service.
Handles task queue management, assignment, and DAG-based execution.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Any
from uuid import UUID, uuid4

from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from shared.database.models import Task, TaskDependency, Agent
from shared.models.schemas import (
    TaskStatus,
    TaskSubmitRequest,
    TaskSubmitResponse,
    TaskStatusResponse,
    AgentType,
    AgentStatus,
)
from shared.events.producers import event_producer
from shared.observability.metrics import (
    TASK_SUBMITTED_TOTAL,
    TASK_COMPLETED_TOTAL,
    TASK_FAILED_TOTAL,
    TASK_QUEUE_SIZE,
    TASK_RETRY_TOTAL,
)

logger = structlog.get_logger()


class TaskScheduler:
    """
    Manages task scheduling, assignment, and execution tracking.
    Supports DAG-based dependencies and priority queuing.
    """

    def __init__(
        self,
        default_timeout: int = 300,
        max_retries: int = 3,
        retry_delay: int = 5,
        queue_max_size: int = 10000,
    ):
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.queue_max_size = queue_max_size
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the task scheduler."""
        logger.info("Starting task scheduler")
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self) -> None:
        """Stop the task scheduler gracefully."""
        logger.info("Stopping task scheduler")
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

    async def submit_task(
        self,
        session: AsyncSession,
        request: TaskSubmitRequest,
        trace_id: Optional[str] = None,
    ) -> TaskSubmitResponse:
        """
        Submit a new task to the queue.

        Args:
            session: Database session
            request: Task submission request
            trace_id: Optional trace ID for distributed tracing

        Returns:
            TaskSubmitResponse with the task ID
        """
        logger.info(
            "Submitting new task",
            description=request.description[:100],
            priority=request.priority,
        )

        # Check queue size
        queue_size = await self._get_queue_size(session)
        if queue_size >= self.queue_max_size:
            raise ValueError(f"Task queue full ({self.queue_max_size} tasks)")

        # Create task record
        task = Task(
            description=request.description,
            priority=request.priority,
            status=TaskStatus.PENDING.value,
            input_data={
                "query": request.description,
                "context": request.context or {},
            },
            metadata_={
                "trace_id": trace_id or str(uuid4()),
                "agent_type": request.agent_type.value if request.agent_type else None,
                "deadline": request.deadline.isoformat() if request.deadline else None,
            },
            deadline=request.deadline,
        )

        # Assign to specific agent if requested
        if request.agent_id:
            agent = await session.get(Agent, request.agent_id)
            if agent and agent.status == AgentStatus.IDLE.value:
                task.agent_id = request.agent_id
                task.status = TaskStatus.QUEUED.value

        session.add(task)
        await session.commit()

        # Update metrics
        TASK_SUBMITTED_TOTAL.labels(
            task_type=request.agent_type.value if request.agent_type else "general",
            priority=str(request.priority),
        ).inc()

        TASK_QUEUE_SIZE.labels(
            queue_name="main",
            priority=str(request.priority),
        ).inc()

        logger.info(
            "Task submitted successfully",
            task_id=str(task.id),
            status=task.status,
        )

        return TaskSubmitResponse(
            task_id=task.id,
            status=TaskStatus(task.status),
            assigned_agent=task.agent_id,
            message="Task submitted successfully",
        )

    async def get_task(
        self,
        session: AsyncSession,
        task_id: UUID,
    ) -> Optional[Task]:
        """Get task by ID."""
        result = await session.execute(
            select(Task).where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    async def get_task_status(
        self,
        session: AsyncSession,
        task_id: UUID,
    ) -> Optional[TaskStatusResponse]:
        """Get detailed task status."""
        task = await self.get_task(session, task_id)
        if not task:
            return None

        # Calculate progress based on status
        progress = 0.0
        if task.status == TaskStatus.IN_PROGRESS.value:
            progress = task.metadata_.get("progress", 0.5)
        elif task.status == TaskStatus.COMPLETED.value:
            progress = 1.0

        # Calculate estimated completion
        estimated_completion = None
        if task.started_at and task.status == TaskStatus.IN_PROGRESS.value:
            avg_duration = task.metadata_.get("avg_duration", self.default_timeout)
            estimated_completion = task.started_at + timedelta(seconds=avg_duration)

        return TaskStatusResponse(
            task_id=task.id,
            status=TaskStatus(task.status),
            assigned_agent=task.agent_id,
            progress=progress,
            started_at=task.started_at,
            estimated_completion=estimated_completion,
            result=task.output_data.get("result") if task.output_data else None,
        )

    async def assign_task(
        self,
        session: AsyncSession,
        task_id: UUID,
        agent_id: UUID,
    ) -> bool:
        """
        Assign a task to an agent.

        Args:
            session: Database session
            task_id: Task to assign
            agent_id: Agent to assign to

        Returns:
            True if assignment successful
        """
        task = await self.get_task(session, task_id)
        if not task or task.status not in (TaskStatus.PENDING.value, TaskStatus.QUEUED.value):
            return False

        # Verify agent is available
        agent = await session.get(Agent, agent_id)
        if not agent or agent.status != AgentStatus.IDLE.value:
            return False

        # Update task
        task.agent_id = agent_id
        task.status = TaskStatus.QUEUED.value
        task.updated_at = datetime.utcnow()

        # Update agent status
        agent.status = AgentStatus.BUSY.value
        agent.updated_at = datetime.utcnow()

        await session.commit()

        # Publish assignment event
        await event_producer.publish_task_assigned(
            task_id=task_id,
            agent_id=agent_id,
            description=task.description,
            priority=task.priority,
            deadline=task.deadline,
            input_data=task.input_data,
            trace_id=task.metadata_.get("trace_id"),
        )

        logger.info(
            "Task assigned to agent",
            task_id=str(task_id),
            agent_id=str(agent_id),
        )

        return True

    async def start_task(
        self,
        session: AsyncSession,
        task_id: UUID,
    ) -> bool:
        """Mark a task as started."""
        task = await self.get_task(session, task_id)
        if not task or task.status != TaskStatus.QUEUED.value:
            return False

        task.status = TaskStatus.IN_PROGRESS.value
        task.started_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()

        await session.commit()

        # Publish start event
        await event_producer.publish_task_started(
            task_id=task_id,
            agent_id=task.agent_id,
            trace_id=task.metadata_.get("trace_id"),
        )

        logger.info("Task started", task_id=str(task_id))

        return True

    async def update_task_progress(
        self,
        session: AsyncSession,
        task_id: UUID,
        progress: float,
        message: Optional[str] = None,
    ) -> bool:
        """Update task progress."""
        task = await self.get_task(session, task_id)
        if not task or task.status != TaskStatus.IN_PROGRESS.value:
            return False

        task.metadata_["progress"] = progress
        if message:
            task.metadata_["progress_message"] = message
        task.updated_at = datetime.utcnow()

        await session.commit()

        # Publish progress event
        await event_producer.publish_task_progress(
            task_id=task_id,
            agent_id=task.agent_id,
            progress=progress,
            message=message,
            trace_id=task.metadata_.get("trace_id"),
        )

        return True

    async def complete_task(
        self,
        session: AsyncSession,
        task_id: UUID,
        result: Any = None,
    ) -> bool:
        """Mark a task as completed."""
        task = await self.get_task(session, task_id)
        if not task or task.status != TaskStatus.IN_PROGRESS.value:
            return False

        task.status = TaskStatus.COMPLETED.value
        task.completed_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()
        task.output_data = {"result": result}

        # Free up the agent
        if task.agent_id:
            agent = await session.get(Agent, task.agent_id)
            if agent:
                agent.status = AgentStatus.IDLE.value
                agent.updated_at = datetime.utcnow()

        await session.commit()

        # Publish completion event
        await event_producer.publish_task_completed(
            task_id=task_id,
            agent_id=task.agent_id,
            result=result,
            trace_id=task.metadata_.get("trace_id"),
        )

        # Update metrics
        TASK_COMPLETED_TOTAL.labels(
            task_type=task.metadata_.get("agent_type", "general"),
            status="success",
        ).inc()

        TASK_QUEUE_SIZE.labels(
            queue_name="main",
            priority=str(task.priority),
        ).dec()

        logger.info("Task completed", task_id=str(task_id))

        return True

    async def fail_task(
        self,
        session: AsyncSession,
        task_id: UUID,
        error: str,
        retry: bool = True,
    ) -> bool:
        """Mark a task as failed, optionally retrying."""
        task = await self.get_task(session, task_id)
        if not task:
            return False

        retry_count = task.metadata_.get("retry_count", 0)

        if retry and retry_count < self.max_retries:
            # Schedule retry
            task.status = TaskStatus.RETRYING.value
            task.metadata_["retry_count"] = retry_count + 1
            task.metadata_["last_error"] = error
            task.agent_id = None  # Allow reassignment
            task.updated_at = datetime.utcnow()

            TASK_RETRY_TOTAL.labels(
                task_type=task.metadata_.get("agent_type", "general"),
            ).inc()

            logger.warning(
                "Task will be retried",
                task_id=str(task_id),
                retry_count=retry_count + 1,
                error=error,
            )
        else:
            # Mark as failed
            task.status = TaskStatus.FAILED.value
            task.completed_at = datetime.utcnow()
            task.updated_at = datetime.utcnow()
            task.output_data = {"error": error}

            TASK_FAILED_TOTAL.labels(
                task_type=task.metadata_.get("agent_type", "general"),
                error_type="execution_error",
            ).inc()

            TASK_QUEUE_SIZE.labels(
                queue_name="main",
                priority=str(task.priority),
            ).dec()

            logger.error(
                "Task failed",
                task_id=str(task_id),
                error=error,
            )

        # Free up the agent
        if task.agent_id:
            agent = await session.get(Agent, task.agent_id)
            if agent:
                agent.status = AgentStatus.IDLE.value
                agent.updated_at = datetime.utcnow()

        await session.commit()

        # Publish failure event
        await event_producer.publish_task_failed(
            task_id=task_id,
            agent_id=task.agent_id,
            error=error,
            retry_count=retry_count,
            trace_id=task.metadata_.get("trace_id"),
        )

        return True

    async def cancel_task(
        self,
        session: AsyncSession,
        task_id: UUID,
    ) -> bool:
        """Cancel a pending or queued task."""
        task = await self.get_task(session, task_id)
        if not task or task.status not in (
            TaskStatus.PENDING.value,
            TaskStatus.QUEUED.value,
        ):
            return False

        task.status = TaskStatus.CANCELLED.value
        task.completed_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()

        # Free up the agent if assigned
        if task.agent_id:
            agent = await session.get(Agent, task.agent_id)
            if agent:
                agent.status = AgentStatus.IDLE.value
                agent.updated_at = datetime.utcnow()

        await session.commit()

        TASK_QUEUE_SIZE.labels(
            queue_name="main",
            priority=str(task.priority),
        ).dec()

        logger.info("Task cancelled", task_id=str(task_id))

        return True

    async def add_dependency(
        self,
        session: AsyncSession,
        task_id: UUID,
        depends_on_task_id: UUID,
    ) -> bool:
        """Add a dependency between tasks."""
        if task_id == depends_on_task_id:
            return False

        # Check both tasks exist
        task = await self.get_task(session, task_id)
        depends_on = await self.get_task(session, depends_on_task_id)
        if not task or not depends_on:
            return False

        dependency = TaskDependency(
            task_id=task_id,
            depends_on_task_id=depends_on_task_id,
        )

        session.add(dependency)

        try:
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            return False

    async def get_ready_tasks(
        self,
        session: AsyncSession,
        limit: int = 10,
    ) -> list[Task]:
        """
        Get tasks that are ready to be assigned (no pending dependencies).
        Tasks are returned in priority order.
        """
        # Get tasks with pending or retrying status
        query = select(Task).where(
            Task.status.in_(["pending", "retrying"])
        ).order_by(
            Task.priority.desc(),
            Task.created_at.asc(),
        ).limit(limit)

        result = await session.execute(query)
        candidates = result.scalars().all()

        ready_tasks = []
        for task in candidates:
            # Check if all dependencies are completed
            deps_result = await session.execute(
                select(TaskDependency).where(TaskDependency.task_id == task.id)
            )
            dependencies = deps_result.scalars().all()

            all_deps_completed = True
            for dep in dependencies:
                dep_task = await self.get_task(session, dep.depends_on_task_id)
                if dep_task and dep_task.status != TaskStatus.COMPLETED.value:
                    all_deps_completed = False
                    break

            if all_deps_completed:
                ready_tasks.append(task)

        return ready_tasks

    async def _get_queue_size(self, session: AsyncSession) -> int:
        """Get current queue size."""
        result = await session.execute(
            select(Task).where(
                Task.status.in_(["pending", "queued", "in_progress", "retrying"])
            )
        )
        return len(result.scalars().all())

    async def _scheduler_loop(self) -> None:
        """Background task to schedule pending tasks."""
        from shared.database.connections import db_manager
        from core.agent_manager import AgentManager

        logger.info("Starting task scheduler loop")
        agent_manager = AgentManager()

        while self._running:
            try:
                await asyncio.sleep(1)  # Check every second

                async with db_manager.session() as session:
                    # Get ready tasks
                    ready_tasks = await self.get_ready_tasks(session, limit=10)

                    for task in ready_tasks:
                        # Find an available agent
                        agent_type = None
                        if task.metadata_.get("agent_type"):
                            agent_type = AgentType(task.metadata_["agent_type"])

                        agent = await agent_manager.get_available_agent(
                            session,
                            agent_type=agent_type,
                        )

                        if agent:
                            await self.assign_task(session, task.id, agent.id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Scheduler loop error", error=str(e))
