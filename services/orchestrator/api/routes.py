"""
API routes for the Orchestrator Service.
Provides REST endpoints for agent and task management.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from shared.database.connections import get_db_session
from shared.models.schemas import (
    AgentType,
    AgentStatus,
    TaskStatus,
    AgentSpawnRequest,
    TaskSubmitRequest,
)
from api.schemas import (
    SpawnAgentRequest,
    SpawnAgentResponse,
    AgentResponse,
    AgentListResponse,
    SubmitTaskRequest,
    SubmitTaskResponse,
    TaskResponse,
    TaskListResponse,
    TaskStatusResponse,
    UpdateTaskRequest,
    AddDependencyRequest,
    HealthResponse,
    ErrorResponse,
)
from core.agent_manager import AgentManager
from core.task_scheduler import TaskScheduler
from core.state_coordinator import state_coordinator

logger = structlog.get_logger()

# Initialize routers
router = APIRouter()
agents_router = APIRouter(prefix="/agents", tags=["Agents"])
tasks_router = APIRouter(prefix="/tasks", tags=["Tasks"])
health_router = APIRouter(prefix="/health", tags=["Health"])

# Core managers (initialized on startup)
agent_manager: Optional[AgentManager] = None
task_scheduler: Optional[TaskScheduler] = None
advanced_scheduler = None  # AdvancedScheduler instance


def get_agent_manager() -> AgentManager:
    """Dependency to get agent manager."""
    if agent_manager is None:
        raise RuntimeError("Agent manager not initialized")
    return agent_manager


def get_task_scheduler() -> TaskScheduler:
    """Dependency to get task scheduler."""
    if task_scheduler is None:
        raise RuntimeError("Task scheduler not initialized")
    return task_scheduler


# Agent Routes

@agents_router.post("/spawn", response_model=SpawnAgentResponse)
async def spawn_agent(
    request: SpawnAgentRequest,
    session: AsyncSession = Depends(get_db_session),
    manager: AgentManager = Depends(get_agent_manager),
):
    """Spawn a new agent with the specified configuration."""
    try:
        spawn_request = AgentSpawnRequest(
            agent_type=request.agent_type,
            name=request.name,
            capabilities=request.capabilities,
            config=request.config,
            parent_id=request.parent_id,
        )
        result = await manager.spawn_agent(session, spawn_request)

        return SpawnAgentResponse(
            agent_id=result.agent_id,
            name=request.name or f"{request.agent_type.value}-agent",
            status=result.status,
            message=result.message,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to spawn agent", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to spawn agent")


@agents_router.get("", response_model=AgentListResponse)
async def list_agents(
    agent_type: Optional[AgentType] = None,
    status: Optional[AgentStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    manager: AgentManager = Depends(get_agent_manager),
):
    """List agents with optional filtering."""
    offset = (page - 1) * page_size
    agents = await manager.get_agents(
        session,
        agent_type=agent_type,
        status=status,
        limit=page_size,
        offset=offset,
    )

    agent_responses = []
    for agent in agents:
        from shared.models.schemas import AgentCapabilities, AgentConfig
        agent_responses.append(AgentResponse(
            id=agent.id,
            name=agent.name,
            type=AgentType(agent.type),
            status=AgentStatus(agent.status),
            capabilities=AgentCapabilities(**agent.capabilities),
            config=AgentConfig(**agent.config),
            parent_id=agent.parent_id,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            last_heartbeat=agent.last_heartbeat,
        ))

    return AgentListResponse(
        agents=agent_responses,
        total=len(agents),
        page=page,
        page_size=page_size,
    )


@agents_router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    manager: AgentManager = Depends(get_agent_manager),
):
    """Get agent by ID."""
    agent = await manager.get_agent(session, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    from shared.models.schemas import AgentCapabilities, AgentConfig
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        type=AgentType(agent.type),
        status=AgentStatus(agent.status),
        capabilities=AgentCapabilities(**agent.capabilities),
        config=AgentConfig(**agent.config),
        parent_id=agent.parent_id,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        last_heartbeat=agent.last_heartbeat,
    )


@agents_router.post("/{agent_id}/heartbeat")
async def record_heartbeat(
    agent_id: UUID,
    metrics: Optional[dict] = None,
    session: AsyncSession = Depends(get_db_session),
    manager: AgentManager = Depends(get_agent_manager),
):
    """Record agent heartbeat."""
    success = await manager.record_heartbeat(session, agent_id, metrics)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"status": "ok"}


@agents_router.post("/{agent_id}/terminate")
async def terminate_agent(
    agent_id: UUID,
    reason: str = "manual",
    session: AsyncSession = Depends(get_db_session),
    manager: AgentManager = Depends(get_agent_manager),
):
    """Terminate an agent gracefully."""
    success = await manager.terminate_agent(session, agent_id, reason)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"status": "terminated", "agent_id": str(agent_id)}


@agents_router.patch("/{agent_id}/status")
async def update_agent_status(
    agent_id: UUID,
    status: AgentStatus,
    session: AsyncSession = Depends(get_db_session),
    manager: AgentManager = Depends(get_agent_manager),
):
    """Update agent status."""
    agent = await manager.update_agent_status(session, agent_id, status)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"status": "updated", "agent_id": str(agent_id), "new_status": status}


# Task Routes

@tasks_router.post("/submit", response_model=SubmitTaskResponse)
async def submit_task(
    request: SubmitTaskRequest,
    session: AsyncSession = Depends(get_db_session),
    scheduler: TaskScheduler = Depends(get_task_scheduler),
):
    """Submit a new task to the queue."""
    try:
        task_request = TaskSubmitRequest(
            description=request.description,
            priority=request.priority,
            deadline=request.deadline,
            context=request.context,
            agent_type=request.agent_type,
            agent_id=request.agent_id,
        )
        result = await scheduler.submit_task(session, task_request)

        return SubmitTaskResponse(
            task_id=result.task_id,
            status=result.status,
            assigned_agent=result.assigned_agent,
            message=result.message,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to submit task", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to submit task")


@tasks_router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[TaskStatus] = None,
    agent_id: Optional[UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
):
    """List tasks with optional filtering."""
    from sqlalchemy import select
    from shared.database.models import Task

    query = select(Task)

    if status:
        query = query.where(Task.status == status.value)
    if agent_id:
        query = query.where(Task.agent_id == agent_id)

    query = query.order_by(Task.created_at.desc())
    query = query.limit(page_size).offset((page - 1) * page_size)

    result = await session.execute(query)
    tasks = result.scalars().all()

    task_responses = [
        TaskResponse(
            id=task.id,
            description=task.description,
            status=TaskStatus(task.status),
            priority=task.priority,
            agent_id=task.agent_id,
            parent_task_id=task.parent_task_id,
            input_data=task.input_data,
            output_data=task.output_data,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
        )
        for task in tasks
    ]

    return TaskListResponse(
        tasks=task_responses,
        total=len(tasks),
        page=page,
        page_size=page_size,
    )


@tasks_router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    scheduler: TaskScheduler = Depends(get_task_scheduler),
):
    """Get task by ID."""
    task = await scheduler.get_task(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse(
        id=task.id,
        description=task.description,
        status=TaskStatus(task.status),
        priority=task.priority,
        agent_id=task.agent_id,
        parent_task_id=task.parent_task_id,
        input_data=task.input_data,
        output_data=task.output_data,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
    )


@tasks_router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    scheduler: TaskScheduler = Depends(get_task_scheduler),
):
    """Get detailed task status."""
    status = await scheduler.get_task_status(session, task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatusResponse(
        task_id=status.task_id,
        status=status.status,
        assigned_agent=status.assigned_agent,
        progress=status.progress,
        started_at=status.started_at,
        estimated_completion=status.estimated_completion,
        result=status.result,
    )


@tasks_router.patch("/{task_id}")
async def update_task(
    task_id: UUID,
    request: UpdateTaskRequest,
    session: AsyncSession = Depends(get_db_session),
    scheduler: TaskScheduler = Depends(get_task_scheduler),
):
    """Update task status or complete task."""
    task = await scheduler.get_task(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if request.status == TaskStatus.COMPLETED and request.result is not None:
        await scheduler.complete_task(session, task_id, request.result)
    elif request.status == TaskStatus.FAILED and request.error:
        await scheduler.fail_task(session, task_id, request.error)
    elif request.progress is not None:
        await scheduler.update_task_progress(session, task_id, request.progress)

    return {"status": "updated", "task_id": str(task_id)}


@tasks_router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    scheduler: TaskScheduler = Depends(get_task_scheduler),
):
    """Cancel a pending task."""
    success = await scheduler.cancel_task(session, task_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Task cannot be cancelled (may be completed or already cancelled)"
        )
    return {"status": "cancelled", "task_id": str(task_id)}


@tasks_router.post("/{task_id}/dependencies")
async def add_dependency(
    task_id: UUID,
    request: AddDependencyRequest,
    session: AsyncSession = Depends(get_db_session),
    scheduler: TaskScheduler = Depends(get_task_scheduler),
):
    """Add a dependency to a task."""
    success = await scheduler.add_dependency(
        session,
        task_id,
        request.depends_on_task_id,
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add dependency")
    return {"status": "dependency_added", "task_id": str(task_id)}


# Health Routes

@health_router.get("", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint."""
    from shared.database.connections import db_manager, redis_manager

    components = {}

    # Check database
    db_health = await db_manager.health_check()
    components["database"] = db_health

    # Check Redis
    redis_health = await redis_manager.health_check()
    components["redis"] = redis_health

    # Determine overall status
    all_healthy = all(
        c.get("status") == "healthy"
        for c in components.values()
    )

    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        components=components,
    )


@health_router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe."""
    from shared.database.connections import db_manager, redis_manager

    try:
        # Check database connection
        db_health = await db_manager.health_check()
        if db_health.get("status") != "healthy":
            raise HTTPException(status_code=503, detail="Database not ready")

        # Check Redis connection
        redis_health = await redis_manager.health_check()
        if redis_health.get("status") != "healthy":
            raise HTTPException(status_code=503, detail="Redis not ready")

        return {"status": "ready"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@health_router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe."""
    return {"status": "alive"}


# WebSocket for Real-time Events

@router.websocket("/events/stream")
async def websocket_events(websocket: WebSocket):
    """WebSocket endpoint for real-time event streaming."""
    await websocket.accept()

    try:
        # Subscribe to Redis pub/sub for events
        async for event in state_coordinator.subscribe(
            "agent.events",
            "task.events",
        ):
            await websocket.send_json(event)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# Include routers
router.include_router(agents_router)
router.include_router(tasks_router)
router.include_router(health_router)
