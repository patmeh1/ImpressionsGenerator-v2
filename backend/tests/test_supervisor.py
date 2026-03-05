"""Tests for the Supervisor Agent and full pipeline orchestration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.supervisor import SupervisorAgent
from app.agents.base import AgentResult


@pytest.mark.asyncio
class TestSupervisorAgent:
    def setup_method(self):
        self.agent = SupervisorAgent()

    async def test_successful_pipeline_no_revisions(self):
        """Test pipeline that succeeds on first pass."""
        self.agent.style_analyst.run = AsyncMock(return_value=AgentResult(
            success=True,
            data={
                "style_instructions": "Use short sentences.",
                "style_profile": {"doctor_id": "dr-001"},
                "source": "cached",
            },
            confidence=0.95,
        ))
        self.agent.clinical_rag.run = AsyncMock(return_value=AgentResult(
            success=True,
            data={"few_shot_examples": [], "example_count": 0},
            confidence=0.50,
        ))
        self.agent.report_writer.run = AsyncMock(return_value=AgentResult(
            success=True,
            data={
                "findings": "Clear lungs.",
                "impressions": "No acute process.",
                "recommendations": "Follow-up.",
                "is_revision": False,
            },
            confidence=0.90,
        ))
        self.agent.grounding_validator.run = AsyncMock(return_value=AgentResult(
            success=True,
            data={
                "is_grounded": True,
                "overall_confidence": 0.95,
                "issues": [],
                "hallucinated_claims": [],
            },
            confidence=0.95,
        ))
        self.agent.clinical_reviewer.run = AsyncMock(return_value=AgentResult(
            success=True,
            data={
                "overall_quality": 0.92,
                "critical_issues": [],
            },
            confidence=0.92,
        ))

        result = await self.agent.execute({
            "dictated_text": "CT chest clear lungs",
            "doctor_id": "dr-001",
            "report_type": "CT",
            "body_region": "Chest",
        })

        assert result.success
        assert result.data["decision"] == "accepted"
        assert result.data["revisions"] == 0
        assert result.data["findings"] == "Clear lungs."

    async def test_pipeline_with_revision(self):
        """Test pipeline that requires one revision before accepting."""
        self.agent.style_analyst.run = AsyncMock(return_value=AgentResult(
            success=True,
            data={"style_instructions": "", "style_profile": {}, "source": "default"},
            confidence=0.50,
        ))
        self.agent.clinical_rag.run = AsyncMock(return_value=AgentResult(
            success=True,
            data={"few_shot_examples": [], "example_count": 0},
            confidence=0.50,
        ))

        call_count = 0

        async def mock_writer(context):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return AgentResult(
                    success=True,
                    data={
                        "findings": "5mm nodule (hallucinated).",
                        "impressions": "I", "recommendations": "R",
                        "is_revision": False,
                    },
                    confidence=0.90,
                )
            return AgentResult(
                success=True,
                data={
                    "findings": "Clear lungs.",
                    "impressions": "No acute.", "recommendations": "Follow-up.",
                    "is_revision": True,
                },
                confidence=0.90,
            )

        self.agent.report_writer.run = AsyncMock(side_effect=mock_writer)

        grounding_count = 0

        async def mock_grounding(context):
            nonlocal grounding_count
            grounding_count += 1
            if grounding_count == 1:
                return AgentResult(
                    success=True,
                    data={
                        "is_grounded": False,
                        "overall_confidence": 0.40,
                        "issues": ["Hallucinated measurement"],
                        "hallucinated_claims": ["5mm nodule"],
                    },
                    confidence=0.40,
                )
            return AgentResult(
                success=True,
                data={
                    "is_grounded": True,
                    "overall_confidence": 0.95,
                    "issues": [],
                    "hallucinated_claims": [],
                },
                confidence=0.95,
            )

        self.agent.grounding_validator.run = AsyncMock(side_effect=mock_grounding)
        self.agent.clinical_reviewer.run = AsyncMock(return_value=AgentResult(
            success=True,
            data={"overall_quality": 0.90, "critical_issues": []},
            confidence=0.90,
        ))

        result = await self.agent.execute({
            "dictated_text": "CT chest clear lungs",
            "doctor_id": "dr-001",
        })

        assert result.success
        assert result.data["decision"] == "accepted"
        assert result.data["revisions"] == 1

    async def test_pipeline_failure_on_style_error(self):
        """Test pipeline failure when style analysis fails."""
        self.agent.style_analyst.run = AsyncMock(return_value=AgentResult(
            success=False,
            error="Cosmos DB unavailable",
            confidence=0.0,
        ))

        result = await self.agent.execute({
            "dictated_text": "CT chest",
            "doctor_id": "dr-001",
        })

        assert not result.success
        assert "Style analysis failed" in result.error

    def test_decision_logic_accepts_high_quality(self):
        grounding = AgentResult(
            success=True,
            data={"is_grounded": True, "overall_confidence": 0.95},
            confidence=0.95,
        )
        review = AgentResult(
            success=True,
            data={"overall_quality": 0.90, "critical_issues": []},
            confidence=0.90,
        )
        assert self.agent._decide(grounding, review, 0) == "accept"

    def test_decision_logic_revises_low_grounding(self):
        grounding = AgentResult(
            success=True,
            data={"is_grounded": False, "overall_confidence": 0.40},
            confidence=0.40,
        )
        review = AgentResult(
            success=True,
            data={"overall_quality": 0.90, "critical_issues": []},
            confidence=0.90,
        )
        assert self.agent._decide(grounding, review, 0) == "revise"

    def test_decision_logic_revises_critical_issues(self):
        grounding = AgentResult(
            success=True,
            data={"is_grounded": True, "overall_confidence": 0.95},
            confidence=0.95,
        )
        review = AgentResult(
            success=True,
            data={"overall_quality": 0.80, "critical_issues": ["Wrong terminology"]},
            confidence=0.80,
        )
        assert self.agent._decide(grounding, review, 0) == "revise"

    def test_decision_logic_accepts_on_max_revision(self):
        grounding = AgentResult(
            success=True,
            data={"is_grounded": False, "overall_confidence": 0.50},
            confidence=0.50,
        )
        review = AgentResult(
            success=True,
            data={"overall_quality": 0.50, "critical_issues": ["Issue"]},
            confidence=0.50,
        )
        assert self.agent._decide(grounding, review, 3) == "accept"
