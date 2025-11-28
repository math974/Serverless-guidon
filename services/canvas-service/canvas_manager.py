"""
Canvas management with Google Cloud Storage for snapshots
"""
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import io
import json
import sys
from google.cloud import firestore
from google.cloud import storage
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shared.observability import init_observability

logger, _ = init_observability('canvas-service', app=None)

_db_client = None

def get_db():
    """Return Firestore client configured for the target database."""
    global _db_client
    if _db_client is None:
        database_id = os.getenv('FIRESTORE_DATABASE', 'guidon-db')
        _db_client = firestore.Client(database=database_id)
    return _db_client


def load_settings() -> Dict:
    """Load settings from setting.json file.

    Returns:
        Dict with settings or default values if file not found
    """
    default_settings = {
        'canvas_size': 48,
        'pixel_scale': 10,
        'default_color': '#FFFFFF',
        'user_manager_url': '',
        'user_manager_timeout': 5
    }

    settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'setting.json')

    try:
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                default_settings.update(settings)
                logger.info("Settings loaded from setting.json", settings=default_settings)

                if settings.get('user_manager_url') and not os.environ.get('USER_MANAGER_URL'):
                    os.environ['USER_MANAGER_URL'] = settings['user_manager_url']
                if settings.get('user_manager_timeout') and not os.environ.get('USER_MANAGER_TIMEOUT'):
                    os.environ['USER_MANAGER_TIMEOUT'] = str(settings['user_manager_timeout'])

                return default_settings
        else:
            logger.warning("setting.json not found, using defaults", defaults=default_settings)
            return default_settings
    except Exception as e:
        logger.warning(
            "Error loading setting.json, using defaults",
            error=e,
            defaults=default_settings
        )
        return default_settings


