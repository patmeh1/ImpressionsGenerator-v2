"""Report generation endpoint — v2 with multi-agent pipeline."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.models.report import GenerateRequest
from app.services.generation import generation_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/generate", tags=["generate"])


@router.post("")
async def generate_report(
    body: GenerateRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Generate a structured clinical report using the multi-agent pipeline.

    The request is processed by a Supervisor Agent that orchestrates:
    Style Analyst → RAG → Report Writer → Grounding Validator → Clinical Reviewer

    Returns the report with grounding validation, clinical review scores,
    and the full pipeline trace for observability.
    """
    if "Admin" not in user.get("roles", []) and user.get("user_id") != body.doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only generate reports for yourself",
        )

    try:
        report = await generation_service.generate(
            dictated_text=body.dictated_text,
            doctor_id=body.doctor_id,
            report_type=body.report_type,
            body_region=body.body_region,
        )
    except RuntimeError as e:
        logger.error("Multi-agent pipeline failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Report generation failed: {e}",
        ) from e
    except Exception as e:
        logger.exception("Unexpected error during report generation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during report generation",
        ) from e

    return report


@router.get("/pipeline-info")
async def get_pipeline_info() -> dict[str, Any]:
    """Return information about the multi-agent pipeline configuration."""
    return {
        "version": "2.0.0",
        "pipeline": "multi-agent",
        "agents": [
            {"name": "style_analyst", "role": "Extract doctor writing style", "pattern": "tool_agent"},
            {"name": "clinical_rag", "role": "RAG few-shot retrieval", "pattern": "tool_agent"},
            {"name": "report_writer", "role": "Generate report sections", "pattern": "core_llm"},
            {"name": "grounding_validator", "role": "AI-powered grounding check", "pattern": "peer_review"},
            {"name": "clinical_reviewer", "role": "Medical accuracy review", "pattern": "peer_review"},
            {"name": "supervisor", "role": "Pipeline orchestration", "pattern": "supervisor"},
        ],
        "orchestration_pattern": "sequential_with_peer_review",
        "max_revisions": 3,
        "model": "GPT-5.2",
        "region": "swedencentral",
    }
