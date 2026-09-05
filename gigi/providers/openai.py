"""OpenAI, and anything speaking its chat-completions API.

`OPENAI_BASE_URL` points this at vLLM, llama.cpp, LM Studio, OpenRouter or a
corporate gateway, which is most of the reason to support this shape at all.
"""

from __future__ import annotations

import os

from gigi.providers._http import ProviderError, post_json

NAME = "openai"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"


def available() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def model() -> str:
    return os.environ.get("GIGI_OPENAI_MODEL", DEFAULT_MODEL)


def base_url() -> str:
    return os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def complete(system: str, question: str, max_tokens: int = 512) -> str:
    """Ask the model, and return its text. Raises ProviderError on any failure,
    including from an OpenAI-compatible server that is not OpenAI."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ProviderError("OPENAI_API_KEY is not set")

    body = post_json(
        f"{base_url()}/chat/completions",
        {
            "model": model(),
            "max_tokens": max_tokens,
            # Matching is a lookup, not a composition: the same question
            # must select the same entries every time.
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": question},
            ],
        },
        {"Authorization": f"Bearer {key}"},
    )
    try:
        return body["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError(f"unexpected response shape: {str(body)[:200]}") from exc
