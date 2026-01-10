# Distributed Multi-Agent Orchestration Platform

[![Lines of Code](https://img.shields.io/badge/Lines%20of%20Code-23%2C000%2B-blue)](.)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

A production-ready distributed multi-agent orchestration platform that coordinates AI agents across distributed environments with offline capability, intelligent synchronization, and enterprise-grade reliability.

**Total Lines of Code: 23,000+** (Python, TypeScript, React)

## Overview

This platform provides:
- **Agent Lifecycle Management**: Spawn, monitor, and terminate AI agents dynamically
- **Task Orchestration**: DAG-based task dependencies, priority queuing, and parallel execution
- **Event-Driven Communication**: Kafka-based event streaming for inter-agent messaging
- **State Management**: Hierarchical memory with Redis (hot state) and PostgreSQL (persistent)
- **Vector Search**: Semantic memory search using pgvector
- **Observability**: Distributed tracing, metrics, and structured logging
- **Advanced Analytics**: Time-series metrics, performance scoring, and AI-powered insights
- **Audit Trail**: Comprehensive event logging for compliance and debugging
- **Webhook System**: Reliable event delivery with retries and HMAC signatures
- **React Dashboard**: Production-grade UI with real-time updates
- **Landing Page**: Premium Next.js marketing site with authentication

## Architecture Diagrams

### High-Level System Architecture

```mermaid
flowchart TB
    subgraph Clients["Client Layer"]
        API[REST API Clients]
        WS[WebSocket Clients]
        CLI[CLI Tools]
    end

    subgraph Gateway["API Gateway"]
        FW[FastAPI Server]
        AUTH[JWT Authentication]
        CORS[CORS Middleware]
    end

    subgraph Orchestrator["Orchestrator Service"]
        AM[Agent Manager]
        TS[Task Scheduler]
        SC[State Coordinator]

        AM -->|manages| TS
        TS -->|coordinates| SC
    end

    subgraph EventBus["Event Bus - Apache Kafka"]
        T1[agent.lifecycle]
        T2[agent.tasks]
        T3[agent.communication]
        T4[agent.state]
        T5[system.events]
    end

    subgraph Workers["Agent Worker Pool"]
        W1[Research Agent]
        W2[Analysis Agent]
        W3[Coordinator Agent]
        W4[Worker Agent n...]
    end

    subgraph DataLayer["Data Layer"]
        PG[(PostgreSQL + pgvector)]
        RD[(Redis Stack)]
    end

    subgraph Observability["Observability Stack"]
        PROM[Prometheus]
        GRAF[Grafana]
        JAEG[Jaeger]
    end

    Clients --> Gateway
    Gateway --> Orchestrator
    Orchestrator <--> EventBus
    EventBus <--> Workers
    Orchestrator <--> DataLayer
    Workers <--> DataLayer
    Orchestrator --> Observability
    Workers --> Observability
```

### Component Interaction Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant O as Orchestrator
    participant K as Kafka
    participant W as Agent Worker
    participant R as Redis
    participant P as PostgreSQL

    C->>O: POST /api/v1/tasks/submit
    O->>P: Store task (status: pending)
    O->>K: Publish task.created event
    O-->>C: Return task_id

    K->>W: Consume task event
    W->>R: Get agent state
    W->>W: Execute task (LLM call)
    W->>R: Update progress
    W->>K: Publish task.progress event

    W->>P: Store results
    W->>K: Publish task.completed event
    K->>O: Consume completion event
    O->>P: Update task status

    C->>O: GET /api/v1/tasks/{id}/status
    O->>P: Query task
    O-->>C: Return task result
```

### Agent Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> Starting: spawn()
    Starting --> Idle: initialized
    Idle --> Busy: task_assigned
    Busy --> Idle: task_completed
    Busy --> Failed: error
    Idle --> Stopping: terminate()
    Failed --> Stopping: cleanup
    Stopping --> [*]: terminated

    Idle --> Idle: heartbeat
    Busy --> Busy: progress_update
```

### Task Execution DAG

```mermaid
flowchart LR
    subgraph TaskDAG["Task Dependency Graph"]
        T1[Task 1: Research]
        T2[Task 2: Data Collection]
        T3[Task 3: Analysis]
        T4[Task 4: Synthesis]
        T5[Task 5: Report Generation]

        T1 --> T3
        T2 --> T3
        T3 --> T4
        T4 --> T5
    end

    subgraph Execution["Parallel Execution"]
        E1[Agent 1] --> T1
        E2[Agent 2] --> T2
        E3[Agent 3] --> T3
        E3 --> T4
        E3 --> T5
    end
```

### Memory Hierarchy

```mermaid
flowchart TB
    subgraph Memory["Hierarchical Memory System"]
        subgraph ShortTerm["Short-Term Memory (Redis)"]
            STM1[Active Task Context]
            STM2[Current Conversation]
            STM3[Working Memory]
        end

        subgraph MidTerm["Mid-Term Memory (Redis)"]
            MTM1[Recent Task History]
            MTM2[Session Data]
            MTM3[Agent State Cache]
        end

        subgraph LongTerm["Long-Term Memory (PostgreSQL + pgvector)"]
            LTM1[Knowledge Base]
            LTM2[Vector Embeddings]
            LTM3[Historical Data]
        end
    end

    ShortTerm -->|TTL: 1 hour| MidTerm
    MidTerm -->|TTL: 24 hours| LongTerm
    LongTerm -->|Semantic Search| ShortTerm
```

### Infrastructure Components

```mermaid
flowchart TB
    subgraph Docker["Docker Compose Environment"]
        subgraph Core["Core Services"]
            ORC[Orchestrator :8000]
            WRK1[Agent Worker 1]
            WRK2[Agent Worker 2]
            WRK3[Agent Worker 3]
        end

        subgraph Data["Data Services"]
            PG[PostgreSQL :5432]
            RD[Redis :6379]
        end

        subgraph Messaging["Message Broker"]
            ZK[Zookeeper :2181]
            KF[Kafka :9092]
        end

        subgraph Monitoring["Monitoring Stack"]
            PR[Prometheus :9090]
            GF[Grafana :3000]
            JG[Jaeger :16686]
        end
    end

    ORC --> PG
    ORC --> RD
    ORC --> KF
    WRK1 & WRK2 & WRK3 --> KF
    WRK1 & WRK2 & WRK3 --> PG
    WRK1 & WRK2 & WRK3 --> RD
    KF --> ZK
    PR --> ORC
    PR --> WRK1 & WRK2 & WRK3
    GF --> PR
```

### Event-Driven Architecture

```mermaid
flowchart LR
    subgraph Producers["Event Producers"]
        P1[Orchestrator]
        P2[Agent Workers]
    end

    subgraph Kafka["Kafka Topics"]
        direction TB
        T1[agent.lifecycle<br/>partitions: 3]
        T2[agent.tasks<br/>partitions: 6]
        T3[agent.communication<br/>partitions: 3]
        T4[agent.state<br/>partitions: 3]
        T5[dead.letter<br/>partitions: 1]
    end

    subgraph Consumers["Event Consumers"]
        C1[Task Scheduler]
        C2[State Coordinator]
        C3[Agent Workers]
        C4[Metrics Collector]
    end

    P1 --> T1 & T2
    P2 --> T2 & T3 & T4

    T1 --> C1 & C2
    T2 --> C3
    T3 --> C3
    T4 --> C2 & C4
```

## Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11+, FastAPI |
| Frontend | React 18, TypeScript, Vite |
| Landing Page | Next.js 14, Tailwind CSS, Framer Motion |
| Message Broker | Apache Kafka |
| Primary Database | PostgreSQL 16 + pgvector |
| Cache/State | Redis 7.4+ |
| LLM Integration | Anthropic Claude, OpenAI |
| Agent Framework | LangChain + LangGraph |
| Tracing | OpenTelemetry + Jaeger |
| Metrics | Prometheus + Grafana |
| Containerization | Docker + Kubernetes |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Anthropic API key (for Claude)
- OpenAI API key (optional, for embeddings)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/DistributedMultiAgentOrchestration.git
   cd DistributedMultiAgentOrchestration
   ```

2. **Set up environment variables**
   ```bash
   # Create .env file with your API keys
   cat > .env << EOF
   ANTHROPIC_API_KEY=your_anthropic_key_here
   OPENAI_API_KEY=your_openai_key_here
   EOF
   ```

3. **Start all services**
   ```bash
   docker-compose up -d
   ```

4. **Verify services are running**
   ```bash
   docker-compose ps
   ```

5. **Check health status**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

### Service Endpoints

| Service | URL | Description |
|---------|-----|-------------|
| Orchestrator API | http://localhost:8000 | Main API endpoint |
| API Documentation | http://localhost:8000/docs | Swagger UI |
| Prometheus | http://localhost:9090 | Metrics |
| Grafana | http://localhost:3000 | Dashboards (admin/admin) |
| Jaeger UI | http://localhost:16686 | Distributed tracing |
| Redis Insight | http://localhost:8001 | Redis management |

### API Examples

**Spawn an Agent**
```bash
curl -X POST http://localhost:8000/api/v1/agents/spawn \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "research",
    "name": "research-agent-1",
    "capabilities": ["web_search", "document_analysis"]
  }'
```

**Submit a Task**
```bash
curl -X POST http://localhost:8000/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Research the latest developments in multi-agent AI systems",
    "priority": 1,
    "agent_type": "research"
  }'
