from __future__ import annotations

from src.config import get_azure_settings


def test_api_key_is_never_printed(monkeypatch, capsys) -> None:
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.2-chat")
    monkeypatch.setenv("AZURE_RESOURCE_NAME", "example")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "secret-key")

    settings = get_azure_settings()
    captured = capsys.readouterr()

    assert settings["AZURE_OPENAI_API_KEY"] == "secret-key"
    assert "secret-key" not in captured.out
    assert "secret-key" not in captured.err
