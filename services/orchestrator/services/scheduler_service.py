"""
Advanced Task Scheduler Service
Provides multiple scheduling strategies and sophisticated task orchestration.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any, Callable, Set
from uuid import UUID, uuid4
from dataclasses import dataclass, field
import asyncio
import heapq
from collections import defaultdict

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update, func
import structlog

from shared.database.connections import redis_manager

logger = structlog.get_logger()


class SchedulingStrategy(str, Enum):
    FIFO = "fifo"
    PRIORITY = "priority"
    DEADLINE = "deadline"
    FAIR_SHARE = "fair_share"
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    ML_OPTIMIZED = "ml_optimized"


class TaskState(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"  # Waiting for dependencies


@dataclass(order=True)
class ScheduledTask:
    """Task in the scheduling queue."""
    priority_score: float
    task_id: UUID = field(compare=False)
    original_priority: int = field(compare=False)
    created_at: datetime = field(compare=False)
    deadline: Optional[datetime] = field(compare=False, default=None)
    agent_type: Optional[str] = field(compare=False, default=None)
    dependencies: Set[UUID] = field(compare=False, default_factory=set)
    metadata: Dict[str, Any] = field(compare=False, default_factory=dict)


class SchedulerConfig(BaseModel):
    """Scheduler configuration."""
    strategy: SchedulingStrategy = SchedulingStrategy.PRIORITY
    max_queue_size: int = 10000
    aging_factor: float = 0.1  # Priority boost per minute
    deadline_weight: float = 2.0  # Weight for deadline-based scoring
    fair_share_window_seconds: int = 3600
    round_robin_quantum: int = 5  # Tasks per agent before rotation


class AgentCapacity(BaseModel):
    """Agent capacity tracking."""
    agent_id: UUID
    agent_type: str
    max_concurrent: int
    current_load: int
    success_rate: float
    avg_execution_time_ms: float
    last_task_at: Optional[datetime] = None


class SchedulingDecision(BaseModel):
    """Result of a scheduling decision."""
    task_id: UUID
    agent_id: UUID
    strategy_used: SchedulingStrategy
    priority_score: float
    reasoning: str
    scheduled_at: datetime


class QueueStats(BaseModel):
    """Queue statistics."""
    total_tasks: int
    by_state: Dict[str, int]
    by_priority: Dict[int, int]
    by_agent_type: Dict[str, int]
    oldest_task_age_seconds: float
    avg_wait_time_seconds: float
    estimated_throughput_per_hour: float


class AdvancedScheduler:
    """
    Advanced Task Scheduler with multiple scheduling strategies.
    Supports priority queues, deadlines, fair sharing, and ML optimization.
    """

    def __init__(self, config: Optional[SchedulerConfig] = None):
        self.config = config or SchedulerConfig()
        self._task_queue: List[ScheduledTask] = []
        self._task_map: Dict[UUID, ScheduledTask] = {}
        self._agent_capacity: Dict[UUID, AgentCapacity] = {}
        self._agent_task_counts: Dict[UUID, int] = defaultdict(int)
        self._round_robin_index: Dict[str, int] = defaultdict(int)
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def start(self):
        """Start the scheduler."""
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info(f"AdvancedScheduler started with strategy: {self.config.strategy}")

    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("AdvancedScheduler stopped")

    async def _scheduler_loop(self):
        """Main scheduling loop."""
        while self._running:
            try:
                await asyncio.sleep(1)
                await self._process_aging()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")

    async def _process_aging(self):
        """Apply aging to prevent starvation."""
        async with self._lock:
            now = datetime.utcnow()
            needs_reheap = False

            for task in self._task_queue:
                # Calculate age in minutes
                age_minutes = (now - task.created_at).total_seconds() / 60
                aging_boost = age_minutes * self.config.aging_factor

                # Recalculate priority score with aging
                new_score = self._calculate_priority_score(
                    task.original_priority,
                    task.deadline,
                    aging_boost,
                )

                if new_score != task.priority_score:
                    task.priority_score = new_score
                    needs_reheap = True

            if needs_reheap:
                heapq.heapify(self._task_queue)

    def _calculate_priority_score(
        self,
        priority: int,
        deadline: Optional[datetime],
        aging_boost: float = 0,
    ) -> float:
        """
        Calculate priority score for scheduling.
        Lower score = higher priority (for min-heap).
        """
        # Base score from priority (invert so higher priority = lower score)
        score = -priority

        # Add deadline urgency
        if deadline:
            now = datetime.utcnow()
            time_until_deadline = (deadline - now).total_seconds()
            if time_until_deadline <= 0:
                # Already past deadline - highest priority
                score -= 1000
            else:
                # Weight by urgency
                urgency = 1.0 / (time_until_deadline / 3600 + 1)  # Hours to deadline
                score -= urgency * self.config.deadline_weight * 100

        # Apply aging boost
        score -= aging_boost

        return score

    async def enqueue_task(
        self,
        task_id: UUID,
        priority: int = 0,
        deadline: Optional[datetime] = None,
        agent_type: Optional[str] = None,
        dependencies: Optional[Set[UUID]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add a task to the scheduling queue."""
        async with self._lock:
            if len(self._task_queue) >= self.config.max_queue_size:
                logger.warning("Scheduler queue full")
                return False

            if task_id in self._task_map:
                logger.warning(f"Task already in queue: {task_id}")
                return False

            score = self._calculate_priority_score(priority, deadline)

            scheduled_task = ScheduledTask(
                priority_score=score,
                task_id=task_id,
                original_priority=priority,
                created_at=datetime.utcnow(),
                deadline=deadline,
                agent_type=agent_type,
                dependencies=dependencies or set(),
                metadata=metadata or {},
            )

            heapq.heappush(self._task_queue, scheduled_task)
            self._task_map[task_id] = scheduled_task

            logger.debug(f"Task enqueued: {task_id} with score {score}")
            return True

    async def dequeue_task(
        self,
        agent_id: UUID,
        agent_type: Optional[str] = None,
    ) -> Optional[ScheduledTask]:
        """Get the next task for an agent."""
        async with self._lock:
            if not self._task_queue:
                return None

            # Find suitable task based on strategy
            if self.config.strategy == SchedulingStrategy.FIFO:
                return await self._dequeue_fifo(agent_id, agent_type)
            elif self.config.strategy == SchedulingStrategy.PRIORITY:
                return await self._dequeue_priority(agent_id, agent_type)
            elif self.config.strategy == SchedulingStrategy.DEADLINE:
                return await self._dequeue_deadline(agent_id, agent_type)
            elif self.config.strategy == SchedulingStrategy.FAIR_SHARE:
                return await self._dequeue_fair_share(agent_id, agent_type)
            elif self.config.strategy == SchedulingStrategy.ROUND_ROBIN:
                return await self._dequeue_round_robin(agent_id, agent_type)
            else:
                return await self._dequeue_priority(agent_id, agent_type)

    async def _dequeue_fifo(
        self,
        agent_id: UUID,
        agent_type: Optional[str],
    ) -> Optional[ScheduledTask]:
        """FIFO dequeue - oldest task first."""
        # Sort by creation time
        sorted_tasks = sorted(self._task_queue, key=lambda t: t.created_at)

        for task in sorted_tasks:
            if await self._can_execute(task, agent_type):
                self._task_queue.remove(task)
                heapq.heapify(self._task_queue)
                del self._task_map[task.task_id]
                self._agent_task_counts[agent_id] += 1
                return task

        return None

    async def _dequeue_priority(
        self,
        agent_id: UUID,
        agent_type: Optional[str],
    ) -> Optional[ScheduledTask]:
        """Priority-based dequeue."""
        # Try tasks in priority order
        temp_list = []

        while self._task_queue:
            task = heapq.heappop(self._task_queue)

            if await self._can_execute(task, agent_type):
                # Put back temp tasks
                for t in temp_list:
                    heapq.heappush(self._task_queue, t)

                del self._task_map[task.task_id]
                self._agent_task_counts[agent_id] += 1
                return task

            temp_list.append(task)

        # No suitable task found, restore queue
        for t in temp_list:
            heapq.heappush(self._task_queue, t)

        return None

    async def _dequeue_deadline(
        self,
        agent_id: UUID,
        agent_type: Optional[str],
    ) -> Optional[ScheduledTask]:
        """Deadline-based dequeue - earliest deadline first."""
        now = datetime.utcnow()
        deadline_tasks = [
            t for t in self._task_queue
            if t.deadline and await self._can_execute(t, agent_type)
        ]
        no_deadline_tasks = [
            t for t in self._task_queue
            if not t.deadline and await self._can_execute(t, agent_type)
        ]

        # Sort deadline tasks by deadline
        deadline_tasks.sort(key=lambda t: t.deadline)

        # Try deadline tasks first
        for task in deadline_tasks:
            self._task_queue.remove(task)
            heapq.heapify(self._task_queue)
            del self._task_map[task.task_id]
            self._agent_task_counts[agent_id] += 1
            return task

        # Fall back to no-deadline tasks by priority
        for task in sorted(no_deadline_tasks, key=lambda t: t.priority_score):
            self._task_queue.remove(task)
            heapq.heapify(self._task_queue)
            del self._task_map[task.task_id]
            self._agent_task_counts[agent_id] += 1
            return task

        return None

    async def _dequeue_fair_share(
        self,
        agent_id: UUID,
        agent_type: Optional[str],
    ) -> Optional[ScheduledTask]:
        """Fair share dequeue - balance work across agents."""
        # Find agent with lowest recent task count
        task_counts = self._agent_task_counts.copy()
        min_count = min(task_counts.values()) if task_counts else 0

        # Only give task if this agent has <= min + 1 tasks
        if task_counts.get(agent_id, 0) > min_count + 1:
            return None

        return await self._dequeue_priority(agent_id, agent_type)

    async def _dequeue_round_robin(
        self,
        agent_id: UUID,
        agent_type: Optional[str],
    ) -> Optional[ScheduledTask]:
        """Round-robin dequeue."""
        key = agent_type or "default"
        current_agent_tasks = self._agent_task_counts.get(agent_id, 0)

        # Check if agent has exceeded its quantum
        if current_agent_tasks >= self.config.round_robin_quantum:
            # Reset and let other agents have a turn
            self._agent_task_counts[agent_id] = 0

        return await self._dequeue_priority(agent_id, agent_type)

    async def _can_execute(
        self,
        task: ScheduledTask,
        agent_type: Optional[str],
    ) -> bool:
        """Check if a task can be executed by an agent."""
        # Check agent type compatibility
        if task.agent_type and agent_type and task.agent_type != agent_type:
            return False

        # Check dependencies
        if task.dependencies:
            for dep_id in task.dependencies:
                if dep_id in self._task_map:
                    # Dependency still pending
                    return False

        return True

    async def cancel_task(self, task_id: UUID) -> bool:
        """Cancel a queued task."""
        async with self._lock:
            if task_id not in self._task_map:
                return False

            task = self._task_map[task_id]
            self._task_queue.remove(task)
            heapq.heapify(self._task_queue)
            del self._task_map[task_id]

            logger.info(f"Task cancelled: {task_id}")
            return True

    async def update_priority(
        self,
        task_id: UUID,
        new_priority: int,
    ) -> bool:
        """Update task priority."""
        async with self._lock:
            if task_id not in self._task_map:
                return False

            task = self._task_map[task_id]
            task.original_priority = new_priority
            task.priority_score = self._calculate_priority_score(
                new_priority,
                task.deadline,
            )

            heapq.heapify(self._task_queue)
            return True

    async def register_agent(
        self,
        agent_id: UUID,
        agent_type: str,
        max_concurrent: int = 5,
    ):
        """Register an agent with capacity info."""
        self._agent_capacity[agent_id] = AgentCapacity(
            agent_id=agent_id,
            agent_type=agent_type,
            max_concurrent=max_concurrent,
            current_load=0,
            success_rate=1.0,
            avg_execution_time_ms=0,
        )
        logger.info(f"Agent registered: {agent_id}")

    async def unregister_agent(self, agent_id: UUID):
        """Unregister an agent."""
        if agent_id in self._agent_capacity:
            del self._agent_capacity[agent_id]
        if agent_id in self._agent_task_counts:
            del self._agent_task_counts[agent_id]
        logger.info(f"Agent unregistered: {agent_id}")

    async def update_agent_metrics(
        self,
        agent_id: UUID,
        current_load: Optional[int] = None,
        success_rate: Optional[float] = None,
        avg_execution_time_ms: Optional[float] = None,
    ):
        """Update agent performance metrics."""
        if agent_id not in self._agent_capacity:
            return

        cap = self._agent_capacity[agent_id]
        if current_load is not None:
            cap.current_load = current_load
        if success_rate is not None:
            cap.success_rate = success_rate
        if avg_execution_time_ms is not None:
            cap.avg_execution_time_ms = avg_execution_time_ms
        cap.last_task_at = datetime.utcnow()

    async def get_queue_stats(self) -> QueueStats:
        """Get current queue statistics."""
        async with self._lock:
            if not self._task_queue:
                return QueueStats(
                    total_tasks=0,
                    by_state={},
                    by_priority={},
                    by_agent_type={},
                    oldest_task_age_seconds=0,
                    avg_wait_time_seconds=0,
                    estimated_throughput_per_hour=0,
                )

            now = datetime.utcnow()

            # Count by priority
            by_priority: Dict[int, int] = defaultdict(int)
            for task in self._task_queue:
                by_priority[task.original_priority] += 1

            # Count by agent type
            by_agent_type: Dict[str, int] = defaultdict(int)
            for task in self._task_queue:
                key = task.agent_type or "any"
                by_agent_type[key] += 1

            # Calculate ages
            ages = [(now - t.created_at).total_seconds() for t in self._task_queue]
            oldest = max(ages) if ages else 0
            avg_wait = sum(ages) / len(ages) if ages else 0

            # Estimate throughput based on agent capacity
            total_capacity = sum(
                c.max_concurrent - c.current_load
                for c in self._agent_capacity.values()
            )

            return QueueStats(
                total_tasks=len(self._task_queue),
                by_state={"queued": len(self._task_queue)},
                by_priority=dict(by_priority),
                by_agent_type=dict(by_agent_type),
                oldest_task_age_seconds=oldest,
                avg_wait_time_seconds=avg_wait,
                estimated_throughput_per_hour=total_capacity * 60,  # Rough estimate
            )

    async def get_best_agent(
        self,
        task: ScheduledTask,
    ) -> Optional[UUID]:
        """Find the best agent for a task using ML-like scoring."""
        candidates = []

        for agent_id, capacity in self._agent_capacity.items():
            # Skip if wrong type
            if task.agent_type and capacity.agent_type != task.agent_type:
                continue

            # Skip if at capacity
            if capacity.current_load >= capacity.max_concurrent:
                continue

            # Calculate suitability score
            score = self._calculate_agent_score(capacity, task)
            candidates.append((agent_id, score))

        if not candidates:
            return None

        # Return agent with highest score
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _calculate_agent_score(
        self,
        capacity: AgentCapacity,
        task: ScheduledTask,
    ) -> float:
        """Calculate agent suitability score for a task."""
        score = 0.0

        # Factor 1: Available capacity (0-30 points)
        availability = (capacity.max_concurrent - capacity.current_load) / capacity.max_concurrent
        score += availability * 30

        # Factor 2: Success rate (0-40 points)
        score += capacity.success_rate * 40

        # Factor 3: Speed (0-20 points) - faster is better
        if capacity.avg_execution_time_ms > 0:
            # Normalize: assume 5000ms is slow, 100ms is fast
            speed_score = max(0, 1 - (capacity.avg_execution_time_ms / 5000))
            score += speed_score * 20

        # Factor 4: Fairness (0-10 points) - prefer agents with fewer recent tasks
        task_count = self._agent_task_counts.get(capacity.agent_id, 0)
        max_count = max(self._agent_task_counts.values()) if self._agent_task_counts else 1
        fairness = 1 - (task_count / max_count) if max_count > 0 else 1
        score += fairness * 10

        return score

    async def resolve_dependencies(self, completed_task_id: UUID):
        """Mark a task as completed and unblock dependent tasks."""
        async with self._lock:
            for task in self._task_queue:
                if completed_task_id in task.dependencies:
                    task.dependencies.remove(completed_task_id)
                    logger.debug(
                        f"Dependency resolved: {completed_task_id} -> {task.task_id}"
                    )
