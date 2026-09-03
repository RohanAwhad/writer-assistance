"""Env-var handling of the AI client (RES-001 names, alias rules)."""

import pytest

from app.ai import vertex
from app.errors import ConfigError


def full_env() -> dict[str, str]:
    return {
        "ANTHROPIC_VERTEX_PROJECT_ID": "proj-123",
        "ANTHROPIC_MODEL": "claude-big",
        "ANTHROPIC_SMALL_FAST_MODEL": "claude-small",
        "GOOGLE_VERTEX_LOCATION": "us-east5",
    }


def test_read_settings_reads_res_001_names() -> None:
    settings = vertex.read_vertex_settings(full_env())
    assert settings.project_id == "proj-123"
    assert settings.model == "claude-big"
    assert settings.small_model == "claude-small"
    assert settings.region == "us-east5"
    assert settings.base_url is None
    assert settings.access_token is None


def test_google_vertex_location_wins_over_vertex_location() -> None:
    env = full_env()
    env["VERTEX_LOCATION"] = "europe-west1"
    settings = vertex.read_vertex_settings(env)
    assert settings.region == "us-east5"


def test_vertex_location_is_fallback_region() -> None:
    env = full_env()
    env.pop("GOOGLE_VERTEX_LOCATION")
    env["VERTEX_LOCATION"] = "europe-west1"
    settings = vertex.read_vertex_settings(env)
    assert settings.region == "europe-west1"


def test_optional_passthrough_vars() -> None:
    env = full_env()
    env["ANTHROPIC_BASE_URL"] = "http://localhost:8000"
    env["VERTEX_ACCESS_TOKEN"] = "token-value"
    settings = vertex.read_vertex_settings(env)
    assert settings.base_url == "http://localhost:8000"
    assert settings.access_token == "token-value"


def test_missing_env_vars_raise_config_error() -> None:
    with pytest.raises(ConfigError) as excinfo:
        vertex.read_vertex_settings({"ANTHROPIC_MODEL": "m"})
    message = str(excinfo.value)
    assert "ANTHROPIC_VERTEX_PROJECT_ID" in message
    assert "ANTHROPIC_SMALL_FAST_MODEL" in message


def test_missing_region_raises_config_error_mentioning_both_names() -> None:
    env = full_env()
    del env["GOOGLE_VERTEX_LOCATION"]
    with pytest.raises(ConfigError) as excinfo:
        vertex.read_vertex_settings(env)
    assert "GOOGLE_VERTEX_LOCATION" in str(excinfo.value)
    assert "VERTEX_LOCATION" in str(excinfo.value)


def test_region_alias_helper() -> None:
    assert vertex.vertex_region({"GOOGLE_VERTEX_LOCATION": "a", "VERTEX_LOCATION": "b"}) == "a"
    assert vertex.vertex_region({"VERTEX_LOCATION": "b"}) == "b"
    assert vertex.vertex_region({}) is None


def test_build_ai_client_from_env_dict_constructs_offline() -> None:
    env = full_env()
    env["VERTEX_ACCESS_TOKEN"] = "dummy"
    client = vertex.build_ai_client(env)
    assert client is not None
