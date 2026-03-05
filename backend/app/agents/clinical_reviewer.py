"""Clinical Reviewer Agent — peer review for medical accuracy and quality."""

from typing import Any

from app.agents.base import AgentResult, BaseAgent
from app.services.openai_service import openai_service


class ClinicalReviewerAgent(BaseAgent):
    """
    Reviews generated reports for medical accuracy, terminology correctness,
    completeness, and style adherence.

    Acts as a peer reviewer in the multi-agent pipeline, providing structured
    feedback that the Supervisor can use to decide accept/revise.
    """

    def __init__(self) -> None:
        super().__init__("clinical_reviewer")

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        dictated_text = context["dictated_text"]
        findings = context.get("findings", "")
        impressions = context.get("impressions", "")
        recommendations = context.get("recommendations", "")
        style_instructions = context.get("style_instructions", "")
        report_type = context.get("report_type", "")
        body_region = context.get("body_region", "")

        review_prompt = self._build_review_prompt(
            dictated_text,
            findings,
            impressions,
            recommendations,
            style_instructions,
            report_type,
            body_region,
        )

        try:
            result = await openai_service.call_with_json_response(
                system_prompt=self._system_prompt(),
                user_message=review_prompt,
                temperature=0.2,
            )

            quality_score = result.get("overall_quality", 0.0)

            return AgentResult(
                success=True,
                data={
                    "overall_quality": quality_score,
                    "medical_accuracy": result.get("medical_accuracy", 0.0),
                    "terminology_correctness": result.get("terminology_correctness", 0.0),
                    "completeness": result.get("completeness", 0.0),
                    "style_adherence": result.get("style_adherence", 0.0),
                    "critical_issues": result.get("critical_issues", []),
                    "suggestions": result.get("suggestions", []),
                    "summary": result.get("summary", ""),
                },
                confidence=quality_score,
            )
        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Clinical review failed: {e}",
                confidence=0.0,
            )

    def _system_prompt(self) -> str:
        return """You are a senior radiologist performing peer review of AI-generated clinical reports.

Evaluate the report on these dimensions (score 0-1 each):
1. medical_accuracy — Are all medical claims clinically sound?
2. terminology_correctness — Is medical terminology used correctly?
3. completeness — Are all dictated findings addressed in the report?
4. style_adherence — Does the report match the specified writing style?

Return a JSON object with:
- "overall_quality": float 0-1 (weighted average of the four dimensions)
- "medical_accuracy": float 0-1
- "terminology_correctness": float 0-1
- "completeness": float 0-1
- "style_adherence": float 0-1
- "critical_issues": list of strings — serious problems that MUST be fixed
- "suggestions": list of strings — optional improvements
- "summary": brief text summary of the review

Be thorough but fair. Only flag critical_issues for genuine medical errors,
missing critical findings, or significant style deviations.

Respond ONLY with valid JSON."""

    def _build_review_prompt(
        self,
        dictation: str,
        findings: str,
        impressions: str,
        recommendations: str,
        style_instructions: str,
        report_type: str,
        body_region: str,
    ) -> str:
        return f"""ORIGINAL DICTATION:
{dictation}

REPORT TYPE: {report_type or 'Not specified'}
BODY REGION: {body_region or 'Not specified'}

STYLE INSTRUCTIONS:
{style_instructions or 'Standard radiology reporting style'}

GENERATED REPORT:
--- Findings ---
{findings}

--- Impressions ---
{impressions}

--- Recommendations ---
{recommendations}

Perform a thorough peer review of this report."""
