"""Azure OpenAI service — MAF + Azure AI Foundry SDK 2.x.

Uses AIProjectClient (azure-ai-projects) for project-based resource
discovery and inference.  Falls back to direct AzureOpenAI when no
Foundry connection string is configured.
"""

import json
import logging
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from openai import AzureOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class OpenAIService:
    """Manages AI interactions via Azure AI Foundry SDK 2.x (AIProjectClient).

    Falls back to direct AzureOpenAI client when no Foundry connection string
    is configured, ensuring backward compatibility.
    """

    def __init__(self) -> None:
        self._project_client: AIProjectClient | None = None
        self._openai_client: AzureOpenAI | None = None
        self._deployment: str = settings.FOUNDRY_MODEL_DEPLOYMENT or settings.OPENAI_DEPLOYMENT_NAME

    async def initialize(self) -> None:
        """Initialize the AI client via Foundry SDK 2.x or direct OpenAI."""
        credential = DefaultAzureCredential()

        if settings.FOUNDRY_PROJECT_CONNECTION_STRING:
            self._project_client = AIProjectClient.from_connection_string(
                conn_str=settings.FOUNDRY_PROJECT_CONNECTION_STRING,
                credential=credential,
            )
            logger.info(
                "Foundry SDK 2.x AIProjectClient initialized (deployment=%s)",
                self._deployment,
            )
        else:
            from azure.identity import get_bearer_token_provider

            token_provider = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )
            self._openai_client = AzureOpenAI(
                azure_endpoint=settings.OPENAI_ENDPOINT,
                azure_ad_token_provider=token_provider,
                api_version=settings.OPENAI_API_VERSION,
            )
            logger.info(
                "Direct AzureOpenAI client initialized (deployment=%s)",
                self._deployment,
            )

    async def _ensure_initialized(self) -> None:
        """Lazy-initialize if startup initialization was skipped."""
        if self._project_client is None and self._openai_client is None:
            logger.info("OpenAIService not initialized — performing lazy init")
            await self.initialize()

    def _get_inference_client(self) -> AzureOpenAI:
        """Return an OpenAI-compatible inference client.

        Prefers Foundry SDK 2.x AIProjectClient.inference.get_azure_openai_client(),
        falling back to the direct AzureOpenAI client.
        """
        if self._project_client is not None:
            return self._project_client.inference.get_azure_openai_client()
        if self._openai_client is not None:
            return self._openai_client
        raise RuntimeError("OpenAIService not initialized — call initialize() first")

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
        await self._ensure_initialized()
        client = self._get_inference_client()

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

        try:
            response = client.chat.completions.create(
                model=self._deployment,
                messages=messages,
                max_completion_tokens=2000,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            logger.error("OpenAI chat completion failed: %s", e)
            raise

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
        max_completion_tokens: int = 2000,
    ) -> dict[str, Any]:
        """Generic JSON-response call used by validator and reviewer agents."""
        await self._ensure_initialized()
        client = self._get_inference_client()

        response = client.chat.completions.create(
            model=self._deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_completion_tokens=max_completion_tokens,
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
