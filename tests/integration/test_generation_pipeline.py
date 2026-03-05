"""Integration tests for the multi-agent generation pipeline."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture
def mock_all_services():
    """Mock all external Azure services for integration testing."""
    with (
        patch("app.services.cosmos_db.cosmos_service") as cosmos,
        patch("app.services.openai_service.openai_service") as openai,
        patch("app.services.ai_search.ai_search_service") as search,
    ):
        # Cosmos mocks
        cosmos.get_style_profile = AsyncMock(return_value={
            "doctor_id": "dr-integration",
            "vocabulary_patterns": ["bilateral", "unremarkable"],
            "abbreviation_map": {"CT": "computed tomography"},
            "sentence_structure": ["short declarative"],
            "section_ordering": ["findings", "impressions", "recommendations"],
            "sample_phrases": ["no acute findings"],
        })
        cosmos.list_notes = AsyncMock(return_value=[])
        cosmos.create_report = AsyncMock(return_value={
            "id": "rpt-integration-001",
            "doctor_id": "dr-integration",
            "findings": "",
            "impressions": "",
            "recommendations": "",
            "status": "draft",
            "created_at": "2026-01-01T00:00:00",
        })

        # OpenAI mocks
        openai.generate_report = AsyncMock(return_value={
            "findings": "Lungs are clear bilaterally. No pleural effusion. Heart size normal.",
            "impressions": "No acute cardiopulmonary process.",
            "recommendations": "Routine follow-up in 12 months as clinically indicated.",
        })
        openai.call_with_json_response = AsyncMock(return_value={
            "overall_confidence": 0.95,
            "section_scores": {"findings": 0.96, "impressions": 0.94, "recommendations": 0.95},
            "issues": [],
            "hallucinated_claims": [],
            "missing_from_input": [],
            "summary": "Report is well-grounded.",
            "overall_quality": 0.92,
            "medical_accuracy": 0.94,
            "terminology_correctness": 0.93,
            "completeness": 0.90,
            "style_adherence": 0.91,
            "critical_issues": [],
            "suggestions": ["Consider adding comparison with prior studies."],
        })

        # Search mocks
        search.search_similar_notes = AsyncMock(return_value=[
            {
                "id": "ex-1",
                "content": "CT chest: Clear lungs.",
                "findings": "Clear lungs.",
                "impressions": "No acute.",
                "recommendations": "Follow-up.",
                "report_type": "CT",
                "body_region": "Chest",
                "score": 0.95,
            }
        ])
        search.index_report = AsyncMock()

        yield {"cosmos": cosmos, "openai": openai, "search": search}


@pytest.mark.asyncio
class TestMultiAgentPipelineIntegration:
    async def test_full_pipeline_with_grounding_pass(self, mock_all_services):
        """Test the complete pipeline when grounding passes on first attempt."""
        from app.services.generation import GenerationService

        service = GenerationService()
        result = await service.generate(
            dictated_text=(
                "CT chest without contrast. Lungs clear bilaterally. "
                "No pleural effusion. Heart size is normal."
            ),
            doctor_id="dr-integration",
            report_type="CT",
            body_region="Chest",
        )

        assert result["id"] == "rpt-integration-001"
        assert result["grounding"]["overall_confidence"] >= 0.85
        assert result["grounding"]["is_grounded"] is True  # not in mock return
        assert result["review"]["overall_quality"] >= 0.75
        assert result["decision"] == "accepted"
        assert result["revisions"] == 0

    async def test_full_pipeline_with_revision(self, mock_all_services):
        """Test pipeline that requires revision due to grounding failure."""
        call_count = 0

        async def mock_grounding_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # First grounding + first review
                if "hallucinated" in str(kwargs.get("user_message", "")):
                    return {
                        "overall_confidence": 0.40,
                        "section_scores": {"findings": 0.30},
                        "issues": ["Fabricated measurement"],
                        "hallucinated_claims": ["5mm nodule not in dictation"],
                        "missing_from_input": [],
                        "summary": "Hallucination detected.",
                        "overall_quality": 0.45,
                        "medical_accuracy": 0.30,
                        "critical_issues": [],
                        "suggestions": [],
                    }
            # After revision, all good
            return {
                "overall_confidence": 0.95,
                "section_scores": {"findings": 0.96},
                "issues": [],
                "hallucinated_claims": [],
                "missing_from_input": [],
                "summary": "Well-grounded.",
                "overall_quality": 0.92,
                "medical_accuracy": 0.94,
                "terminology_correctness": 0.93,
                "completeness": 0.90,
                "style_adherence": 0.91,
                "critical_issues": [],
                "suggestions": [],
            }

        # Override the default mock for this test
        mock_all_services["openai"].call_with_json_response = AsyncMock(
            side_effect=mock_grounding_response
        )

        from app.services.generation import GenerationService

        service = GenerationService()
        result = await service.generate(
            dictated_text="CT chest clear lungs",
            doctor_id="dr-integration",
            report_type="CT",
            body_region="Chest",
        )

        assert result["id"] == "rpt-integration-001"
        # The pipeline should have completed (accepted or accepted_with_warnings)
        assert result["decision"] in ("accepted", "accepted_with_warnings")
