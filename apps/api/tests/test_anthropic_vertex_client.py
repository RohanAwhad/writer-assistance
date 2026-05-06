from types import SimpleNamespace
from typing import Any, cast

import pytest

from writer_assistance_api.ai.client import (
    AiSuggestionDraft,
    DiscoveredLens,
    resolve_analysis_lens,
)
from writer_assistance_api.ai.anthropic_vertex_client import AnthropicVertexAiClient, MODEL_NAME


def test_discover_lenses_uses_tool_based_structured_output() -> None:
    messages = StubMessages(
        content=[
            SimpleNamespace(
                type="tool_use",
                name="emit_lenses",
                input={
                    "lenses": [
                        {
                            "name": "Demand trend",
                            "description": "Highlights pricing power and revenue implications.",
                        }
                    ]
                },
            )
        ]
    )
    client = AnthropicVertexAiClient(
        project_id="project-id",
        region="us-east5",
        client=SimpleNamespace(messages=messages),  # type: ignore[arg-type]
    )

    lenses = client.discover_lenses(
        markdown="# Market\n\nDemand is rising.",
        logical_path="research/market.md",
    )

    assert lenses == [
        DiscoveredLens(
            name="Demand trend",
            description="Highlights pricing power and revenue implications.",
        )
    ]
    assert len(messages.create_calls) == 1
    assert messages.create_calls[0]["model"] == MODEL_NAME
    assert messages.create_calls[0]["tool_choice"] == {"type": "tool", "name": "emit_lenses"}
    assert messages.create_calls[0]["tools"][0]["name"] == "emit_lenses"
    assert messages.create_calls[0]["tools"][0]["input_schema"] is not None


def test_analyze_resource_uses_tool_based_structured_output() -> None:
    messages = StubMessages()
    client = AnthropicVertexAiClient(
        project_id="project-id",
        region="us-east5",
        client=SimpleNamespace(messages=messages),  # type: ignore[arg-type]
    )

    suggestions = client.analyze_resource(
        lens_name="Demand trend",
        lens_description="Highlights pricing power and revenue implications.",
        markdown="# Market\n\nDemand is rising.",
        logical_path="research/market.md",
    )

    assert suggestions == [
        AiSuggestionDraft.model_validate(
            {
                "body": "Highlight the demand trend as evidence for pricing power.",
                "anchor": {
                    "quoteText": "Demand is rising.",
                    "normalizedText": "demand is rising.",
                    "startOffset": 0,
                    "endOffset": 17,
                    "blockPath": ["paragraph", "1"],
                    "resolutionStatus": "exact",
                },
            }
        )
    ]
    assert len(messages.create_calls) == 1
    assert messages.create_calls[0]["model"] == MODEL_NAME
    assert messages.create_calls[0]["tool_choice"] == {"type": "tool", "name": "emit_suggestions"}
    assert messages.create_calls[0]["tools"][0]["name"] == "emit_suggestions"
    assert messages.create_calls[0]["tools"][0]["input_schema"] is not None


def test_analyze_resource_includes_dynamic_lens_details_in_prompt() -> None:
    messages = StubMessages()
    client = AnthropicVertexAiClient(
        project_id="project-id",
        region="us-east5",
        client=SimpleNamespace(messages=messages),  # type: ignore[arg-type]
    )

    client.analyze_resource(
        lens_name="Demand trend",
        lens_description="Highlights pricing power and revenue implications.",
        markdown="# Market\n\nDemand is rising.",
        logical_path="research/market.md",
    )

    prompt = messages.create_calls[0]["messages"][0]["content"]
    assert "Lens name: Demand trend" in prompt
    assert "Lens description: Highlights pricing power and revenue implications." in prompt


def test_resolve_analysis_lens_supports_legacy_catalog_and_rejects_unknown_values() -> None:
    assert resolve_analysis_lens(lens="financial") == (
        "financial",
        "Focus on financial signals, costs, pricing, demand, revenue implications, and investment relevance.",
    )

    with pytest.raises(ValueError, match="Unknown legacy lens"):
        resolve_analysis_lens(lens=cast(Any, "unknown"))


class StubMessages:
    def __init__(self, *, content: list[Any] | None = None) -> None:
        self.create_calls: list[dict[str, Any]] = []
        self._content = content or [
            SimpleNamespace(
                type="tool_use",
                name="emit_suggestions",
                input={
                    "suggestions": [
                        {
                            "body": "Highlight the demand trend as evidence for pricing power.",
                            "anchor": {
                                "quoteText": "Demand is rising.",
                                "normalizedText": "demand is rising.",
                                "startOffset": 0,
                                "endOffset": 17,
                                "blockPath": ["paragraph", "1"],
                                "resolutionStatus": "exact",
                            },
                        }
                    ]
                },
            )
        ]

    def create(self, **kwargs: Any) -> Any:
        self.create_calls.append(kwargs)
        return SimpleNamespace(content=self._content)
