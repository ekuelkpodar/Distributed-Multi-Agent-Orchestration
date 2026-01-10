"""
API routes for Analytics and Insights.
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from shared.database.connections import get_db_session
from services.metrics_service import (
    MetricsService,
    TimeGranularity,
    MetricAggregation,
    TimeSeriesPoint,
    PerformanceReport,
    SystemMetrics,
)
from services.insights_service import (
    AIInsightsService,
    InsightType,
    Insight,
    PerformanceAnalysis,
    AnomalyDetection,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/analytics", tags=["Analytics"])

# Service instances (initialized on startup)
metrics_service: Optional[MetricsService] = None
insights_service: Optional[AIInsightsService] = None


def get_metrics_service() -> MetricsService:
    if metrics_service is None:
        raise RuntimeError("Metrics service not initialized")
    return metrics_service


def get_insights_service() -> AIInsightsService:
    if insights_service is None:
        raise RuntimeError("Insights service not initialized")
    return insights_service


# Metrics endpoints

@router.get("/metrics/system", response_model=SystemMetrics)
async def get_system_metrics(
    session: AsyncSession = Depends(get_db_session),
    service: MetricsService = Depends(get_metrics_service),
):
    """Get current system-wide metrics snapshot."""
    return await service.get_system_metrics(session)


@router.get("/metrics/trending")
async def get_trending_metrics(
    hours: int = Query(24, ge=1, le=168),
    session: AsyncSession = Depends(get_db_session),
    service: MetricsService = Depends(get_metrics_service),
):
    """Get trending metrics comparing current period to previous."""
    return await service.get_trending_metrics(session, hours)


@router.get("/metrics/timeseries")
async def get_time_series(
    metric_name: str,
    start_time: datetime,
    end_time: Optional[datetime] = None,
    granularity: TimeGranularity = TimeGranularity.HOUR,
    service: MetricsService = Depends(get_metrics_service),
):
    """Get time series data for a specific metric."""
    if end_time is None:
        end_time = datetime.utcnow()

    points = await service.get_time_series(
        metric_name,
        start_time,
        end_time,
        granularity,
    )

    return {
        "metric_name": metric_name,
        "start_time": start_time,
        "end_time": end_time,
        "granularity": granularity,
        "data_points": [p.model_dump() for p in points],
    }


@router.get("/metrics/aggregation", response_model=MetricAggregation)
async def get_metric_aggregation(
    metric_name: str,
    start_time: datetime,
    end_time: Optional[datetime] = None,
    granularity: TimeGranularity = TimeGranularity.HOUR,
    service: MetricsService = Depends(get_metrics_service),
):
    """Get aggregated metrics for a time period."""
    if end_time is None:
        end_time = datetime.utcnow()

    result = await service.get_aggregation(
        metric_name,
        start_time,
        end_time,
        granularity,
    )

    if not result:
        raise HTTPException(status_code=404, detail="No metrics found")

    return result


@router.get("/agents/{agent_id}/performance", response_model=PerformanceReport)
async def get_agent_performance(
    agent_id: UUID,
    hours: int = Query(24, ge=1, le=720),
    session: AsyncSession = Depends(get_db_session),
    service: MetricsService = Depends(get_metrics_service),
):
    """Get detailed performance report for an agent."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)

    report = await service.get_agent_performance(
        session,
        agent_id,
        start_time,
        end_time,
    )

    if not report:
        raise HTTPException(status_code=404, detail="Agent not found")

    return report


# Insights endpoints

@router.get("/insights", response_model=list[Insight])
async def get_insights(
    insight_type: Optional[InsightType] = None,
    service: AIInsightsService = Depends(get_insights_service),
):
    """Get cached AI-generated insights."""
    return await service.get_cached_insights(insight_type)


@router.get("/insights/performance", response_model=PerformanceAnalysis)
async def analyze_performance(
    hours: int = Query(24, ge=1, le=168),
    session: AsyncSession = Depends(get_db_session),
    service: AIInsightsService = Depends(get_insights_service),
):
    """Analyze system performance and get AI-powered insights."""
    result = await service.analyze_performance(session, hours)
    if not result:
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze performance"
        )
    return result


@router.get("/insights/anomalies", response_model=list[AnomalyDetection])
async def detect_anomalies(
    hours: int = Query(24, ge=1, le=168),
    session: AsyncSession = Depends(get_db_session),
    service: AIInsightsService = Depends(get_insights_service),
):
    """Detect anomalies in system behavior."""
    return await service.detect_anomalies(session, hours)


@router.get("/insights/optimization", response_model=list[Insight])
async def get_optimization_insights(
    session: AsyncSession = Depends(get_db_session),
    service: AIInsightsService = Depends(get_insights_service),
):
    """Generate optimization insights based on current state."""
    return await service.generate_optimization_insights(session)


@router.get("/insights/predictions")
async def get_predictions(
    hours_ahead: int = Query(24, ge=1, le=168),
    session: AsyncSession = Depends(get_db_session),
    service: AIInsightsService = Depends(get_insights_service),
):
    """Generate predictions for system behavior."""
    return await service.get_predictions(session, hours_ahead)


# Dashboard summary endpoint

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    session: AsyncSession = Depends(get_db_session),
    metrics: MetricsService = Depends(get_metrics_service),
    insights: AIInsightsService = Depends(get_insights_service),
):
    """Get comprehensive dashboard summary with metrics and insights."""
    # Get system metrics
    system_metrics = await metrics.get_system_metrics(session)

    # Get trending data
    trending = await metrics.get_trending_metrics(session, 24)

    # Get any cached insights
    cached_insights = await insights.get_cached_insights()

    # Get anomalies
    anomalies = await insights.detect_anomalies(session, 24)

    return {
        "timestamp": datetime.utcnow(),
        "system_metrics": system_metrics.model_dump(),
        "trending": trending,
        "insights_count": len(cached_insights),
        "recent_insights": [i.model_dump() for i in cached_insights[:5]],
        "anomalies_count": len(anomalies),
        "anomalies": [a.model_dump() for a in anomalies[:3]],
    }
