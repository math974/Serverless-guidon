"""Client for canvas-service API."""
import os
import requests
from typing import Optional, Dict, List
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from shared.observability import init_observability

logger, _ = init_observability('canvas-client', app=None)

CANVAS_SERVICE_URL = os.environ.get('CANVAS_SERVICE_URL', '')


class CanvasClient:
    """Identity-token authenticated HTTP client for the canvas-service API."""

    def __init__(self, base_url: str = None):
        service_url = base_url or CANVAS_SERVICE_URL
        if not service_url:
            raise ValueError("CANVAS_SERVICE_URL is not configured")
        service_url = service_url.rstrip('/')
        if not service_url.startswith('http://') and not service_url.startswith('https://'):
            service_url = f"https://{service_url}"
        elif service_url.startswith('http://'):
            service_url = service_url.replace('http://', 'https://', 1)
        self.base_url = service_url
        self._auth_request = google_requests.Request()

    def _build_headers(self, correlation_id: Optional[str] = None) -> Dict[str, str]:
        """Build headers with authentication token."""
        headers = {}
        if correlation_id:
            headers['X-Correlation-ID'] = correlation_id

        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.base_url)
            normalized_audience = f"{parsed.scheme}://{parsed.netloc}"

            token = id_token.fetch_id_token(self._auth_request, normalized_audience)
            headers['Authorization'] = f'Bearer {token}'
        except Exception as e:
            logger.warning(
                "Failed to fetch identity token for canvas-service",
                error=e,
                base_url=self.base_url
            )
        return headers

    def draw_pixel(self, x: int, y: int, color: str, user_id: str, username: str = None, correlation_id: str = None) -> Dict:
        """Draw a pixel on the canvas.

        Args:
            x: X coordinate (0 to canvas_size-1, where canvas_size is dynamic)
            y: Y coordinate (0 to canvas_size-1, where canvas_size is dynamic)
            color: Hex color code (e.g., #FF0000)
            user_id: User ID
            username: Username (optional)
            correlation_id: Correlation ID for logging (optional)

        Returns:
            Dict with success status and details
        """
        if not self.base_url:
            return {'success': False, 'error': 'Canvas service URL not configured'}

        url = f"{self.base_url}/canvas/draw"
        headers = self._build_headers(correlation_id)
        headers['Content-Type'] = 'application/json'

        payload = {
            'x': x,
            'y': y,
            'color': color,
            'user_id': user_id
        }
        if username:
            payload['username'] = username

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    "Error calling canvas-service draw",
                    status_code=response.status_code,
                    response_text=response.text[:200],
                    correlation_id=correlation_id
                )
                return {'success': False, 'error': f'Canvas service error: {response.status_code}'}
        except Exception as e:
            logger.error("Exception calling canvas-service draw", error=e, correlation_id=correlation_id)
            return {'success': False, 'error': str(e)}

    def get_canvas_size(self, correlation_id: str = None) -> Optional[int]:
        """Get canvas size only (lightweight call).

        Args:
            correlation_id: Correlation ID for logging (optional)

        Returns:
            Canvas size (int) or None if error
        """
        if not self.base_url:
            return None

        url = f"{self.base_url}/canvas/size"
        headers = self._build_headers(correlation_id)
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('size')
            else:
                logger.error(
                    "Error calling canvas-service size",
                    status_code=response.status_code,
                    correlation_id=correlation_id
                )
                return None
        except Exception as e:
            logger.error("Exception calling canvas-service size", error=e, correlation_id=correlation_id)
            return None

    def get_canvas_state(self, correlation_id: str = None) -> Dict:
        """Get canvas state as 2D array.

        Args:
            correlation_id: Correlation ID for logging (optional)

        Returns:
            Dict with size, pixels array, and stats
        """
        if not self.base_url:
            return {'error': 'Canvas service URL not configured'}

        url = f"{self.base_url}/canvas/state"
        headers = self._build_headers(correlation_id)

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    "Error calling canvas-service state",
                    status_code=response.status_code,
                    correlation_id=correlation_id
                )
                return {'error': f'Canvas service error: {response.status_code}'}
        except Exception as e:
            logger.error("Exception calling canvas-service state", error=e, correlation_id=correlation_id)
            return {'error': str(e)}

    def create_snapshot(self, user_id: str = None, username: str = None, correlation_id: str = None) -> Dict:
        """Create a snapshot of the canvas.

        Args:
            user_id: User ID (optional)
            username: Username (optional)
            correlation_id: Correlation ID for logging (optional)

        Returns:
            Dict with success status, snapshot_id, and public_url
        """
        if not self.base_url:
            return {'success': False, 'error': 'Canvas service URL not configured'}

        url = f"{self.base_url}/canvas/snapshot"
        headers = self._build_headers(correlation_id)
        headers['Content-Type'] = 'application/json'

        payload = {}
        if user_id:
            payload['user_id'] = user_id
        if username:
            payload['username'] = username

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    "Error calling canvas-service snapshot",
                    status_code=response.status_code,
                    correlation_id=correlation_id
                )
                return {'success': False, 'error': f'Canvas service error: {response.status_code}'}
        except Exception as e:
            logger.error("Exception calling canvas-service snapshot", error=e, correlation_id=correlation_id)
            return {'success': False, 'error': str(e)}

    def get_canvas_stats(self, correlation_id: str = None) -> Dict:
        """Get canvas statistics.

        Args:
            correlation_id: Correlation ID for logging (optional)

        Returns:
            Dict with canvas statistics
        """
        if not self.base_url:
            return {'error': 'Canvas service URL not configured'}

        url = f"{self.base_url}/canvas/stats"
        headers = self._build_headers(correlation_id)

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    "Error calling canvas-service stats",
                    status_code=response.status_code,
                    correlation_id=correlation_id
                )
                return {'error': f'Canvas service error: {response.status_code}'}
        except Exception as e:
            logger.error("Exception calling canvas-service stats", error=e, correlation_id=correlation_id)
            return {'error': str(e)}

    def get_pixel_info(self, x: int, y: int, correlation_id: str = None) -> Optional[Dict]:
        """Get detailed information about a specific pixel.

        Args:
            x: X coordinate
            y: Y coordinate
            correlation_id: Correlation ID for logging (optional)

        Returns:
            Dict with pixel information or None if error
        """
        if not self.base_url:
            return None

        url = f"{self.base_url}/canvas/pixel/{x}/{y}"
        headers = self._build_headers(correlation_id)

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    "Error calling canvas-service pixel info",
                    status_code=response.status_code,
                    correlation_id=correlation_id
                )
                return None
        except Exception as e:
            logger.error("Exception calling canvas-service pixel info", error=e, correlation_id=correlation_id)
            return None

