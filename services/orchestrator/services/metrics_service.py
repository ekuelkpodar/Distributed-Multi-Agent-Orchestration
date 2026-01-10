"""
Advanced Analytics Engine - MetricsService
Provides time-series metrics collection, aggregation, and analysis.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any
from uuid import UUID
from dataclasses import dataclass, field
import asyncio
from collections import defaultdict
import json

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
import structlog

from shared.database.connections import redis_manager

logger = structlog.get_logger()


class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class TimeGranularity(str, Enum):
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass
class MetricPoint:
    """Single metric data point."""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


class MetricAggregation(BaseModel):
    """Aggregated metric result."""
    name: str
    value: float
    min_value: float
    max_value: float
    avg_value: float
    sum_value: float
    count: int
    start_time: datetime
    end_time: datetime
    granularity: TimeGranularity
    labels: Dict[str, str] = {}


class TimeSeriesPoint(BaseModel):
    """Time series data point."""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = {}


class PerformanceReport(BaseModel):
    """Agent performance report."""
    agent_id: UUID
    agent_name: str
    period_start: datetime
    period_end: datetime
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    success_rate: float
    avg_execution_time_ms: float
    p50_execution_time_ms: float
    p95_execution_time_ms: float
    p99_execution_time_ms: float
    throughput_per_hour: float
    error_rate: float


class SystemMetrics(BaseModel):
    """System-wide metrics snapshot."""
    timestamp: datetime
    active_agents: int
    idle_agents: int
    failed_agents: int
    pending_tasks: int
    running_tasks: int
    completed_tasks_24h: int
    failed_tasks_24h: int
    avg_queue_wait_time_ms: float
    avg_execution_time_ms: float
    system_load: float
    memory_usage_mb: float
    cpu_usage_percent: float


class MetricsService:
    """
    Advanced Analytics Engine for collecting and analyzing metrics.
    Supports time-series data, aggregations, and performance reporting.
    """

    def __init__(self, retention_days: int = 30):
        self.retention_days = retention_days
        self._metrics_buffer: List[MetricPoint] = []
        self._buffer_lock = asyncio.Lock()
        self._flush_interval = 10  # seconds
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the metrics service."""
        self._running = True
        self._flush_task = asyncio.create_task(self._periodic_flush())
        logger.info("MetricsService started")

    async def stop(self):
        """Stop the metrics service."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self._flush_buffer()
        logger.info("MetricsService stopped")

    async def _periodic_flush(self):
        """Periodically flush metrics buffer to storage."""
        while self._running:
            await asyncio.sleep(self._flush_interval)
            await self._flush_buffer()

    async def _flush_buffer(self):
        """Flush buffered metrics to Redis."""
        async with self._buffer_lock:
            if not self._metrics_buffer:
                return

            metrics_to_flush = self._metrics_buffer.copy()
            self._metrics_buffer.clear()

        try:
            redis = await redis_manager.get_client()
            if not redis:
                logger.warning("Redis not available for metrics storage")
                return

            pipe = redis.pipeline()
            for metric in metrics_to_flush:
                key = f"metrics:{metric.name}:{metric.timestamp.strftime('%Y%m%d%H')}"
                value = {
                    "value": metric.value,
                    "timestamp": metric.timestamp.isoformat(),
                    "labels": metric.labels,
                    "type": metric.metric_type.value,
                }
                pipe.lpush(key, json.dumps(value))
                pipe.expire(key, self.retention_days * 86400)

            await pipe.execute()
            logger.debug(f"Flushed {len(metrics_to_flush)} metrics to Redis")
        except Exception as e:
            logger.error(f"Failed to flush metrics: {e}")
            # Re-add metrics to buffer
            async with self._buffer_lock:
                self._metrics_buffer.extend(metrics_to_flush)

    async def record_metric(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        metric_type: MetricType = MetricType.GAUGE,
        timestamp: Optional[datetime] = None,
    ):
        """Record a metric data point."""
        point = MetricPoint(
            name=name,
            value=value,
            timestamp=timestamp or datetime.utcnow(),
            labels=labels or {},
            metric_type=metric_type,
        )
        async with self._buffer_lock:
            self._metrics_buffer.append(point)

    async def record_task_execution(
        self,
        task_id: UUID,
        agent_id: UUID,
        execution_time_ms: float,
        status: str,
        labels: Optional[Dict[str, str]] = None,
    ):
        """Record task execution metrics."""
        base_labels = {
            "task_id": str(task_id),
            "agent_id": str(agent_id),
            "status": status,
            **(labels or {}),
        }

        await self.record_metric(
            "task.execution_time_ms",
            execution_time_ms,
            base_labels,
            MetricType.HISTOGRAM,
        )

        await self.record_metric(
            f"task.{status}.count",
            1,
            {"agent_id": str(agent_id)},
            MetricType.COUNTER,
        )

    async def record_agent_heartbeat(
        self,
        agent_id: UUID,
        cpu_usage: float,
        memory_usage: float,
        active_tasks: int,
    ):
        """Record agent health metrics."""
        labels = {"agent_id": str(agent_id)}

        await self.record_metric("agent.cpu_usage", cpu_usage, labels)
        await self.record_metric("agent.memory_usage", memory_usage, labels)
        await self.record_metric("agent.active_tasks", active_tasks, labels)

    async def get_time_series(
        self,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        granularity: TimeGranularity = TimeGranularity.HOUR,
        labels: Optional[Dict[str, str]] = None,
    ) -> List[TimeSeriesPoint]:
        """Get time series data for a metric."""
        try:
            redis = await redis_manager.get_client()
            if not redis:
                return []

            # Generate keys for the time range
            keys = []
            current = start_time
            while current <= end_time:
                key = f"metrics:{metric_name}:{current.strftime('%Y%m%d%H')}"
                keys.append(key)
                current += timedelta(hours=1)

            # Fetch data from all keys
            all_points = []
            for key in keys:
                data = await redis.lrange(key, 0, -1)
                for item in data:
                    point_data = json.loads(item)
                    timestamp = datetime.fromisoformat(point_data["timestamp"])

                    # Filter by labels if specified
                    if labels:
                        point_labels = point_data.get("labels", {})
                        if not all(point_labels.get(k) == v for k, v in labels.items()):
                            continue

                    if start_time <= timestamp <= end_time:
                        all_points.append(TimeSeriesPoint(
                            timestamp=timestamp,
                            value=point_data["value"],
                            labels=point_data.get("labels", {}),
                        ))

            # Sort by timestamp
            all_points.sort(key=lambda x: x.timestamp)

            # Aggregate by granularity
            if granularity != TimeGranularity.MINUTE:
                all_points = self._aggregate_points(all_points, granularity)

            return all_points

        except Exception as e:
            logger.error(f"Failed to get time series: {e}")
            return []

    def _aggregate_points(
        self,
        points: List[TimeSeriesPoint],
        granularity: TimeGranularity,
    ) -> List[TimeSeriesPoint]:
        """Aggregate points by granularity."""
        if not points:
            return []

        buckets: Dict[str, List[float]] = defaultdict(list)

        for point in points:
            if granularity == TimeGranularity.HOUR:
                bucket_key = point.timestamp.strftime("%Y%m%d%H")
            elif granularity == TimeGranularity.DAY:
                bucket_key = point.timestamp.strftime("%Y%m%d")
            elif granularity == TimeGranularity.WEEK:
                week_start = point.timestamp - timedelta(days=point.timestamp.weekday())
                bucket_key = week_start.strftime("%Y%m%d")
            else:  # MONTH
                bucket_key = point.timestamp.strftime("%Y%m")

            buckets[bucket_key].append(point.value)

        aggregated = []
        for bucket_key, values in sorted(buckets.items()):
            # Parse bucket key back to datetime
            if granularity == TimeGranularity.HOUR:
                ts = datetime.strptime(bucket_key, "%Y%m%d%H")
            elif granularity == TimeGranularity.DAY:
                ts = datetime.strptime(bucket_key, "%Y%m%d")
            elif granularity == TimeGranularity.WEEK:
                ts = datetime.strptime(bucket_key, "%Y%m%d")
            else:
                ts = datetime.strptime(bucket_key + "01", "%Y%m%d")

            aggregated.append(TimeSeriesPoint(
                timestamp=ts,
                value=sum(values) / len(values),  # Average
                labels={},
            ))

        return aggregated

    async def get_aggregation(
        self,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        granularity: TimeGranularity = TimeGranularity.HOUR,
        labels: Optional[Dict[str, str]] = None,
    ) -> Optional[MetricAggregation]:
        """Get aggregated metrics for a time period."""
        points = await self.get_time_series(
            metric_name, start_time, end_time, TimeGranularity.MINUTE, labels
        )

        if not points:
            return None

        values = [p.value for p in points]

        return MetricAggregation(
            name=metric_name,
            value=values[-1] if values else 0,
            min_value=min(values),
            max_value=max(values),
            avg_value=sum(values) / len(values),
            sum_value=sum(values),
            count=len(values),
            start_time=start_time,
            end_time=end_time,
            granularity=granularity,
            labels=labels or {},
        )

    async def get_agent_performance(
        self,
        session: AsyncSession,
        agent_id: UUID,
        start_time: datetime,
        end_time: datetime,
    ) -> Optional[PerformanceReport]:
        """Get detailed performance report for an agent."""
        from shared.database.models import Agent, Task

        # Get agent info
        agent_result = await session.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        if not agent:
            return None

        # Get task statistics
        tasks_result = await session.execute(
            select(Task).where(
                and_(
                    Task.agent_id == agent_id,
                    Task.created_at >= start_time,
                    Task.created_at <= end_time,
                )
            )
        )
        tasks = tasks_result.scalars().all()

        if not tasks:
            return PerformanceReport(
                agent_id=agent_id,
                agent_name=agent.name,
                period_start=start_time,
                period_end=end_time,
                total_tasks=0,
                completed_tasks=0,
                failed_tasks=0,
                success_rate=0.0,
                avg_execution_time_ms=0.0,
                p50_execution_time_ms=0.0,
                p95_execution_time_ms=0.0,
                p99_execution_time_ms=0.0,
                throughput_per_hour=0.0,
                error_rate=0.0,
            )

        # Calculate metrics
        completed = [t for t in tasks if t.status == "completed"]
        failed = [t for t in tasks if t.status == "failed"]

        # Calculate execution times
        execution_times = []
        for task in completed:
            if task.started_at and task.completed_at:
                duration = (task.completed_at - task.started_at).total_seconds() * 1000
                execution_times.append(duration)

        execution_times.sort()

        def percentile(data: List[float], p: float) -> float:
            if not data:
                return 0.0
            k = (len(data) - 1) * p / 100
            f = int(k)
            c = f + 1 if f < len(data) - 1 else f
            return data[f] + (k - f) * (data[c] - data[f]) if f != c else data[f]

        hours = (end_time - start_time).total_seconds() / 3600

        return PerformanceReport(
            agent_id=agent_id,
            agent_name=agent.name,
            period_start=start_time,
            period_end=end_time,
            total_tasks=len(tasks),
            completed_tasks=len(completed),
            failed_tasks=len(failed),
            success_rate=len(completed) / len(tasks) * 100 if tasks else 0,
            avg_execution_time_ms=sum(execution_times) / len(execution_times) if execution_times else 0,
            p50_execution_time_ms=percentile(execution_times, 50),
            p95_execution_time_ms=percentile(execution_times, 95),
            p99_execution_time_ms=percentile(execution_times, 99),
            throughput_per_hour=len(completed) / hours if hours > 0 else 0,
            error_rate=len(failed) / len(tasks) * 100 if tasks else 0,
        )

    async def get_system_metrics(
        self,
        session: AsyncSession,
    ) -> SystemMetrics:
        """Get current system-wide metrics snapshot."""
        from shared.database.models import Agent, Task

        now = datetime.utcnow()
        day_ago = now - timedelta(days=1)

        # Agent counts
        agents_result = await session.execute(
            select(
                Agent.status,
                func.count(Agent.id).label("count")
            ).group_by(Agent.status)
        )
        agent_counts = {row.status: row.count for row in agents_result}

        # Task counts
        tasks_result = await session.execute(
            select(
                Task.status,
                func.count(Task.id).label("count")
            ).where(Task.created_at >= day_ago).group_by(Task.status)
        )
        task_counts = {row.status: row.count for row in tasks_result}

        # Average execution time
        avg_time_result = await session.execute(
            select(func.avg(
                func.extract('epoch', Task.completed_at - Task.started_at) * 1000
            )).where(
                and_(
                    Task.status == "completed",
                    Task.completed_at >= day_ago,
                    Task.started_at.isnot(None),
                )
            )
        )
        avg_execution_time = avg_time_result.scalar() or 0

        # Average queue wait time
        avg_wait_result = await session.execute(
            select(func.avg(
                func.extract('epoch', Task.started_at - Task.created_at) * 1000
            )).where(
                and_(
                    Task.started_at.isnot(None),
                    Task.created_at >= day_ago,
                )
            )
        )
        avg_wait_time = avg_wait_result.scalar() or 0

        return SystemMetrics(
            timestamp=now,
            active_agents=agent_counts.get("active", 0) + agent_counts.get("busy", 0),
            idle_agents=agent_counts.get("idle", 0),
            failed_agents=agent_counts.get("failed", 0),
            pending_tasks=task_counts.get("pending", 0),
            running_tasks=task_counts.get("running", 0),
            completed_tasks_24h=task_counts.get("completed", 0),
            failed_tasks_24h=task_counts.get("failed", 0),
            avg_queue_wait_time_ms=float(avg_wait_time),
            avg_execution_time_ms=float(avg_execution_time),
            system_load=0.0,  # Would need actual system metrics
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
        )

    async def get_trending_metrics(
        self,
        session: AsyncSession,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """Get trending metrics comparing current period to previous."""
        now = datetime.utcnow()
        current_start = now - timedelta(hours=hours)
        previous_start = current_start - timedelta(hours=hours)

        from shared.database.models import Task

        # Current period tasks
        current_result = await session.execute(
            select(
                Task.status,
                func.count(Task.id).label("count")
            ).where(Task.created_at >= current_start).group_by(Task.status)
        )
        current_counts = {row.status: row.count for row in current_result}

        # Previous period tasks
        previous_result = await session.execute(
            select(
                Task.status,
                func.count(Task.id).label("count")
            ).where(
                and_(
                    Task.created_at >= previous_start,
                    Task.created_at < current_start,
                )
            ).group_by(Task.status)
        )
        previous_counts = {row.status: row.count for row in previous_result}

        def calculate_trend(current: int, previous: int) -> Dict[str, Any]:
            if previous == 0:
                change = 100 if current > 0 else 0
            else:
                change = ((current - previous) / previous) * 100
            return {
                "current": current,
                "previous": previous,
                "change_percent": round(change, 2),
                "direction": "up" if change > 0 else "down" if change < 0 else "stable",
            }

        return {
            "period_hours": hours,
            "completed_tasks": calculate_trend(
                current_counts.get("completed", 0),
                previous_counts.get("completed", 0),
            ),
            "failed_tasks": calculate_trend(
                current_counts.get("failed", 0),
                previous_counts.get("failed", 0),
            ),
            "total_tasks": calculate_trend(
                sum(current_counts.values()),
                sum(previous_counts.values()),
            ),
        }
