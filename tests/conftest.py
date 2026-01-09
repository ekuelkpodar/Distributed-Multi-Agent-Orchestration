"""
Pytest configuration and fixtures for tests.
"""

import asyncio
import os
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test_db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9092"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_agent_data():
    """Sample agent data for tests."""
    return {
        "name": "test-research-agent",
        "type": "research",
        "capabilities": {
            "skills": ["web_search", "document_analysis"],
            "max_concurrent_tasks": 5,
        },
        "config": {
            "model": "claude-sonnet-4-20250514",
            "temperature": 0.7,
            "max_tokens": 4096,
        },
    }


@pytest.fixture
def sample_task_data():
    """Sample task data for tests."""
    return {
        "description": "Research the latest AI developments",
        "priority": 1,
        "input_data": {
            "query": "What are the latest AI developments?",
            "context": {},
        },
        "metadata": {
            "trace_id": "test-trace-123",
        },
    }


@pytest.fixture
def sample_memory_data():
    """Sample memory data for tests."""
    return {
        "memory_type": "conversation",
        "content": "Q: What is the capital of France?\nA: Paris",
        "metadata": {
            "source": "test",
        },
    }
