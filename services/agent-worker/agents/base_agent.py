"""
Base Agent class for all agent implementations.
Provides core functionality for LLM interaction, memory, and task execution.
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional, Callable
from uuid import UUID, uuid4

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
import structlog

from shared.models.schemas import AgentType, AgentStatus, TaskStatus
from shared.events.producers import event_producer
from shared.observability.metrics import (
    LLM_REQUESTS_TOTAL,
    LLM_REQUEST_DURATION,
    LLM_TOKENS_TOTAL,
    LLM_ERRORS_TOTAL,
    TASK_DURATION,
)
from config import get_settings
from execution.memory_manager import MemoryManager

logger = structlog.get_logger()
settings = get_settings()


class BaseAgent(ABC):
    """
    Abstract base class for all agent implementations.
    Provides common functionality for LLM interaction, memory, and execution.
    """

    def __init__(
        self,
        agent_id: UUID,
        agent_type: AgentType,
        name: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        memory_enabled: bool = True,
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.name = name
        self.model = model or settings.default_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.memory_enabled = memory_enabled

        self._status = AgentStatus.IDLE
        self._current_task: Optional[UUID] = None
        self._llm = None
        self._memory: Optional[MemoryManager] = None
        self._tools: list[Callable] = []
        self._system_prompt: str = self._get_default_system_prompt()

    @property
    def status(self) -> AgentStatus:
        """Get current agent status."""
        return self._status

    @status.setter
    def status(self, value: AgentStatus) -> None:
        """Set agent status and publish event."""
        self._status = value

    @abstractmethod
    def _get_default_system_prompt(self) -> str:
        """Get the default system prompt for this agent type."""
        pass

    @abstractmethod
    async def execute(self, task_input: dict) -> dict:
        """
        Execute a task with the given input.
        Must be implemented by subclasses.

        Args:
            task_input: Task input data containing query and context

        Returns:
            Task result dictionary
        """
        pass

    def _get_llm(self):
        """Get or create the LLM instance."""
        if self._llm is None:
            if "claude" in self.model.lower():
                self._llm = ChatAnthropic(
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    timeout=settings.llm_timeout,
                    anthropic_api_key=settings.anthropic_api_key,
                )
            else:
                self._llm = ChatOpenAI(
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    timeout=settings.llm_timeout,
                    openai_api_key=settings.openai_api_key,
                )
        return self._llm

    async def get_memory_manager(self) -> MemoryManager:
        """Get or create the memory manager."""
        if self._memory is None:
            self._memory = MemoryManager(self.agent_id)
            await self._memory.initialize()
        return self._memory

    async def invoke_llm(
        self,
        query: str,
        context: Optional[dict] = None,
        include_memory: bool = True,
    ) -> str:
        """
        Invoke the LLM with the given query and context.

        Args:
            query: User query or task description
            context: Additional context for the query
            include_memory: Whether to include relevant memories

        Returns:
            LLM response text
        """
        import time

        start_time = time.time()
        llm = self._get_llm()

        try:
            # Build messages
            messages = [SystemMessage(content=self._system_prompt)]

            # Include relevant memories if enabled
            if include_memory and self.memory_enabled:
                memory_manager = await self.get_memory_manager()
                relevant_memories = await memory_manager.search_memories(
                    query,
                    limit=5,
                )
                if relevant_memories:
                    memory_context = "\n\nRelevant context from memory:\n"
                    for mem in relevant_memories:
                        memory_context += f"- {mem['content']}\n"
                    messages.append(SystemMessage(content=memory_context))

            # Add context if provided
            if context:
                context_str = "\n\nAdditional context:\n"
                for key, value in context.items():
                    context_str += f"- {key}: {value}\n"
                messages.append(SystemMessage(content=context_str))

            # Add user query
            messages.append(HumanMessage(content=query))

            # Invoke LLM
            response = await llm.ainvoke(messages)

            duration = time.time() - start_time

            # Update metrics
            LLM_REQUESTS_TOTAL.labels(
                model=self.model,
                operation="invoke",
            ).inc()

            LLM_REQUEST_DURATION.labels(model=self.model).observe(duration)

            # Extract token counts if available
            if hasattr(response, "response_metadata"):
                metadata = response.response_metadata
                if "usage" in metadata:
                    LLM_TOKENS_TOTAL.labels(
                        model=self.model,
                        token_type="input",
                    ).inc(metadata["usage"].get("input_tokens", 0))
                    LLM_TOKENS_TOTAL.labels(
                        model=self.model,
                        token_type="output",
                    ).inc(metadata["usage"].get("output_tokens", 0))

            logger.debug(
                "LLM invocation completed",
                agent_id=str(self.agent_id),
                model=self.model,
                duration_ms=round(duration * 1000, 2),
            )

            # Store interaction in memory
            if self.memory_enabled:
                await memory_manager.store_conversation(
                    query=query,
                    response=response.content,
                )

            return response.content

        except Exception as e:
            duration = time.time() - start_time

            LLM_ERRORS_TOTAL.labels(
                model=self.model,
                error_type=type(e).__name__,
            ).inc()

            logger.error(
                "LLM invocation failed",
                agent_id=str(self.agent_id),
                model=self.model,
                error=str(e),
                duration_ms=round(duration * 1000, 2),
            )
            raise

    async def run_task(
        self,
        task_id: UUID,
        task_input: dict,
    ) -> dict:
        """
        Run a task with proper lifecycle management.

        Args:
            task_id: Task ID
            task_input: Task input data

        Returns:
            Task result dictionary
        """
        import time

        self._current_task = task_id
        self.status = AgentStatus.BUSY
        start_time = time.time()

        logger.info(
            "Starting task execution",
            agent_id=str(self.agent_id),
            task_id=str(task_id),
        )

        try:
            # Publish task started event
            await event_producer.publish_task_started(
                task_id=task_id,
                agent_id=self.agent_id,
            )

            # Execute the task
            result = await self.execute(task_input)

            duration = time.time() - start_time

            # Update metrics
            TASK_DURATION.labels(
                task_type=self.agent_type.value,
                agent_type=self.agent_type.value,
            ).observe(duration)

            # Publish task completed event
            await event_producer.publish_task_completed(
                task_id=task_id,
                agent_id=self.agent_id,
                result=result,
            )

            logger.info(
                "Task completed successfully",
                agent_id=str(self.agent_id),
                task_id=str(task_id),
                duration_ms=round(duration * 1000, 2),
            )

            return result

        except Exception as e:
            duration = time.time() - start_time

            logger.error(
                "Task execution failed",
                agent_id=str(self.agent_id),
                task_id=str(task_id),
                error=str(e),
                duration_ms=round(duration * 1000, 2),
            )

            # Publish task failed event
            await event_producer.publish_task_failed(
                task_id=task_id,
                agent_id=self.agent_id,
                error=str(e),
            )

            raise

        finally:
            self._current_task = None
            self.status = AgentStatus.IDLE

    async def report_progress(
        self,
        progress: float,
        message: Optional[str] = None,
    ) -> None:
        """Report task progress."""
        if self._current_task:
            await event_producer.publish_task_progress(
                task_id=self._current_task,
                agent_id=self.agent_id,
                progress=progress,
                message=message,
            )

    async def send_heartbeat(self, metrics: Optional[dict] = None) -> None:
        """Send agent heartbeat."""
        await event_producer.publish_agent_heartbeat(
            agent_id=self.agent_id,
            status=self.status,
            metrics=metrics or {},
        )

    def register_tool(self, tool: Callable) -> None:
        """Register a tool for the agent to use."""
        self._tools.append(tool)

    async def cleanup(self) -> None:
        """Cleanup agent resources."""
        if self._memory:
            await self._memory.cleanup()
        logger.info("Agent cleanup completed", agent_id=str(self.agent_id))
