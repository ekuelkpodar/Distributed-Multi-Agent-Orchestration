"""
Unit tests for the Task Scheduler.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timedelta

from shared.models.schemas import TaskStatus, AgentType, TaskSubmitRequest


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    session.get = AsyncMock()
    return session


@pytest.fixture
def task_scheduler():
    """Create a task scheduler instance."""
    from services.orchestrator.core.task_scheduler import TaskScheduler
    return TaskScheduler(
        default_timeout=300,
        max_retries=3,
        retry_delay=5,
        queue_max_size=10000,
    )


class TestTaskScheduler:
    """Tests for TaskScheduler class."""

    @pytest.mark.asyncio
    async def test_submit_task_success(self, task_scheduler, mock_session):
        """Test successful task submission."""
        with patch.object(task_scheduler, '_get_queue_size', return_value=0):
            request = TaskSubmitRequest(
                description="Test task description",
                priority=1,
                agent_type=AgentType.RESEARCH,
            )

            result = await task_scheduler.submit_task(mock_session, request)

            assert result.task_id is not None
            assert result.status == TaskStatus.PENDING
            assert "successfully" in result.message

    @pytest.mark.asyncio
    async def test_submit_task_queue_full(self, task_scheduler, mock_session):
        """Test task submission when queue is full."""
        with patch.object(task_scheduler, '_get_queue_size', return_value=10000):
            request = TaskSubmitRequest(
                description="Test task",
                priority=1,
            )

            with pytest.raises(ValueError, match="Task queue full"):
                await task_scheduler.submit_task(mock_session, request)

    @pytest.mark.asyncio
    async def test_get_task_status(self, task_scheduler, mock_session):
        """Test getting task status."""
        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.status = TaskStatus.IN_PROGRESS.value
        mock_task.agent_id = uuid4()
        mock_task.started_at = datetime.utcnow()
        mock_task.metadata_ = {"progress": 0.5}

        with patch.object(task_scheduler, 'get_task', return_value=mock_task):
            result = await task_scheduler.get_task_status(mock_session, mock_task.id)

            assert result is not None
            assert result.task_id == mock_task.id
            assert result.status == TaskStatus.IN_PROGRESS
            assert result.progress == 0.5

    @pytest.mark.asyncio
    async def test_get_task_status_not_found(self, task_scheduler, mock_session):
        """Test getting status of non-existent task."""
        with patch.object(task_scheduler, 'get_task', return_value=None):
            result = await task_scheduler.get_task_status(mock_session, uuid4())

            assert result is None

    @pytest.mark.asyncio
    async def test_complete_task_success(self, task_scheduler, mock_session):
        """Test successful task completion."""
        mock_task = MagicMock()
        mock_task.status = TaskStatus.IN_PROGRESS.value
        mock_task.agent_id = uuid4()
        mock_task.metadata_ = {}
        mock_task.priority = 1

        mock_agent = MagicMock()
        mock_session.get.return_value = mock_agent

        with patch.object(task_scheduler, 'get_task', return_value=mock_task):
            with patch('services.orchestrator.core.task_scheduler.event_producer') as mock_producer:
                mock_producer.publish_task_completed = AsyncMock(return_value=True)

                result = await task_scheduler.complete_task(
                    mock_session,
                    uuid4(),
                    result={"answer": "test result"}
                )

                assert result is True
                assert mock_task.status == TaskStatus.COMPLETED.value
                assert mock_task.output_data == {"result": {"answer": "test result"}}

    @pytest.mark.asyncio
    async def test_complete_task_wrong_status(self, task_scheduler, mock_session):
        """Test completing task with wrong status."""
        mock_task = MagicMock()
        mock_task.status = TaskStatus.PENDING.value

        with patch.object(task_scheduler, 'get_task', return_value=mock_task):
            result = await task_scheduler.complete_task(mock_session, uuid4())

            assert result is False

    @pytest.mark.asyncio
    async def test_fail_task_with_retry(self, task_scheduler, mock_session):
        """Test failing task with retry."""
        mock_task = MagicMock()
        mock_task.status = TaskStatus.IN_PROGRESS.value
        mock_task.agent_id = uuid4()
        mock_task.metadata_ = {"retry_count": 0, "agent_type": "research"}
        mock_task.priority = 1

        mock_agent = MagicMock()
        mock_session.get.return_value = mock_agent

        with patch.object(task_scheduler, 'get_task', return_value=mock_task):
            with patch('services.orchestrator.core.task_scheduler.event_producer') as mock_producer:
                mock_producer.publish_task_failed = AsyncMock(return_value=True)

                result = await task_scheduler.fail_task(
                    mock_session,
                    uuid4(),
                    error="Test error",
                    retry=True
                )

                assert result is True
                assert mock_task.status == TaskStatus.RETRYING.value
                assert mock_task.metadata_["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_fail_task_max_retries_exceeded(self, task_scheduler, mock_session):
        """Test failing task after max retries."""
        mock_task = MagicMock()
        mock_task.status = TaskStatus.IN_PROGRESS.value
        mock_task.agent_id = uuid4()
        mock_task.metadata_ = {"retry_count": 3, "agent_type": "research"}
        mock_task.priority = 1

        mock_agent = MagicMock()
        mock_session.get.return_value = mock_agent

        with patch.object(task_scheduler, 'get_task', return_value=mock_task):
            with patch('services.orchestrator.core.task_scheduler.event_producer') as mock_producer:
                mock_producer.publish_task_failed = AsyncMock(return_value=True)

                result = await task_scheduler.fail_task(
                    mock_session,
                    uuid4(),
                    error="Test error",
                    retry=True
                )

                assert result is True
                assert mock_task.status == TaskStatus.FAILED.value

    @pytest.mark.asyncio
    async def test_cancel_task_success(self, task_scheduler, mock_session):
        """Test successful task cancellation."""
        mock_task = MagicMock()
        mock_task.status = TaskStatus.PENDING.value
        mock_task.agent_id = None
        mock_task.priority = 1

        with patch.object(task_scheduler, 'get_task', return_value=mock_task):
            result = await task_scheduler.cancel_task(mock_session, uuid4())

            assert result is True
            assert mock_task.status == TaskStatus.CANCELLED.value

    @pytest.mark.asyncio
    async def test_cancel_task_wrong_status(self, task_scheduler, mock_session):
        """Test cancelling task with wrong status."""
        mock_task = MagicMock()
        mock_task.status = TaskStatus.COMPLETED.value

        with patch.object(task_scheduler, 'get_task', return_value=mock_task):
            result = await task_scheduler.cancel_task(mock_session, uuid4())

            assert result is False

    @pytest.mark.asyncio
    async def test_add_dependency_success(self, task_scheduler, mock_session):
        """Test adding task dependency."""
        task_id = uuid4()
        depends_on_id = uuid4()

        mock_task = MagicMock()
        mock_depends_on = MagicMock()

        async def get_task_side_effect(session, tid):
            if tid == task_id:
                return mock_task
            return mock_depends_on

        with patch.object(task_scheduler, 'get_task', side_effect=get_task_side_effect):
            result = await task_scheduler.add_dependency(
                mock_session,
                task_id,
                depends_on_id
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_add_dependency_self_reference(self, task_scheduler, mock_session):
        """Test adding self-referencing dependency."""
        task_id = uuid4()

        result = await task_scheduler.add_dependency(
            mock_session,
            task_id,
            task_id
        )

        assert result is False
