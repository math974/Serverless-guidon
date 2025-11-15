"""Response utilities."""
import os

def get_proxy_url(request=None) -> str:
    """Get proxy URL from request, ensuring HTTPS.

    Args:
        request: Functions Framework request object (optional)

    Returns:
        Proxy URL with HTTPS
    """
    if request:
        proxy_url = request.url.rstrip('/')
        if '/' in proxy_url.split('://', 1)[1]:
            proxy_url = '/'.join(proxy_url.split('/')[:3])
    else:
        # Fallback: try to get from environment or use default
        proxy_url = os.environ.get('PROXY_URL', 'https://discord-proxy.run.app')

    if proxy_url.startswith('http://'):
        proxy_url = proxy_url.replace('http://', 'https://', 1)
    return proxy_url


def get_error_response(interaction_type: str, error_type: str = 'unavailable') -> tuple:
    """Get error response formatted for interaction type.

    Args:
        interaction_type: 'discord' or 'web'
        error_type: 'unavailable' or 'internal'

    Returns:
        Tuple of (response_dict, status_code)
    """
    if interaction_type == 'discord':
        if error_type == 'unavailable':
            return {
                'type': 4,
                'data': {
                    'embeds': [{
                        'title': 'Service Temporarily Unavailable',
                        'description': 'The message queue is temporarily unavailable. Please try again in a moment.',
                        'color': 0xFF0000,
                        'footer': {'text': 'Service continues running - error logged'}
                    }]
                }
            }, 200
        else:
            return {
                'type': 4,
                'data': {
                    'embeds': [{
                        'title': 'Internal Error',
                        'description': 'An unexpected error occurred. The service is still running.',
                        'color': 0xFF0000,
                        'footer': {'text': 'Error logged - service continues running'}
                    }]
                }
            }, 200
    else:
        if error_type == 'unavailable':
            return {
                'status': 'error',
                'message': 'Service temporarily unavailable. Please try again in a moment.'
            }, 503
        else:
            return {
                'status': 'error',
                'message': 'An unexpected error occurred.'
            }, 500
