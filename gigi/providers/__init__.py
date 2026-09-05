"""Model providers, for matching a question to registry entries.

A dict, not a plugin system -- the same shape as `backends`. Adding one is
writing the module and adding the line.

Every provider does exactly one job: given a system prompt and a question,
return the model's text. They do not know what Gigi is asking, and nothing they
return is shown to a user. `ask.py` parses the reply as a list of registry ids
and throws away anything that does not resolve, so the worst a bad provider can
do is match nothing.

Talking HTTP directly rather than through three SDKs, for the same reason the
MCP server is hand-rolled: these are small, stable JSON APIs, and a dependency
that saves forty lines is still one to install, pin, and have break the image.
"""

from __future__ import annotations

from types import ModuleType

from gigi.providers import anthropic, ollama, openai

PROVIDERS: dict[str, ModuleType] = {
    "anthropic": anthropic,
    "openai": openai,
    "ollama": ollama,
}


def get_provider(name: str) -> ModuleType:
    if name not in PROVIDERS:
        raise KeyError(f"unknown provider {name!r} (known: {', '.join(PROVIDERS)})")
    return PROVIDERS[name]


def available_providers() -> list[str]:
    """Providers configured in this environment. Usually none, which is fine:
    `gigi ask` works without any of them."""
    return [name for name, module in PROVIDERS.items() if module.available()]


def first_available() -> ModuleType | None:
    """What `--model auto` picks. Order is the dict's: a configured API key
    beats a local server only because it is more likely to be deliberate."""
    for name in PROVIDERS:
        if PROVIDERS[name].available():
            return PROVIDERS[name]
    return None


__all__ = ["PROVIDERS", "available_providers", "first_available", "get_provider"]
