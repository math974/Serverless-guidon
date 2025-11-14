"""Discord-specific utilities (signature verification, sending responses)."""
import requests
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

from config import DISCORD_PUBLIC_KEY, DISCORD_BOT_TOKEN, DISCORD_API_BASE_URL


def verify_discord_signature(signature: str, timestamp: str, body: bytes) -> bool:
    """Verify Discord request signature."""
    if not DISCORD_PUBLIC_KEY:
        print("WARNING: DISCORD_PUBLIC_KEY not configured")
        return False

    try:
        verify_key = VerifyKey(bytes.fromhex(DISCORD_PUBLIC_KEY))
        message = timestamp.encode() + body
        verify_key.verify(message, bytes.fromhex(signature))
        return True
    except (BadSignatureError, ValueError) as e:
        print(f"Signature verification failed: {e}")
        return False


def send_discord_response(interaction_token: str, application_id: str, response: dict) -> bool:
    """Send response to Discord using webhook.

    This is the central function that handles all Discord API calls.
    """
    if not DISCORD_BOT_TOKEN:
        return False

    url = f"{DISCORD_API_BASE_URL}/webhooks/{application_id}/{interaction_token}"
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        if 'data' in response:
            followup_payload = response['data']
        elif 'type' in response and 'data' in response:
            followup_payload = response['data']
        else:
            followup_payload = response

        has_content = bool(followup_payload.get('content'))
        has_embeds = bool(followup_payload.get('embeds'))
        if not has_content and not has_embeds:
            return False

        result = requests.post(url, headers=headers, json=followup_payload, timeout=10)
        return result.status_code in [200, 204]
    except Exception as e:
        print(f"Error sending response to Discord: {e}")
        return False

