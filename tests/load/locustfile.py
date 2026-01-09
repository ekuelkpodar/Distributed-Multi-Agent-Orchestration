"""
Load testing script for the Multi-Agent Orchestration Platform.
Uses Locust for distributed load testing.

Run with: locust -f tests/load/locustfile.py --host=http://localhost:8000
"""

import json
import random
from uuid import uuid4

from locust import HttpUser, task, between, events


class OrchestratorUser(HttpUser):
    """Simulates a user interacting with the orchestrator API."""

    wait_time = between(1, 3)

    def on_start(self):
        """Initialize user with spawned agents."""
        self.agent_ids = []
        self.task_ids = []

        # Spawn initial agents
        for _ in range(2):
            self.spawn_agent()

    def on_stop(self):
        """Clean up spawned agents."""
        for agent_id in self.agent_ids:
            self.client.post(
                f"/api/v1/agents/{agent_id}/terminate",
                params={"reason": "load_test_cleanup"}
            )

    @task(10)
    def spawn_agent(self):
        """Spawn a new agent."""
        agent_type = random.choice(["research", "analysis", "worker"])
        payload = {
            "agent_type": agent_type,
            "name": f"load-test-{agent_type}-{uuid4().hex[:8]}",
            "capabilities": ["web_search", "analysis"],
        }

        with self.client.post(
            "/api/v1/agents/spawn",
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.agent_ids.append(data.get("agent_id"))
                response.success()
            else:
                response.failure(f"Failed to spawn agent: {response.text}")

    @task(30)
    def submit_task(self):
        """Submit a new task."""
        if not self.agent_ids:
            return

        descriptions = [
            "Analyze the current market trends",
            "Research recent AI developments",
            "Process the provided dataset",
            "Generate a comprehensive report",
            "Summarize the key findings",
        ]

        payload = {
            "description": random.choice(descriptions),
            "priority": random.randint(-5, 5),
            "agent_type": random.choice(["research", "analysis"]),
        }

        with self.client.post(
            "/api/v1/tasks/submit",
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.task_ids.append(data.get("task_id"))
                # Keep only last 100 task IDs
                self.task_ids = self.task_ids[-100:]
                response.success()
            else:
                response.failure(f"Failed to submit task: {response.text}")

    @task(20)
    def get_task_status(self):
        """Check status of a random task."""
        if not self.task_ids:
            return

        task_id = random.choice(self.task_ids)

        with self.client.get(
            f"/api/v1/tasks/{task_id}/status",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Failed to get task status: {response.text}")

    @task(15)
    def list_agents(self):
        """List all agents."""
        params = {
            "page": 1,
            "page_size": 20,
        }

        with self.client.get(
            "/api/v1/agents",
            params=params,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to list agents: {response.text}")

    @task(15)
    def list_tasks(self):
        """List all tasks."""
        params = {
            "page": 1,
            "page_size": 20,
        }

        with self.client.get(
            "/api/v1/tasks",
            params=params,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to list tasks: {response.text}")

    @task(5)
    def get_agent_details(self):
        """Get details of a specific agent."""
        if not self.agent_ids:
            return

        agent_id = random.choice(self.agent_ids)

        with self.client.get(
            f"/api/v1/agents/{agent_id}",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Failed to get agent: {response.text}")

    @task(5)
    def send_heartbeat(self):
        """Send heartbeat for a random agent."""
        if not self.agent_ids:
            return

        agent_id = random.choice(self.agent_ids)
        metrics = {
            "cpu_usage": random.uniform(0, 100),
            "memory_usage": random.uniform(0, 100),
            "active_tasks": random.randint(0, 5),
        }

        with self.client.post(
            f"/api/v1/agents/{agent_id}/heartbeat",
            json=metrics,
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Failed to send heartbeat: {response.text}")

    @task(2)
    def health_check(self):
        """Check system health."""
        with self.client.get(
            "/api/v1/health",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.text}")


class HighVolumeUser(HttpUser):
    """Simulates high-volume task submission."""

    wait_time = between(0.1, 0.5)

    @task
    def submit_task_fast(self):
        """Submit tasks as fast as possible."""
        payload = {
            "description": f"High volume task {uuid4().hex[:8]}",
            "priority": random.randint(-10, 10),
        }

        self.client.post("/api/v1/tasks/submit", json=payload)


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    print("Load test started")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    print("Load test completed")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Failure rate: {environment.stats.total.fail_ratio * 100:.2f}%")
    print(f"Average response time: {environment.stats.total.avg_response_time:.2f}ms")
