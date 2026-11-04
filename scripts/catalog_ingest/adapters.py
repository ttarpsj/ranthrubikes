from __future__ import annotations

import json
import time
import urllib.robotparser
import urllib.request
from typing import Any


class AdapterError(ValueError):
    pass


def fetch_structured_json(url: str, *, user_agent: str, rate_limit_seconds: float, allow_public_metadata: bool) -> dict[str, Any]:
    """Fetch only explicitly approved public JSON after a robots check.

    This intentionally does not bypass login, robots rules, rate limits, or anti-bot controls.
    """
    if not allow_public_metadata:
        raise AdapterError("public metadata access is not enabled for this brand")
    parser = urllib.robotparser.RobotFileParser()
    parsed = urllib.request.urlparse(url)
    parser.set_url(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
    try:
        parser.read()
    except OSError as error:
        raise AdapterError(f"could not verify robots.txt: {error}") from error
    if not parser.can_fetch(user_agent, url):
        raise AdapterError("robots.txt does not permit this URL")
    time.sleep(max(0.0, rate_limit_seconds))
    request = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status != 200:
                raise AdapterError(f"metadata request failed ({response.status})")
            return json.loads(response.read().decode("utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AdapterError(f"could not read structured metadata: {error}") from error
