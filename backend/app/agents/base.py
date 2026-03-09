"""Base agent class — MAF patterns with Azure AI Foundry SDK 2.x.

Uses Microsoft Agent Framework (MAF) for declarative agent capabilities,
tool routing, and supervisor orchestration.  AI inference is handled via
Azure AI Foundry SDK 2.x (AIProjectClient) in openai_service.py.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from opentelemetry import trace

from app.config import settings

tracer = trace.get_tracer("impressions-generator.agents")
logger = logging.getLogger(__name__)


class AgentResult:
    """Standardised result from any agent in the pipeline."""

    def __init__(
        self,
        success: bool,
        data: dict[str, Any] | None = None,
        error: str | None = None,
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.success = success
        self.data = data or {}
        self.error = error
        self.confidence = confidence
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


class AgentCapability:
    """Describes a capability (tool) that an agent can expose via MAF."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.parameters = parameters or {}

    def to_tool_definition(self) -> dict[str, Any]:
        """Convert to an OpenAI function-calling compatible tool definition."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class BaseAgent(ABC):
    """Base class for all agents in the MAF multi-agent pipeline.

    Each agent declares its capabilities (tools) and can be registered with
    the MAF supervisor for orchestration via Azure AI Foundry SDK 2.x.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")
        self._capabilities: list[AgentCapability] = []

    def register_capability(self, capability: AgentCapability) -> None:
        """Register a capability that this agent provides."""
        self._capabilities.append(capability)
        self.logger.debug(
            "Registered capability '%s' on agent '%s'",
            capability.name,
            self.name,
        )

    @property
    def tool_definitions(self) -> list[dict[str, Any]]:
        """Return OpenAI-compatible tool definitions for all capabilities."""
        return [cap.to_tool_definition() for cap in self._capabilities]

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> AgentResult:
        """Execute the agent's task given a pipeline context."""
        ...

    async def handle_tool_call(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> AgentResult:
        """Handle a tool call routed by the MAF supervisor."""
        self.logger.info(
            "Agent '%s' handling tool call '%s'", self.name, tool_name
        )
        return await self.execute(arguments)

    async def run(self, context: dict[str, Any]) -> AgentResult:
        """Run the agent with OpenTelemetry tracing."""
        with tracer.start_as_current_span(
            f"agent.{self.name}",
            attributes={
                "agent.name": self.name,
                "agent.framework": "MAF",
                "agent.foundry_sdk": "2.x",
            },
        ) as span:
            self.logger.info("Agent '%s' starting (MAF + Foundry SDK 2.x)", self.name)
            try:
                result = await self.execute(context)
                span.set_attribute("agent.success", result.success)
                span.set_attribute("agent.confidence", result.confidence)
                if result.error:
                    span.set_attribute("agent.error", result.error)
                self.logger.info(
                    "Agent '%s' completed (success=%s, confidence=%.2f)",
                    self.name,
                    result.success,
                    result.confidence,
                )
                return result
            except Exception as e:
                span.set_attribute("agent.success", False)
                span.set_attribute("agent.error", str(e))
                span.record_exception(e)
                self.logger.exception("Agent '%s' failed", self.name)
                return AgentResult(success=False, error=str(e), confidence=0.0)
