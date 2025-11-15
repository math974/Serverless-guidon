"""Discord command registration service.
Uses Functions Framework for Cloud Run
"""
import os
import requests
from functions_framework import create_app

app = create_app(__name__)

DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
DISCORD_APPLICATION_ID = os.environ.get('DISCORD_APPLICATION_ID')
DISCORD_API_BASE_URL = "https://discord.com/api/v10"
BASE_COMMANDS = [
    {
        "name": "hello",
        "description": "RATP service greeting",
        "type": 1
    },
    {
        "name": "ping",
        "description": "Test bot latency",
        "type": 1
    },
    {
        "name": "help",
        "description": "Show available commands",
        "type": 1
    }
]

ART_COMMANDS = [
    {
        "name": "draw",
        "description": "Draw a pixel on the canvas",
        "type": 1,
        "options": [
            {
                "name": "x",
                "description": "X coordinate",
                "type": 4,  # Integer
                "required": True
            },
            {
                "name": "y",
                "description": "Y coordinate",
                "type": 4,  # Integer
                "required": True
            },
            {
                "name": "color",
                "description": "Color in hex format (e.g., #FF0000)",
                "type": 3,  # String
                "required": True
            }
        ]
    },
    {
        "name": "snapshot",
        "description": "Take a snapshot of the current canvas",
        "type": 1
    }
]

ALL_COMMANDS = BASE_COMMANDS + ART_COMMANDS


def register_command(command: dict) -> dict:
    """Register a Discord command."""
    if not DISCORD_BOT_TOKEN or not DISCORD_APPLICATION_ID:
        return {
            'status': 'error',
            'message': 'Discord tokens not configured. Set DISCORD_BOT_TOKEN and DISCORD_APPLICATION_ID.'
        }

    url = f"{DISCORD_API_BASE_URL}/applications/{DISCORD_APPLICATION_ID}/commands"
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers, json=command, timeout=10)
        if response.status_code in [200, 201]:
            return {
                'status': 'success',
                'message': f"Command '/{command['name']}' registered successfully",
                'data': response.json()
            }
        return {
            'status': 'error',
            'message': f"HTTP {response.status_code}",
            'details': response.text
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


@app.route("/health", methods=['GET'])
def health(request):
    """Health check endpoint."""
    return {
        'status': 'healthy',
        'service': 'discord-registrar',
        'configured': bool(DISCORD_BOT_TOKEN and DISCORD_APPLICATION_ID)
    }, 200


@app.route("/register", methods=['POST'])
def register_all(request):
    """Register all Discord commands."""
    if not DISCORD_BOT_TOKEN or not DISCORD_APPLICATION_ID:
        return {
            'status': 'error',
            'message': 'Discord tokens not configured'
        }, 500

    results = []
    for command in ALL_COMMANDS:
        result = register_command(command)
        results.append({
            'command': command['name'],
            'status': result['status'],
            'message': result['message']
        })

    success_count = sum(1 for r in results if r['status'] == 'success')
    error_count = len(results) - success_count

    return {
        'status': 'completed',
        'total': len(results),
        'success': success_count,
        'errors': error_count,
        'results': results
    }, 200


@app.route("/register/<command_name>", methods=['POST'])
def register_one(request, command_name: str):
    """Register a specific command."""
    if not DISCORD_BOT_TOKEN or not DISCORD_APPLICATION_ID:
        return {
            'status': 'error',
            'message': 'Discord tokens not configured'
        }, 500

    command = next((c for c in ALL_COMMANDS if c['name'] == command_name), None)
    if not command:
        return {
            'status': 'error',
            'message': f"Command '{command_name}' not found"
        }, 404

    result = register_command(command)
    status_code = 200 if result['status'] == 'success' else 500

    return result, status_code


@app.route("/commands", methods=['GET'])
def list_commands(request):
    """List all defined commands."""
    return {
        'commands': ALL_COMMANDS,
        'base_count': len(BASE_COMMANDS),
        'art_count': len(ART_COMMANDS),
        'total': len(ALL_COMMANDS)
    }, 200
