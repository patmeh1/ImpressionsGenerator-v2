"""Grounding Validator Agent — AI-powered grounding check with confidence scores."""

import json
from typing import Any

from app.agents.base import AgentResult, BaseAgent
from app.services.openai_service import openai_service


class GroundingValidatorAgent(BaseAgent):
    """
    AI-powered grounding validation that replaces the v1 regex-based check.

    Uses the LLM to verify every claim in the generated report against
    the original dictation, returning structured confidence scores per
    section and specific hallucination findings.
    """

    def __init__(self) -> None:
        super().__init__("grounding_validator")

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        dictated_text = context["dictated_text"]
        findings = context.get("findings", "")
        impressions = context.get("impressions", "")
        recommendations = context.get("recommendations", "")

        validation_prompt = self._build_validation_prompt(
            dictated_text, findings, impressions, recommendations
        )

        try:
            result = await openai_service.call_with_json_response(
                system_prompt=self._system_prompt(),
                user_message=validation_prompt,
                temperature=0.1,
            )

            overall_score = result.get("overall_confidence", 0.0)
            is_grounded = overall_score >= 0.85
            issues = result.get("issues", [])

            return AgentResult(
                success=True,
                data={
                    "is_grounded": is_grounded,
                    "overall_confidence": overall_score,
                    "section_scores": result.get("section_scores", {}),
                    "issues": issues,
                    "hallucinated_claims": result.get("hallucinated_claims", []),
                    "missing_from_input": result.get("missing_from_input", []),
                    "summary": result.get("summary", ""),
                },
                confidence=overall_score,
            )
        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Grounding validation failed: {e}",
                confidence=0.0,
            )

    def _system_prompt(self) -> str:
        return """You are a clinical grounding validation specialist.

Your task is to compare a generated clinical report against the original dictation
and verify that every claim, measurement, date, and clinical finding in the report
is directly supported by the dictation.

Return a JSON object with:
- "overall_confidence": float 0-1 (1 = perfectly grounded)
- "section_scores": {"findings": float, "impressions": float, "recommendations": float}
- "issues": list of strings describing specific grounding problems
- "hallucinated_claims": list of strings — claims in the report NOT in the dictation
- "missing_from_input": list of strings — important input details omitted from report
- "summary": brief text summary of the grounding assessment

Be strict: any fabricated measurement, date, or clinical value should significantly
lower the confidence score. Minor rephrasing of qualitative descriptions is acceptable.

Respond ONLY with valid JSON."""

    def _build_validation_prompt(
        self,
        dictation: str,
        findings: str,
        impressions: str,
        recommendations: str,
    ) -> str:
        return f"""ORIGINAL DICTATION:
{dictation}

GENERATED REPORT:
--- Findings ---
{findings}

--- Impressions ---
{impressions}

--- Recommendations ---
{recommendations}

Validate that every claim in the generated report is grounded in the dictation."""
