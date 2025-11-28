import json
import os
from datetime import datetime, timezone


def ping_http(request):
    """HTTP handler: returns a ping/pong payload with timestamp."""
    payload = {
        "ping": "pong",
        "ts": datetime.now(timezone.utc).isoformat(),
        "service": "ping-http",
        "region": os.getenv("FUNCTION_REGION", "unknown"),
    }
    return (json.dumps(payload), 200, {"Content-Type": "application/json"})


