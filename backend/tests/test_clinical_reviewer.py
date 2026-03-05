"""Tests for the Clinical Reviewer Agent."""

import pytest
from unittest.mock import AsyncMock, patch

from app.agents.clinical_reviewer import ClinicalReviewerAgent


@pytest.mark.asyncio
class TestClinicalReviewerAgent:
    def setup_method(self):
        self.agent = ClinicalReviewerAgent()

    @patch("app.agents.clinical_reviewer.openai_service")
    async def test_high_quality_report(self, mock_openai):
        mock_openai.call_with_json_response = AsyncMock(return_value={
            "overall_quality": 0.93,
            "medical_accuracy": 0.95,
            "terminology_correctness": 0.94,
            "completeness": 0.90,
            "style_adherence": 0.91,
            "critical_issues": [],
            "suggestions": ["Consider adding comparison with prior studies."],
            "summary": "High-quality report with appropriate medical terminology.",
        })

        result = await self.agent.execute({
            "dictated_text": "CT chest clear lungs bilateral",
            "findings": "Clear lungs bilaterally.",
            "impressions": "No acute cardiopulmonary process.",
            "recommendations": "Routine follow-up.",
            "style_instructions": "Short declarative sentences.",
            "report_type": "CT",
            "body_region": "Chest",
        })

        assert result.success
        assert result.data["overall_quality"] >= 0.90
        assert len(result.data["critical_issues"]) == 0

    @patch("app.agents.clinical_reviewer.openai_service")
    async def test_report_with_critical_issues(self, mock_openai):
        mock_openai.call_with_json_response = AsyncMock(return_value={
            "overall_quality": 0.45,
            "medical_accuracy": 0.30,
            "terminology_correctness": 0.50,
            "completeness": 0.40,
            "style_adherence": 0.60,
            "critical_issues": ["Incorrect use of 'pneumothorax' — not supported by findings"],
            "suggestions": [],
            "summary": "Report has significant medical accuracy issues.",
        })

        result = await self.agent.execute({
            "dictated_text": "CT chest clear lungs",
            "findings": "Pneumothorax noted.",
            "impressions": "",
            "recommendations": "",
        })

        assert result.success
        assert result.data["overall_quality"] < 0.50
        assert len(result.data["critical_issues"]) > 0