class CanvasManager:
    """Manages the shared canvas state in Firestore and snapshots in GCS."""

    # --- Load settings ---
    _settings = load_settings()
    CANVAS_SIZE = _settings.get('canvas_size', 48)
    DEFAULT_COLOR = _settings.get('default_color', '#FFFFFF')
    PIXEL_SCALE = _settings.get('pixel_scale', 10)

    BUCKET_NAME = os.environ.get('GCS_CANVAS_BUCKET', 'discord-canvas-snapshots')
    USER_MANAGER_URL = os.environ.get('USER_MANAGER_URL', _settings.get('user_manager_url', ''))
    USER_MANAGER_TIMEOUT = float(os.environ.get('USER_MANAGER_TIMEOUT', _settings.get('user_manager_timeout', 5)))

    def __init__(self):
        self.db = get_db()
        self.canvas_ref = self.db.collection('canvas').document('main')
        self.pixels_ref = self.db.collection('pixels')
        self.snapshots_ref = self.db.collection('snapshots')

        try:
            self.storage_client = storage.Client()
            self.bucket = self.storage_client.bucket(self.BUCKET_NAME)
            self.gcs_available = True
        except Exception as e:
            logger.warning(
                "GCS client not available",
                error=e,
                bucket=self.BUCKET_NAME
            )
            self.gcs_available = False

        self._initialize_canvas()

    def _initialize_canvas(self):
        """Initialize canvas with default state if it doesn't exist."""
        doc = self.canvas_ref.get()
        if not doc.exists:
            initial_data = {
                'created_at': firestore.SERVER_TIMESTAMP,
                'last_update': firestore.SERVER_TIMESTAMP,
                'total_pixels': 0,
                'unique_contributors': []
            }
            self.canvas_ref.set(initial_data)
            logger.info("Canvas initialized with default state")

    def draw_pixel(self, x: int, y: int, color: str, user_id: str, username: str = None) -> Dict:
        """
        Draw a pixel on the canvas.

        Args:
            x: X coordinate (0-47)
            y: Y coordinate (0-47)
            color: Hex color code (e.g., #FF0000)
            user_id: Discord/Web user ID
            username: Username (optional)

        Returns:
            Dict with status and details
        """
        if not (0 <= x < self.CANVAS_SIZE and 0 <= y < self.CANVAS_SIZE):
            return {
                'success': False,
                'error': f'Coordinates must be 0-{self.CANVAS_SIZE-1}'
            }

        if not color.startswith('#') or len(color) != 7:
            return {
                'success': False,
                'error': 'Color must be in format #RRGGBB'
            }

        try:
            pixel_id = f"{x}_{y}"
            pixel_key = f"pixel_{x}_{y}"

            pixel_doc = self.pixels_ref.document(pixel_id).get()
            previous_color = None
            previous_user = None

            if pixel_doc.exists:
                pixel_data = pixel_doc.to_dict()
                previous_color = pixel_data.get('color')
                previous_user = pixel_data.get('user_id')

            color_changed = previous_color != color

            pixel_data = {
                'x': x,
                'y': y,
                'color': color,
                'user_id': user_id,
                'username': username,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'previous_color': previous_color,
                'previous_user': previous_user,
                'edit_count': firestore.Increment(1)
            }

            self.pixels_ref.document(pixel_id).set(pixel_data, merge=True)

            canvas_update = {
                pixel_key: color,
                'last_update': firestore.SERVER_TIMESTAMP,
                'last_update_by': user_id,
                'last_update_username': username
            }

            if not pixel_doc.exists:
                canvas_update['total_pixels'] = firestore.Increment(1)

            try:
                canvas_doc = self.canvas_ref.get()
                if canvas_doc.exists:
                    contributors = set(canvas_doc.to_dict().get('unique_contributors', []))
                    contributors.add(user_id)
                    canvas_update['unique_contributors'] = list(contributors)
            except Exception as e:
                logger.warning(
                    "Could not update contributors",
                    error=e,
                    user_id=user_id
                )

            self.canvas_ref.set(canvas_update, merge=True)

            return {
                'success': True,
                'x': x,
                'y': y,
                'color': color,
                'previous_color': previous_color,
                'changed': color_changed
            }

        except Exception as e:
            logger.error(
                "Error drawing pixel",
                error=e,
                user_id=user_id,
                x=x,
                y=y
            )
            return {
                'success': False,
                'error': str(e)
            }

    def get_canvas_state(self) -> Dict[str, str]:
        """Get current canvas state as a dictionary of pixel colors."""
        doc = self.canvas_ref.get()
        if doc.exists:
            data = doc.to_dict()
            pixels = {k: v for k, v in data.items() if k.startswith('pixel_')}
            return pixels
        return {}

    def get_canvas_array(self) -> List[List[str]]:
        """Get canvas as 2D array for easier rendering."""
        canvas = [[self.DEFAULT_COLOR for _ in range(self.CANVAS_SIZE)]
                  for _ in range(self.CANVAS_SIZE)]

        pixels = self.get_canvas_state()

        for key, color in pixels.items():
            if key.startswith('pixel_'):
                parts = key.replace('pixel_', '').split('_')
                if len(parts) == 2:
                    x, y = int(parts[0]), int(parts[1])
                    if 0 <= x < self.CANVAS_SIZE and 0 <= y < self.CANVAS_SIZE:
                        canvas[y][x] = color

        return canvas

    def get_canvas_stats(self, user_client=None, correlation_id: str = None) -> Dict:
        """Get canvas statistics.

        Args:
            user_client: Optional UserManagementClient to fetch contributor details
            correlation_id: Optional correlation ID for logging
        """
        doc = self.canvas_ref.get()
        if doc.exists:
            data = doc.to_dict()

            unique_contributors = data.get('unique_contributors', [])
            if isinstance(unique_contributors, set):
                unique_contributors = list(unique_contributors)

            contributors_list = []
            if user_client and unique_contributors:
                for user_id in unique_contributors[:50]:
                    try:
                        user_data = user_client._make_request(
                            'GET',
                            f'/api/users/{user_id}',
                            correlation_id=correlation_id
                        )
                        if user_data:
                            contributors_list.append({
                                'id': user_id,
                                'username': user_data.get('username', f'User {user_id}'),
                                'avatar': user_data.get('avatar')
                            })
                    except Exception as e:
                        logger.warning(
                            "Failed to fetch contributor details",
                            error=e,
                            user_id=user_id,
                            correlation_id=correlation_id
                        )
                        contributors_list.append({
                            'id': user_id,
                            'username': f'User {user_id}',
                            'avatar': None
                        })

            result = {
                'total_pixels': data.get('total_pixels', 0),
                'unique_contributors': len(unique_contributors),
                'last_update': data.get('last_update'),
                'last_update_by': data.get('last_update_by'),
                'last_update_username': data.get('last_update_username')
            }

            if contributors_list:
                result['contributors'] = contributors_list

            return result
        return {
            'total_pixels': 0,
            'unique_contributors': 0
        }

    def create_snapshot(self, user_id: str = None, username: str = None) -> Dict:
        """
        Create a snapshot of the current canvas state.
        Generates an image and uploads it to Google Cloud Storage.

        Returns:
            Dict with success status, snapshot_id, and public_url
        """
        try:
            timestamp = int(datetime.now(timezone.utc).timestamp())
            snapshot_id = f"snapshot_{timestamp}_{user_id or 'system'}"

            canvas_array = self.get_canvas_array()

            img_size = self.CANVAS_SIZE * self.PIXEL_SCALE
            img = Image.new('RGB', (img_size, img_size), 'white')
            draw = ImageDraw.Draw(img)

            for y in range(self.CANVAS_SIZE):
                for x in range(self.CANVAS_SIZE):
                    color_hex = canvas_array[y][x]

                    color_hex_clean = color_hex.lstrip('#')
                    rgb = tuple(int(color_hex_clean[i:i+2], 16) for i in (0, 2, 4))

                    x1 = x * self.PIXEL_SCALE
                    y1 = y * self.PIXEL_SCALE
                    x2 = x1 + self.PIXEL_SCALE
                    y2 = y1 + self.PIXEL_SCALE

                    draw.rectangle([x1, y1, x2, y2], fill=rgb)

            for i in range(self.CANVAS_SIZE + 1):
                pos = i * self.PIXEL_SCALE
                draw.line([(pos, 0), (pos, img_size)], fill=(200, 200, 200), width=1)
                draw.line([(0, pos), (img_size, pos)], fill=(200, 200, 200), width=1)

            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            except:
                font = ImageFont.load_default()

            watermark = f"Canvas Snapshot - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
            draw.text((5, img_size - 20), watermark, fill=(100, 100, 100), font=font)

            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG', optimize=True)
            img_bytes.seek(0)

            public_url = None
            if self.gcs_available:
                try:
                    blob_name = f"snapshots/{snapshot_id}.png"
                    blob = self.bucket.blob(blob_name)

                    blob.upload_from_file(img_bytes, content_type='image/png')

                    try:
                        blob.make_public()
                        public_url = blob.public_url
                    except Exception as acl_error:
                        try:
                            expiration = datetime.now(timezone.utc) + timedelta(days=7)
                            public_url = blob.generate_signed_url(
                                expiration=expiration,
                                method='GET',
                                version='v4'
                            )
                            logger.info(
                                "Snapshot uploaded with signed URL",
                                snapshot_id=snapshot_id
                            )
                        except Exception as signed_url_error:
                            public_url = f"https://storage.googleapis.com/{self.BUCKET_NAME}/{blob_name}"
                            logger.info(
                                "Using public GCS URL format (bucket must allow public read via IAM)",
                                snapshot_id=snapshot_id,
                                url=public_url
                            )
                    logger.info(
                        "Snapshot uploaded to GCS",
                        snapshot_id=snapshot_id,
                        url=public_url
                    )
                except Exception as e:
                    error_str = str(e)
                    error_type = type(e).__name__
                    logger.warning(
                        "Error uploading snapshot to GCS",
                        error_message=error_str,
                        error_type=error_type,
                        snapshot_id=snapshot_id
                    )
                    public_url = None

            snapshot_data = {
                'snapshot_id': snapshot_id,
                'created_at': firestore.SERVER_TIMESTAMP,
                'created_by': user_id,
                'username': username,
                'image_size': img_size,
                'pixel_count': self.CANVAS_SIZE * self.CANVAS_SIZE,
                'public_url': public_url,
                'storage_backend': 'gcs' if public_url else 'none'
            }

            snapshot_data['canvas_state_json'] = json.dumps(canvas_array)

            self.snapshots_ref.document(snapshot_id).set(snapshot_data)

            return {
                'success': True,
                'snapshot_id': snapshot_id,
                'public_url': public_url,
                'image_size': img_size,
                'pixel_count': self.CANVAS_SIZE * self.CANVAS_SIZE
            }

        except Exception as e:
            logger.error(
                "Error creating snapshot",
                error=e,
                user_id=user_id
            )
            return {
                'success': False,
                'error': str(e)
            }

    def get_pixel_info(self, x: int, y: int) -> Optional[Dict]:
        """Get detailed information about a specific pixel."""
        if not (0 <= x < self.CANVAS_SIZE and 0 <= y < self.CANVAS_SIZE):
            return None

        pixel_id = f"{x}_{y}"
        doc = self.pixels_ref.document(pixel_id).get()

        if doc.exists:
            return doc.to_dict()

        return {
            'x': x,
            'y': y,
            'color': self.DEFAULT_COLOR,
            'user_id': None,
            'username': 'Empty',
            'timestamp': None
        }

