"""Tests for the base agent class."""

import pytest

from app.agents.base import AgentResult, BaseAgent


class DummyAgent(BaseAgent):
    def __init__(self, should_fail=False):
        super().__init__("dummy")
        self.should_fail = should_fail

    async def execute(self, context):
        if self.should_fail:
            raise ValueError("Agent error")
        return AgentResult(
            success=True,
            data={"key": "value"},
            confidence=0.99,
        )


class TestAgentResult:
    def test_to_dict(self):
        result = AgentResult(
            success=True,
            data={"findings": "test"},
            confidence=0.95,
            metadata={"agent": "test"},
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["confidence"] == 0.95
        assert d["data"]["findings"] == "test"

    def test_default_values(self):
        result = AgentResult(success=False, error="fail")
        assert result.data == {}
        assert result.confidence == 1.0
        assert result.metadata == {}


@pytest.mark.asyncio
class TestBaseAgent:
    async def test_successful_run(self):
        agent = DummyAgent()
        result = await agent.run({"input": "test"})
        assert result.success
        assert result.data["key"] == "value"

    async def test_failed_run_catches_exception(self):
        agent = DummyAgent(should_fail=True)
        result = await agent.run({"input": "test"})
        assert not result.success
        assert "Agent error" in result.error
        assert result.confidence == 0.0
