"""Tests for the Clinical RAG Agent."""

import pytest
from unittest.mock import AsyncMock, patch

from app.agents.clinical_rag import ClinicalRAGAgent


@pytest.mark.asyncio
class TestClinicalRAGAgent:
    def setup_method(self):
        self.agent = ClinicalRAGAgent()

    @patch("app.agents.clinical_rag.ai_search_service")
    async def test_returns_examples_with_filters(self, mock_search):
        mock_search.search_similar_notes = AsyncMock(return_value=[
            {"id": "1", "content": "Example 1", "findings": "F1",
             "impressions": "I1", "recommendations": "R1", "score": 0.9},
            {"id": "2", "content": "Example 2", "findings": "F2",
             "impressions": "I2", "recommendations": "R2", "score": 0.8},
        ])

        result = await self.agent.execute({
            "doctor_id": "dr-001",
            "dictated_text": "CT chest clear lungs",
            "report_type": "CT",
            "body_region": "Chest",
        })

        assert result.success
        assert result.data["example_count"] == 2
        assert len(result.data["few_shot_examples"]) == 2

    @patch("app.agents.clinical_rag.ai_search_service")
    async def test_broadens_search_with_few_results(self, mock_search):
        call_count = 0

        async def mock_search_fn(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [{"id": "1", "content": "One result", "findings": "F",
                         "impressions": "I", "recommendations": "R", "score": 0.9}]
            return [{"id": "2", "content": "Broader result", "findings": "F2",
                     "impressions": "I2", "recommendations": "R2", "score": 0.7}]

        mock_search.search_similar_notes = AsyncMock(side_effect=mock_search_fn)

        result = await self.agent.execute({
            "doctor_id": "dr-001",
            "dictated_text": "CT chest",
            "report_type": "CT",
            "body_region": "Chest",
        })

        assert result.success
        assert result.data["example_count"] == 2

    @patch("app.agents.clinical_rag.ai_search_service")
    async def test_handles_search_failure(self, mock_search):
        mock_search.search_similar_notes = AsyncMock(
            side_effect=Exception("Search unavailable")
        )

        result = await self.agent.execute({
            "doctor_id": "dr-001",
            "dictated_text": "CT chest",
        })

        assert result.success
        assert result.data["example_count"] == 0
