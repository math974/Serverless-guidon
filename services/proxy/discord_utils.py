"""Discord-specific utilities (signature verification)."""
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.observability import init_observability  # noqa: E402

from config import DISCORD_PUBLIC_KEY  # noqa: E402

# Initialize logger for this module
logger, _ = init_observability('discord-proxy-utils', app=None)


def verify_discord_signature(signature: str, timestamp: str, body: bytes) -> bool:
    """Verify Discord request signature."""
    if not DISCORD_PUBLIC_KEY:
        logger.warning("DISCORD_PUBLIC_KEY not configured")
        return False

    try:
        verify_key = VerifyKey(bytes.fromhex(DISCORD_PUBLIC_KEY))
        message = timestamp.encode() + body
        verify_key.verify(message, bytes.fromhex(signature))
        return True
    except (BadSignatureError, ValueError) as e:
        logger.warning("Signature verification failed", error=e)
        return False
