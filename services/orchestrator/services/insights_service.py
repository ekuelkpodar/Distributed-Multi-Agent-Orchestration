"""
AI-Powered Insights Service
Uses Claude API to analyze metrics and provide intelligent recommendations.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any
from uuid import UUID
from dataclasses import dataclass
import json
import asyncio

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
import structlog

from config import get_settings
from shared.database.connections import redis_manager

logger = structlog.get_logger()
settings = get_settings()


class InsightType(str, Enum):
    PERFORMANCE = "performance"
    ANOMALY = "anomaly"
    OPTIMIZATION = "optimization"
    PREDICTION = "prediction"
    RECOMMENDATION = "recommendation"


class InsightPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Insight(BaseModel):
    """AI-generated insight."""
    id: str
    type: InsightType
    priority: InsightPriority
    title: str
    description: str
    impact: str
    recommendations: List[str]
    affected_resources: List[str]
    confidence: float
    created_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}


class PerformanceAnalysis(BaseModel):
    """Performance analysis result."""
    score: float  # 0-100
    grade: str  # A, B, C, D, F
    strengths: List[str]
    weaknesses: List[str]
    bottlenecks: List[str]
    recommendations: List[str]
    comparison_to_baseline: Dict[str, float]


class AnomalyDetection(BaseModel):
    """Detected anomaly."""
    metric_name: str
    detected_at: datetime
    severity: InsightPriority
    expected_value: float
    actual_value: float
    deviation_percent: float
    possible_causes: List[str]
    suggested_actions: List[str]


class AIInsightsService:
    """
    AI-Powered Insights Service for generating intelligent recommendations.
    Uses Claude API for analysis and pattern recognition.
    """

    def __init__(self, cache_ttl: int = 3600):
        self.cache_ttl = cache_ttl
        self._client = None
        self._model = "claude-sonnet-4-20250514"
        self._insights_cache: Dict[str, Insight] = {}

    async def _get_client(self):
        """Get or create the AI client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(
                    api_key=settings.anthropic_api_key
                )
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
                return None
        return self._client

    async def _call_claude(
        self,
        prompt: str,
        system: str = "You are an expert system analyzer for a distributed multi-agent orchestration platform.",
        max_tokens: int = 2000,
    ) -> Optional[str]:
        """Make a call to Claude API."""
        client = await self._get_client()
        if not client:
            return None

        try:
            response = await client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            return None

    async def analyze_performance(
        self,
        session: AsyncSession,
        hours: int = 24,
    ) -> Optional[PerformanceAnalysis]:
        """Analyze system performance and provide insights."""
        from shared.database.models import Agent, Task

        # Gather metrics
        now = datetime.utcnow()
        start_time = now - timedelta(hours=hours)

        # Get task statistics
        tasks_result = await session.execute(
            select(
                Task.status,
                func.count(Task.id).label("count"),
                func.avg(
                    func.extract('epoch', Task.completed_at - Task.started_at)
                ).label("avg_duration"),
            ).where(Task.created_at >= start_time).group_by(Task.status)
        )
        task_stats = {row.status: {"count": row.count, "avg_duration": row.avg_duration or 0}
                      for row in tasks_result}

        # Get agent statistics
        agents_result = await session.execute(
            select(
                Agent.status,
                func.count(Agent.id).label("count"),
            ).group_by(Agent.status)
        )
        agent_stats = {row.status: row.count for row in agents_result}

        total_tasks = sum(s["count"] for s in task_stats.values())
        completed_tasks = task_stats.get("completed", {}).get("count", 0)
        failed_tasks = task_stats.get("failed", {}).get("count", 0)
        success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        avg_duration = task_stats.get("completed", {}).get("avg_duration", 0)

        # Prepare prompt for Claude
        metrics_summary = f"""
System Performance Metrics (Last {hours} hours):
- Total Tasks: {total_tasks}
- Completed Tasks: {completed_tasks}
- Failed Tasks: {failed_tasks}
- Success Rate: {success_rate:.1f}%
- Average Task Duration: {avg_duration:.2f} seconds
- Active Agents: {agent_stats.get('active', 0) + agent_stats.get('busy', 0)}
- Idle Agents: {agent_stats.get('idle', 0)}
- Failed Agents: {agent_stats.get('failed', 0)}
"""

        prompt = f"""
{metrics_summary}

Analyze this system performance data and provide:
1. A performance score from 0-100
2. A letter grade (A, B, C, D, F)
3. List of 2-3 key strengths
4. List of 2-3 areas for improvement
5. Any potential bottlenecks identified
6. 3-5 specific actionable recommendations

Respond in JSON format:
{{
    "score": <number>,
    "grade": "<letter>",
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "bottlenecks": ["bottleneck1"],
    "recommendations": ["rec1", "rec2", "rec3"],
    "comparison_to_baseline": {{"success_rate": <diff>, "throughput": <diff>}}
}}
"""

        response = await self._call_claude(prompt)
        if not response:
            # Return fallback analysis
            return self._generate_fallback_analysis(
                success_rate, total_tasks, failed_tasks, avg_duration
            )

        try:
            # Parse JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response[json_start:json_end])
                return PerformanceAnalysis(
                    score=data.get("score", 0),
                    grade=data.get("grade", "C"),
                    strengths=data.get("strengths", []),
                    weaknesses=data.get("weaknesses", []),
                    bottlenecks=data.get("bottlenecks", []),
                    recommendations=data.get("recommendations", []),
                    comparison_to_baseline=data.get("comparison_to_baseline", {}),
                )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response: {e}")

        return self._generate_fallback_analysis(
            success_rate, total_tasks, failed_tasks, avg_duration
        )

    def _generate_fallback_analysis(
        self,
        success_rate: float,
        total_tasks: int,
        failed_tasks: int,
        avg_duration: float,
    ) -> PerformanceAnalysis:
        """Generate fallback analysis when AI is unavailable."""
        if success_rate >= 95:
            score, grade = 95, "A"
        elif success_rate >= 85:
            score, grade = 85, "B"
        elif success_rate >= 75:
            score, grade = 75, "C"
        elif success_rate >= 60:
            score, grade = 60, "D"
        else:
            score, grade = 40, "F"

        strengths = []
        weaknesses = []
        recommendations = []

        if success_rate >= 90:
            strengths.append("High task success rate")
        else:
            weaknesses.append(f"Task success rate of {success_rate:.1f}% needs improvement")
            recommendations.append("Investigate causes of task failures")

        if total_tasks > 100:
            strengths.append("High throughput")
        elif total_tasks < 10:
            weaknesses.append("Low task volume")

        if avg_duration < 5:
            strengths.append("Fast average task execution time")
        elif avg_duration > 30:
            weaknesses.append("Slow average task execution time")
            recommendations.append("Optimize slow tasks or increase parallelization")

        return PerformanceAnalysis(
            score=score,
            grade=grade,
            strengths=strengths or ["System is operational"],
            weaknesses=weaknesses or ["No significant issues detected"],
            bottlenecks=[],
            recommendations=recommendations or ["Continue monitoring system health"],
            comparison_to_baseline={},
        )

    async def detect_anomalies(
        self,
        session: AsyncSession,
        hours: int = 24,
    ) -> List[AnomalyDetection]:
        """Detect anomalies in system behavior."""
        from shared.database.models import Task

        anomalies = []
        now = datetime.utcnow()
        current_start = now - timedelta(hours=hours)
        baseline_start = current_start - timedelta(hours=hours * 7)  # 7x baseline

        # Get current period stats
        current_result = await session.execute(
            select(
                func.count(Task.id).label("total"),
                func.sum(func.cast(Task.status == "failed", Integer := 1)).label("failed"),
                func.avg(
                    func.extract('epoch', Task.completed_at - Task.started_at)
                ).label("avg_duration"),
            ).where(Task.created_at >= current_start)
        )
        current = current_result.first()

        # Get baseline period stats
        baseline_result = await session.execute(
            select(
                func.count(Task.id).label("total"),
                func.sum(func.cast(Task.status == "failed", Integer := 1)).label("failed"),
                func.avg(
                    func.extract('epoch', Task.completed_at - Task.started_at)
                ).label("avg_duration"),
            ).where(
                and_(
                    Task.created_at >= baseline_start,
                    Task.created_at < current_start,
                )
            )
        )
        baseline = baseline_result.first()

        if not current or not baseline:
            return anomalies

        # Normalize baseline to same period
        baseline_total = (baseline.total or 0) / 7
        baseline_failed = (baseline.failed or 0) / 7
        baseline_duration = baseline.avg_duration or 0

        current_total = current.total or 0
        current_failed = current.failed or 0
        current_duration = current.avg_duration or 0

        # Check for anomalies (> 50% deviation)
        if baseline_total > 0:
            total_deviation = ((current_total - baseline_total) / baseline_total) * 100
            if abs(total_deviation) > 50:
                anomalies.append(AnomalyDetection(
                    metric_name="task_volume",
                    detected_at=now,
                    severity=InsightPriority.MEDIUM if abs(total_deviation) < 100 else InsightPriority.HIGH,
                    expected_value=baseline_total,
                    actual_value=current_total,
                    deviation_percent=total_deviation,
                    possible_causes=[
                        "Increased/decreased workload",
                        "System capacity changes",
                        "External factors affecting task submission",
                    ],
                    suggested_actions=[
                        "Monitor agent capacity",
                        "Review task queue backlog",
                        "Scale agents if needed",
                    ],
                ))

        if baseline_failed > 0:
            failed_deviation = ((current_failed - baseline_failed) / baseline_failed) * 100
            if failed_deviation > 50:
                anomalies.append(AnomalyDetection(
                    metric_name="task_failure_rate",
                    detected_at=now,
                    severity=InsightPriority.HIGH if failed_deviation > 100 else InsightPriority.MEDIUM,
                    expected_value=baseline_failed,
                    actual_value=current_failed,
                    deviation_percent=failed_deviation,
                    possible_causes=[
                        "Configuration issues",
                        "Resource constraints",
                        "External service failures",
                        "Code changes affecting stability",
                    ],
                    suggested_actions=[
                        "Review recent deployments",
                        "Check error logs for patterns",
                        "Verify external dependencies",
                        "Consider rolling back recent changes",
                    ],
                ))

        if baseline_duration > 0 and current_duration > 0:
            duration_deviation = ((current_duration - baseline_duration) / baseline_duration) * 100
            if duration_deviation > 50:
                anomalies.append(AnomalyDetection(
                    metric_name="task_duration",
                    detected_at=now,
                    severity=InsightPriority.MEDIUM,
                    expected_value=baseline_duration,
                    actual_value=current_duration,
                    deviation_percent=duration_deviation,
                    possible_causes=[
                        "Increased task complexity",
                        "Resource contention",
                        "Network latency",
                        "External service slowdowns",
                    ],
                    suggested_actions=[
                        "Profile slow tasks",
                        "Check system resources",
                        "Optimize database queries",
                        "Review external API performance",
                    ],
                ))

        return anomalies

    async def generate_optimization_insights(
        self,
        session: AsyncSession,
    ) -> List[Insight]:
        """Generate optimization insights based on current state."""
        from shared.database.models import Agent, Task
        from uuid import uuid4

        insights = []
        now = datetime.utcnow()
        day_ago = now - timedelta(days=1)

        # Check for idle agents
        idle_agents_result = await session.execute(
            select(func.count(Agent.id)).where(Agent.status == "idle")
        )
        idle_count = idle_agents_result.scalar() or 0

        pending_tasks_result = await session.execute(
            select(func.count(Task.id)).where(Task.status == "pending")
        )
        pending_count = pending_tasks_result.scalar() or 0

        if idle_count > 3 and pending_count == 0:
            insights.append(Insight(
                id=str(uuid4()),
                type=InsightType.OPTIMIZATION,
                priority=InsightPriority.LOW,
                title="Excess Idle Agents",
                description=f"There are {idle_count} idle agents with no pending tasks.",
                impact="Resources may be over-provisioned, leading to unnecessary costs.",
                recommendations=[
                    f"Consider scaling down by {idle_count - 2} agents",
                    "Implement auto-scaling based on queue depth",
                    "Review agent pool configurations",
                ],
                affected_resources=["agent_pool"],
                confidence=0.85,
                created_at=now,
                expires_at=now + timedelta(hours=6),
            ))

        if pending_count > 50 and idle_count == 0:
            insights.append(Insight(
                id=str(uuid4()),
                type=InsightType.OPTIMIZATION,
                priority=InsightPriority.HIGH,
                title="Task Queue Backlog",
                description=f"There are {pending_count} pending tasks with no idle agents available.",
                impact="Tasks are experiencing delays. User experience may be affected.",
                recommendations=[
                    "Scale up agent pool immediately",
                    "Enable burst scaling if available",
                    "Review task priorities and defer non-critical work",
                ],
                affected_resources=["task_queue", "agent_pool"],
                confidence=0.95,
                created_at=now,
                expires_at=now + timedelta(hours=1),
            ))

        # Check for high failure rates
        failure_result = await session.execute(
            select(
                func.count(Task.id).filter(Task.status == "failed").label("failed"),
                func.count(Task.id).label("total"),
            ).where(Task.created_at >= day_ago)
        )
        failure_row = failure_result.first()
        if failure_row and failure_row.total > 10:
            failure_rate = (failure_row.failed / failure_row.total) * 100
            if failure_rate > 10:
                insights.append(Insight(
                    id=str(uuid4()),
                    type=InsightType.ANOMALY,
                    priority=InsightPriority.HIGH if failure_rate > 20 else InsightPriority.MEDIUM,
                    title="Elevated Task Failure Rate",
                    description=f"Task failure rate is {failure_rate:.1f}% over the last 24 hours.",
                    impact="System reliability is degraded. Failed tasks may need retry.",
                    recommendations=[
                        "Review error logs for common failure patterns",
                        "Check agent health and resource usage",
                        "Verify external service connectivity",
                        "Consider implementing circuit breakers",
                    ],
                    affected_resources=["tasks", "agents"],
                    confidence=0.9,
                    created_at=now,
                    expires_at=now + timedelta(hours=4),
                ))

        return insights

    async def get_predictions(
        self,
        session: AsyncSession,
        hours_ahead: int = 24,
    ) -> Dict[str, Any]:
        """Generate predictions for system behavior."""
        from shared.database.models import Task

        # Get historical patterns (last 7 days by hour)
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)

        hourly_result = await session.execute(
            select(
                func.extract('hour', Task.created_at).label("hour"),
                func.count(Task.id).label("count"),
            ).where(Task.created_at >= week_ago).group_by(
                func.extract('hour', Task.created_at)
            )
        )
        hourly_patterns = {int(row.hour): row.count / 7 for row in hourly_result}

        # Generate predictions
        predictions = []
        for i in range(hours_ahead):
            pred_time = now + timedelta(hours=i)
            hour = pred_time.hour
            expected_tasks = hourly_patterns.get(hour, 0)
            predictions.append({
                "timestamp": pred_time.isoformat(),
                "hour": hour,
                "predicted_tasks": round(expected_tasks, 1),
                "confidence": 0.7 if hour in hourly_patterns else 0.3,
            })

        return {
            "generated_at": now.isoformat(),
            "horizon_hours": hours_ahead,
            "predictions": predictions,
            "model": "simple_hourly_average",
            "note": "Predictions based on 7-day hourly averages",
        }

    async def cache_insight(self, insight: Insight):
        """Cache an insight in Redis."""
        try:
            redis = await redis_manager.get_client()
            if redis:
                key = f"insights:{insight.id}"
                await redis.setex(
                    key,
                    self.cache_ttl,
                    insight.model_dump_json(),
                )
        except Exception as e:
            logger.error(f"Failed to cache insight: {e}")

    async def get_cached_insights(
        self,
        insight_type: Optional[InsightType] = None,
    ) -> List[Insight]:
        """Get cached insights."""
        try:
            redis = await redis_manager.get_client()
            if not redis:
                return []

            keys = await redis.keys("insights:*")
            insights = []

            for key in keys:
                data = await redis.get(key)
                if data:
                    insight = Insight.model_validate_json(data)
                    if insight_type is None or insight.type == insight_type:
                        insights.append(insight)

            return sorted(insights, key=lambda x: x.created_at, reverse=True)
        except Exception as e:
            logger.error(f"Failed to get cached insights: {e}")
            return []
