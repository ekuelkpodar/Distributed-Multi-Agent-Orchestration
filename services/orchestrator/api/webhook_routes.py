"""
API routes for Webhooks.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, HttpUrl
import structlog

from services.webhook_service import (
    WebhookService,
    WebhookConfig,
    WebhookDelivery,
    WebhookEventType,
    WebhookStatus,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# Service instance (initialized on startup)
webhook_service: Optional[WebhookService] = None


def get_webhook_service() -> WebhookService:
    if webhook_service is None:
        raise RuntimeError("Webhook service not initialized")
    return webhook_service


class CreateWebhookRequest(BaseModel):
    """Request to create a webhook."""
    name: str
    url: str
    events: List[WebhookEventType]
    secret: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None


class UpdateWebhookRequest(BaseModel):
    """Request to update a webhook."""
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[List[WebhookEventType]] = None
    status: Optional[WebhookStatus] = None
    headers: Optional[Dict[str, str]] = None


class WebhookResponse(BaseModel):
    """Webhook response model."""
    id: str
    name: str
    url: str
    events: List[WebhookEventType]
    status: WebhookStatus
    headers: Dict[str, str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_delivery_at: Optional[datetime]
    failure_count: int
    success_count: int
    # Note: secret is not returned for security


@router.post("", response_model=WebhookResponse)
async def create_webhook(
    request: CreateWebhookRequest,
    service: WebhookService = Depends(get_webhook_service),
):
    """Create a new webhook endpoint."""
    webhook = await service.register_webhook(
        name=request.name,
        url=request.url,
        events=request.events,
        secret=request.secret,
        headers=request.headers,
        metadata=request.metadata,
    )

    return WebhookResponse(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        events=webhook.events,
        status=webhook.status,
        headers=webhook.headers,
        metadata=webhook.metadata,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
        last_delivery_at=webhook.last_delivery_at,
        failure_count=webhook.failure_count,
        success_count=webhook.success_count,
    )


@router.get("", response_model=List[WebhookResponse])
async def list_webhooks(
    status: Optional[WebhookStatus] = None,
    service: WebhookService = Depends(get_webhook_service),
):
    """List all webhooks."""
    webhooks = await service.list_webhooks(status)
    return [
        WebhookResponse(
            id=w.id,
            name=w.name,
            url=w.url,
            events=w.events,
            status=w.status,
            headers=w.headers,
            metadata=w.metadata,
            created_at=w.created_at,
            updated_at=w.updated_at,
            last_delivery_at=w.last_delivery_at,
            failure_count=w.failure_count,
            success_count=w.success_count,
        )
        for w in webhooks
    ]


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: str,
    service: WebhookService = Depends(get_webhook_service),
):
    """Get a webhook by ID."""
    webhook = await service.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return WebhookResponse(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        events=webhook.events,
        status=webhook.status,
        headers=webhook.headers,
        metadata=webhook.metadata,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
        last_delivery_at=webhook.last_delivery_at,
        failure_count=webhook.failure_count,
        success_count=webhook.success_count,
    )


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    request: UpdateWebhookRequest,
    service: WebhookService = Depends(get_webhook_service),
):
    """Update a webhook."""
    webhook = await service.update_webhook(
        webhook_id=webhook_id,
        name=request.name,
        url=request.url,
        events=request.events,
        status=request.status,
        headers=request.headers,
    )

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return WebhookResponse(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        events=webhook.events,
        status=webhook.status,
        headers=webhook.headers,
        metadata=webhook.metadata,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
        last_delivery_at=webhook.last_delivery_at,
        failure_count=webhook.failure_count,
        success_count=webhook.success_count,
    )


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    service: WebhookService = Depends(get_webhook_service),
):
    """Delete a webhook."""
    success = await service.delete_webhook(webhook_id)
    if not success:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return {"status": "deleted", "webhook_id": webhook_id}


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    service: WebhookService = Depends(get_webhook_service),
):
    """Send a test event to a webhook."""
    result = await service.test_webhook(webhook_id)
    return result


@router.get("/{webhook_id}/deliveries", response_model=List[WebhookDelivery])
async def get_delivery_history(
    webhook_id: str,
    limit: int = Query(100, ge=1, le=500),
    service: WebhookService = Depends(get_webhook_service),
):
    """Get delivery history for a webhook."""
    return await service.get_delivery_history(webhook_id, limit)


@router.get("/{webhook_id}/stats")
async def get_webhook_stats(
    webhook_id: str,
    hours: int = Query(24, ge=1, le=168),
    service: WebhookService = Depends(get_webhook_service),
):
    """Get delivery statistics for a webhook."""
    return await service.get_delivery_stats(webhook_id, hours)


@router.get("/stats/all")
async def get_all_webhook_stats(
    hours: int = Query(24, ge=1, le=168),
    service: WebhookService = Depends(get_webhook_service),
):
    """Get delivery statistics across all webhooks."""
    return await service.get_delivery_stats(None, hours)


@router.get("/event-types")
async def list_event_types():
    """List all available webhook event types."""
    return {
        "event_types": [
            {
                "value": e.value,
                "name": e.name,
                "description": _get_event_description(e),
            }
            for e in WebhookEventType
        ]
    }


def _get_event_description(event_type: WebhookEventType) -> str:
    """Get description for an event type."""
    descriptions = {
        WebhookEventType.AGENT_CREATED: "Triggered when a new agent is spawned",
        WebhookEventType.AGENT_UPDATED: "Triggered when an agent configuration is updated",
        WebhookEventType.AGENT_DELETED: "Triggered when an agent is terminated",
        WebhookEventType.AGENT_STATUS_CHANGED: "Triggered when an agent's status changes",
        WebhookEventType.TASK_CREATED: "Triggered when a new task is submitted",
        WebhookEventType.TASK_STARTED: "Triggered when a task begins execution",
        WebhookEventType.TASK_COMPLETED: "Triggered when a task completes successfully",
        WebhookEventType.TASK_FAILED: "Triggered when a task fails",
        WebhookEventType.TASK_CANCELLED: "Triggered when a task is cancelled",
        WebhookEventType.SYSTEM_ALERT: "Triggered for system-level alerts",
        WebhookEventType.SYSTEM_ERROR: "Triggered for system errors",
        WebhookEventType.ALL: "Subscribe to all events",
    }
    return descriptions.get(event_type, "No description available")
