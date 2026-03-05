"""Style Analyst Agent — extracts and maintains doctor writing style profiles."""

from typing import Any

from app.agents.base import AgentResult, BaseAgent
from app.models.style_profile import StyleProfile
from app.services.cosmos_db import cosmos_service
from app.services.openai_service import openai_service


class StyleAnalystAgent(BaseAgent):
    """
    Extracts, maintains, and adapts doctor writing style profiles.

    Retrieves existing style profiles from Cosmos DB or extracts new ones
    by analyzing the doctor's historical clinical notes via Azure OpenAI.
    """

    def __init__(self) -> None:
        super().__init__("style_analyst")

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        doctor_id = context["doctor_id"]

        # Try to retrieve existing profile
        existing = await cosmos_service.get_style_profile(doctor_id)
        if existing:
            profile = StyleProfile(
                **{k: v for k, v in existing.items() if k in StyleProfile.model_fields}
            )
            style_instructions = self._build_style_instructions(profile)
            return AgentResult(
                success=True,
                data={
                    "style_profile": profile.model_dump(),
                    "style_instructions": style_instructions,
                    "source": "cached",
                },
                confidence=0.95,
                metadata={"doctor_id": doctor_id},
            )

        # Extract style from notes
        try:
            profile = await self._extract_style(doctor_id)
            style_instructions = self._build_style_instructions(profile)
            return AgentResult(
                success=True,
                data={
                    "style_profile": profile.model_dump(),
                    "style_instructions": style_instructions,
                    "source": "extracted",
                },
                confidence=0.80,
                metadata={"doctor_id": doctor_id},
            )
        except Exception as e:
            # Return default style if extraction fails
            default_profile = StyleProfile(doctor_id=doctor_id)
            return AgentResult(
                success=True,
                data={
                    "style_profile": default_profile.model_dump(),
                    "style_instructions": self._build_style_instructions(default_profile),
                    "source": "default",
                },
                confidence=0.50,
                error=f"Style extraction failed, using defaults: {e}",
                metadata={"doctor_id": doctor_id},
            )

    async def _extract_style(self, doctor_id: str) -> StyleProfile:
        """Extract style from a doctor's historical notes."""
        notes = await cosmos_service.list_notes(doctor_id)
        if not notes:
            return StyleProfile(doctor_id=doctor_id)

        combined_text = "\n\n".join(
            f"--- Note {i} ---\n{n.get('content', '')}"
            for i, n in enumerate(notes, 1)
            if n.get("content", "").strip()
        )[:100_000]

        style_data = await openai_service.analyze_style(combined_text)

        profile = StyleProfile(
            doctor_id=doctor_id,
            vocabulary_patterns=style_data.get("vocabulary_patterns", []),
            abbreviation_map=style_data.get("abbreviation_map", {}),
            sentence_structure=style_data.get("sentence_structure", []),
            section_ordering=style_data.get("section_ordering", []),
            sample_phrases=style_data.get("sample_phrases", []),
        )

        # Persist the profile
        profile_dict = profile.model_dump()
        await cosmos_service.upsert_style_profile(profile_dict)

        return profile

    def _build_style_instructions(self, profile: StyleProfile) -> str:
        """Convert a style profile into instructions for the LLM."""
        parts: list[str] = []

        if profile.vocabulary_patterns:
            terms = ", ".join(profile.vocabulary_patterns[:20])
            parts.append(f"Use these preferred medical terms: {terms}")

        if profile.abbreviation_map:
            abbrevs = ", ".join(
                f"{k} = {v}" for k, v in list(profile.abbreviation_map.items())[:15]
            )
            parts.append(f"Apply these abbreviations: {abbrevs}")

        if profile.sentence_structure:
            structures = "; ".join(profile.sentence_structure[:10])
            parts.append(f"Sentence style: {structures}")

        if profile.section_ordering:
            ordering = " → ".join(profile.section_ordering)
            parts.append(f"Section order: {ordering}")

        if profile.sample_phrases:
            phrases = "; ".join(f'"{p}"' for p in profile.sample_phrases[:10])
            parts.append(f"Characteristic phrases to emulate: {phrases}")

        if not parts:
            return "No specific style preferences. Use standard radiology reporting style."

        return "\n".join(parts)
