"""Claude, over the Messages API.

Configured by `ANTHROPIC_API_KEY`; the model is overridable with
`GIGI_ANTHROPIC_MODEL` so this file does not have to be edited when a better
one ships.
"""

from __future__ import annotations

import os

from gigi.providers._http import ProviderError, post_json

NAME = "anthropic"
URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"


def available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def model() -> str:
    return os.environ.get("GIGI_ANTHROPIC_MODEL", DEFAULT_MODEL)


def complete(system: str, question: str, max_tokens: int = 512) -> str:
    """Ask Claude, and return its text. Raises ProviderError on any failure --
    the caller falls back to word matching rather than surfacing an outage."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ProviderError("ANTHROPIC_API_KEY is not set")

    body = post_json(
        URL,
        {
            "model": model(),
            "max_tokens": max_tokens,
            # Matching is a lookup, not a composition: the same question
            # must select the same entries every time.
            "temperature": 0,
            "system": system,
            "messages": [{"role": "user", "content": question}],
        },
        {"x-api-key": key, "anthropic-version": API_VERSION},
    )
    try:
        return "".join(
            block["text"] for block in body["content"] if block.get("type") == "text"
        )
    except (KeyError, TypeError) as exc:
        raise ProviderError(f"unexpected response shape: {str(body)[:200]}") from exc
