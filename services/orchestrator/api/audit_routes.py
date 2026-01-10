"""
API routes for Audit Trail.
"""

from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
import structlog

from services.audit_service import (
    AuditService,
    AuditEntry,
    AuditQuery,
    AuditSummary,
    AuditEventType,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/audit", tags=["Audit"])

# Service instance (initialized on startup)
audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    if audit_service is None:
        raise RuntimeError("Audit service not initialized")
    return audit_service


class AuditQueryRequest(BaseModel):
    """Request model for audit queries."""
    event_types: Optional[List[AuditEventType]] = None
    actor_id: Optional[str] = None
    actor_type: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    success: Optional[bool] = None
    search_text: Optional[str] = None
    page: int = 1
    page_size: int = 50


@router.get("/entries", response_model=List[AuditEntry])
async def query_audit_entries(
    event_types: Optional[str] = None,  # Comma-separated
    actor_id: Optional[str] = None,
    actor_type: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    success: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: AuditService = Depends(get_audit_service),
):
    """Query audit log entries with filters."""
    # Parse event types
    parsed_types = None
    if event_types:
        try:
            parsed_types = [
                AuditEventType(t.strip())
                for t in event_types.split(",")
            ]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid event type: {e}")

    query = AuditQuery(
        event_types=parsed_types,
        actor_id=actor_id,
        actor_type=actor_type,
        resource_type=resource_type,
        resource_id=resource_id,
        start_time=start_time,
        end_time=end_time,
        success=success,
        search_text=search,
        page=page,
        page_size=page_size,
    )

    return await service.query(query)


@router.post("/entries/search", response_model=List[AuditEntry])
async def search_audit_entries(
    request: AuditQueryRequest,
    service: AuditService = Depends(get_audit_service),
):
    """Advanced audit log search with POST body."""
    query = AuditQuery(**request.model_dump())
    return await service.query(query)


@router.get("/entries/{entry_id}", response_model=AuditEntry)
async def get_audit_entry(
    entry_id: str,
    service: AuditService = Depends(get_audit_service),
):
    """Get a single audit entry by ID."""
    entry = await service.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Audit entry not found")
    return entry


@router.get("/summary", response_model=AuditSummary)
async def get_audit_summary(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    service: AuditService = Depends(get_audit_service),
):
    """Get summary of audit events."""
    return await service.get_summary(start_time, end_time)


@router.get("/resources/{resource_type}/{resource_id}", response_model=List[AuditEntry])
async def get_resource_history(
    resource_type: str,
    resource_id: str,
    limit: int = Query(100, ge=1, le=500),
    service: AuditService = Depends(get_audit_service),
):
    """Get audit history for a specific resource."""
    return await service.get_resource_history(resource_type, resource_id, limit)


@router.get("/actors/{actor_id}", response_model=List[AuditEntry])
async def get_actor_activity(
    actor_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=500),
    service: AuditService = Depends(get_audit_service),
):
    """Get all activity for a specific actor."""
    return await service.get_actor_activity(actor_id, start_time, end_time, limit)


@router.get("/failed", response_model=List[AuditEntry])
async def get_failed_events(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(100, ge=1, le=500),
    service: AuditService = Depends(get_audit_service),
):
    """Get failed events in the specified time range."""
    return await service.get_failed_events(hours, limit)


@router.get("/security", response_model=List[AuditEntry])
async def get_security_events(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(100, ge=1, le=500),
    service: AuditService = Depends(get_audit_service),
):
    """Get security-related events."""
    return await service.get_security_events(hours, limit)


@router.get("/event-types")
async def list_event_types():
    """List all available audit event types."""
    return {
        "event_types": [
            {
                "value": e.value,
                "name": e.name,
                "category": e.value.split(".")[0],
            }
            for e in AuditEventType
        ]
    }
