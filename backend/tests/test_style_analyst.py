"""Tests for the Style Analyst Agent."""

import pytest
from unittest.mock import AsyncMock, patch

from app.agents.style_analyst import StyleAnalystAgent


@pytest.mark.asyncio
class TestStyleAnalystAgent:
    def setup_method(self):
        self.agent = StyleAnalystAgent()

    @patch("app.agents.style_analyst.cosmos_service")
    async def test_returns_cached_profile(self, mock_cosmos):
        mock_cosmos.get_style_profile = AsyncMock(return_value={
            "doctor_id": "dr-001",
            "vocabulary_patterns": ["bilateral"],
            "abbreviation_map": {},
            "sentence_structure": [],
            "section_ordering": [],
            "sample_phrases": [],
        })

        result = await self.agent.execute({"doctor_id": "dr-001"})

        assert result.success
        assert result.data["source"] == "cached"
        assert result.confidence == 0.95

    @patch("app.agents.style_analyst.openai_service")
    @patch("app.agents.style_analyst.cosmos_service")
    async def test_extracts_new_profile(self, mock_cosmos, mock_openai):
        mock_cosmos.get_style_profile = AsyncMock(return_value=None)
        mock_cosmos.list_notes = AsyncMock(return_value=[
            {"content": "CT chest: Clear lungs bilaterally."}
        ])
        mock_cosmos.upsert_style_profile = AsyncMock()
        mock_openai.analyze_style = AsyncMock(return_value={
            "vocabulary_patterns": ["bilateral"],
            "abbreviation_map": {},
            "sentence_structure": ["short declarative"],
            "section_ordering": ["findings", "impressions"],
            "sample_phrases": ["no acute findings"],
        })

        result = await self.agent.execute({"doctor_id": "dr-001"})

        assert result.success
        assert result.data["source"] == "extracted"
        assert result.confidence == 0.80

    @patch("app.agents.style_analyst.openai_service")
    @patch("app.agents.style_analyst.cosmos_service")
    async def test_returns_default_on_failure(self, mock_cosmos, mock_openai):
        mock_cosmos.get_style_profile = AsyncMock(return_value=None)
        mock_cosmos.list_notes = AsyncMock(side_effect=Exception("DB error"))

        result = await self.agent.execute({"doctor_id": "dr-001"})

        assert result.success
        assert result.data["source"] == "default"
        assert result.confidence == 0.50
