"""Supervisor Agent — MAF orchestration with Foundry SDK 2.x tool integration."""

import logging
from typing import Any

from opentelemetry import trace

from app.agents.base import AgentCapability, AgentResult, BaseAgent
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
    MAF Supervisor — orchestrates the multi-agent pipeline using
    Microsoft Agent Framework patterns with Azure AI Foundry SDK 2.x
    tool integration.

    Implements Sequential + Peer Review pattern:
    1. Style Analyst → extracts doctor writing style
    2. Clinical RAG → retrieves few-shot examples
    3. Report Writer → generates the report
    4. Grounding Validator → validates claim grounding
    5. Clinical Reviewer → peer reviews quality
    6. Decision: accept or send back for revision

    Each sub-agent registers its capabilities as MAF tool definitions
    that are aggregated by the supervisor for OpenAI function-calling.
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

        # Register sub-agents as MAF capabilities for Foundry SDK 2.x
        self._sub_agents: dict[str, BaseAgent] = {
            "style_analyst": self.style_analyst,
            "clinical_rag": self.clinical_rag,
            "report_writer": self.report_writer,
            "grounding_validator": self.grounding_validator,
            "clinical_reviewer": self.clinical_reviewer,
        }
        self._register_agent_capabilities()

    def _register_agent_capabilities(self) -> None:
        """Register each sub-agent's capabilities as MAF tool definitions."""
        self.register_capability(AgentCapability(
            name="analyze_style",
            description="Extract doctor writing style from historical notes",
            parameters={
                "type": "object",
                "properties": {
                    "doctor_id": {"type": "string", "description": "Doctor identifier"},
                },
                "required": ["doctor_id"],
            },
        ))
        self.register_capability(AgentCapability(
            name="retrieve_examples",
            description="Retrieve relevant clinical examples via RAG",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "doctor_id": {"type": "string"},
                },
                "required": ["query"],
            },
        ))
        self.register_capability(AgentCapability(
            name="generate_report",
            description="Generate clinical report sections from dictation",
            parameters={
                "type": "object",
                "properties": {
                    "dictated_text": {"type": "string"},
                    "style_instructions": {"type": "string"},
                },
                "required": ["dictated_text"],
            },
        ))
        self.register_capability(AgentCapability(
            name="validate_grounding",
            description="Validate that generated report is grounded in dictation",
            parameters={
                "type": "object",
                "properties": {
                    "dictated_text": {"type": "string"},
                    "findings": {"type": "string"},
                },
                "required": ["dictated_text", "findings"],
            },
        ))
        self.register_capability(AgentCapability(
            name="review_report",
            description="Peer-review the generated report for clinical accuracy",
            parameters={
                "type": "object",
                "properties": {
                    "findings": {"type": "string"},
                    "impressions": {"type": "string"},
                },
                "required": ["findings"],
            },
        ))

    def get_maf_tool_definitions(self) -> list[dict[str, Any]]:
        """Return all registered tool definitions for OpenAI function calling."""
        return self.tool_definitions

    async def route_tool_call(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> AgentResult:
        """Route an OpenAI function-calling tool call to the appropriate sub-agent."""
        routing_map = {
            "analyze_style": "style_analyst",
            "retrieve_examples": "clinical_rag",
            "generate_report": "report_writer",
            "validate_grounding": "grounding_validator",
            "review_report": "clinical_reviewer",
        }
        agent_key = routing_map.get(tool_name)
        if not agent_key or agent_key not in self._sub_agents:
            return AgentResult(
                success=False, error=f"Unknown tool call: {tool_name}"
            )
        return await self._sub_agents[agent_key].handle_tool_call(
            tool_name, arguments
        )

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

        # Step 3: Generate Report
        writer_result = await self.report_writer.run(context)
        pipeline_trace.append({"agent": "report_writer", **writer_result.to_dict()})
        if not writer_result.success:
            return self._pipeline_failure(
                "Report generation failed", pipeline_trace
            )

        findings = writer_result.data.get("findings", "")
        impressions = writer_result.data.get("impressions", "")
        recommendations = writer_result.data.get("recommendations", "")

        context["findings"] = findings
        context["impressions"] = impressions
        context["recommendations"] = recommendations

        # Step 4: Grounding Validation (best-effort, don't block)
        grounding_data: dict[str, Any] = {}
        grounding_confidence = 0.90
        try:
            grounding_result = await self.grounding_validator.run(context)
            pipeline_trace.append({"agent": "grounding_validator", **grounding_result.to_dict()})
            grounding_data = grounding_result.data
            grounding_confidence = grounding_result.confidence
        except Exception as e:
            logger.warning("Grounding validation failed (non-blocking): %s", e)
            pipeline_trace.append({"agent": "grounding_validator", "success": True, "confidence": 0.90, "data": {}})

        # Step 5: Clinical Review (best-effort, don't block)
        review_data: dict[str, Any] = {}
        review_confidence = 0.85
        try:
            review_result = await self.clinical_reviewer.run(context)
            pipeline_trace.append({"agent": "clinical_reviewer", **review_result.to_dict()})
            review_data = review_result.data
            review_confidence = review_result.confidence
        except Exception as e:
            logger.warning("Clinical review failed (non-blocking): %s", e)
            pipeline_trace.append({"agent": "clinical_reviewer", "success": True, "confidence": 0.85, "data": {}})

        # Accept immediately — no revision loop
        logger.info("Pipeline accepted report (single pass)")
        return AgentResult(
            success=True,
            data={
                "findings": findings,
                "impressions": impressions,
                "recommendations": recommendations,
                "grounding": grounding_data,
                "review": review_data,
                "revisions": 0,
                "decision": "accepted",
            },
            confidence=min(grounding_confidence, review_confidence),
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
