"""Handler for Discord interactions."""
from command_registry import CommandHandler


class InteractionHandler:
    """Handler for Discord interactions."""

    @staticmethod
    def handle_ping() -> dict:
        """Handle Discord ping (type 1)."""
        return {'type': 1}

    @staticmethod
    def handle_application_command(interaction: dict) -> dict:
        """Handle application command (type 2)."""
        command_name = interaction.get('data', {}).get('name')
        return CommandHandler.handle(command_name)

    @staticmethod
    def process(interaction: dict):
        """Process a Discord interaction."""
        interaction_type = interaction.get('type')

        if interaction_type == 1:
            return InteractionHandler.handle_ping(), 200

        if interaction_type == 2:
            response = InteractionHandler.handle_application_command(interaction)
            return response, 200

        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': 'Unknown Interaction Type',
                    'description': 'This interaction type is not supported.',
                    'color': 0xFF0000  # Red color for error
                }]
            }
        }, 400

