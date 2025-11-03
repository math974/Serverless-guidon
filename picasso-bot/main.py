"""Main application entry point."""
import os
import threading
from flask import Flask
from config import Config
from discord_service import DiscordService
from routes import register_routes
import command_handlers  # Import to register handlers


app = Flask(__name__)

# Register all routes
register_routes(app)


def auto_register_commands():
    """Automatically register Discord commands on startup."""
    if Config.AUTO_REGISTER_COMMANDS and Config.DISCORD_BOT_TOKEN and Config.DISCORD_APPLICATION_ID:
        print("Auto-registering Discord commands on startup...")
        DiscordService.register_all_commands()


# Auto-register commands on startup (non-blocking)
threading.Thread(target=auto_register_commands, daemon=True).start()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
