"""Style extraction service — v2 compatibility wrapper.

Delegates to StyleAnalystAgent for actual extraction while maintaining
backward compatibility with routers that import style_extraction_service.
"""

import logging
from typing import Any

from app.models.style_profile import StyleProfile
from app.services.cosmos_db import cosmos_service
from app.services.openai_service import openai_service

logger = logging.getLogger(__name__)


class StyleExtractionService:
    """Backward-compatible style extraction that delegates to the agent."""

    async def extract_style(self, doctor_id: str) -> StyleProfile:
        """Extract style from a doctor's notes."""
        notes = await cosmos_service.list_notes(doctor_id)
        if not notes:
            logger.warning("No notes for doctor %s; returning empty profile", doctor_id)
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

        profile_dict = profile.model_dump()
        existing = await cosmos_service.get_style_profile(doctor_id)
        if existing:
            profile_dict["id"] = existing["id"]
        await cosmos_service.upsert_style_profile(profile_dict)

        logger.info("Style profile updated for doctor %s", doctor_id)
        return profile

    def build_style_instructions(self, profile: StyleProfile) -> str:
        """Convert a style profile into instructions for the LLM."""
        parts: list[str] = []
        if profile.vocabulary_patterns:
            parts.append(f"Use these terms: {', '.join(profile.vocabulary_patterns[:20])}")
        if profile.abbreviation_map:
            parts.append(f"Abbreviations: {', '.join(f'{k}={v}' for k, v in list(profile.abbreviation_map.items())[:15])}")
        if profile.sentence_structure:
            parts.append(f"Style: {'; '.join(profile.sentence_structure[:10])}")
        if profile.section_ordering:
            parts.append(f"Order: {' → '.join(profile.section_ordering)}")
        if profile.sample_phrases:
            parts.append(f"Phrases: {'; '.join(profile.sample_phrases[:10])}")
        return "\n".join(parts) if parts else "Standard radiology reporting style."


# Singleton instance
style_extraction_service = StyleExtractionService()
