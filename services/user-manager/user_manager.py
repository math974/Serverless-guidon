"""User management for Firestore."""
import os
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
        database_id = os.getenv('FIRESTORE_DATABASE', 'guidon-db')
        _db_client = firestore.Client(database=database_id)
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
            logger.debug(
                "User retrieved from Firestore",
                correlation_id=correlation_id,
                user_id=user_id,
                has_user_data=bool(user_data),
                user_keys=list(user_data.keys()) if user_data else []
            )
            # --- Cache for 60 seconds ---
            if use_cache:
                cache.set(f"user:{user_id}", user_data, ttl=60)
            return user_data
        else:
            logger.debug(
                "User document does not exist in Firestore",
                correlation_id=correlation_id,
                user_id=user_id,
                collection_id=self.users_collection.id
            )

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
            **kwargs
        }

        # --- Check if user exists ---
        existing = self.get_user(user_id, use_cache=False, correlation_id=correlation_id)
        if not existing:
            user_data.setdefault('total_draws', 0)
            user_data.setdefault('is_banned', False)
            user_data.setdefault('is_premium', False)
            user_data['created_at'] = firestore.SERVER_TIMESTAMP
            logger.info(
                "Creating new user",
                correlation_id=correlation_id,
                user_id=user_id,
                username=username
            )
        else:
            for field in ('total_draws', 'is_banned', 'is_premium'):
                if field not in user_data and existing.get(field) is not None:
                    user_data[field] = existing[field]
            logger.info(
                "Updating existing user",
                correlation_id=correlation_id,
                user_id=user_id,
                username=username
            )

        # --- Update Firestore ---
        try:
            logger.debug(
                "Saving user to Firestore",
                correlation_id=correlation_id,
                user_id=user_id,
                username=username,
                collection_id=self.users_collection.id,
                database_id=getattr(self.db, '_database', 'default')
            )

            doc_ref = self.users_collection.document(user_id)
            doc_ref.set(user_data, merge=True)

            verify_doc = doc_ref.get()
            if verify_doc.exists:
                logger.info(
                    "User saved to Firestore successfully",
                    correlation_id=correlation_id,
                    user_id=user_id,
                    username=username,
                    document_exists=True
                )
            else:
                logger.error(
                    "User document does not exist after save",
                    correlation_id=correlation_id,
                    user_id=user_id,
                    username=username
                )
                raise Exception("Failed to create user document in Firestore")
        except Exception as e:
            logger.error(
                "Failed to save user to Firestore",
                error=e,
                correlation_id=correlation_id,
                user_id=user_id,
                username=username
            )
            raise

        # --- Invalidate cache ---
        cache.delete(f"user:{user_id}")

        logger.info(
            "Cache invalidated",
            correlation_id=correlation_id,
            user_id=user_id
        )

        # --- Retrieve saved user to get actual timestamps (not Sentinel objects) ---
        import time
        time.sleep(0.1)

        saved_user = self.get_user(user_id, use_cache=False, correlation_id=correlation_id)
        if saved_user:
            logger.info(
                "User retrieved after save",
                correlation_id=correlation_id,
                user_id=user_id,
                has_created_at='created_at' in saved_user
            )
            return saved_user
        else:
            logger.warning(
                "User not found immediately after save, returning user_data",
                correlation_id=correlation_id,
                user_id=user_id
            )
            clean_data = {}
            for k, v in user_data.items():
                if v == firestore.SERVER_TIMESTAMP:
                    clean_data[k] = None
                else:
                    clean_data[k] = v
            return clean_data

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
            'updated_at': firestore.SERVER_TIMESTAMP
        }

        if command == 'draw':
            updates['total_draws'] = firestore.Increment(1)

        self.users_collection.document(user_id).set(updates, merge=True)

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
            self.users_collection.document(user_id).set({
                'is_banned': True,
                'ban_reason': reason,
                'banned_at': firestore.SERVER_TIMESTAMP
            }, merge=True)
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
            # Use set with merge=True to handle case where user doesn't exist yet
            self.users_collection.document(user_id).set({
                'is_banned': False,
                'ban_reason': None,
                'unbanned_at': firestore.SERVER_TIMESTAMP
            }, merge=True)
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
            doc_ref = self.users_collection.document(user_id)
            doc = doc_ref.get()

            if not doc.exists:
                logger.warning(
                    "User does not exist, creating user before setting premium",
                    correlation_id=correlation_id,
                    user_id=user_id
                )
                doc_ref.set({
                    'user_id': user_id,
                    'is_premium': is_premium,
                    'is_banned': False,
                    'created_at': firestore.SERVER_TIMESTAMP,
                    'premium_updated_at': firestore.SERVER_TIMESTAMP,
                    'usage': {}
                })
            else:
                doc_ref.update({
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
                error=str(e),
                correlation_id=correlation_id,
                user_id=user_id
            )
            import traceback
            traceback.print_exc()
            return False

