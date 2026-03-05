"""Supervisor Agent — orchestrates the multi-agent pipeline."""

import logging
from typing import Any

from opentelemetry import trace

from app.agents.base import AgentResult, BaseAgent
from app.agents.clinical_rag import ClinicalRAGAgent
from app.agents.clinical_reviewer import ClinicalReviewerAgent
from app.agents.grounding_validator import GroundingValidatorAgent
from app.agents.report_writer import ReportWriterAgent
from app.agents.style_analyst import StyleAnalystAgent
from app.config import settings

tracer = trace.get_tracer("impressions-generator.supervisor")
logger = logging.getLogger(__name__)


class SupervisorAgent(BaseAgent):
    """
    Orchestrates the full multi-agent report generation pipeline.

    Implements Sequential + Peer Review pattern:
    1. Style Analyst → extracts doctor writing style
    2. Clinical RAG → retrieves few-shot examples
    3. Report Writer → generates the report
    4. Grounding Validator → validates claim grounding
    5. Clinical Reviewer → peer reviews quality
    6. Decision: accept or send back for revision

    If grounding or review fails, routes output back to Report Writer
    with specific feedback for iterative refinement.
    """

    def __init__(self) -> None:
        super().__init__("supervisor")
        self.style_analyst = StyleAnalystAgent()
        self.clinical_rag = ClinicalRAGAgent()
        self.report_writer = ReportWriterAgent()
        self.grounding_validator = GroundingValidatorAgent()
        self.clinical_reviewer = ClinicalReviewerAgent()
        self.max_revisions = settings.AGENT_MAX_REVISIONS
        self.grounding_threshold = settings.GROUNDING_CONFIDENCE_THRESHOLD

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        with tracer.start_as_current_span(
            "supervisor.pipeline",
            attributes={
                "doctor_id": context.get("doctor_id", ""),
                "report_type": context.get("report_type", ""),
                "body_region": context.get("body_region", ""),
            },
        ):
            return await self._run_pipeline(context)

    async def _run_pipeline(self, context: dict[str, Any]) -> AgentResult:
        pipeline_trace: list[dict[str, Any]] = []

        # Step 1: Style Analysis
        style_result = await self.style_analyst.run(context)
        pipeline_trace.append({"agent": "style_analyst", **style_result.to_dict()})
        if not style_result.success:
            return self._pipeline_failure("Style analysis failed", pipeline_trace)

        context["style_instructions"] = style_result.data.get("style_instructions", "")
        context["style_profile"] = style_result.data.get("style_profile", {})

        # Step 2: Clinical RAG
        rag_result = await self.clinical_rag.run(context)
        pipeline_trace.append({"agent": "clinical_rag", **rag_result.to_dict()})

        context["few_shot_examples"] = rag_result.data.get("few_shot_examples", [])

        # Steps 3-5: Write → Validate → Review (with revision loop)
        revision = 0
        while revision <= self.max_revisions:
            # Step 3: Generate Report
            writer_result = await self.report_writer.run(context)
            pipeline_trace.append({
                "agent": "report_writer",
                "revision": revision,
                **writer_result.to_dict(),
            })
            if not writer_result.success:
                return self._pipeline_failure(
                    "Report generation failed", pipeline_trace
                )

            findings = writer_result.data.get("findings", "")
            impressions = writer_result.data.get("impressions", "")
            recommendations = writer_result.data.get("recommendations", "")

            # Update context for validators
            context["findings"] = findings
            context["impressions"] = impressions
            context["recommendations"] = recommendations

            # Step 4: Grounding Validation
            grounding_result = await self.grounding_validator.run(context)
            pipeline_trace.append({
                "agent": "grounding_validator",
                "revision": revision,
                **grounding_result.to_dict(),
            })

            # Step 5: Clinical Review
            review_result = await self.clinical_reviewer.run(context)
            pipeline_trace.append({
                "agent": "clinical_reviewer",
                "revision": revision,
                **review_result.to_dict(),
            })

            # Decision: accept or revise?
            decision = self._decide(grounding_result, review_result, revision)

            if decision == "accept":
                logger.info(
                    "Pipeline accepted report after %d revision(s)", revision
                )
                return AgentResult(
                    success=True,
                    data={
                        "findings": findings,
                        "impressions": impressions,
                        "recommendations": recommendations,
                        "grounding": grounding_result.data,
                        "review": review_result.data,
                        "revisions": revision,
                        "decision": "accepted",
                    },
                    confidence=min(
                        grounding_result.confidence, review_result.confidence
                    ),
                    metadata={"pipeline_trace": pipeline_trace},
                )

            # Revise: build feedback for the writer
            feedback = self._build_revision_feedback(
                grounding_result, review_result
            )
            context["revision_feedback"] = feedback
            revision += 1
            logger.info("Requesting revision %d: %s", revision, feedback[:200])

        # Max revisions exceeded — return best effort
        logger.warning(
            "Max revisions (%d) exceeded; returning best-effort report",
            self.max_revisions,
        )
        return AgentResult(
            success=True,
            data={
                "findings": context.get("findings", ""),
                "impressions": context.get("impressions", ""),
                "recommendations": context.get("recommendations", ""),
                "grounding": grounding_result.data,
                "review": review_result.data,
                "revisions": self.max_revisions,
                "decision": "accepted_with_warnings",
            },
            confidence=min(grounding_result.confidence, review_result.confidence),
            metadata={"pipeline_trace": pipeline_trace},
        )

    def _decide(
        self,
        grounding: AgentResult,
        review: AgentResult,
        revision: int,
    ) -> str:
        """Decide whether to accept the report or request revision."""
        grounding_ok = grounding.data.get("is_grounded", False)
        grounding_score = grounding.data.get("overall_confidence", 0.0)
        review_quality = review.data.get("overall_quality", 0.0)
        critical_issues = review.data.get("critical_issues", [])

        # Accept if both pass thresholds and no critical issues
        if (
            grounding_ok
            and grounding_score >= self.grounding_threshold
            and review_quality >= 0.75
            and not critical_issues
        ):
            return "accept"

        # Accept with lower threshold on final revision
        if revision >= self.max_revisions:
            return "accept"

        # On later revisions, be more lenient
        if revision >= 2 and grounding_score >= 0.70 and review_quality >= 0.65:
            return "accept"

        return "revise"

    def _build_revision_feedback(
        self, grounding: AgentResult, review: AgentResult
    ) -> str:
        """Compile feedback from grounding and review agents for the writer."""
        parts: list[str] = []

        # Grounding issues
        hallucinated = grounding.data.get("hallucinated_claims", [])
        if hallucinated:
            parts.append(
                "GROUNDING ISSUES — these claims are NOT in the dictation, remove them:\n"
                + "\n".join(f"  - {h}" for h in hallucinated)
            )

        grounding_issues = grounding.data.get("issues", [])
        if grounding_issues:
            parts.append(
                "GROUNDING WARNINGS:\n"
                + "\n".join(f"  - {i}" for i in grounding_issues)
            )

        # Review issues
        critical = review.data.get("critical_issues", [])
        if critical:
            parts.append(
                "CRITICAL REVIEW ISSUES — must fix:\n"
                + "\n".join(f"  - {c}" for c in critical)
            )

        suggestions = review.data.get("suggestions", [])
        if suggestions:
            parts.append(
                "SUGGESTIONS:\n"
                + "\n".join(f"  - {s}" for s in suggestions[:3])
            )

        return "\n\n".join(parts) if parts else "Please improve overall quality."

    def _pipeline_failure(
        self, message: str, trace: list[dict[str, Any]]
    ) -> AgentResult:
        return AgentResult(
            success=False,
            error=message,
            confidence=0.0,
            metadata={"pipeline_trace": trace},
        )


# Singleton instance
supervisor_agent = SupervisorAgent()
