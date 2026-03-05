"""Base agent class with OpenTelemetry tracing support."""

import logging
from abc import ABC, abstractmethod
from typing import Any

from opentelemetry import trace

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


class BaseAgent(ABC):
    """Base class for all agents in the multi-agent pipeline."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> AgentResult:
        """Execute the agent's task given a pipeline context."""
        ...

    async def run(self, context: dict[str, Any]) -> AgentResult:
        """Run the agent with OpenTelemetry tracing."""
        with tracer.start_as_current_span(
            f"agent.{self.name}",
            attributes={"agent.name": self.name},
        ) as span:
            self.logger.info("Agent '%s' starting", self.name)
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
