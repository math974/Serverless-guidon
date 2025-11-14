"""Service for Discord API interactions."""
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import requests
from .config import Config, COMMANDS


class DiscordService:
    """Service for Discord API interactions."""

    @staticmethod
    def verify_signature(signature: str, timestamp: str, body: bytes) -> bool:
        """Verify Discord request signature."""
        if not Config.DISCORD_PUBLIC_KEY:
            return False

        try:
            verify_key = VerifyKey(bytes.fromhex(Config.DISCORD_PUBLIC_KEY))
            message = timestamp.encode() + body
            verify_key.verify(message, bytes.fromhex(signature))
            return True
        except (BadSignatureError, ValueError):
            return False

    @staticmethod
    def register_command(command: dict) -> dict:
        """Register a single Discord command."""
        if not Config.DISCORD_BOT_TOKEN or not Config.DISCORD_APPLICATION_ID:
            return {'status': 'error', 'message': 'Discord tokens not configured'}

        url = f"{Config.DISCORD_API_BASE_URL}/applications/{Config.DISCORD_APPLICATION_ID}/commands"
        headers = {
            "Authorization": f"Bot {Config.DISCORD_BOT_TOKEN}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(url, headers=headers, json=command, timeout=5)
            if response.status_code in [200, 201]:
                return {
                    'status': 'success',
                    'message': f"Command '/{command['name']}' registered successfully"
                }
            return {
                'status': 'error',
                'message': f"Error: {response.status_code}",
                'details': response.text
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    @staticmethod
    def register_all_commands() -> None:
        """Register all Discord commands."""
        for command in COMMANDS:
            result = DiscordService.register_command(command)
            if result['status'] == 'success':
                print(result['message'])
            else:
                print(f"Warning: Failed to register '/{command['name']}': {result['message']}")

