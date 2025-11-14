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
                # Pass interaction_data if handler accepts it
                import inspect
                sig = inspect.signature(handler)
                if len(sig.parameters) > 0:
                    return handler(interaction_data)
                else:
                    return handler()
            except Exception as e:
                # Log error but don't crash - return error message to user
                import traceback
                error_msg = str(e)
                print(f"ERROR in handler '{command_name}': {error_msg}")
                print(traceback.format_exc())

                return {
                    'type': 4,
                    'data': {
                        'embeds': [{
                            'title': 'Command Error',
                            'description': f'An error occurred while processing `/{"command_name"}`. Please try again later.',
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
                    'title': 'Unknown Command',
                    'description': f'Command `/{command_name}` is not recognized. Use `/help` to see available commands.',
                    'color': 0xFF0000
                }]
            }
        }