```

**Get Task Status**
```bash
curl http://localhost:8000/api/v1/tasks/{task_id}/status
```

## Project Structure

```
DistributedMultiAgentOrchestration/
├── services/
│   ├── orchestrator/           # Central coordinator service
│   │   ├── api/                # REST API routes
│   │   ├── core/               # Core business logic
│   │   │   ├── agent_manager.py
│   │   │   ├── task_scheduler.py
│   │   │   └── state_coordinator.py
│   │   ├── config.py           # Service configuration
│   │   └── main.py             # FastAPI application
│   └── agent-worker/           # Distributed worker service
│       ├── agents/             # Agent implementations
│       │   ├── base_agent.py
│       │   ├── research_agent.py
│       │   └── analysis_agent.py
│       ├── execution/          # Task execution engine
│       │   ├── task_executor.py
│       │   └── memory_manager.py
│       └── main.py             # Worker entry point
├── shared/                     # Shared libraries
│   ├── database/               # Database connections & models
│   ├── events/                 # Kafka producers/consumers
│   ├── models/                 # Pydantic schemas
│   └── observability/          # Tracing, metrics, logging
├── infrastructure/             # Infrastructure configs
│   ├── postgres/               # Database init scripts
│   ├── prometheus/             # Prometheus config
│   └── grafana/                # Grafana dashboards
├── kubernetes/                 # K8s deployment manifests
├── tests/                      # Test suites
│   ├── unit/
│   └── integration/
├── docker-compose.yml          # Local development
└── README.md
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka brokers | `localhost:9092` |
| `ANTHROPIC_API_KEY` | Anthropic API key | Required |
| `OPENAI_API_KEY` | OpenAI API key | Optional |
| `LOG_LEVEL` | Logging level | `INFO` |
| `JAEGER_AGENT_HOST` | Jaeger host | `localhost` |
| `JAEGER_AGENT_PORT` | Jaeger port | `6831` |

