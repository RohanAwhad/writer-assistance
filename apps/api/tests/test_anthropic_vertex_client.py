from types import SimpleNamespace
from typing import Any

from writer_assistance_api.ai.client import AiSuggestionDraft
from writer_assistance_api.ai.anthropic_vertex_client import AnthropicVertexAiClient, MODEL_NAME


def test_analyze_resource_uses_sdk_parse_for_structured_output() -> None:
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
    assert len(messages.parse_calls) == 1
    assert messages.parse_calls[0]["model"] == MODEL_NAME
    assert messages.parse_calls[0]["output_format"] is not None


class StubMessages:
    def __init__(self) -> None:
        self.parse_calls: list[dict[str, Any]] = []

    def create(self, **_: Any) -> Any:
        raise AssertionError("analyze_resource should use messages.parse for structured output")

    def parse(self, **kwargs: Any) -> Any:
        self.parse_calls.append(kwargs)
        return SimpleNamespace(
            parsed_output=SimpleNamespace(
                suggestions=[
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
            )
        )
