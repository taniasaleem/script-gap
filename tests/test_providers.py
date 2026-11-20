"""What each provider function actually sends, and what it records. No network:
the SDK client and HTTP calls are replaced, and the request is captured."""
import types

from scriptgap import providers
from scriptgap.common import load_config


def fake_openai(sent):
    def create(**kw):
        sent.update(kw)
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="jawab"),
                                           finish_reason="stop")],
            model="gpt-6.1-terra",
            usage=types.SimpleNamespace(prompt_tokens=5, completion_tokens=7))

    return lambda: types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)))


def test_openai_sends_the_pinned_effort_and_records_it(monkeypatch):
    sent = {}
    monkeypatch.setattr("openai.OpenAI", fake_openai(sent))
    out = providers.call_openai(
        {"model": "gpt-6.1-terra", "effort": "medium", "max_tokens": 16000}, "kya haal hai")
    assert sent == {"model": "gpt-6.1-terra", "max_completion_tokens": 16000,
                    "reasoning_effort": "medium",
                    "messages": [{"role": "user", "content": "kya haal hai"}]}
    assert out["params"]["reasoning_effort"] == "medium"
    assert out["response"] == "jawab"


def test_openai_without_effort_leaves_the_provider_default(monkeypatch):
    sent = {}
    monkeypatch.setattr("openai.OpenAI", fake_openai(sent))
    providers.call_openai({"model": "gpt-6.1-terra"}, "kya haal hai")
    assert "reasoning_effort" not in sent


class _Resp:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data

    def raise_for_status(self):
        pass


def test_ollama_sets_the_context_window_and_keeps_thinking_out_of_the_reply(monkeypatch):
    providers._OLLAMA_DIGESTS.clear()
    monkeypatch.setattr(providers.requests, "get", lambda url, timeout: _Resp(
        {"models": [{"name": "gemma4:12b", "digest": "abc123def4567890"}]}))
    posted = {}

    def post(url, json, timeout):
        posted.update(json)
        return _Resp({"message": {"content": "jawab", "thinking": "pehle sochta hoon"},
                      "done_reason": "stop", "prompt_eval_count": 5, "eval_count": 9})

    monkeypatch.setattr(providers.requests, "post", post)
    out = providers.call_ollama(
        {"model": "gemma4:12b", "max_tokens": 8192, "num_ctx": 16384}, "kya haal hai")
    assert posted["options"] == {"num_predict": 8192, "num_ctx": 16384}
    assert out["params"] == {"num_predict": 8192, "num_ctx": 16384}
    assert out["response"] == "jawab"  # the scored text never includes the thinking
    assert out["model_version"] == "gemma4:12b@abc123def456"


def test_config_pins_every_model():
    models = load_config()["models"]
    assert all("FILL_ME" not in m["model"] for m in models)
    assert {m["provider"] for m in models} == set(providers.PROVIDERS)
    for m in models:
        if m["provider"] == "ollama":
            # Prompt plus the longest allowed reply has to fit in the window.
            assert m["num_ctx"] >= m["max_tokens"] + 1024
