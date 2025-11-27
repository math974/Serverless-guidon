"""Statistics and analytics manager."""
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict
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


class StatsManager:
    """Statistics and analytics."""

    def __init__(self):
        self.db = get_db()

    def get_user_count(self, correlation_id: str = None) -> int:
        """Get total user count.

        Args:
            correlation_id: Correlation ID for logging

        Returns:
            Total number of users
        """
        # --- Try cache ---
        cached = cache.get("stats:user_count")
        if cached is not None:
            logger.debug(
                "User count from cache",
                correlation_id=correlation_id
            )
            return cached

        # --- Count users (expensive operation) ---
        count = len(list(self.db.collection('users').stream()))

        # --- Cache for 5 minutes ---
        cache.set("stats:user_count", count, ttl=300)

        logger.info(
            "User count retrieved",
            correlation_id=correlation_id,
            count=count
        )
        return count

    def get_active_users(
        self,
        hours: int = 24,
        correlation_id: str = None
    ) -> int:
        """Get count of active users in last N hours.

        Args:
            hours: Number of hours to look back (default: 24)
            correlation_id: Correlation ID for logging

        Returns:
            Number of active users
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = self.db.collection('users').where('updated_at', '>', cutoff)
        count = len(list(query.stream()))

        logger.info(
            "Active users retrieved",
            correlation_id=correlation_id,
            hours=hours,
            count=count
        )
        return count

    def get_leaderboard(
        self,
        limit: int = 10,
        correlation_id: str = None
    ) -> List[Dict]:
        """Get top users by draw count.

        Args:
            limit: Number of users to return (default: 10)
            correlation_id: Correlation ID for logging

        Returns:
            List of user dicts with leaderboard data
        """
        users = self.db.collection('users').order_by(
            'total_draws', direction=firestore.Query.DESCENDING
        ).limit(limit).stream()

        leaderboard = []
        for doc in users:
            data = doc.to_dict()
            leaderboard.append({
                'user_id': data.get('user_id'),
                'username': data.get('username'),
                'total_draws': data.get('total_draws', 0),
                'is_premium': data.get('is_premium', False),
                'avatar': data.get('avatar'),
                'discriminator': data.get('discriminator', '0')
            })

        logger.info(
            "Leaderboard retrieved",
            correlation_id=correlation_id,
            limit=limit,
            count=len(leaderboard)
        )
        return leaderboard

