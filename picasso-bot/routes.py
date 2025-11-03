"""Flask routes."""
from flask import request, jsonify
from datetime import datetime
from config import Config, COMMANDS
from discord_service import DiscordService
from interaction_handler import InteractionHandler


def register_routes(app):
    """Register all Flask routes."""

    @app.route("/health")
    def health():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'discord-bot',
            'environment': {
                'public_key_set': bool(Config.DISCORD_PUBLIC_KEY),
                'bot_token_set': bool(Config.DISCORD_BOT_TOKEN),
                'app_id_set': bool(Config.DISCORD_APPLICATION_ID)
            }
        })

    @app.route("/discord/interactions", methods=['POST'])
    def discord_interactions():
        """Handle Discord interactions endpoint."""
        signature = request.headers.get('X-Signature-Ed25519')
        timestamp = request.headers.get('X-Signature-Timestamp')

        if not signature or not timestamp:
            return 'Bad Request - Missing headers', 400

        if not DiscordService.verify_signature(signature, timestamp, request.get_data()):
            return 'Unauthorized', 401

        try:
            interaction = request.get_json()
        except Exception:
            return 'Bad Request - Invalid JSON', 400

        response, status_code = InteractionHandler.process(interaction)
        return jsonify(response), status_code

    @app.route("/register-commands", methods=['POST'])
    def register_commands():
        """Endpoint to register Discord slash commands."""
        if not Config.DISCORD_BOT_TOKEN or not Config.DISCORD_APPLICATION_ID:
            return jsonify({
                'error': 'DISCORD_BOT_TOKEN and DISCORD_APPLICATION_ID must be configured'
            }), 500

        results = []
        for command in COMMANDS:
            result = DiscordService.register_command(command)
            results.append({
                'command': command['name'],
                **result
            })

        return jsonify({
            'message': 'Registration completed',
            'results': results,
            'note': 'Commands may take a few minutes to appear in Discord'
        })

