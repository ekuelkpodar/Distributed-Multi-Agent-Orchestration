"""
Configuration management for the Orchestrator Service.
Uses Pydantic Settings for type-safe configuration with environment variable support.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Service identification
    service_name: str = Field(default="orchestrator")
    service_version: str = Field(default="1.0.0")
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    # API Configuration
    host: str = Field(default="0.0.0.0", alias="ORCHESTRATOR_HOST")
    port: int = Field(default=8000, alias="ORCHESTRATOR_PORT")
    api_prefix: str = Field(default="/api/v1")
    cors_origins: list[str] = Field(default=["*"])

    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://agent_user:agent_pass@localhost:5432/agents_db"
    )
    database_pool_size: int = Field(default=20)
    database_max_overflow: int = Field(default=40)
    database_pool_recycle: int = Field(default=3600)

    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379")
    redis_max_connections: int = Field(default=50)

    # Kafka Configuration
    kafka_bootstrap_servers: str = Field(default="localhost:9092")
    kafka_group_id: str = Field(default="orchestrator")
    kafka_auto_offset_reset: str = Field(default="earliest")

    # JWT Configuration
    jwt_secret_key: str = Field(default="your-super-secret-jwt-key")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=60)

    # LLM Configuration
    anthropic_api_key: Optional[str] = Field(default=None)
    openai_api_key: Optional[str] = Field(default=None)
    default_model: str = Field(default="claude-sonnet-4-20250514")
    llm_timeout: int = Field(default=120)
    llm_max_retries: int = Field(default=3)

    # Observability Configuration
    jaeger_agent_host: str = Field(default="localhost")
    jaeger_agent_port: int = Field(default=6831)
    otlp_endpoint: Optional[str] = Field(default=None)
    log_level: str = Field(default="INFO")
    enable_tracing: bool = Field(default=True)
    enable_metrics: bool = Field(default=True)

    # Agent Configuration
    agent_heartbeat_interval: int = Field(default=30)
    agent_heartbeat_timeout: int = Field(default=90)
    max_concurrent_agents: int = Field(default=100)
    default_agent_pool_size: int = Field(default=5)

    # Task Configuration
    task_default_timeout: int = Field(default=300)
    task_max_retries: int = Field(default=3)
    task_retry_delay: int = Field(default=5)
    task_queue_max_size: int = Field(default=10000)

    # Rate Limiting
    rate_limit_requests: int = Field(default=100)
    rate_limit_window: int = Field(default=60)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
