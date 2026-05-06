from __future__ import annotations

from collections.abc import Mapping

from anthropic import AnthropicVertex
from pydantic import BaseModel, Field

from writer_assistance_api.ai.client import (
    AiSuggestionDraft,
    LensName,
)
from writer_assistance_api.config import Settings

MODEL_NAME = "claude-sonnet-4-5@20250929"
SYSTEM_PROMPT = """
You are generating note suggestions for a reading workspace.

Rules:
- Suggestions must be specific, concise, and useful to a human reader.
- Use only direct quotes that appear in the provided markdown.
- Return at most 3 suggestions.
- If no useful suggestions exist, return an empty suggestions list.
""".strip()

LENS_INSTRUCTIONS: Mapping[LensName, str] = {
    "financial": "Focus on financial signals, costs, pricing, demand, revenue implications, and investment relevance.",
    "real_estate": "Focus on land use, zoning, property value implications, occupancy, supply constraints, and development signals.",
    "political": "Focus on governance, regulation, public policy, institutional power, and political risk or opportunity.",
    "software_engineering": "Focus on systems design, implementation constraints, process trade-offs, reliability, and technical debt themes.",
}


class AnalyzeResourceOutput(BaseModel):
    suggestions: list[AiSuggestionDraft] = Field(default_factory=list)


class AnthropicVertexAiClient:
    def __init__(
        self,
        *,
        project_id: str,
        region: str,
        client: AnthropicVertex | None = None,
    ) -> None:
        self._client = client or AnthropicVertex(project_id=project_id, region=region)

    @classmethod
    def from_settings(cls, settings: Settings) -> "AnthropicVertexAiClient":
        if not settings.anthropic_vertex_project_id or not settings.cloud_ml_region:
            raise RuntimeError(
                "Anthropic Vertex AI is not configured. "
                "Set ANTHROPIC_VERTEX_PROJECT_ID and CLOUD_ML_REGION."
            )
        return cls(
            project_id=settings.anthropic_vertex_project_id,
            region=settings.cloud_ml_region,
        )

    def analyze_resource(
        self,
        *,
        lens: LensName,
        markdown: str,
        logical_path: str,
    ) -> list[AiSuggestionDraft]:
        response = self._client.messages.parse(
            model=MODEL_NAME,
            max_tokens=2000,
            temperature=0,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": _build_user_prompt(
                        lens=lens,
                        markdown=markdown,
                        logical_path=logical_path,
                    ),
                }
            ],
            output_format=AnalyzeResourceOutput,
        )
        parsed_output = response.parsed_output
        if parsed_output is None:
            raise ValueError("AI response did not include parsed structured output")
        return parsed_output.suggestions


def _build_user_prompt(*, lens: LensName, markdown: str, logical_path: str) -> str:
    return (
        f"Lens: {lens}\n"
        f"Lens guidance: {LENS_INSTRUCTIONS[lens]}\n"
        f"Resource path: {logical_path}\n\n"
        "Markdown:\n"
        f"{markdown}"
    )
