import json
import pytest
from src import llm_client
from src.grounded_wording import rewrite_verified_text
from src.fuse_insights import fuse


class Response:
    status_code = 200
    def json(self):
        return {"done": True, "done_reason": "stop", "message": {"content": '{"ok":true}'},
                "prompt_eval_count": 10, "eval_count": 5}


def local_client(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3.5:4b")
    monkeypatch.setattr(llm_client, "load_environment", lambda: None)
    return llm_client.LLMClient(max_retries=1)


def test_local_provider_never_loads_cloud_credentials(monkeypatch):
    monkeypatch.setattr(llm_client, "get_azure_settings", lambda: pytest.fail("Cloud credentials must not be loaded"))
    client = local_client(monkeypatch)
    captured = {}
    def post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return Response()
    monkeypatch.setattr(client.session, "post", post)
    result = client.run_json_prompt("Return JSON")
    assert result["provider"] == "ollama"
    assert result["parsed_output"] == {"ok": True}
    assert result["usage"]["total_tokens"] == 15
    assert captured["url"] == "http://127.0.0.1:11434/api/chat"
    assert captured["json"]["think"] is False
    assert captured["json"]["stream"] is False
    assert captured["allow_redirects"] is False
    assert client.session.trust_env is False


def test_local_endpoint_cannot_send_reports_to_remote_hosts(monkeypatch):
    local_client(monkeypatch)
    for url in ("https://example.com", "http://127.0.0.1@evil.test", "http://localhost:11434/proxy", "http://localhost:11434?proxy=1"):
        monkeypatch.setenv("OLLAMA_BASE_URL", url)
        with pytest.raises(ValueError, match="loopback"):
            llm_client.LLMClient()


def test_incomplete_or_oversized_model_responses_are_not_success(monkeypatch):
    client = local_client(monkeypatch)
    response = Response()
    response.json = lambda: {"done": True, "done_reason": "length", "message": {"content": '{"ok":true}'}}
    monkeypatch.setattr(client.session, "post", lambda *a, **k: response)
    assert client.run_json_prompt("Return JSON")["error"]
    monkeypatch.setenv("OLLAMA_MAX_INPUT_CHARACTERS", "2")
    assert client.run_json_prompt("Too long")["error"]


class Rewriter:
    deployment = "local-test"
    def __init__(self, alter=None):
        self.alter = alter
    def run_json_prompt(self, prompt, **kwargs):
        data = json.loads(prompt)
        output = {key: value.replace("Revenue increased", "Revenue rose") for key, value in data.items()}
        if self.alter:
            output = self.alter(output)
        return {"parsed_output": output, "error": None, "usage": {"total_tokens": 5}}


def test_wording_uses_model_output_and_preserves_figures_names_and_risk():
    rewritten, generation = rewrite_verified_text({"summary": "Revenue increased 24% for Example PLC. Risk is HIGH."},
        ["Example PLC"], Rewriter())
    assert rewritten["summary"] == "Revenue rose 24% for Example PLC. Risk is HIGH."
    assert generation["mode"] == "local_model"


@pytest.mark.parametrize("alter", [
    lambda data: {"summary": data["summary"].replace("[[KEEP0000]]", "25%")},
    lambda data: {"summary": data["summary"].replace("HIGH", "LOW")},
    lambda data: {"summary": data["summary"] + " Buy this stock now."},
    lambda data: {"summary": data["summary"] + " It will reach 99."},
    lambda data: {},
])
def test_unsafe_wording_is_rejected_instead_of_presented_as_generated(alter):
    rewritten, generation = rewrite_verified_text({"summary": "Revenue increased 24%. Risk is HIGH."}, client=Rewriter(alter))
    assert rewritten is None
    assert generation["mode"] == "rule_based_fallback"


def test_fusion_exposes_model_success_and_fallback_without_silent_templates(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("USE_AZURE_OPENAI", "false")
    monkeypatch.setattr("src.fuse_insights.rewrite_verified_text", lambda texts, names: (
        {**texts, "plain_language_overview": "A genuine local-model explanation."}, {"mode": "local_model", "provider": "ollama"}))
    result = fuse({"selected_stock": {"symbol": "JKH.N0000", "company_name": "John Keells Holdings PLC"}})
    assert result["fallback_used"] is False
    assert result["insight"]["plain_language_overview"] == "A genuine local-model explanation."
    monkeypatch.setattr("src.fuse_insights.rewrite_verified_text", lambda *args: (None, {"mode": "rule_based_fallback"}))
    result = fuse({"selected_stock": {"symbol": "JKH.N0000"}})
    assert result["fallback_used"] is True
    assert "rule-based" in result["warnings"][0]
