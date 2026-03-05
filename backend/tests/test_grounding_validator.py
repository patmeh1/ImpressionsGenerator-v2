"""Tests for the Grounding Validator Agent."""

import pytest
from unittest.mock import AsyncMock, patch

from app.agents.grounding_validator import GroundingValidatorAgent


@pytest.mark.asyncio
class TestGroundingValidatorAgent:
    def setup_method(self):
        self.agent = GroundingValidatorAgent()

    @patch("app.agents.grounding_validator.openai_service")
    async def test_grounded_report(self, mock_openai):
        mock_openai.call_with_json_response = AsyncMock(return_value={
            "overall_confidence": 0.95,
            "section_scores": {"findings": 0.96, "impressions": 0.94, "recommendations": 0.95},
            "issues": [],
            "hallucinated_claims": [],
            "missing_from_input": [],
            "summary": "Report is well-grounded.",
        })

        result = await self.agent.execute({
            "dictated_text": "CT chest clear lungs",
            "findings": "Clear lungs bilaterally.",
            "impressions": "No acute process.",
            "recommendations": "Follow-up.",
        })

        assert result.success
        assert result.data["is_grounded"] is True
        assert result.confidence >= 0.85

    @patch("app.agents.grounding_validator.openai_service")
    async def test_ungrounded_report(self, mock_openai):
        mock_openai.call_with_json_response = AsyncMock(return_value={
            "overall_confidence": 0.40,
            "section_scores": {"findings": 0.30},
            "issues": ["Fabricated measurement"],
            "hallucinated_claims": ["5mm nodule not in dictation"],
            "missing_from_input": [],
            "summary": "Report contains hallucinations.",
        })

        result = await self.agent.execute({
            "dictated_text": "CT chest clear lungs",
            "findings": "5mm nodule in RLL.",
            "impressions": "",
            "recommendations": "",
        })

        assert result.success
        assert result.data["is_grounded"] is False
        assert len(result.data["hallucinated_claims"]) > 0

    @patch("app.agents.grounding_validator.openai_service")
    async def test_handles_validation_failure(self, mock_openai):
        mock_openai.call_with_json_response = AsyncMock(
            side_effect=Exception("Service error")
        )

        result = await self.agent.execute({
            "dictated_text": "CT chest",
            "findings": "Test",
            "impressions": "",
            "recommendations": "",
        })

        assert not result.success
        assert "Service error" in result.error
