"""Orchestrator service for multi-agent report generation pipeline — v2."""

import logging
from typing import Any

from app.agents.supervisor import supervisor_agent
from app.services.ai_search import ai_search_service
from app.services.cosmos_db import cosmos_service

logger = logging.getLogger(__name__)


class GenerationService:
    """
    Orchestrates report generation via the multi-agent pipeline.

    Replaces the v1 monolithic pipeline with a Supervisor Agent that
    coordinates Style Analyst, RAG, Writer, Grounding, and Reviewer agents.
    """

    async def generate(
        self,
        dictated_text: str,
        doctor_id: str,
        report_type: str = "",
        body_region: str = "",
    ) -> dict[str, Any]:
        """Execute the multi-agent generation pipeline."""
        logger.info(
            "Starting multi-agent generation for doctor %s (type=%s, region=%s)",
            doctor_id, report_type, body_region,
        )

        # Build pipeline context
        context = {
            "dictated_text": dictated_text,
            "doctor_id": doctor_id,
            "report_type": report_type,
            "body_region": body_region,
        }

        # Run the supervisor agent (which orchestrates all sub-agents)
        result = await supervisor_agent.run(context)

        if not result.success:
            raise RuntimeError(
                f"Multi-agent pipeline failed: {result.error}"
            )

        # Persist the report
        report_data = {
            "doctor_id": doctor_id,
            "input_text": dictated_text,
            "report_type": report_type,
            "body_region": body_region,
            "findings": result.data["findings"],
            "impressions": result.data["impressions"],
            "recommendations": result.data["recommendations"],
        }
        report = await cosmos_service.create_report(report_data)

        # Index for future RAG retrieval
        try:
            await ai_search_service.index_report(report)
        except Exception as e:
            logger.warning("Failed to index report for search: %s", e)

        # Attach agent pipeline metadata
        report["grounding"] = result.data.get("grounding", {})
        report["review"] = result.data.get("review", {})
        report["revisions"] = result.data.get("revisions", 0)
        report["decision"] = result.data.get("decision", "")
        report["pipeline_trace"] = result.metadata.get("pipeline_trace", [])

        logger.info(
            "Multi-agent generation complete: report %s (decision=%s, revisions=%d)",
            report["id"],
            result.data.get("decision", "unknown"),
            result.data.get("revisions", 0),
        )
        return report


# Singleton instance
generation_service = GenerationService()
