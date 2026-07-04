import hashlib
import json
from typing import Any


def stable_hash(payload: dict[str, Any], prefix: str, length: int = 16) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:length]}"
