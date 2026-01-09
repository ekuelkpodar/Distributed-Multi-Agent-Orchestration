"""
Unit tests for the Agent Manager.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from shared.models.schemas import AgentType, AgentStatus, AgentSpawnRequest


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def agent_manager():
    """Create an agent manager instance."""
    from services.orchestrator.core.agent_manager import AgentManager
    return AgentManager(
        heartbeat_interval=30,
        heartbeat_timeout=90,
        max_agents=100,
    )


class TestAgentManager:
    """Tests for AgentManager class."""

    @pytest.mark.asyncio
    async def test_spawn_agent_success(self, agent_manager, mock_session):
        """Test successful agent spawning."""
        with patch.object(agent_manager, '_count_active_agents', return_value=0):
            with patch.object(agent_manager, '_assign_to_pool', return_value=None):
                with patch('services.orchestrator.core.agent_manager.event_producer') as mock_producer:
                    mock_producer.publish_agent_spawned = AsyncMock(return_value=True)

                    request = AgentSpawnRequest(
                        agent_type=AgentType.RESEARCH,
                        name="test-agent",
                        capabilities=["web_search"],
                    )

                    result = await agent_manager.spawn_agent(mock_session, request)

                    assert result.agent_id is not None
                    assert result.status == AgentStatus.STARTING
                    assert "spawned successfully" in result.message

    @pytest.mark.asyncio
    async def test_spawn_agent_limit_reached(self, agent_manager, mock_session):
        """Test agent spawning when limit is reached."""
        with patch.object(agent_manager, '_count_active_agents', return_value=100):
            request = AgentSpawnRequest(
                agent_type=AgentType.RESEARCH,
                name="test-agent",
            )

            with pytest.raises(ValueError, match="Maximum agent limit"):
                await agent_manager.spawn_agent(mock_session, request)

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, agent_manager, mock_session):
        """Test getting a non-existent agent."""
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        result = await agent_manager.get_agent(mock_session, uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_record_heartbeat_success(self, agent_manager, mock_session):
        """Test successful heartbeat recording."""
        mock_session.execute.return_value.rowcount = 1

        with patch.object(agent_manager, 'get_agent', return_value=MagicMock(status=AgentStatus.IDLE.value)):
            with patch('services.orchestrator.core.agent_manager.event_producer') as mock_producer:
                mock_producer.publish_agent_heartbeat = AsyncMock(return_value=True)

                result = await agent_manager.record_heartbeat(mock_session, uuid4())

                assert result is True

    @pytest.mark.asyncio
    async def test_record_heartbeat_agent_not_found(self, agent_manager, mock_session):
        """Test heartbeat for non-existent agent."""
        mock_session.execute.return_value.rowcount = 0

        result = await agent_manager.record_heartbeat(mock_session, uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_terminate_agent_success(self, agent_manager, mock_session):
        """Test successful agent termination."""
        mock_agent = MagicMock()
        mock_agent.status = AgentStatus.IDLE.value
        mock_agent.type = AgentType.RESEARCH.value

        with patch.object(agent_manager, 'get_agent', return_value=mock_agent):
            with patch('services.orchestrator.core.agent_manager.event_producer') as mock_producer:
                mock_producer.publish_agent_stopped = AsyncMock(return_value=True)

                result = await agent_manager.terminate_agent(mock_session, uuid4())

                assert result is True
                assert mock_agent.status == AgentStatus.OFFLINE.value

    @pytest.mark.asyncio
    async def test_terminate_agent_not_found(self, agent_manager, mock_session):
        """Test terminating non-existent agent."""
        with patch.object(agent_manager, 'get_agent', return_value=None):
            result = await agent_manager.terminate_agent(mock_session, uuid4())

            assert result is False
