"""HTTP request handlers for user management service."""
from typing import Optional, Dict, Any
from datetime import datetime
from flask import Request, jsonify
from user_manager import UserManager
from rate_limiter import RateLimiter
from stats_manager import StatsManager
from shared.observability import init_observability

logger, _ = init_observability('user-management-service', app=None)


def serialize_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Firestore timestamps to ISO format strings for JSON serialization.

    Args:
        user_data: User data dict from Firestore

    Returns:
        User data dict with serializable timestamps
    """
    if not user_data:
        return user_data

    serialized = {}
    for key, value in user_data.items():
        if isinstance(value, datetime):
            serialized[key] = value.isoformat()
        else:
            serialized[key] = value
    return serialized

# --- Initialize managers ---
user_manager = UserManager()
rate_limiter = RateLimiter()
stats_manager = StatsManager()


def get_correlation_id(request: Request) -> Optional[str]:
    """Extract correlation ID from request."""
    return getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))

def handle_users(request: Request, path: str, method: str):
    """Handle user management routes."""
    correlation_id = get_correlation_id(request)

    logger.debug(
        "Handling user request",
        correlation_id=correlation_id,
        path=path,
        method=method
    )

    # --- GET /api/users/{user_id} ---
    if method == 'GET' and path.startswith('/api/users/'):
        user_id = path.split('/')[-1]
        user = user_manager.get_user(user_id, correlation_id=correlation_id)

        if user:
            logger.info(
                "User retrieved",
                correlation_id=correlation_id,
                user_id=user_id
            )
            # Serialize timestamps for JSON response
            serialized_user = serialize_user_data(user)
            return jsonify(serialized_user), 200
        else:
            logger.warning(
                "User not found",
                correlation_id=correlation_id,
                user_id=user_id
            )
            return jsonify({'error': 'User not found'}), 404

    # --- POST /api/users - Create/Update user ---
    elif method == 'POST' and path == '/api/users':
        data = request.get_json()
        if not data:
            logger.warning(
                "Invalid JSON in create user request",
                correlation_id=correlation_id
            )
            return jsonify({'error': 'Invalid JSON'}), 400

        user_id = data.get('user_id')
        username = data.get('username')

        if not user_id or not username:
            logger.warning(
                "Missing required fields in create user request",
                correlation_id=correlation_id,
                has_user_id=bool(user_id),
                has_username=bool(username)
            )
            return jsonify({'error': 'user_id and username required'}), 400

        try:
            logger.info(
                "Starting user creation/update",
                correlation_id=correlation_id,
                user_id=user_id,
                username=username,
                additional_fields=list({k: v for k, v in data.items() if k not in ['user_id', 'username']}.keys())
            )

            user = user_manager.create_or_update_user(
                user_id,
                username,
                correlation_id=correlation_id,
                **{k: v for k, v in data.items() if k not in ['user_id', 'username']}
            )

            logger.info(
                "User created/updated in UserManager",
                correlation_id=correlation_id,
                user_id=user_id,
                has_user=bool(user),
                user_keys=list(user.keys()) if user else []
            )

            serialized_user = serialize_user_data(user)

            logger.info(
                "User serialized",
                correlation_id=correlation_id,
                user_id=user_id,
                serialized_keys=list(serialized_user.keys()) if serialized_user else []
            )

            is_new = 'created_at' in serialized_user and serialized_user.get('created_at')

            logger.info(
                "User created/updated successfully",
                correlation_id=correlation_id,
                user_id=user_id,
                username=username,
                is_new_user=bool(is_new),
                has_created_at='created_at' in serialized_user
            )

            return jsonify(serialized_user), 200
        except Exception as e:
            logger.error(
                "Error creating/updating user",
                error=e,
                correlation_id=correlation_id,
                user_id=user_id,
                username=username
            )
            return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

    # --- POST /api/users/{user_id}/increment ---
    elif method == 'POST' and '/increment' in path:
        user_id = path.split('/')[-2]
        data = request.get_json() or {}
        command = data.get('command', 'unknown')
        include_stats = data.get('include_stats', False)

        new_total = user_manager.increment_usage(user_id, command, correlation_id=correlation_id)
        response = {'status': 'incremented'}
        if new_total is not None:
            response['total_draws'] = new_total

        if include_stats:
            user_data = user_manager.get_user(user_id, correlation_id=correlation_id)
            if user_data:
                response['is_premium'] = user_data.get('is_premium', False)
                response['is_banned'] = user_data.get('is_banned', False)

        return jsonify(response), 200

    # --- POST /api/users/{user_id}/ban ---
    elif method == 'POST' and '/ban' in path:
        try:
            # Extract user_id from path: /api/users/{user_id}/ban
            path_parts = path.split('/')
            if len(path_parts) < 4 or path_parts[-1] != 'ban':
                logger.warning(
                    "Invalid ban path format",
                    correlation_id=correlation_id,
                    path=path
                )
                return jsonify({'error': 'Invalid path format'}), 400

            user_id = path_parts[-2]
            if not user_id:
                logger.warning(
                    "Missing user_id in ban path",
                    correlation_id=correlation_id,
                    path=path
                )
                return jsonify({'error': 'Missing user_id'}), 400

            data = request.get_json() or {}
            reason = data.get('reason')

            success = user_manager.ban_user(user_id, reason, correlation_id=correlation_id)
            if success:
                logger.info(
                    "User banned successfully",
                    correlation_id=correlation_id,
                    user_id=user_id,
                    reason=reason
                )
                return jsonify({'status': 'banned'}), 200
            else:
                logger.error(
                    "Failed to ban user",
                    correlation_id=correlation_id,
                    user_id=user_id
                )
                return jsonify({'error': 'Failed to ban user'}), 500
        except Exception as e:
            logger.error(
                "Error in ban handler",
                error=e,
                correlation_id=correlation_id,
                path=path
            )
            return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

    # --- POST /api/users/{user_id}/unban ---
    elif method == 'POST' and '/unban' in path:
        user_id = path.split('/')[-2]

        success = user_manager.unban_user(user_id, correlation_id=correlation_id)
        if success:
            return jsonify({'status': 'unbanned'}), 200
        else:
            return jsonify({'error': 'Failed to unban'}), 500

    # --- PUT /api/users/{user_id}/premium ---
    elif method == 'PUT' and '/premium' in path:
        user_id = path.split('/')[-2]
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400

        is_premium = data.get('is_premium', False)

        success = user_manager.set_premium(user_id, is_premium, correlation_id=correlation_id)
        if success:
            return jsonify({'status': 'updated'}), 200
        else:
            return jsonify({'error': 'Failed to update'}), 500

    logger.warning(
        "Unknown user route",
        correlation_id=correlation_id,
        path=path,
        method=method
    )
    return jsonify({'error': 'Not Found'}), 404


def handle_rate_limit(request: Request, path: str, method: str):
    """Handle rate limiting routes."""
    correlation_id = get_correlation_id(request)

    # --- POST /api/rate-limit/check ---
    if method == 'POST' and path == '/api/rate-limit/check':
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400

        user_id = data.get('user_id')
        command = data.get('command')
        is_premium = data.get('is_premium', False)

        if not user_id or not command:
            logger.warning(
                "Missing required fields in rate limit check",
                correlation_id=correlation_id,
                has_user_id=bool(user_id),
                has_command=bool(command)
            )
            return jsonify({'error': 'user_id and command required'}), 400

        # Check if user is banned
        user = user_manager.get_user(user_id, correlation_id=correlation_id)
        if user and user.get('is_banned'):
            logger.warning(
                "Banned user attempted command",
                correlation_id=correlation_id,
                user_id=user_id,
                command=command
            )
            return jsonify({
                'allowed': False,
                'error': 'User is banned',
                'remaining': 0
            }), 403

        # If user data has premium, use it
        if user and user.get('is_premium'):
            is_premium = True

        # Check rate limit
        result = rate_limiter.check_rate_limit(user_id, command, is_premium, correlation_id=correlation_id)

        if not result['allowed']:
            return jsonify(result), 429

        return jsonify(result), 200

    # GET /api/rate-limit/{user_id}
    elif method == 'GET' and path.startswith('/api/rate-limit/'):
        user_id = path.split('/')[-1]
        command = request.args.get('command', 'draw')

        user = user_manager.get_user(user_id, correlation_id=correlation_id)
        is_premium = user.get('is_premium', False) if user else False

        info = rate_limiter.get_limits_info(user_id, command, is_premium, correlation_id=correlation_id)
        return jsonify(info), 200

    # DELETE /api/rate-limit/{user_id}
    elif method == 'DELETE' and path.startswith('/api/rate-limit/'):
        user_id = path.split('/')[-1]
        command = request.args.get('command')

        rate_limiter.reset_limits(user_id, command, correlation_id=correlation_id)
        return jsonify({'status': 'reset'}), 200

    logger.warning(
        "Unknown rate limit route",
        correlation_id=correlation_id,
        path=path,
        method=method
    )
    return jsonify({'error': 'Not Found'}), 404


def handle_stats(request: Request, path: str, method: str):
    """Handle statistics routes."""
    correlation_id = get_correlation_id(request)

    # GET /api/stats/users
    if path == '/api/stats/users':
        count = stats_manager.get_user_count(correlation_id=correlation_id)
        return jsonify({'total_users': count}), 200

    # GET /api/stats/active
    elif path == '/api/stats/active':
        hours = int(request.args.get('hours', 24))
        count = stats_manager.get_active_users(hours, correlation_id=correlation_id)
        return jsonify({
            'active_users': count,
            'period_hours': hours
        }), 200

    # GET /api/stats/leaderboard
    elif path == '/api/stats/leaderboard':
        limit = int(request.args.get('limit', 10))
        leaderboard = stats_manager.get_leaderboard(limit, correlation_id=correlation_id)
        return jsonify({'leaderboard': leaderboard}), 200

    logger.warning(
        "Unknown stats route",
        correlation_id=correlation_id,
        path=path,
        method=method
    )
    return jsonify({'error': 'Not Found'}), 404

