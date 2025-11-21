"""
Utility client used by processors to talk to the user-manager service.
Shared across all processor services.
"""
import os
from typing import Dict, Optional, Any, List
import requests
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from shared.observability import init_observability

logger, _ = init_observability('shared-user-client', app=None)
DEFAULT_TIMEOUT = float(os.getenv('USER_MANAGER_TIMEOUT', '5'))


class UserManagementClient:
    """Identity-token authenticated HTTP client for the user-manager service."""

    def __init__(self, base_url: Optional[str] = None):
        env_url = (
            base_url
            or os.environ.get('USER_MANAGER_URL')
        )
        if not env_url:
            raise ValueError("USER_MANAGER_URL is not configured")
        self.base_url = env_url.rstrip('/')
        self._auth_request = google_requests.Request()

    def _build_headers(self, correlation_id: Optional[str] = None) -> Dict[str, str]:
        headers = {}
        if correlation_id:
            headers['X-Correlation-ID'] = correlation_id

        try:
            token = id_token.fetch_id_token(self._auth_request, self.base_url)
            headers['Authorization'] = f'Bearer {token}'
        except Exception as e:
            logger.warning(
                "Failed to fetch identity token for user-manager",
                error=e,
                base_url=self.base_url
            )
        return headers

    def _make_request(
        self,
        method: str,
        endpoint: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> Optional[Dict]:
        url = f"{self.base_url}{endpoint}"
        headers = self._build_headers(correlation_id)
        headers.update(kwargs.pop('headers', {}))

        try:
            response = requests.request(
                method, url, headers=headers, timeout=DEFAULT_TIMEOUT, **kwargs
            )
            # Accept 200-299 (success) and 429 (rate limited) status codes
            if 200 <= response.status_code < 300 or response.status_code == 429:
                return response.json()
            else:
                logger.warning(
                    f"User-manager {method} {endpoint} returned {response.status_code}",
                    correlation_id=correlation_id,
                    status_code=response.status_code,
                    response_text=response.text[:200]
                )
                return None
        except Exception as e:
            logger.error(
                f"Error calling user-manager {method} {endpoint}",
                error=e,
                correlation_id=correlation_id
            )
            return None

    def check_rate_limit(
        self,
        user_id: str,
        username: str,
        command: str,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check if user can execute command (rate limit check)."""
        user = self._make_request('GET', f'/api/users/{user_id}', correlation_id=correlation_id)
        is_premium = user.get('is_premium', False) if user else False

        result = self._make_request(
            'POST',
            '/api/rate-limit/check',
            correlation_id=correlation_id,
            json={
                'user_id': user_id,
                'command': command,
                'is_premium': is_premium
            }
        )
        return result or {'allowed': True}

    def increment_usage(
        self,
        user_id: str,
        command: str,
        correlation_id: Optional[str] = None
    ) -> Optional[int]:
        """Increment usage counter for a user command.

        Returns:
            New total_draws value if command is 'draw', None otherwise
        """
        result = self._make_request(
            'POST',
            f'/api/users/{user_id}/increment',
            correlation_id=correlation_id,
            json={'command': command}
        )
        if result and 'total_draws' in result:
            return result['total_draws']
        return None if result is None else 0

    def get_user_stats(
        self,
        user_id: str,
        correlation_id: Optional[str] = None
    ) -> Optional[Dict]:
        """Get user statistics (extracted from user data)."""
        user = self._make_request(
            'GET',
            f'/api/users/{user_id}',
            correlation_id=correlation_id
        )
        if user:
            return {
                'total_draws': user.get('total_draws', 0),
                'is_premium': user.get('is_premium', False),
                'is_banned': user.get('is_banned', False)
            }
        return None

    def get_rate_limit_info(
        self,
        user_id: str,
        command: str,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get rate limit information for a user and command."""
        user = self._make_request('GET', f'/api/users/{user_id}', correlation_id=correlation_id)
        is_premium = user.get('is_premium', False) if user else False

        result = self._make_request(
            'GET',
            f'/api/rate-limit/{user_id}?command={command}',
            correlation_id=correlation_id
        )
        return result or {'remaining': 0, 'max': 0}

    def is_user_registered(
        self,
        user_id: str,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Check if user is registered."""
        result = self._make_request(
            'GET',
            f'/api/users/{user_id}',
            correlation_id=correlation_id
        )
        return result is not None and result.get('registered', False)

    def get_leaderboard(
        self,
        limit: int = 10,
        correlation_id: Optional[str] = None
    ) -> List[Dict]:
        """Get leaderboard of top contributors."""
        result = self._make_request(
            'GET',
            f'/api/stats/leaderboard?limit={limit}',
            correlation_id=correlation_id
        )
        return result.get('leaderboard', []) if result else []

