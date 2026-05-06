from types import SimpleNamespace
from typing import Any

from writer_assistance_api.ai.client import AiSuggestionDraft
from writer_assistance_api.ai.anthropic_vertex_client import AnthropicVertexAiClient, MODEL_NAME


def test_analyze_resource_uses_tool_based_structured_output() -> None:
    messages = StubMessages()
    client = AnthropicVertexAiClient(
        project_id="project-id",
        region="us-east5",
        client=SimpleNamespace(messages=messages),  # type: ignore[arg-type]
    )

    suggestions = client.analyze_resource(
        lens="financial",
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


class StubMessages:
    def __init__(self) -> None:
        self.create_calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.create_calls.append(kwargs)
        return SimpleNamespace(
            content=[
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
        )
