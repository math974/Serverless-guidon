"""Rate limiting system."""
import os
import time
from typing import Optional, Dict
from google.cloud import firestore
from shared.observability import init_observability

logger, _ = init_observability('user-management-service', app=None)

_db_client = None

def get_db():
    """Get Firestore client singleton."""
    global _db_client
    if _db_client is None:
        database_id = os.getenv('FIRESTORE_DATABASE', 'guidon-db')
        _db_client = firestore.Client(database=database_id)
    return _db_client

class RateLimiter:
    """Rate limiting system with configurable limits per command."""

    RATE_LIMITS = None

    @classmethod
    def load_rate_limits(cls):
        if cls.RATE_LIMITS is None:
            import json
            default_limits = {
                'draw': {
                    'default': {'calls': 10, 'period': 60},
                    'premium': {'calls': 30, 'period': 60}
                },
                'snapshot': {
                    'default': {'calls': 5, 'period': 300},
                    'premium': {'calls': 15, 'period': 300}
                },
                'default': {
                    'default': {'calls': 30, 'period': 60},
                    'premium': {'calls': 60, 'period': 60}
                }
            }
            env_value = os.getenv('RATE_LIMITS_JSON')
            if env_value:
                try:
                    cls.RATE_LIMITS = json.loads(env_value)
                except json.JSONDecodeError:
                    cls.RATE_LIMITS = default_limits
            else:
                cls.RATE_LIMITS = default_limits
        return cls.RATE_LIMITS

    def __init__(self):
        self.db = get_db()
        self.rate_limits_collection = self.db.collection('rate_limits')

    def check_rate_limit(
        self,
        user_id: str,
        command: str,
        is_premium: bool = False,
        correlation_id: Optional[str] = None
    ) -> Dict:
        """Check if user can execute command.

        Args:
            user_id: Discord user ID
            command: Command name
            is_premium: Whether user has premium status
            correlation_id: Correlation ID for logging

        Returns:
            Dict with keys: allowed (bool), remaining (int), reset_in (int), max (int)
        """
        rate_limits = self.load_rate_limits()

        # --- Get rate limit config ---
        command_limits = rate_limits.get(command, rate_limits['default'])
        limit_type = 'premium' if is_premium else 'default'
        config = command_limits[limit_type]

        max_calls = config['calls']
        period_seconds = config['period']

        # --- Get rate limit document ---
        limit_key = f"{user_id}_{command}"
        limit_ref = self.rate_limits_collection.document(limit_key)
        limit_doc = limit_ref.get()

        current_time = time.time()

        if not limit_doc.exists:
            # --- First call - create record ---
            limit_ref.set({
                'user_id': user_id,
                'command': command,
                'calls': [current_time],
                'created_at': firestore.SERVER_TIMESTAMP
            })

            result = {
                'allowed': True,
                'remaining': max_calls - 1,
                'reset_in': period_seconds,
                'max': max_calls
            }

            logger.debug(
                "Rate limit check: first call",
                correlation_id=correlation_id,
                user_id=user_id,
                command=command,
                remaining=result['remaining']
            )
            return result

        # --- Get existing calls ---
        data = limit_doc.to_dict()
        calls = data.get('calls', [])

        # --- Remove old calls outside the time window ---
        cutoff_time = current_time - period_seconds
        recent_calls = [call_time for call_time in calls if call_time > cutoff_time]

        if len(recent_calls) >= max_calls:
            # --- Rate limit exceeded ---
            oldest_call = min(recent_calls)
            reset_in = int(oldest_call + period_seconds - current_time)

            result = {
                'allowed': False,
                'remaining': 0,
                'reset_in': reset_in,
                'max': max_calls
            }
            logger.warning(
                "Rate limit exceeded",
                correlation_id=correlation_id,
                user_id=user_id,
                command=command,
                reset_in=reset_in
            )
            return result

        # --- Add current call ---
        recent_calls.append(current_time)
        limit_ref.update({'calls': recent_calls})

        result = {
            'allowed': True,
            'remaining': max_calls - len(recent_calls),
            'reset_in': period_seconds,
            'max': max_calls
        }

        logger.debug(
            "Rate limit check: allowed",
            correlation_id=correlation_id,
            user_id=user_id,
            command=command,
            remaining=result['remaining']
        )
        return result

    def reset_limits(
        self,
        user_id: str,
        command: Optional[str] = None,
        correlation_id: Optional[str] = None
    ):
        """Reset rate limits for a user.

        Args:
            user_id: Discord user ID
            command: Command name (optional, resets all if None)
            correlation_id: Correlation ID for logging
        """
        if command:
            # --- Reset specific command ---
            limit_key = f"{user_id}_{command}"
            self.rate_limits_collection.document(limit_key).delete()

            logger.info(
                "Rate limit reset for command",
                correlation_id=correlation_id,
                user_id=user_id,
                command=command
            )
        else:
            # --- Reset all limits for user ---
            query = self.rate_limits_collection.where('user_id', '==', user_id)
            deleted_count = 0
            for doc in query.stream():
                doc.reference.delete()
                deleted_count += 1

            logger.info(
                "Rate limits reset for user",
                correlation_id=correlation_id,
                user_id=user_id,
                deleted_count=deleted_count
            )

    def get_limits_info(
        self,
        user_id: str,
        command: str,
        is_premium: bool = False,
        correlation_id: Optional[str] = None
    ) -> Dict:
        """Get remaining calls information.

        Args:
            user_id: Discord user ID
            command: Command name
            is_premium: Whether user has premium status
            correlation_id: Correlation ID for logging

        Returns:
            Dict with rate limit information
        """
        return self.check_rate_limit(user_id, command, is_premium, correlation_id)

