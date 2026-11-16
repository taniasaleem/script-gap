"""One function per provider. Each takes (model_cfg, prompt) and returns a dict
with the reply text and the metadata we need to pin results to a version.

Deliberately three plain functions, not a plugin system.

Methodology choices, applied identically to every model:
  * No system prompt. The question is how models treat users as they type.
  * Single user turn, no conversation history.
  * Provider-default sampling. Claude Opus 5.5 rejects temperature and other
    sampling parameters, so forcing temperature=0 elsewhere would make the
    conditions unequal. Variance is handled with `samples` in config.toml.
"""
from __future__ import annotations

import requests


def call_anthropic(cfg: dict, prompt: str) -> dict:
    import anthropic

    client = anthropic.Anthropic()  # ANTHROPIC_API_KEY or `ant auth login`
    # Thinking cannot be disabled on Claude Opus 5.5; effort is the only
    # control, and its default is "medium". We set it explicitly so the run is
    # reproducible and recorded.
    # Server-side refusal fallbacks are deliberately NOT enabled: a fallback
    # would answer with a different model and contaminate per-model results.
    # A refusal is recorded as its own outcome instead.
    resp = client.messages.create(
        model=cfg["model"],
        max_tokens=cfg.get("max_tokens", 16000),
        output_config={"effort": cfg.get("effort", "medium")},
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    return {
        "response": text,
        "model_version": resp.model,
        "stop_reason": resp.stop_reason,
        "usage": {"input_tokens": resp.usage.input_tokens,
                  "output_tokens": resp.usage.output_tokens},
        "params": {"effort": cfg.get("effort", "medium"),
                   "max_tokens": cfg.get("max_tokens", 16000)},
    }


def call_openai(cfg: dict, prompt: str) -> dict:
    import openai

    client = openai.OpenAI()  # OPENAI_API_KEY
    resp = client.chat.completions.create(
        model=cfg["model"],
        max_completion_tokens=cfg.get("max_tokens", 16000),
        messages=[{"role": "user", "content": prompt}],
    )
    choice = resp.choices[0]
    return {
        "response": choice.message.content or "",
        # resp.model is the dated snapshot that actually served the request.
        "model_version": resp.model,
        "stop_reason": choice.finish_reason,
        "usage": {"input_tokens": resp.usage.prompt_tokens,
                  "output_tokens": resp.usage.completion_tokens},
        "params": {"max_completion_tokens": cfg.get("max_tokens", 16000)},
    }


_OLLAMA_DIGESTS: dict[str, str] = {}


def _ollama_digest(base: str, model: str) -> str:
    """Tags like `qwen3:8b` move; the digest pins the exact weights."""
    if model not in _OLLAMA_DIGESTS:
        tags = requests.get(f"{base}/api/tags", timeout=30).json().get("models", [])
        for t in tags:
            if t.get("name") == model or t.get("model") == model:
                _OLLAMA_DIGESTS[model] = t.get("digest", "")
                break
        else:
            raise RuntimeError(f"Ollama has no local model {model!r}; run `ollama pull {model}`")
    return _OLLAMA_DIGESTS[model]


def call_ollama(cfg: dict, prompt: str) -> dict:
    base = cfg.get("base_url", "http://localhost:11434").rstrip("/")
    digest = _ollama_digest(base, cfg["model"])
    r = requests.post(
        f"{base}/api/chat",
        json={
            "model": cfg["model"],
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": cfg.get("max_tokens", 4096)},
        },
        timeout=cfg.get("timeout_s", 600),
    )
    r.raise_for_status()
    data = r.json()
    return {
        "response": data.get("message", {}).get("content", ""),
        "model_version": f"{cfg['model']}@{digest[:12]}",
        "stop_reason": data.get("done_reason"),
        "usage": {"input_tokens": data.get("prompt_eval_count"),
                  "output_tokens": data.get("eval_count")},
        "params": {"num_predict": cfg.get("max_tokens", 4096)},
    }


PROVIDERS = {
    "anthropic": call_anthropic,
    "openai": call_openai,
    "ollama": call_ollama,
}
