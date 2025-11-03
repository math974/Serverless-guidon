"""Registry for Discord command handlers."""


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
    def handle(cls, command_name: str) -> dict:
        """Handle a command by name."""
        handler = cls.HANDLERS.get(command_name)
        if handler:
            return handler()
        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': 'Unknown Command',
                    'description': f'Command `/{command_name}` is not recognized. Use `/help` to see available commands.',
                    'color': 0xFF0000
                }]
            }
        }

