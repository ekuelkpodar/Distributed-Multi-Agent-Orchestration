"""
Task Executor for the Agent Worker Service.
Handles task execution lifecycle, retries, and error handling.
"""

import asyncio
from datetime import datetime
from typing import Any, Optional, Type
from uuid import UUID

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import structlog

from shared.models.schemas import AgentType, TaskStatus
from shared.events.producers import event_producer
from shared.observability.metrics import TASK_DURATION, TASK_FAILED_TOTAL
from agents.base_agent import BaseAgent
from agents.research_agent import ResearchAgent
from agents.analysis_agent import AnalysisAgent
from config import get_settings

logger = structlog.get_logger()
settings = get_settings()


# Agent type to class mapping
AGENT_CLASSES: dict[AgentType, Type[BaseAgent]] = {
    AgentType.RESEARCH: ResearchAgent,
    AgentType.ANALYSIS: AnalysisAgent,
}


class TaskExecutionError(Exception):
    """Custom exception for task execution failures."""

    def __init__(self, message: str, task_id: UUID, recoverable: bool = True):
        self.message = message
        self.task_id = task_id
        self.recoverable = recoverable
        super().__init__(message)


class TaskExecutor:
    """
    Executes tasks assigned to this worker.
    Manages agent lifecycle and task execution with retries.
    """

    def __init__(
        self,
        worker_id: str,
        max_concurrent_tasks: int = 5,
        task_timeout: int = 300,
        retry_attempts: int = 3,
    ):
        self.worker_id = worker_id
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_timeout = task_timeout
        self.retry_attempts = retry_attempts

        self._agents: dict[UUID, BaseAgent] = {}
        self._active_tasks: dict[UUID, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self._running = False

    async def start(self) -> None:
        """Start the task executor."""
        logger.info("Starting task executor", worker_id=self.worker_id)
        self._running = True

    async def stop(self) -> None:
        """Stop the task executor and cleanup."""
        logger.info("Stopping task executor", worker_id=self.worker_id)
        self._running = False

        # Cancel active tasks
        for task_id, task in self._active_tasks.items():
            if not task.done():
                task.cancel()
                logger.warning("Cancelled active task", task_id=str(task_id))

        # Cleanup agents
        for agent_id, agent in self._agents.items():
            await agent.cleanup()

        self._agents.clear()
        self._active_tasks.clear()

    async def get_or_create_agent(
        self,
        agent_id: UUID,
        agent_type: AgentType,
        agent_name: Optional[str] = None,
        config: Optional[dict] = None,
    ) -> BaseAgent:
        """
        Get an existing agent or create a new one.

        Args:
            agent_id: Agent UUID
            agent_type: Type of agent to create
            agent_name: Optional agent name
            config: Optional agent configuration

        Returns:
            Agent instance
        """
        if agent_id in self._agents:
            return self._agents[agent_id]

        # Get agent class
        agent_class = AGENT_CLASSES.get(agent_type)
        if not agent_class:
            # Default to a generic worker agent
            logger.warning(
                "Unknown agent type, using research agent",
                agent_type=agent_type,
            )
            agent_class = ResearchAgent

        # Create agent
        agent = agent_class(
            agent_id=agent_id,
            name=agent_name or f"{agent_type.value}-{agent_id.hex[:8]}",
            **(config or {}),
        )

        self._agents[agent_id] = agent
        logger.info(
            "Created agent",
            agent_id=str(agent_id),
            agent_type=agent_type,
            name=agent.name,
        )

        return agent

    async def execute_task(
        self,
        task_id: UUID,
        agent_id: UUID,
        agent_type: AgentType,
        task_input: dict,
        trace_id: Optional[str] = None,
    ) -> dict:
        """
        Execute a task with the specified agent.

        Args:
            task_id: Task UUID
            agent_id: Agent UUID
            agent_type: Agent type
            task_input: Task input data
            trace_id: Optional trace ID

        Returns:
            Task result dictionary
        """
        async with self._semaphore:
            return await self._execute_with_retry(
                task_id=task_id,
                agent_id=agent_id,
                agent_type=agent_type,
                task_input=task_input,
                trace_id=trace_id,
            )

    async def _execute_with_retry(
        self,
        task_id: UUID,
        agent_id: UUID,
        agent_type: AgentType,
        task_input: dict,
        trace_id: Optional[str] = None,
    ) -> dict:
        """Execute task with retry logic."""
        last_error = None

        for attempt in range(self.retry_attempts):
            try:
                return await self._execute_task_internal(
                    task_id=task_id,
                    agent_id=agent_id,
                    agent_type=agent_type,
                    task_input=task_input,
                    trace_id=trace_id,
                )

            except TaskExecutionError as e:
                last_error = e
                if not e.recoverable:
                    logger.error(
                        "Non-recoverable task error",
                        task_id=str(task_id),
                        error=str(e),
                    )
                    break

                logger.warning(
                    "Task execution failed, retrying",
                    task_id=str(task_id),
                    attempt=attempt + 1,
                    max_attempts=self.retry_attempts,
                    error=str(e),
                )

                # Exponential backoff
                await asyncio.sleep(settings.retry_delay * (2 ** attempt))

            except asyncio.CancelledError:
                logger.info("Task cancelled", task_id=str(task_id))
                raise

            except Exception as e:
                last_error = e
                logger.error(
                    "Unexpected task error",
                    task_id=str(task_id),
                    error=str(e),
                    error_type=type(e).__name__,
                )

                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(settings.retry_delay * (2 ** attempt))

        # All retries exhausted
        TASK_FAILED_TOTAL.labels(
            task_type=agent_type.value,
            error_type=type(last_error).__name__ if last_error else "unknown",
        ).inc()

        raise TaskExecutionError(
            message=str(last_error) if last_error else "Task failed after retries",
            task_id=task_id,
            recoverable=False,
        )

    async def _execute_task_internal(
        self,
        task_id: UUID,
        agent_id: UUID,
        agent_type: AgentType,
        task_input: dict,
        trace_id: Optional[str] = None,
    ) -> dict:
        """Internal task execution with timeout."""
        # Get or create agent
        agent = await self.get_or_create_agent(agent_id, agent_type)

        # Create task with timeout
        task = asyncio.create_task(
            agent.run_task(task_id, task_input)
        )
        self._active_tasks[task_id] = task

        try:
            result = await asyncio.wait_for(task, timeout=self.task_timeout)
            return result

        except asyncio.TimeoutError:
            logger.error(
                "Task execution timeout",
                task_id=str(task_id),
                timeout=self.task_timeout,
            )
            raise TaskExecutionError(
                message=f"Task timed out after {self.task_timeout}s",
                task_id=task_id,
                recoverable=True,
            )

        finally:
            self._active_tasks.pop(task_id, None)

    async def cancel_task(self, task_id: UUID) -> bool:
        """Cancel an active task."""
        task = self._active_tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            logger.info("Task cancelled", task_id=str(task_id))
            return True
        return False

    def get_active_task_count(self) -> int:
        """Get the number of active tasks."""
        return len(self._active_tasks)

    def get_agent_count(self) -> int:
        """Get the number of active agents."""
        return len(self._agents)

    async def cleanup_idle_agents(self, max_idle_time: int = 300) -> int:
        """Clean up idle agents to free resources."""
        # This would check agent last activity and cleanup
        # For now, just return 0
        return 0


class TaskEventHandler:
    """Handles task-related events from Kafka."""

    def __init__(self, executor: TaskExecutor):
        self.executor = executor

    async def handle_task_assigned(self, event: dict) -> None:
        """Handle task.assigned event."""
        task_id = UUID(event["task_id"])
        agent_id = UUID(event["agent_id"])
        task_data = event.get("task_data", {})
        trace_id = event.get("trace_id")

        # Determine agent type from task metadata
        agent_type_str = task_data.get("agent_type", "research")
        try:
            agent_type = AgentType(agent_type_str)
        except ValueError:
            agent_type = AgentType.RESEARCH

        logger.info(
            "Handling task assignment",
            task_id=str(task_id),
            agent_id=str(agent_id),
            agent_type=agent_type,
        )

        try:
            result = await self.executor.execute_task(
                task_id=task_id,
                agent_id=agent_id,
                agent_type=agent_type,
                task_input={
                    "query": task_data.get("description", ""),
                    "context": task_data.get("input_data", {}),
                },
                trace_id=trace_id,
            )

            logger.info(
                "Task completed successfully",
                task_id=str(task_id),
            )

        except TaskExecutionError as e:
            logger.error(
                "Task execution failed",
                task_id=str(task_id),
                error=str(e),
            )

        except Exception as e:
            logger.error(
                "Unexpected error handling task",
                task_id=str(task_id),
                error=str(e),
            )
