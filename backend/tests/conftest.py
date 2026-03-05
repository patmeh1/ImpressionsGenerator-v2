"""Test configuration and shared fixtures."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_cosmos_service():
    with patch("app.services.cosmos_db.cosmos_service") as mock:
        mock.get_style_profile = AsyncMock(return_value=None)
        mock.list_notes = AsyncMock(return_value=[])
        mock.upsert_style_profile = AsyncMock()
        mock.create_report = AsyncMock(return_value={
            "id": "test-report-id",
            "doctor_id": "dr-001",
            "findings": "Test findings",
            "impressions": "Test impressions",
            "recommendations": "Test recommendations",
            "status": "draft",
            "created_at": "2026-01-01T00:00:00",
        })
        mock.get_report = AsyncMock(return_value=None)
        mock.list_reports = AsyncMock(return_value=[])
        yield mock


@pytest.fixture
def mock_openai_service():
    with patch("app.services.openai_service.openai_service") as mock:
        mock.generate_report = AsyncMock(return_value={
            "findings": "Test findings",
            "impressions": "Test impressions",
            "recommendations": "Test recommendations",
        })
        mock.call_with_json_response = AsyncMock(return_value={
            "overall_confidence": 0.95,
            "section_scores": {"findings": 0.95, "impressions": 0.93, "recommendations": 0.97},
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
            "suggestions": [],
        })
        mock.analyze_style = AsyncMock(return_value={
            "vocabulary_patterns": ["bilateral", "no acute"],
            "abbreviation_map": {"CT": "computed tomography"},
            "sentence_structure": ["short declarative"],
            "section_ordering": ["findings", "impressions", "recommendations"],
            "sample_phrases": ["no acute findings"],
        })
        yield mock


@pytest.fixture
def mock_ai_search_service():
    with patch("app.services.ai_search.ai_search_service") as mock:
        mock.search_similar_notes = AsyncMock(return_value=[
            {
                "id": "ex-1",
                "content": "Prior CT chest showing...",
                "findings": "Clear lungs.",
                "impressions": "No acute findings.",
                "recommendations": "Routine follow-up.",
                "report_type": "CT",
                "body_region": "Chest",
                "score": 0.95,
            }
        ])
        mock.index_report = AsyncMock()
        yield mock


@pytest.fixture
def sample_dictation():
    return (
        "CT chest without contrast. Lungs are clear bilaterally. "
        "No pleural effusion. Heart size is normal. "
        "Mediastinal structures are unremarkable. "
        "No lymphadenopathy. 3.2 cm nodule in the right lower lobe."
    )


@pytest.fixture
def sample_context(sample_dictation):
    return {
        "dictated_text": sample_dictation,
        "doctor_id": "dr-001",
        "report_type": "CT",
        "body_region": "Chest",
    }
