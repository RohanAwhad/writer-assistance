from __future__ import annotations

from typing import Any

from anthropic import AnthropicVertex
from pydantic import BaseModel, Field

from writer_assistance_api.ai.client import (
    AiSuggestionDraft,
    DiscoveredLens,
    LensName,
    resolve_analysis_lens,
)
from writer_assistance_api.config import Settings

MODEL_NAME = "claude-sonnet-4-5@20250929"
LENS_DISCOVERY_SYSTEM_PROMPT = """
You are discovering document-specific analysis lenses for a reading workspace.

Rules:
- Return 1 to 4 lenses tailored to the provided document.
- Each lens needs a concise name and a one-sentence description.
- Prefer document-specific angles over generic categories.
- Do not repeat the same idea with slightly different wording.
""".strip()
SUGGESTION_SYSTEM_PROMPT = """
You are generating note suggestions for a reading workspace.

Rules:
- Suggestions must be specific, concise, and useful to a human reader.
- Use only direct quotes that appear in the provided markdown.
- Return at most 3 suggestions.
- If no useful suggestions exist, return an empty suggestions list.
""".strip()

class DiscoverLensesOutput(BaseModel):
    lenses: list[DiscoveredLens] = Field(default_factory=list)


class AnalyzeResourceOutput(BaseModel):
    suggestions: list[AiSuggestionDraft] = Field(default_factory=list)


DISCOVER_TOOL_NAME = "emit_lenses"
SUGGEST_TOOL_NAME = "emit_suggestions"


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

    def discover_lenses(
        self,
        *,
        markdown: str,
        logical_path: str,
    ) -> list[DiscoveredLens]:
        response = self._client.messages.create(
            model=MODEL_NAME,
            max_tokens=1200,
            temperature=0,
            system=LENS_DISCOVERY_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": _build_lens_discovery_prompt(
                        markdown=markdown,
                        logical_path=logical_path,
                    ),
                }
            ],
            tools=[
                {
                    "name": DISCOVER_TOOL_NAME,
                    "description": "Return discovered analysis lenses for the document.",
                    "input_schema": DiscoverLensesOutput.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": DISCOVER_TOOL_NAME},
        )
        tool_input = _extract_tool_input(
            response.content,
            tool_name=DISCOVER_TOOL_NAME,
            error_message="AI response did not include a tool_use block for lens discovery",
        )
        parsed_output = DiscoverLensesOutput.model_validate(tool_input)
        return parsed_output.lenses

    def analyze_resource(
        self,
        *,
        markdown: str,
        logical_path: str,
        lens_name: str | None = None,
        lens_description: str | None = None,
        lens: LensName | None = None,
    ) -> list[AiSuggestionDraft]:
        resolved_lens_name, resolved_lens_description = resolve_analysis_lens(
            lens_name=lens_name,
            lens_description=lens_description,
            lens=lens,
        )
        response = self._client.messages.create(
            model=MODEL_NAME,
            max_tokens=2000,
            temperature=0,
            system=SUGGESTION_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": _build_suggestion_prompt(
                        lens_name=resolved_lens_name,
                        lens_description=resolved_lens_description,
                        markdown=markdown,
                        logical_path=logical_path,
                    ),
                }
            ],
            tools=[
                {
                    "name": SUGGEST_TOOL_NAME,
                    "description": "Return reading-workspace note suggestions in the expected schema.",
                    "input_schema": AnalyzeResourceOutput.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": SUGGEST_TOOL_NAME},
        )
        tool_input = _extract_tool_input(
            response.content,
            tool_name=SUGGEST_TOOL_NAME,
            error_message="AI response did not include a tool_use block",
        )
        parsed_output = AnalyzeResourceOutput.model_validate(tool_input)
        return parsed_output.suggestions


def _build_lens_discovery_prompt(*, markdown: str, logical_path: str) -> str:
    return (
        "Discover the best analysis lenses for this document.\n"
        f"Resource path: {logical_path}\n\n"
        "Markdown:\n"
        f"{markdown}"
    )


def _build_suggestion_prompt(
    *,
    lens_name: str,
    lens_description: str,
    markdown: str,
    logical_path: str,
) -> str:
    return (
        f"Lens name: {lens_name}\n"
        f"Lens description: {lens_description}\n"
        f"Resource path: {logical_path}\n\n"
        "Markdown:\n"
        f"{markdown}"
    )


def _extract_tool_input(
    content: list[Any],
    *,
    tool_name: str,
    error_message: str,
) -> Any:
    tool_input = next(
        (
            getattr(block, "input", None)
            for block in content
            if getattr(block, "type", None) == "tool_use"
            and getattr(block, "name", None) == tool_name
        ),
        None,
    )
    if tool_input is None:
        raise ValueError(error_message)
    return tool_input
