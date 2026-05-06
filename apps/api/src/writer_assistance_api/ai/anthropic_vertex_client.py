from __future__ import annotations

import json
from collections.abc import Mapping

from anthropic import AnthropicVertex

from writer_assistance_api.ai.client import (
    AiSuggestionDraft,
    LensName,
    normalize_suggestion_drafts,
)
from writer_assistance_api.config import Settings

MODEL_NAME = "claude-sonnet-4-5@20250929"
SYSTEM_PROMPT = """
You are generating note suggestions for a reading workspace.

Return JSON only with this shape:
{
  "suggestions": [
    {
      "body": "short suggested note text",
      "anchor": {
        "quoteText": "exact quote from the resource",
        "normalizedText": "lowercased normalized quote text",
        "startOffset": 0,
        "endOffset": 10,
        "blockPath": ["paragraph", "1"],
        "resolutionStatus": "exact"
      }
    }
  ]
}

Rules:
- Suggestions must be specific, concise, and useful to a human reader.
- Use only direct quotes that appear in the provided markdown.
- Return at most 3 suggestions.
- If no useful suggestions exist, return {"suggestions": []}.
""".strip()

LENS_INSTRUCTIONS: Mapping[LensName, str] = {
    "financial": "Focus on financial signals, costs, pricing, demand, revenue implications, and investment relevance.",
    "real_estate": "Focus on land use, zoning, property value implications, occupancy, supply constraints, and development signals.",
    "political": "Focus on governance, regulation, public policy, institutional power, and political risk or opportunity.",
    "software_engineering": "Focus on systems design, implementation constraints, process trade-offs, reliability, and technical debt themes.",
}


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
        response = self._client.messages.create(
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
        )
        text = _extract_text_content(response.content)
        payload = _extract_json_payload(text)
        if not isinstance(payload, dict):
            raise ValueError("AI response must be a JSON object")

        suggestions = payload.get("suggestions")
        if not isinstance(suggestions, list):
            raise ValueError("AI response must include a suggestions array")
        return normalize_suggestion_drafts(suggestions)


def _build_user_prompt(*, lens: LensName, markdown: str, logical_path: str) -> str:
    return (
        f"Lens: {lens}\n"
        f"Lens guidance: {LENS_INSTRUCTIONS[lens]}\n"
        f"Resource path: {logical_path}\n\n"
        "Markdown:\n"
        f"{markdown}"
    )


def _extract_text_content(content_blocks: object) -> str:
    if not isinstance(content_blocks, list):
        raise ValueError("AI response did not include content blocks")

    text_parts: list[str] = []
    for block in content_blocks:
        block_text = getattr(block, "text", None)
        if isinstance(block_text, str):
            text_parts.append(block_text)

    combined = "".join(text_parts).strip()
    if not combined:
        raise ValueError("AI response did not include text content")
    return combined


def _extract_json_payload(text: str) -> object:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.removeprefix("```json").removeprefix("```").strip()
        if stripped.endswith("```"):
            stripped = stripped[:-3].strip()
    return json.loads(stripped)
