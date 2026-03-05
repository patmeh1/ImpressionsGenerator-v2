"""Tests for the Report Writer Agent."""

import pytest
from unittest.mock import AsyncMock, patch

from app.agents.report_writer import ReportWriterAgent


@pytest.mark.asyncio
class TestReportWriterAgent:
    def setup_method(self):
        self.agent = ReportWriterAgent()

    @patch("app.agents.report_writer.openai_service")
    async def test_generates_report(self, mock_openai):
        mock_openai.generate_report = AsyncMock(return_value={
            "findings": "Clear lungs bilaterally.",
            "impressions": "No acute cardiopulmonary process.",
            "recommendations": "Routine follow-up.",
        })

        result = await self.agent.execute({
            "dictated_text": "CT chest clear lungs bilateral",
            "style_instructions": "Use short sentences.",
            "few_shot_examples": [],
            "report_type": "CT",
            "body_region": "Chest",
        })

        assert result.success
        assert result.data["findings"] == "Clear lungs bilaterally."
        assert result.data["is_revision"] is False

    @patch("app.agents.report_writer.openai_service")
    async def test_handles_revision_feedback(self, mock_openai):
        mock_openai.generate_report = AsyncMock(return_value={
            "findings": "Revised findings.",
            "impressions": "Revised impressions.",
            "recommendations": "Revised recommendations.",
        })

        result = await self.agent.execute({
            "dictated_text": "CT chest",
            "revision_feedback": "Remove hallucinated measurement of 5mm.",
        })

        assert result.success
        assert result.data["is_revision"] is True

    @patch("app.agents.report_writer.openai_service")
    async def test_handles_generation_failure(self, mock_openai):
        mock_openai.generate_report = AsyncMock(
            side_effect=RuntimeError("Model unavailable")
        )

        result = await self.agent.execute({
            "dictated_text": "CT chest",
        })

        assert not result.success
        assert "Model unavailable" in result.error
