"""One JSON POST, with the failure modes named.

Shared by every provider so that a timeout, an outage or a bad key produces the
same thing everywhere: a `ProviderError` that `ask.py` catches and falls back
from. `gigi ask` must keep working when the network does not.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

# Short on purpose. This sits in front of a question somebody typed, and a CLI
# that hangs for a minute on a dead endpoint is worse than one that falls back
# to keyword matching immediately.
TIMEOUT_SECONDS = 30


class ProviderError(Exception):
    """The model could not be reached, or did not answer usefully."""


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """POST JSON, get JSON. Every network failure becomes a ProviderError."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:200]
        raise ProviderError(f"HTTP {exc.code} from {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise ProviderError(f"could not reach {url}: {exc.reason}") from exc
    except (TimeoutError, json.JSONDecodeError, OSError) as exc:
        raise ProviderError(f"{type(exc).__name__} talking to {url}: {exc}") from exc
