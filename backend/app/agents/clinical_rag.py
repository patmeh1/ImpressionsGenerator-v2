"""Clinical RAG Agent — searches Azure AI Search for relevant historical notes."""

from typing import Any

from app.agents.base import AgentResult, BaseAgent
from app.services.ai_search import ai_search_service


class ClinicalRAGAgent(BaseAgent):
    """
    Searches Azure AI Search for relevant historical notes for few-shot prompting.

    Dynamically adjusts search strategy based on query characteristics and
    available data. Filters by doctor, report type, and body region.
    """

    def __init__(self) -> None:
        super().__init__("clinical_rag")

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        doctor_id = context["doctor_id"]
        dictated_text = context["dictated_text"]
        report_type = context.get("report_type", "")
        body_region = context.get("body_region", "")

        examples: list[dict[str, Any]] = []

        # Strategy 1: Search with full filters
        try:
            examples = await ai_search_service.search_similar_notes(
                doctor_id=doctor_id,
                query_text=dictated_text,
                report_type=report_type or None,
                body_region=body_region or None,
                top=3,
            )
        except Exception as e:
            self.logger.warning("Primary search failed: %s", e)

        # Strategy 2: Broaden search if too few results
        if len(examples) < 2 and (report_type or body_region):
            try:
                broader = await ai_search_service.search_similar_notes(
                    doctor_id=doctor_id,
                    query_text=dictated_text,
                    top=3,
                )
                existing_ids = {ex["id"] for ex in examples}
                for ex in broader:
                    if ex["id"] not in existing_ids and len(examples) < 3:
                        examples.append(ex)
            except Exception as e:
                self.logger.warning("Broadened search also failed: %s", e)

        confidence = min(1.0, 0.5 + len(examples) * 0.17)

        return AgentResult(
            success=True,
            data={
                "few_shot_examples": examples,
                "search_strategy": "filtered" if examples else "broadened",
                "example_count": len(examples),
            },
            confidence=confidence,
            metadata={
                "doctor_id": doctor_id,
                "report_type": report_type,
                "body_region": body_region,
            },
        )
