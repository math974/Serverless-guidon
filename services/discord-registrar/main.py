"""Discord command registration service.
Uses Functions Framework for Cloud Functions Gen2
"""
import os
import requests
from functions_framework import http
from flask import Request, jsonify

from shared.observability import init_observability, traced_function
from shared.correlation import with_correlation

logger, tracing = init_observability('discord-registrar', app=None)

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


def register_command(command: dict, correlation_id: str = None) -> dict:
    """Register a Discord command."""
    if not DISCORD_BOT_TOKEN or not DISCORD_APPLICATION_ID:
        logger.error("Discord tokens not configured", correlation_id=correlation_id)
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
        logger.info(f"Registering command '{command['name']}'", correlation_id=correlation_id, command_name=command['name'])
        response = requests.post(url, headers=headers, json=command, timeout=10)
        if response.status_code in [200, 201]:
            logger.info(f"Command '{command['name']}' registered successfully", correlation_id=correlation_id, command_name=command['name'])
            return {
                'status': 'success',
                'message': f"Command '/{command['name']}' registered successfully",
                'data': response.json()
            }
        logger.error(
            f"Failed to register command '{command['name']}'",
            correlation_id=correlation_id,
            command_name=command['name'],
            status_code=response.status_code,
            response_text=response.text[:200]
        )
        return {
            'status': 'error',
            'message': f"HTTP {response.status_code}",
            'details': response.text
        }
    except Exception as e:
        logger.error(f"Exception registering command '{command['name']}'", error=e, correlation_id=correlation_id)
        return {
            'status': 'error',
            'message': str(e)
        }


@http
@with_correlation(logger)
@traced_function("registrar_handler")
def registrar_handler(request: Request):
    """Main HTTP handler for registrar service.

    Routes requests to appropriate handlers based on path.
    """
    path = request.path
    method = request.method

    # --- Health check ---
    if path == "/health" and method == "GET":
        return health_handler(request)

    # --- Register all commands ---
    if path == "/register" and method == "POST":
        return register_all(request)

    # --- Register single command ---
    if path.startswith("/register/") and method == "POST":
        command_name = path.split("/register/", 1)[1]
        return register_one(request, command_name)

    # --- List commands ---
    if path == "/commands" and method == "GET":
        return list_commands(request)

    # 404 for unknown paths
    logger.warning("Unknown path", path=path, method=method)
    return jsonify({'error': 'Not found'}), 404


def health_handler(request: Request):
    """Health check endpoint."""
    correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))
    logger.info("Health check called", correlation_id=correlation_id)
    return jsonify({
        'status': 'healthy',
        'service': 'discord-registrar',
        'configured': bool(DISCORD_BOT_TOKEN and DISCORD_APPLICATION_ID)
    }), 200


@traced_function("register_all_commands")
def register_all(request: Request):
    """Register all Discord commands."""
    correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))

    if not DISCORD_BOT_TOKEN or not DISCORD_APPLICATION_ID:
        logger.error("Discord tokens not configured", correlation_id=correlation_id)
        return jsonify({
            'status': 'error',
            'message': 'Discord tokens not configured'
        }), 500

    logger.info(f"Starting registration of {len(ALL_COMMANDS)} commands", correlation_id=correlation_id, total_commands=len(ALL_COMMANDS))

    results = []
    for command in ALL_COMMANDS:
        result = register_command(command, correlation_id)
        results.append({
            'command': command['name'],
            'status': result['status'],
            'message': result['message']
        })

    success_count = sum(1 for r in results if r['status'] == 'success')
    error_count = len(results) - success_count

    logger.info(
        "Command registration completed",
        correlation_id=correlation_id,
        total=len(results),
        success=success_count,
        errors=error_count
    )
    return jsonify({
        'status': 'completed',
        'total': len(results),
        'success': success_count,
        'errors': error_count,
        'results': results
    }), 200


@traced_function("register_single_command")
def register_one(request: Request, command_name: str):
    """Register a specific command."""
    correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))

    if not DISCORD_BOT_TOKEN or not DISCORD_APPLICATION_ID:
        logger.error("Discord tokens not configured", correlation_id=correlation_id)
        return jsonify({
            'status': 'error',
            'message': 'Discord tokens not configured'
        }), 500

    command = next((c for c in ALL_COMMANDS if c['name'] == command_name), None)
    if not command:
        logger.warning(f"Command '{command_name}' not found", correlation_id=correlation_id, command_name=command_name)
        return jsonify({
            'status': 'error',
            'message': f"Command '{command_name}' not found"
        }), 404

    logger.info(f"Registering single command '{command_name}'", correlation_id=correlation_id, command_name=command_name)
    result = register_command(command, correlation_id)
    status_code = 200 if result['status'] == 'success' else 500

    return jsonify(result), status_code


def list_commands(request: Request):
    """List all defined commands."""
    correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))
    logger.info("Listing all commands", correlation_id=correlation_id, total_commands=len(ALL_COMMANDS))
    return jsonify({
        'commands': ALL_COMMANDS,
        'base_count': len(BASE_COMMANDS),
        'art_count': len(ART_COMMANDS),
        'total': len(ALL_COMMANDS)
    }), 200
