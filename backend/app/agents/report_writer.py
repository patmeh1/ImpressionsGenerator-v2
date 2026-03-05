"""Report Writer Agent — generates findings, impressions, and recommendations."""

from typing import Any

from app.agents.base import AgentResult, BaseAgent
from app.services.openai_service import openai_service


class ReportWriterAgent(BaseAgent):
    """
    Generates clinical report sections (findings, impressions, recommendations)
    using the doctor's style profile and RAG context from prior agents.

    Accepts optional revision feedback from the Supervisor for iterative
    refinement when grounding or review issues are detected.
    """

    def __init__(self) -> None:
        super().__init__("report_writer")

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        dictated_text = context["dictated_text"]
        style_instructions = context.get("style_instructions", "")
        few_shot_examples = context.get("few_shot_examples", [])
        report_type = context.get("report_type", "")
        body_region = context.get("body_region", "")
        revision_feedback = context.get("revision_feedback")

        # Build grounding rules
        grounding_rules = self._build_grounding_rules(dictated_text)

        # If this is a revision, add feedback to the prompt
        if revision_feedback:
            grounding_rules += (
                f"\n\nREVISION FEEDBACK — address these issues:\n{revision_feedback}"
            )

        try:
            generated = await openai_service.generate_report(
                dictated_text=dictated_text,
                style_instructions=style_instructions,
                grounding_rules=grounding_rules,
                few_shot_examples=few_shot_examples,
                report_type=report_type,
                body_region=body_region,
            )

            return AgentResult(
                success=True,
                data={
                    "findings": generated["findings"],
                    "impressions": generated["impressions"],
                    "recommendations": generated["recommendations"],
                    "is_revision": bool(revision_feedback),
                },
                confidence=0.90,
            )
        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Report generation failed: {e}",
                confidence=0.0,
            )

    def _build_grounding_rules(self, dictated_text: str) -> str:
        return (
            "CRITICAL GROUNDING CONSTRAINTS:\n"
            "1. Every measurement, number, date, and percentage in your output "
            "MUST come directly from the dictated input.\n"
            "2. Do NOT invent or infer any quantitative values.\n"
            "3. If the dictation mentions a finding without specific measurements, "
            "describe it qualitatively without adding numbers.\n"
            "4. Preserve all specific values from the dictation exactly as stated.\n"
            f"5. Key details to preserve:\n   {dictated_text[:500]}"
        )
