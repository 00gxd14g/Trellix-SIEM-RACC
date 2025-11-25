"""
Cache Manager for Database Performance Optimization

Provides multi-tier caching strategy:
1. In-memory cache (for settings and frequently accessed data)
2. Redis cache (optional, for distributed deployments)
3. Database query result cache

Author: Database Optimizer Agent
"""

import json
import logging
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Optional, Union

logger = logging.getLogger(__name__)


class InMemoryCache:
    """Simple in-memory cache with TTL support"""

    def __init__(self):
        self._cache = {}
        self._expiry = {}

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in self._cache:
            if key in self._expiry and datetime.utcnow() > self._expiry[key]:
                # Expired, remove from cache
                del self._cache[key]
                del self._expiry[key]
                return None
            return self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in cache with TTL in seconds"""
        self._cache[key] = value
        if ttl > 0:
            self._expiry[key] = datetime.utcnow() + timedelta(seconds=ttl)

    def delete(self, key: str) -> None:
        """Delete key from cache"""
        if key in self._cache:
            del self._cache[key]
        if key in self._expiry:
            del self._expiry[key]

    def clear(self) -> None:
        """Clear all cache"""
        self._cache.clear()
        self._expiry.clear()

    def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern (simple prefix match)"""
        keys_to_delete = [k for k in self._cache.keys() if k.startswith(pattern)]
        for key in keys_to_delete:
            self.delete(key)
        return len(keys_to_delete)


class RedisCache:
    """Redis-based cache for distributed deployments"""

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.enabled = redis_client is not None
        if not self.enabled:
            logger.info("Redis cache not enabled - falling back to in-memory cache")

    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        if not self.enabled:
            return None

        try:
            value = self.redis.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
        return None

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in Redis cache with TTL in seconds"""
        if not self.enabled:
            return

        try:
            serialized = json.dumps(value)
            if ttl > 0:
                self.redis.setex(key, ttl, serialized)
            else:
                self.redis.set(key, serialized)
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")

    def delete(self, key: str) -> None:
        """Delete key from Redis cache"""
        if not self.enabled:
            return

        try:
            self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")

    def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern"""
        if not self.enabled:
            return 0

        try:
            keys = self.redis.keys(f"{pattern}*")
            if keys:
                return self.redis.delete(*keys)
        except Exception as e:
            logger.error(f"Redis clear_pattern error for pattern {pattern}: {e}")
        return 0


class CacheManager:
    """Unified cache manager with fallback strategy"""

    def __init__(self, redis_client=None, enable_memory_cache=True):
        self.redis_cache = RedisCache(redis_client) if redis_client else None
        self.memory_cache = InMemoryCache() if enable_memory_cache else None

        # Cache statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (tries Redis first, then memory)"""
        # Try Redis first
        if self.redis_cache:
            value = self.redis_cache.get(key)
            if value is not None:
                self.stats['hits'] += 1
                # Populate memory cache for faster subsequent access
                if self.memory_cache:
                    self.memory_cache.set(key, value)
                return value

        # Fallback to memory cache
        if self.memory_cache:
            value = self.memory_cache.get(key)
            if value is not None:
                self.stats['hits'] += 1
                return value

        self.stats['misses'] += 1
        return None

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in cache (both Redis and memory)"""
        self.stats['sets'] += 1

        if self.redis_cache:
            self.redis_cache.set(key, value, ttl)

        if self.memory_cache:
            self.memory_cache.set(key, value, ttl)

    def delete(self, key: str) -> None:
        """Delete key from all caches"""
        self.stats['deletes'] += 1

        if self.redis_cache:
            self.redis_cache.delete(key)

        if self.memory_cache:
            self.memory_cache.delete(key)

    def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern from all caches"""
        count = 0

        if self.redis_cache:
            count += self.redis_cache.clear_pattern(pattern)

        if self.memory_cache:
            count += self.memory_cache.clear_pattern(pattern)

        return count

    def get_stats(self) -> dict:
        """Get cache statistics"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0

        return {
            **self.stats,
            'total_requests': total_requests,
            'hit_rate': f"{hit_rate:.2f}%"
        }

    def clear_stats(self) -> None:
        """Clear cache statistics"""
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }

    def clear(self) -> None:
        """Clear all caches"""
        if self.redis_cache:
            # Redis clear not implemented for safety
            pass

        if self.memory_cache:
            self.memory_cache.clear()


# Global cache instance
_cache_instance: Optional[CacheManager] = None


def init_cache(redis_client=None, enable_memory_cache=True) -> CacheManager:
    """Initialize global cache instance"""
    global _cache_instance
    _cache_instance = CacheManager(redis_client, enable_memory_cache)
    logger.info("Cache manager initialized")
    return _cache_instance


def get_cache() -> CacheManager:
    """Get global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance


def generate_cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments"""
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(
    key_prefix: str,
    ttl: int = 300,
    key_func: Optional[Callable] = None
) -> Callable:
    """
    Decorator to cache function results

    Args:
        key_prefix: Prefix for cache key
        ttl: Time to live in seconds
        key_func: Optional function to generate cache key from arguments

    Example:
        @cached('settings:system', ttl=600)
        def get_system_settings(category):
            return SystemSetting.query.filter_by(category=category).first()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()

            # Generate cache key
            if key_func:
                cache_key = f"{key_prefix}:{key_func(*args, **kwargs)}"
            else:
                cache_key = f"{key_prefix}:{generate_cache_key(*args, **kwargs)}"

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value

            # Execute function and cache result
            logger.debug(f"Cache miss: {cache_key}")
            result = func(*args, **kwargs)

            if result is not None:
                cache.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


def invalidate_cache(pattern: str) -> int:
    """
    Invalidate cache entries matching pattern

    Args:
        pattern: Pattern to match cache keys

    Returns:
        Number of keys deleted
    """
    cache = get_cache()
    count = cache.clear_pattern(pattern)
    logger.info(f"Invalidated {count} cache entries matching pattern: {pattern}")
    return count
