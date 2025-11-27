"""Registry for Discord command handlers."""
import inspect
import traceback
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shared.observability import init_observability  # noqa: E402

# Initialize logger for this module
logger, _ = init_observability('discord-processor-colors-registry', app=None)


class CommandHandler:
    """Handler for Discord slash commands."""

    HANDLERS = {}

    @classmethod
    def register(cls, command_name: str):
        """Decorator to register a command handler."""
        def decorator(func):
            cls.HANDLERS[command_name] = func
            return func
        return decorator

    @classmethod
    def handle(cls, command_name: str, interaction_data: dict = None) -> dict:
        """Handle a command by name.

        Args:
            command_name: Name of the command
            interaction_data: Full interaction data (optional, for accessing options)

        Returns:
            Discord interaction response dict
        """
        handler = cls.HANDLERS.get(command_name)
        if handler:
            try:
                sig = inspect.signature(handler)
                if len(sig.parameters) > 0:
                    return handler(interaction_data)
                else:
                    return handler()
            except Exception as e:
                correlation_id = interaction_data.get('correlation_id') if interaction_data else None
                error_traceback = traceback.format_exc()
                logger.error(
                    "Error in command handler",
                    error=e,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    traceback=error_traceback,
                    command_name=command_name,
                    correlation_id=correlation_id
                )

                return {
                    'type': 4,
                    'data': {
                        'embeds': [{
                            'title': 'Command Error',
                            'description': f'An error occurred while processing `/{command_name}`. Please try again later.',
                            'color': 0xFF0000,
                            'footer': {
                                'text': 'Error logged - service continues running'
                            }
                        }]
                    }
                }

        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': 'Command Not Found',
                    'description': f'Command `/{command_name}` is not available in this service.',
                    'color': 0xFF0000
                }]
            }
        }