## Agent Types

### Research Agent
- Web search and document analysis
- Information synthesis and summarization
- Source citation and verification

### Analysis Agent
- Data processing and pattern recognition
- Statistical analysis
- Insight generation and recommendations

### Coordinator Agent
- Sub-task delegation
- Result aggregation
- Workflow orchestration

## Memory Management

The platform implements a hierarchical memory system:

| Tier | Storage | TTL | Use Case |
|------|---------|-----|----------|
| Short-term | Redis | 1 hour | Active task context, working memory |
| Mid-term | Redis | 24 hours | Recent history, session data |
| Long-term | PostgreSQL + pgvector | Permanent | Knowledge base, semantic search |

## Observability

### Metrics (Prometheus)
- Agent utilization and health
- Task completion rates and duration
- Message queue depths
- LLM API latency and errors

### Tracing (Jaeger)
- Distributed request tracing
- Cross-service correlation
- Latency analysis

### Logging (Structured JSON)
- Request/response logging
- Error tracking
- Audit trail

## Production Deployment

### Kubernetes

```bash
# Create namespace
kubectl apply -f kubernetes/namespace.yaml

# Deploy secrets and configmaps
kubectl apply -f kubernetes/secrets.yaml
kubectl apply -f kubernetes/configmap.yaml

# Deploy infrastructure
kubectl apply -f kubernetes/postgres-statefulset.yaml
kubectl apply -f kubernetes/redis-deployment.yaml
kubectl apply -f kubernetes/kafka-statefulset.yaml

# Deploy services
kubectl apply -f kubernetes/orchestrator-deployment.yaml
kubectl apply -f kubernetes/agent-worker-deployment.yaml

# Deploy ingress
kubectl apply -f kubernetes/ingress.yaml
```

### Scaling

The platform supports horizontal scaling:
- **Orchestrator**: 2-10 replicas (HPA based on CPU/memory)
- **Agent Workers**: 3-50 replicas (HPA based on queue depth)

## Testing

```bash
# Unit tests
pytest tests/unit -v

# Integration tests
pytest tests/integration -v

# With coverage
pytest --cov=services --cov=shared tests/
```

## API Reference

See the interactive API documentation at `/docs` when the orchestrator is running.

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/agents/spawn` | Spawn a new agent |
| GET | `/api/v1/agents` | List all agents |
| GET | `/api/v1/agents/{id}` | Get agent details |
| DELETE | `/api/v1/agents/{id}` | Terminate agent |
| POST | `/api/v1/tasks/submit` | Submit a new task |
| GET | `/api/v1/tasks/{id}` | Get task details |
| GET | `/api/v1/tasks/{id}/status` | Get task status |
| GET | `/api/v1/health` | Health check |
| GET | `/metrics` | Prometheus metrics |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
