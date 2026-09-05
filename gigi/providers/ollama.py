"""A local model over Ollama.

The provider that matters for a private registry: no key, and nothing leaves
the machine. Availability is a live check against the endpoint rather than an
environment variable, because "is Ollama running" is the actual question.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from gigi.providers._http import ProviderError, post_json

NAME = "ollama"
DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2"
# Shorter than the request timeout: this runs on the `--model auto` path, where
# a stalled probe would delay every ask on a machine without Ollama.
PROBE_SECONDS = 1.0


def host() -> str:
    return os.environ.get("OLLAMA_HOST", DEFAULT_HOST).rstrip("/")


def model() -> str:
    return os.environ.get("GIGI_OLLAMA_MODEL", DEFAULT_MODEL)


def available() -> bool:
    """Is a server actually answering? Opt in with `GIGI_OLLAMA=1` to skip the
    probe on a machine where it is known to be running."""
    if os.environ.get("GIGI_OLLAMA") == "1":
        return True
    try:
        with urllib.request.urlopen(f"{host()}/api/tags", timeout=PROBE_SECONDS) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False


def complete(system: str, question: str, max_tokens: int = 512) -> str:
    """Ask the local model, and return its text. Raises ProviderError on any
    failure -- most often the server not running, which is not an error worth
    showing a user who never asked for a model."""
    body = post_json(
        f"{host()}/api/chat",
        {
            "model": model(),
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": 0},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": question},
            ],
        },
        {},
    )
    try:
        return body["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise ProviderError(f"unexpected response shape: {str(body)[:200]}") from exc
