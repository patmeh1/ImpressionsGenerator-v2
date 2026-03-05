"""Azure OpenAI service for clinical report generation — v2."""

import json
import logging
from typing import Any

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class OpenAIService:
    """Manages interactions with Azure OpenAI GPT-5.2."""

    def __init__(self) -> None:
        self._client: AzureOpenAI | None = None

    async def initialize(self) -> None:
        """Initialize the Azure OpenAI client."""
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
        self._client = AzureOpenAI(
            azure_endpoint=settings.OPENAI_ENDPOINT,
            azure_ad_token_provider=token_provider,
            api_version=settings.OPENAI_API_VERSION,
        )
        logger.info("Azure OpenAI client initialized (model=%s)", settings.OPENAI_DEPLOYMENT_NAME)

    def _ensure_client(self) -> AzureOpenAI:
        if self._client is None:
            raise RuntimeError("OpenAIService not initialized")
        return self._client

    async def generate_report(
        self,
        dictated_text: str,
        style_instructions: str,
        grounding_rules: str,
        few_shot_examples: list[dict[str, Any]] | None = None,
        report_type: str = "",
        body_region: str = "",
    ) -> dict[str, str]:
        """Generate a structured clinical report from dictation."""
        client = self._ensure_client()

        system_prompt = self._build_system_prompt(style_instructions, grounding_rules)
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]

        if few_shot_examples:
            messages.extend(self._build_few_shot_messages(few_shot_examples))

        user_content = f"Dictation: {dictated_text}"
        if report_type:
            user_content += f"\nReport Type: {report_type}"
        if body_region:
            user_content += f"\nBody Region: {body_region}"

        messages.append({"role": "user", "content": user_content})

        response = client.chat.completions.create(
            model=settings.OPENAI_DEPLOYMENT_NAME,
            messages=messages,
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Empty response from Azure OpenAI")

        result = json.loads(content)
        return {
            "findings": result.get("findings", ""),
            "impressions": result.get("impressions", ""),
            "recommendations": result.get("recommendations", ""),
        }

    async def call_with_json_response(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        """Generic JSON-response call used by validator and reviewer agents."""
        client = self._ensure_client()

        response = client.chat.completions.create(
            model=settings.OPENAI_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Empty response from Azure OpenAI")
        return json.loads(content)

    async def analyze_style(self, notes_text: str) -> dict[str, Any]:
        """Analyze clinical notes to extract writing style features."""
        system_prompt = """You are an expert linguistic analyst specializing in medical writing.
Analyze the provided clinical notes and extract the doctor's writing style features.

Return a JSON object with these keys:
- "vocabulary_patterns": list of common medical terms and phrases the doctor favors
- "abbreviation_map": dict mapping abbreviations to their full forms
- "sentence_structure": list describing typical sentence patterns
- "section_ordering": list of how the doctor typically orders report sections
- "sample_phrases": list of characteristic phrases the doctor commonly uses

Respond ONLY with valid JSON."""

        return await self.call_with_json_response(
            system_prompt=system_prompt,
            user_message=f"Clinical notes to analyze:\n\n{notes_text}",
        )

    def _build_system_prompt(self, style_instructions: str, grounding_rules: str) -> str:
        return f"""You are a clinical radiology/oncology report generation assistant.
Your task is to transform dictated radiology findings into a structured clinical report
that matches the writing style of the specific doctor.

STYLE INSTRUCTIONS:
{style_instructions}

GROUNDING RULES:
{grounding_rules}

IMPORTANT:
- Only include clinical information explicitly stated or directly implied by the dictation.
- Do NOT fabricate measurements, dates, values, or findings.
- Every number, measurement, and percentage in the output MUST originate from the input.
- Maintain medical accuracy and appropriate clinical terminology.
- Structure the output as JSON with keys: "findings", "impressions", "recommendations".

Respond ONLY with valid JSON."""

    def _build_few_shot_messages(self, examples: list[dict[str, Any]]) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        for ex in examples[:3]:
            messages.append({
                "role": "user",
                "content": f"Dictation: {ex.get('input_text', ex.get('content', ''))}",
            })
            output = {
                "findings": ex.get("findings", ""),
                "impressions": ex.get("impressions", ""),
                "recommendations": ex.get("recommendations", ""),
            }
            messages.append({"role": "assistant", "content": json.dumps(output)})
        return messages


# Singleton instance
openai_service = OpenAIService()
