"""Discord embed utilities for consistent embed creation across services."""
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any


# Color constants
COLOR_SUCCESS = 0x00FF00
COLOR_INFO = 0x0066CC
COLOR_WARNING = 0xFF6B6B
COLOR_ERROR = 0xFF4C4C
COLOR_PREMIUM = 0xFFD700
COLOR_SNAPSHOT = 0x4ECDC4
COLOR_COLORS = 0x00AAFF


def create_embed(
    title: str,
    description: str = None,
    color: int = COLOR_INFO,
    fields: List[Dict[str, Any]] = None,
    footer: Dict[str, str] = None,
    thumbnail: Dict[str, str] = None,
    image: Dict[str, str] = None,
    author: Dict[str, str] = None,
    timestamp: bool = True
) -> Dict[str, Any]:
    """Create a Discord embed with consistent formatting.

    Args:
        title: Embed title
        description: Embed description
        color: Embed color (hex integer)
        fields: List of field dicts with 'name', 'value', 'inline' keys
        footer: Footer dict with 'text' key
        thumbnail: Thumbnail dict with 'url' key
        image: Image dict with 'url' key
        author: Author dict with 'name' and optionally 'icon_url'
        timestamp: Whether to include timestamp (default: True)

    Returns:
        Discord embed dict
    """
    embed = {
        'title': title,
        'color': color
    }

    if description:
        embed['description'] = description

    if fields:
        embed['fields'] = fields

    if footer:
        embed['footer'] = footer

    if thumbnail:
        embed['thumbnail'] = thumbnail

    if image:
        embed['image'] = image

    if author:
        embed['author'] = author

    if timestamp:
        embed['timestamp'] = datetime.now(timezone.utc).isoformat()

    return embed


def create_response(
    embed: Dict[str, Any],
    ephemeral: bool = False,
    content: str = None
) -> Dict[str, Any]:
    """Create a Discord interaction response with embed.

    Args:
        embed: Embed dict (from create_embed)
        ephemeral: Whether response should be ephemeral (only visible to user)
        content: Optional text content (in addition to embed)

    Returns:
        Discord interaction response dict
    """
    response = {
        'type': 4,
        'data': {
            'embeds': [embed]
        }
    }

    if content:
        response['data']['content'] = content

    if ephemeral:
        response['data']['flags'] = 64

    return response


def create_error_embed(
    title: str,
    description: str,
    ephemeral: bool = True
) -> Dict[str, Any]:
    """Create an error embed with consistent styling.

    Args:
        title: Error title
        description: Error description
        ephemeral: Whether response should be ephemeral

    Returns:
        Discord interaction response dict
    """
    embed = create_embed(
        title=f'Error: {title}',
        description=description,
        color=COLOR_ERROR
    )
    return create_response(embed, ephemeral=ephemeral)


def create_success_embed(
    title: str,
    description: str = None,
    fields: List[Dict[str, Any]] = None,
    footer: Dict[str, str] = None,
    thumbnail: Dict[str, str] = None,
    author: Dict[str, str] = None,
    ephemeral: bool = False
) -> Dict[str, Any]:
    """Create a success embed with consistent styling.

    Args:
        title: Success title
        description: Success description
        fields: Optional fields
        footer: Optional footer
        thumbnail: Optional thumbnail
        author: Optional author
        ephemeral: Whether response should be ephemeral

    Returns:
        Discord interaction response dict
    """
    embed = create_embed(
        title=title,
        description=description,
        color=COLOR_SUCCESS,
        fields=fields,
        footer=footer,
        thumbnail=thumbnail,
        author=author
    )
    return create_response(embed, ephemeral=ephemeral)


def create_info_embed(
    title: str,
    description: str = None,
    fields: List[Dict[str, Any]] = None,
    footer: Dict[str, str] = None,
    thumbnail: Dict[str, str] = None,
    author: Dict[str, str] = None,
    ephemeral: bool = False
) -> Dict[str, Any]:
    """Create an info embed with consistent styling.

    Args:
        title: Info title
        description: Info description
        fields: Optional fields
        footer: Optional footer
        thumbnail: Optional thumbnail
        author: Optional author
        ephemeral: Whether response should be ephemeral

    Returns:
        Discord interaction response dict
    """
    embed = create_embed(
        title=title,
        description=description,
        color=COLOR_INFO,
        fields=fields,
        footer=footer,
        thumbnail=thumbnail,
        author=author
    )
    return create_response(embed, ephemeral=ephemeral)


def create_warning_embed(
    title: str,
    description: str,
    fields: List[Dict[str, Any]] = None,
    footer: Dict[str, str] = None,
    ephemeral: bool = True
) -> Dict[str, Any]:
    """Create a warning embed with consistent styling.

    Args:
        title: Warning title
        description: Warning description
        fields: Optional fields
        footer: Optional footer
        ephemeral: Whether response should be ephemeral

    Returns:
        Discord interaction response dict
    """
    embed = create_embed(
        title=title,
        description=description,
        color=COLOR_WARNING,
        fields=fields,
        footer=footer
    )
    return create_response(embed, ephemeral=ephemeral)


