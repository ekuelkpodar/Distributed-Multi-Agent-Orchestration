"""
Webhook System Service
Provides reliable webhook delivery with retries, signatures, and event filtering.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any, Callable
from uuid import UUID, uuid4
import json
import hashlib
import hmac
import asyncio
from dataclasses import dataclass, field

import httpx
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
import structlog

from shared.database.connections import redis_manager

logger = structlog.get_logger()


class WebhookEventType(str, Enum):
    # Agent events
    AGENT_CREATED = "agent.created"
    AGENT_UPDATED = "agent.updated"
    AGENT_DELETED = "agent.deleted"
    AGENT_STATUS_CHANGED = "agent.status_changed"

    # Task events
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"

    # System events
    SYSTEM_ALERT = "system.alert"
    SYSTEM_ERROR = "system.error"

    # All events
    ALL = "*"


class WebhookStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    FAILED = "failed"


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


class WebhookConfig(BaseModel):
    """Webhook endpoint configuration."""
    id: str
    name: str
    url: str
    events: List[WebhookEventType]
    secret: str
    status: WebhookStatus = WebhookStatus.ACTIVE
    headers: Dict[str, str] = {}
    metadata: Dict[str, Any] = {}
    retry_count: int = 3
    retry_delay_seconds: int = 60
    timeout_seconds: int = 30
    created_at: datetime
    updated_at: datetime
    last_delivery_at: Optional[datetime] = None
    failure_count: int = 0
    success_count: int = 0


class WebhookDelivery(BaseModel):
    """Webhook delivery attempt record."""
    id: str
    webhook_id: str
    event_type: WebhookEventType
    payload: Dict[str, Any]
    status: DeliveryStatus
    attempt_count: int = 0
    max_attempts: int = 3
    created_at: datetime
    scheduled_for: datetime
    delivered_at: Optional[datetime] = None
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None


class WebhookEvent(BaseModel):
    """Webhook event payload."""
    id: str
    type: WebhookEventType
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Dict[str, Any] = {}


class WebhookService:
    """
    Webhook System Service for reliable event delivery.
    Supports signatures, retries, and event filtering.
    """

    def __init__(self):
        self._webhooks: Dict[str, WebhookConfig] = {}
        self._delivery_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._workers: List[asyncio.Task] = []
        self._http_client: Optional[httpx.AsyncClient] = None
        self._redis_prefix = "webhooks"

    async def start(self, worker_count: int = 3):
        """Start the webhook delivery workers."""
        self._running = True
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
        )

        # Load webhooks from storage
        await self._load_webhooks()

        # Start delivery workers
        for i in range(worker_count):
            worker = asyncio.create_task(self._delivery_worker(i))
            self._workers.append(worker)

        # Start retry scheduler
        self._workers.append(asyncio.create_task(self._retry_scheduler()))

        logger.info(f"WebhookService started with {worker_count} workers")

    async def stop(self):
        """Stop the webhook service."""
        self._running = False

        # Cancel all workers
        for worker in self._workers:
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass

        if self._http_client:
            await self._http_client.aclose()

        logger.info("WebhookService stopped")

    async def _load_webhooks(self):
        """Load webhooks from Redis."""
        try:
            redis = await redis_manager.get_client()
            if not redis:
                return

            keys = await redis.keys(f"{self._redis_prefix}:config:*")
            for key in keys:
                data = await redis.get(key)
                if data:
                    webhook = WebhookConfig.model_validate_json(data)
                    self._webhooks[webhook.id] = webhook
        except Exception as e:
            logger.error(f"Failed to load webhooks: {e}")

    async def _save_webhook(self, webhook: WebhookConfig):
        """Save webhook to Redis."""
        try:
            redis = await redis_manager.get_client()
            if redis:
                key = f"{self._redis_prefix}:config:{webhook.id}"
                await redis.set(key, webhook.model_dump_json())
        except Exception as e:
            logger.error(f"Failed to save webhook: {e}")

    async def register_webhook(
        self,
        name: str,
        url: str,
        events: List[WebhookEventType],
        secret: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WebhookConfig:
        """Register a new webhook endpoint."""
        webhook_id = str(uuid4())
        now = datetime.utcnow()

        webhook = WebhookConfig(
            id=webhook_id,
            name=name,
            url=url,
            events=events,
            secret=secret or self._generate_secret(),
            headers=headers or {},
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )

        self._webhooks[webhook_id] = webhook
        await self._save_webhook(webhook)

        logger.info(f"Registered webhook: {name} ({webhook_id})")
        return webhook

    def _generate_secret(self) -> str:
        """Generate a random webhook secret."""
        import secrets
        return secrets.token_hex(32)

    async def update_webhook(
        self,
        webhook_id: str,
        name: Optional[str] = None,
        url: Optional[str] = None,
        events: Optional[List[WebhookEventType]] = None,
        status: Optional[WebhookStatus] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[WebhookConfig]:
        """Update a webhook configuration."""
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return None

        if name is not None:
            webhook.name = name
        if url is not None:
            webhook.url = url
        if events is not None:
            webhook.events = events
        if status is not None:
            webhook.status = status
        if headers is not None:
            webhook.headers = headers

        webhook.updated_at = datetime.utcnow()

        await self._save_webhook(webhook)
        return webhook

    async def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook."""
        if webhook_id not in self._webhooks:
            return False

        del self._webhooks[webhook_id]

        try:
            redis = await redis_manager.get_client()
            if redis:
                await redis.delete(f"{self._redis_prefix}:config:{webhook_id}")
        except Exception as e:
            logger.error(f"Failed to delete webhook from Redis: {e}")

        logger.info(f"Deleted webhook: {webhook_id}")
        return True

    async def get_webhook(self, webhook_id: str) -> Optional[WebhookConfig]:
        """Get a webhook by ID."""
        return self._webhooks.get(webhook_id)

    async def list_webhooks(
        self,
        status: Optional[WebhookStatus] = None,
    ) -> List[WebhookConfig]:
        """List all webhooks with optional filtering."""
        webhooks = list(self._webhooks.values())
        if status:
            webhooks = [w for w in webhooks if w.status == status]
        return webhooks

    async def trigger_event(
        self,
        event_type: WebhookEventType,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Trigger a webhook event."""
        event = WebhookEvent(
            id=str(uuid4()),
            type=event_type,
            timestamp=datetime.utcnow(),
            data=data,
            metadata=metadata or {},
        )

        # Find matching webhooks
        for webhook in self._webhooks.values():
            if webhook.status != WebhookStatus.ACTIVE:
                continue

            if WebhookEventType.ALL in webhook.events or event_type in webhook.events:
                await self._queue_delivery(webhook, event)

    async def _queue_delivery(self, webhook: WebhookConfig, event: WebhookEvent):
        """Queue a webhook delivery."""
        delivery = WebhookDelivery(
            id=str(uuid4()),
            webhook_id=webhook.id,
            event_type=event.type,
            payload=event.model_dump(),
            status=DeliveryStatus.PENDING,
            max_attempts=webhook.retry_count,
            created_at=datetime.utcnow(),
            scheduled_for=datetime.utcnow(),
        )

        # Store delivery record
        await self._store_delivery(delivery)

        # Queue for delivery
        await self._delivery_queue.put(delivery)

    async def _store_delivery(self, delivery: WebhookDelivery):
        """Store delivery record in Redis."""
        try:
            redis = await redis_manager.get_client()
            if redis:
                key = f"{self._redis_prefix}:delivery:{delivery.id}"
                await redis.setex(key, 86400 * 7, delivery.model_dump_json())  # 7 days
        except Exception as e:
            logger.error(f"Failed to store delivery: {e}")

    async def _delivery_worker(self, worker_id: int):
        """Worker that processes webhook deliveries."""
        logger.info(f"Webhook delivery worker {worker_id} started")

        while self._running:
            try:
                # Get delivery from queue with timeout
                try:
                    delivery = await asyncio.wait_for(
                        self._delivery_queue.get(),
                        timeout=5.0,
                    )
                except asyncio.TimeoutError:
                    continue

                await self._process_delivery(delivery)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Delivery worker {worker_id} error: {e}")
                await asyncio.sleep(1)

    async def _process_delivery(self, delivery: WebhookDelivery):
        """Process a single webhook delivery."""
        webhook = self._webhooks.get(delivery.webhook_id)
        if not webhook:
            logger.warning(f"Webhook not found for delivery: {delivery.webhook_id}")
            return

        delivery.attempt_count += 1
        delivery.status = DeliveryStatus.PENDING

        try:
            # Prepare request
            payload_json = json.dumps(delivery.payload, default=str)
            signature = self._sign_payload(payload_json, webhook.secret)

            headers = {
                "Content-Type": "application/json",
                "X-Webhook-ID": webhook.id,
                "X-Webhook-Signature": signature,
                "X-Webhook-Timestamp": datetime.utcnow().isoformat(),
                "X-Delivery-ID": delivery.id,
                "X-Attempt": str(delivery.attempt_count),
                **webhook.headers,
            }

            # Send request
            start_time = asyncio.get_event_loop().time()
            response = await self._http_client.post(
                webhook.url,
                content=payload_json,
                headers=headers,
                timeout=webhook.timeout_seconds,
            )
            duration = (asyncio.get_event_loop().time() - start_time) * 1000

            delivery.response_status = response.status_code
            delivery.response_body = response.text[:1000] if response.text else None
            delivery.duration_ms = duration

            if 200 <= response.status_code < 300:
                delivery.status = DeliveryStatus.DELIVERED
                delivery.delivered_at = datetime.utcnow()
                webhook.success_count += 1
                webhook.last_delivery_at = datetime.utcnow()
                webhook.failure_count = 0  # Reset on success

                logger.info(
                    f"Webhook delivered: {webhook.name}",
                    delivery_id=delivery.id,
                    status=response.status_code,
                    duration_ms=duration,
                )
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

        except Exception as e:
            error_msg = str(e)
            delivery.error = error_msg
            webhook.failure_count += 1

            if delivery.attempt_count >= delivery.max_attempts:
                delivery.status = DeliveryStatus.FAILED
                logger.error(
                    f"Webhook delivery failed permanently: {webhook.name}",
                    delivery_id=delivery.id,
                    error=error_msg,
                    attempts=delivery.attempt_count,
                )

                # Disable webhook after too many failures
                if webhook.failure_count >= 10:
                    webhook.status = WebhookStatus.FAILED
                    logger.warning(f"Webhook disabled due to failures: {webhook.name}")
            else:
                delivery.status = DeliveryStatus.RETRYING
                # Schedule retry
                delay = webhook.retry_delay_seconds * (2 ** (delivery.attempt_count - 1))
                delivery.scheduled_for = datetime.utcnow() + timedelta(seconds=delay)

                logger.warning(
                    f"Webhook delivery retry scheduled: {webhook.name}",
                    delivery_id=delivery.id,
                    attempt=delivery.attempt_count,
                    next_retry=delivery.scheduled_for,
                )

        # Update records
        await self._store_delivery(delivery)
        await self._save_webhook(webhook)

    def _sign_payload(self, payload: str, secret: str) -> str:
        """Generate HMAC signature for payload."""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

    async def _retry_scheduler(self):
        """Scheduler that re-queues failed deliveries for retry."""
        while self._running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                redis = await redis_manager.get_client()
                if not redis:
                    continue

                # Find deliveries due for retry
                keys = await redis.keys(f"{self._redis_prefix}:delivery:*")
                now = datetime.utcnow()

                for key in keys:
                    data = await redis.get(key)
                    if not data:
                        continue

                    delivery = WebhookDelivery.model_validate_json(data)

                    if (
                        delivery.status == DeliveryStatus.RETRYING
                        and delivery.scheduled_for <= now
                    ):
                        await self._delivery_queue.put(delivery)
                        logger.debug(f"Re-queued delivery for retry: {delivery.id}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Retry scheduler error: {e}")

    async def get_delivery_history(
        self,
        webhook_id: str,
        limit: int = 100,
    ) -> List[WebhookDelivery]:
        """Get delivery history for a webhook."""
        try:
            redis = await redis_manager.get_client()
            if not redis:
                return []

            keys = await redis.keys(f"{self._redis_prefix}:delivery:*")
            deliveries = []

            for key in keys:
                data = await redis.get(key)
                if data:
                    delivery = WebhookDelivery.model_validate_json(data)
                    if delivery.webhook_id == webhook_id:
                        deliveries.append(delivery)

            deliveries.sort(key=lambda x: x.created_at, reverse=True)
            return deliveries[:limit]

        except Exception as e:
            logger.error(f"Failed to get delivery history: {e}")
            return []

    async def get_delivery_stats(
        self,
        webhook_id: Optional[str] = None,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """Get delivery statistics."""
        try:
            redis = await redis_manager.get_client()
            if not redis:
                return {}

            cutoff = datetime.utcnow() - timedelta(hours=hours)
            keys = await redis.keys(f"{self._redis_prefix}:delivery:*")

            total = 0
            delivered = 0
            failed = 0
            retrying = 0
            total_duration = 0
            duration_count = 0

            for key in keys:
                data = await redis.get(key)
                if not data:
                    continue

                delivery = WebhookDelivery.model_validate_json(data)

                if delivery.created_at < cutoff:
                    continue
                if webhook_id and delivery.webhook_id != webhook_id:
                    continue

                total += 1
                if delivery.status == DeliveryStatus.DELIVERED:
                    delivered += 1
                    if delivery.duration_ms:
                        total_duration += delivery.duration_ms
                        duration_count += 1
                elif delivery.status == DeliveryStatus.FAILED:
                    failed += 1
                elif delivery.status == DeliveryStatus.RETRYING:
                    retrying += 1

            return {
                "period_hours": hours,
                "total_deliveries": total,
                "delivered": delivered,
                "failed": failed,
                "retrying": retrying,
                "success_rate": (delivered / total * 100) if total > 0 else 0,
                "average_duration_ms": (total_duration / duration_count) if duration_count > 0 else 0,
            }

        except Exception as e:
            logger.error(f"Failed to get delivery stats: {e}")
            return {}

    async def test_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """Send a test event to a webhook."""
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return {"success": False, "error": "Webhook not found"}

        test_event = WebhookEvent(
            id=str(uuid4()),
            type=WebhookEventType.SYSTEM_ALERT,
            timestamp=datetime.utcnow(),
            data={
                "message": "This is a test webhook delivery",
                "webhook_id": webhook_id,
                "webhook_name": webhook.name,
            },
            metadata={"test": True},
        )

        try:
            payload_json = json.dumps(test_event.model_dump(), default=str)
            signature = self._sign_payload(payload_json, webhook.secret)

            headers = {
                "Content-Type": "application/json",
                "X-Webhook-ID": webhook.id,
                "X-Webhook-Signature": signature,
                "X-Webhook-Timestamp": datetime.utcnow().isoformat(),
                "X-Test": "true",
                **webhook.headers,
            }

            start_time = asyncio.get_event_loop().time()
            response = await self._http_client.post(
                webhook.url,
                content=payload_json,
                headers=headers,
                timeout=10,
            )
            duration = (asyncio.get_event_loop().time() - start_time) * 1000

            return {
                "success": 200 <= response.status_code < 300,
                "status_code": response.status_code,
                "duration_ms": duration,
                "response": response.text[:500] if response.text else None,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
