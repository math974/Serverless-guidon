"""Interaction processing logic."""
from command_handler import handle_simple_command
from response_utils import get_proxy_url


def process_interaction(interaction_data: dict, interaction_type: str = 'discord') -> tuple:
    """Process an interaction (Discord or Web).

    Args:
        interaction_data: Parsed interaction data
        interaction_type: 'discord' or 'web'

    Returns:
        Tuple of (response_dict, status_code) or None if needs Pub/Sub
    """
    if interaction_type == 'discord' and interaction_data.get('type') == 1:
        return {'type': 1}, 200

    if interaction_type == 'discord':
        if interaction_data.get('type') != 2:
            return None
        command_name = interaction_data.get('data', {}).get('name')
    else:
        command_name = interaction_data.get('command')

    if not command_name:
        return None

    simple_response = handle_simple_command(command_name, interaction_type)
    if simple_response:
        return simple_response, 200

    return None


def prepare_pubsub_data(interaction_data: dict, interaction_type: str,
                        signature: str = None, timestamp: str = None) -> dict:
    """Prepare data for Pub/Sub publication.

    Args:
        interaction_data: Original interaction data
        interaction_type: 'discord' or 'web'
        signature: Discord signature (optional)
        timestamp: Discord timestamp (optional)

    Returns:
        Dictionary ready for Pub/Sub
    """
    proxy_url = get_proxy_url()

    if interaction_type == 'web':
        return {
            'interaction': {
                'type': 2,
                'data': {
                    'name': interaction_data.get('command'),
                    'options': interaction_data.get('options', [])
                },
                'token': interaction_data.get('token', 'web-interaction'),
                'application_id': interaction_data.get('application_id', 'web-client')
            },
            'interaction_type': 'web',
            'proxy_url': proxy_url
        }
    else:
        result = {
            'interaction': interaction_data,
            'proxy_url': proxy_url
        }
        if signature and timestamp:
            result['headers'] = {
                'signature': signature,
                'timestamp': timestamp
            }
        return result