def get_user_avatar_url(user_id: str, avatar_hash: Optional[str] = None, discriminator: str = '0') -> str:
    """Generate Discord user avatar URL.

    Args:
        user_id: Discord user ID
        avatar_hash: User's avatar hash (if custom avatar)
        discriminator: User's discriminator (for default avatar)

    Returns:
        Avatar URL string
    """
    if avatar_hash:
        return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png"
    else:
        discriminator_num = int(discriminator) if discriminator and discriminator != '0' else 0
        return f"https://cdn.discordapp.com/embed/avatars/{discriminator_num % 5}.png"


def extract_user_info(interaction: Optional[dict]) -> tuple:
    """Extract user ID, username, and avatar URL from Discord interaction.

    Args:
        interaction: Discord interaction dict

    Returns:
        Tuple of (user_id, username, avatar_url) or (None, None, None) if not found
    """
    if not interaction:
        return None, None, None

    user_payload = interaction.get('member', {}).get('user') or interaction.get('user', {})
    if not user_payload:
        return None, None, None

    username = user_payload.get('username', 'Unknown')
    discriminator = user_payload.get('discriminator', '0')
    user_id = user_payload.get('id')
    avatar_hash = user_payload.get('avatar')

    if discriminator and discriminator != '0':
        username = f"{username}#{discriminator}"

    avatar_url = None
    if user_id:
        avatar_url = get_user_avatar_url(user_id, avatar_hash, discriminator)

    return user_id, username, avatar_url


def create_user_author(username: str, avatar_url: str) -> Dict[str, str]:
    """Create author dict for embed with user info.

    Args:
        username: User's username
        avatar_url: User's avatar URL

    Returns:
        Author dict for embed
    """
    return {
        'name': username,
        'icon_url': avatar_url
    }


def create_user_thumbnail(avatar_url: str) -> Dict[str, str]:
    """Create thumbnail dict for embed with user avatar.

    Args:
        avatar_url: User's avatar URL

    Returns:
        Thumbnail dict for embed
    """
    return {'url': avatar_url}


# Canvas constants
CANVAS_SIZE = 48  # Canvas size (48x48 pixels)

# Named color mappings
COLOR_NAMES = {
    'red': '#FF0000', 'green': '#00FF00', 'blue': '#0000FF', 'yellow': '#FFFF00',
    'orange': '#FFA500', 'purple': '#800080', 'pink': '#FFC0CB', 'brown': '#A52A2A',
    'black': '#000000', 'white': '#FFFFFF', 'gray': '#808080', 'grey': '#808080',
    'cyan': '#00FFFF', 'magenta': '#FF00FF', 'lime': '#00FF00', 'navy': '#000080',
    'teal': '#008080', 'maroon': '#800000', 'olive': '#808000', 'silver': '#C0C0C0',
    'gold': '#FFD700', 'coral': '#FF7F50', 'salmon': '#FA8072', 'khaki': '#F0E68C',
    'violet': '#EE82EE', 'indigo': '#4B0082', 'turquoise': '#40E0D0', 'crimson': '#DC143C'
}


def extract_options(interaction: Optional[dict]) -> Dict[str, Any]:
    """Extract options from Discord interaction.

    Args:
        interaction: Discord interaction dict

    Returns:
        Dict mapping option names to values
    """
    options = {}
    if not interaction:
        return options
    for option in interaction.get('data', {}).get('options', []):
        options[option['name']] = option.get('value')
    return options


def rate_limit_embed(result: Dict[str, Any], command_label: str) -> dict:
    """Create a rate limit exceeded embed.

    Args:
        result: Rate limit result dict with 'reset_in', 'remaining', 'max' keys
        command_label: Name of the command (e.g., 'draw', 'snapshot')

    Returns:
        Discord interaction response dict with warning embed
    """
    reset_time = result.get('reset_in', 0)
    minutes = reset_time // 60
    seconds = reset_time % 60
    time_str = f"{minutes}m {seconds}s" if minutes else f"{seconds}s"
    return create_warning_embed(
        title='Rate Limit Exceeded',
        description=f'You have reached the maximum limit for `{command_label}` commands.\n\n**Please wait:** {time_str}',
        fields=[{
            'name': 'Current Status',
            'value': f'**Remaining:** {result.get("remaining", 0)}/{result.get("max", 0)}\n**Reset in:** {time_str}',
            'inline': False
        }],
        footer={'text': 'Tip: Premium users enjoy larger rate limits'},
        ephemeral=True
    )

