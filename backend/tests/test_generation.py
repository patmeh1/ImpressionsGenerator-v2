"""Tests for the Generation Service (multi-agent orchestration)."""

import pytest
from unittest.mock import AsyncMock, patch

from app.agents.base import AgentResult


@pytest.mark.asyncio
class TestGenerationService:
    @patch("app.services.generation.ai_search_service")
    @patch("app.services.generation.cosmos_service")
    @patch("app.services.generation.supervisor_agent")
    async def test_successful_generation(self, mock_supervisor, mock_cosmos, mock_search):
        from app.services.generation import GenerationService

        mock_supervisor.run = AsyncMock(return_value=AgentResult(
            success=True,
            data={
                "findings": "Clear lungs bilaterally.",
                "impressions": "No acute cardiopulmonary process.",
                "recommendations": "Routine follow-up.",
                "grounding": {"is_grounded": True, "overall_confidence": 0.95},
                "review": {"overall_quality": 0.92},
                "revisions": 0,
                "decision": "accepted",
            },
            confidence=0.92,
            metadata={"pipeline_trace": []},
        ))
        mock_cosmos.create_report = AsyncMock(return_value={
            "id": "rpt-001",
            "doctor_id": "dr-001",
            "findings": "Clear lungs bilaterally.",
            "impressions": "No acute cardiopulmonary process.",
            "recommendations": "Routine follow-up.",
            "status": "draft",
            "created_at": "2026-01-01T00:00:00",
        })
        mock_search.index_report = AsyncMock()

        service = GenerationService()
        result = await service.generate(
            dictated_text="CT chest clear lungs bilateral",
            doctor_id="dr-001",
            report_type="CT",
            body_region="Chest",
        )

        assert result["id"] == "rpt-001"
        assert result["grounding"]["is_grounded"] is True
        assert result["decision"] == "accepted"

    @patch("app.services.generation.supervisor_agent")
    async def test_pipeline_failure_raises(self, mock_supervisor):
        from app.services.generation import GenerationService

        mock_supervisor.run = AsyncMock(return_value=AgentResult(
            success=False,
            error="All agents failed",
            confidence=0.0,
        ))

        service = GenerationService()
        with pytest.raises(RuntimeError, match="Multi-agent pipeline failed"):
            await service.generate(
                dictated_text="CT chest",
                doctor_id="dr-001",
            )
