"""User management for Firestore."""
from typing import Optional, Dict
from google.cloud import firestore
from cache import cache
from shared.observability import init_observability

logger, _ = init_observability('user-management-service', app=None)

_db_client = None


def get_db():
    """Get Firestore client singleton."""
    global _db_client
    if _db_client is None:
        _db_client = firestore.Client()
    return _db_client


class UserManager:
    """Manages user data in Firestore."""

    def __init__(self):
        self.db = get_db()
        self.users_collection = self.db.collection('users')

    def get_user(self, user_id: str, use_cache: bool = True, correlation_id: Optional[str] = None) -> Optional[Dict]:
        """Get user data.

        Args:
            user_id: Discord user ID
            use_cache: Whether to use cache (default: True)
            correlation_id: Correlation ID for logging

        Returns:
            User data dict or None if not found
        """
        # --- Try cache first ---
        if use_cache:
            cache_key = f"user:{user_id}"
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug(
                    "User retrieved from cache",
                    correlation_id=correlation_id,
                    user_id=user_id
                )
                return cached

        # --- Fetch from Firestore ---
        doc = self.users_collection.document(user_id).get()
        if doc.exists:
            user_data = doc.to_dict()
            # --- Cache for 60 seconds ---
            if use_cache:
                cache.set(f"user:{user_id}", user_data, ttl=60)
            logger.debug(
                "User retrieved from Firestore",
                correlation_id=correlation_id,
                user_id=user_id
            )
            return user_data

        logger.warning(
            "User not found",
            correlation_id=correlation_id,
            user_id=user_id
        )
        return None

    def create_or_update_user(
        self,
        user_id: str,
        username: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """Create or update user.

        Args:
            user_id: Discord user ID
            username: Discord username
            correlation_id: Correlation ID for logging
            **kwargs: Additional user data fields

        Returns:
            Updated user data dict
        """
        user_data = {
            'user_id': user_id,
            'username': username,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'total_commands': 0,
            'total_draws': 0,
            'is_banned': False,
            'is_premium': False,
            **kwargs
        }

        # --- Check if user exists ---
        existing = self.get_user(user_id, use_cache=False, correlation_id=correlation_id)
        if not existing:
            user_data['created_at'] = firestore.SERVER_TIMESTAMP
            logger.info(
                "Creating new user",
                correlation_id=correlation_id,
                user_id=user_id,
                username=username
            )
        else:
            logger.info(
                "Updating existing user",
                correlation_id=correlation_id,
                user_id=user_id,
                username=username
            )

        # --- Update Firestore ---
        self.users_collection.document(user_id).set(user_data, merge=True)

        # --- Invalidate cache ---
        cache.delete(f"user:{user_id}")

        logger.info(
            "User saved",
            correlation_id=correlation_id,
            user_id=user_id,
            username=username
        )

        return user_data

    def increment_usage(
        self,
        user_id: str,
        command: str,
        correlation_id: Optional[str] = None
    ):
        """Increment usage counters.

        Args:
            user_id: Discord user ID
            command: Command name
            correlation_id: Correlation ID for logging
        """
        updates = {
            'total_commands': firestore.Increment(1),
            'updated_at': firestore.SERVER_TIMESTAMP
        }

        if command == 'draw':
            updates['total_draws'] = firestore.Increment(1)

        self.users_collection.document(user_id).update(updates)

        # --- Invalidate cache ---
        cache.delete(f"user:{user_id}")

        logger.debug(
            "User usage incremented",
            correlation_id=correlation_id,
            user_id=user_id,
            command=command
        )

    def ban_user(
        self,
        user_id: str,
        reason: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Ban a user.

        Args:
            user_id: Discord user ID
            reason: Ban reason (optional)
            correlation_id: Correlation ID for logging

        Returns:
            True if successful, False otherwise
        """
        try:
            self.users_collection.document(user_id).update({
                'is_banned': True,
                'ban_reason': reason,
                'banned_at': firestore.SERVER_TIMESTAMP
            })
            cache.delete(f"user:{user_id}")

            logger.info(
                "User banned",
                correlation_id=correlation_id,
                user_id=user_id,
                reason=reason
            )
            return True
        except Exception as e:
            logger.error(
                "Error banning user",
                error=e,
                correlation_id=correlation_id,
                user_id=user_id
            )
            return False

    def unban_user(
        self,
        user_id: str,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Unban a user.

        Args:
            user_id: Discord user ID
            correlation_id: Correlation ID for logging

        Returns:
            True if successful, False otherwise
        """
        try:
            self.users_collection.document(user_id).update({
                'is_banned': False,
                'ban_reason': None,
                'unbanned_at': firestore.SERVER_TIMESTAMP
            })
            cache.delete(f"user:{user_id}")

            logger.info(
                "User unbanned",
                correlation_id=correlation_id,
                user_id=user_id
            )
            return True
        except Exception as e:
            logger.error(
                "Error unbanning user",
                error=e,
                correlation_id=correlation_id,
                user_id=user_id
            )
            return False

    def set_premium(
        self,
        user_id: str,
        is_premium: bool,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Set premium status.

        Args:
            user_id: Discord user ID
            is_premium: Premium status
            correlation_id: Correlation ID for logging

        Returns:
            True if successful, False otherwise
        """
        try:
            self.users_collection.document(user_id).update({
                'is_premium': is_premium,
                'premium_updated_at': firestore.SERVER_TIMESTAMP
            })
            cache.delete(f"user:{user_id}")

            logger.info(
                "User premium status updated",
                correlation_id=correlation_id,
                user_id=user_id,
                is_premium=is_premium
            )
            return True
        except Exception as e:
            logger.error(
                "Error setting premium status",
                error=e,
                correlation_id=correlation_id,
                user_id=user_id
            )
            return False

