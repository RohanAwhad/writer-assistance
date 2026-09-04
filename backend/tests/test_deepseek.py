"""Unit tests for the DeepSeek provider (R-070..R-074): env handling,
settings, the OpenAI-compatible transport envelope, and five-call routing.

All tests stub the ChatFn boundary — no env vars, no network (spec SD-16).
"""

import pytest

from app.ai import deepseek
from app.ai.client import ExpertNoteDraft, LensDraft, ParagraphDraft, ToneSampleDraft
from app.errors import AIError, AIFormatError, ConfigError

DEFAULT_MODEL = "deepseek-v4-flash"
MODEL = "deepseek-model-under-test"


def full_env() -> dict[str, str]:
    return {
        "DEEPSEEK_API_KEY": "sk-test",
        "DEEPSEEK_MODEL": MODEL,
    }


def test_read_settings_reads_deepseek_env_names() -> None:
    settings = deepseek.read_deepseek_settings(full_env())
    assert settings.api_key == "sk-test"
    assert settings.model == MODEL


def test_model_defaults_to_deepseek_v4_flash_when_unset() -> None:
    settings = deepseek.read_deepseek_settings({"DEEPSEEK_API_KEY": "sk-test"})
    assert settings.model == DEFAULT_MODEL


def test_missing_api_key_raises_config_error_naming_var() -> None:
    with pytest.raises(ConfigError) as excinfo:
        deepseek.read_deepseek_settings({"DEEPSEEK_MODEL": MODEL})
    assert "DEEPSEEK_API_KEY" in str(excinfo.value)


def test_empty_api_key_counts_as_missing() -> None:
    with pytest.raises(ConfigError):
        deepseek.read_deepseek_settings({"DEEPSEEK_API_KEY": ""})


def test_build_ai_client_from_env_dict_constructs_offline() -> None:
    client = deepseek.build_ai_client(full_env())
    assert client is not None


def make_client(raw: str) -> tuple[deepseek.DeepSeekAIClient, list[tuple[str, str, str, int]]]:
    calls: list[tuple[str, str, str, int]] = []

    def chat(system: str, user: str, model: str, max_tokens: int) -> str:
        calls.append((system, user, model, max_tokens))
        return raw

    return deepseek.DeepSeekAIClient(chat, MODEL), calls


def test_all_five_call_kinds_route_to_the_single_model() -> None:
    calls: list[str] = []

    def chat(system: str, user: str, model: str, max_tokens: int) -> str:
        calls.append(model)
        if "lenses that would produce" in user:
            return '[{"title": "T", "rationale": "R"}]'
        if "through the lens of" in system:
            return '[{"content": "N"}]'
        if "curated notes dump" in user:
            return '["P"]'
        if "EXACTLY 5" in user:
            return "[" + ",".join(f'{{"tone": "t{i}", "text": "s{i}"}}' for i in range(5)) + "]"
        return '{"critique": "C"}'

    client = deepseek.DeepSeekAIClient(chat, MODEL)
    assert client.propose_lenses("p", "c") == [LensDraft("T", "R")]
    assert client.expert_notes("p", "c", "Financial") == [ExpertNoteDraft("N")]
    assert client.generate_report("d") == [ParagraphDraft("P")]
    assert len(client.tone_samples("b", "ctx")) == 5
    assert client.critique("b", "ctx") == "C"
    assert calls == [MODEL, MODEL, MODEL, MODEL, MODEL]


def test_propose_lenses_parses_and_rejects_empty() -> None:
    raw = '[{"title": "Financial", "rationale": "Numbers matter."}]'
    client, calls = make_client(raw)
    assert client.propose_lenses("docs/a.md", "body") == [
        LensDraft("Financial", "Numbers matter.")
    ]
    assert calls[0][2] == MODEL
    assert "docs/a.md" in calls[0][1] and "body" in calls[0][1]
    bad_client, _ = make_client("[]")
    with pytest.raises(AIFormatError):
        bad_client.propose_lenses("p.md", "c")


def test_expert_notes_shapes_request_and_parses() -> None:
    raw = '[{"content": "Note one."}]'
    client, calls = make_client(raw)
    drafts = client.expert_notes("docs/a.md", "body", "Financial")
    assert drafts == [ExpertNoteDraft("Note one.")]
    _system, user, model, _tokens = calls[0]
    assert model == MODEL
    assert "Financial" in user


def test_tone_and_critique_parse() -> None:
    tones_raw = "[" + ",".join(f'{{"tone": "t{i}", "text": "sample {i}"}}' for i in range(5)) + "]"
    client, _ = make_client(tones_raw)
    samples = client.tone_samples("block", "context")
    assert len(samples) == 5
    assert all(isinstance(s, ToneSampleDraft) for s in samples)

    critique_client, _ = make_client('{"critique": "The claim is unsupported."}')
    assert critique_client.critique("block", "context") == "The claim is unsupported."


def test_assistant_text_extraction() -> None:
    valid = {"choices": [{"message": {"content": "  hello "}}]}
    assert deepseek._assistant_text(valid) == "hello"


def test_assistant_text_rejects_out_of_contract_envelopes() -> None:
    cases: list[object] = [
        "not json",
        {"no_choices": []},
        {"choices": []},
        {"choices": ["not an object"]},
        {"choices": [{"no_message": True}]},
        {"choices": [{"message": {"content": ""}}]},
        {"choices": [{"message": {"content": "   "}}]},
        {"choices": [{"message": {"content": 42}}]},
    ]
    for case in cases:
        with pytest.raises(AIError):
            deepseek._assistant_text(case)
