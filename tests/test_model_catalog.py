from src.model_catalog import (
    fetch_model_options,
    fallback_model_options,
    list_api_key_env_names,
    parse_gemini_models,
    parse_openrouter_models,
)


def test_list_api_key_env_names_prefers_numbered_openrouter_keys():
    environ = {
        "OPENROUTER_API_KEY": "legacy-key",
        "OPENROUTER_API_KEY_2": "key-2",
        "OPENROUTER_API_KEY_1": "key-1",
    }

    assert list_api_key_env_names("openrouter", environ=environ) == [
        "OPENROUTER_API_KEY_1",
        "OPENROUTER_API_KEY_2",
        "OPENROUTER_API_KEY",
    ]


def test_fallback_model_options_combines_current_and_env_models():
    environ = {
        "OPENROUTER_MODEL": "model-b, model-c",
    }

    assert fallback_model_options(
        "openrouter",
        current_model="model-a",
        environ=environ,
    ) == ["model-a", "model-b", "model-c"]


def test_deepseek_model_options_use_official_models_and_ignore_openrouter_current_model():
    environ = {
        "DEEPSEEK_MODEL": "deepseek-v4-pro",
    }

    assert fallback_model_options(
        "deepseek",
        current_model="nvidia/nemotron-3-ultra-550b-a55b:free",
        environ=environ,
    ) == [
        "deepseek-v4-flash",
        "deepseek-v4-pro",
        "deepseek-chat",
        "deepseek-reasoner",
    ]


def test_fetch_deepseek_model_options_uses_official_static_list_without_api_key():
    result = fetch_model_options(
        "deepseek",
        current_model="nvidia/nemotron-3-ultra-550b-a55b:free",
    )

    assert result.source == "official"
    assert result.error is None
    assert result.models[:2] == ["deepseek-v4-flash", "deepseek-v4-pro"]


def test_parse_openrouter_models_returns_sorted_ids():
    payload = {
        "data": [
            {"id": "z-model"},
            {"id": "a-model"},
            {"id": ""},
            {"name": "not-an-id"},
        ]
    }

    assert parse_openrouter_models(payload) == ["a-model", "z-model"]


def test_parse_gemini_models_strips_models_prefix_and_filters_generation_methods():
    payload = {
        "models": [
            {
                "name": "models/gemini-2.5-flash",
                "supportedGenerationMethods": ["generateContent"],
            },
            {
                "name": "models/embedding-001",
                "supportedGenerationMethods": ["embedContent"],
            },
            {
                "name": "gemini-2.0-flash",
                "supportedGenerationMethods": ["generateContent"],
            },
        ]
    }

    assert parse_gemini_models(payload) == ["gemini-2.0-flash", "gemini-2.5-flash"]
