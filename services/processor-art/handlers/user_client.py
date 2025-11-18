"""
Utility client used by processor-art to talk to the user-manager service.
"""
import os
from typing import Dict, Optional, Any, List

import requests
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from shared.observability import init_observability

logger, _ = init_observability('processor-art-user-client', app=None)

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
        **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop('headers', {})
        headers.update(self._build_headers(correlation_id))
        kwargs['headers'] = headers
        kwargs.setdefault('timeout', DEFAULT_TIMEOUT)

        try:
            response = requests.request(method, url, **kwargs)
        except requests.Timeout:
            logger.warning(
                "Timeout while calling user-manager",
                method=method,
                url=url,
                correlation_id=correlation_id
            )
            return None
        except Exception as e:
            logger.error(
                "Network error while calling user-manager",
                error=e,
                method=method,
                url=url,
                correlation_id=correlation_id
            )
            return None

        content: Dict[str, Any] = {}
        if response.content:
            try:
                content = response.json()
            except ValueError:
                content = {'raw': response.text}

        status = response.status_code
        if status in (200, 201, 204):
            return content
        if status in (403, 429):
            return content or {'status': status}
        if status == 404:
            logger.info(
                "User-manager resource not found",
                url=url,
                method=method,
                correlation_id=correlation_id
            )
            return None

        logger.error(
            "user-manager call failed",
            status=status,
            url=url,
            method=method,
            body=content,
            correlation_id=correlation_id
        )
        return None

    # --- Public helpers -------------------------------------------------
    def create_or_update_user(
        self,
        user_id: str,
        username: str,
        correlation_id: Optional[str] = None,
        **extra_fields: Any
    ) -> bool:
        payload = {'user_id': user_id, 'username': username, **extra_fields}
        result = self._make_request(
            'POST',
            '/api/users',
            json=payload,
            correlation_id=correlation_id
        )
        return result is not None

    def increment_usage(
        self,
        user_id: str,
        command: str,
        correlation_id: Optional[str] = None
    ) -> bool:
        result = self._make_request(
            'POST',
            f'/api/users/{user_id}/increment',
            json={'command': command},
            correlation_id=correlation_id
        )
        return result is not None

    def get_user_stats(
        self,
        user_id: str,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        result = self._make_request(
            'GET',
            f'/api/users/{user_id}',
            correlation_id=correlation_id
        )
        return result or {}

    def get_rate_limit_info(
        self,
        user_id: str,
        command: str = 'draw',
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        result = self._make_request(
            'GET',
            f'/api/rate-limit/{user_id}',
            params={'command': command},
            correlation_id=correlation_id
        )
        return result or {}

    def get_leaderboard(
        self,
        limit: int = 10,
        correlation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        result = self._make_request(
            'GET',
            '/api/stats/leaderboard',
            params={'limit': limit},
            correlation_id=correlation_id
        )
        if not result:
            return []
        return result.get('leaderboard', [])

    def check_rate_limit(
        self,
        user_id: str,
        username: Optional[str],
        command: str,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ensure user exists, then ask user-manager whether the command is allowed."""
        self.create_or_update_user(user_id, username or 'Unknown', correlation_id=correlation_id)
        payload = {'user_id': user_id, 'command': command}
        result = self._make_request(
            'POST',
            '/api/rate-limit/check',
            json=payload,
            correlation_id=correlation_id
        )
        if result is None:
            return {
                'allowed': True,
                'remaining': 10,
                'max': 10,
                'reset_in': 60,
                'error': 'service_unavailable'
            }
        return result
