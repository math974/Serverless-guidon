"""In-memory cache implementation with TTL."""
import time
from typing import Optional, Dict, Any

class SimpleCache:
    """In-memory cache with TTL for performance."""

    def __init__(self):
        self._cache: Dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key in self._cache:
            value, expires = self._cache[key]
            if time.time() < expires:
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int = 60):
        """Set value in cache with TTL in seconds.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 60)
        """
        expires = time.time() + ttl
        self._cache[key] = (value, expires)

    def delete(self, key: str):
        """Delete from cache.

        Args:
            key: Cache key to delete
        """
        if key in self._cache:
            del self._cache[key]

    def clear(self):
        """Clear all cache."""
        self._cache.clear()

    def size(self) -> int:
        """Get current cache size.

        Returns:
            Number of entries in cache
        """
        return len(self._cache)


# --- Global cache instance ---
cache = SimpleCache()
