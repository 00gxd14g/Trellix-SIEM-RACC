"""
Settings-Specific Caching Layer

Provides optimized caching for settings with automatic invalidation.

Author: Database Optimizer Agent
"""

import logging
from typing import Optional, Dict, Any
from functools import wraps

from utils.cache_manager import get_cache, invalidate_cache

logger = logging.getLogger(__name__)


class SettingsCache:
    """Specialized cache for settings with namespace isolation"""

    # Cache TTL values (in seconds)
    SYSTEM_SETTINGS_TTL = 600  # 10 minutes
    CUSTOMER_SETTINGS_TTL = 300  # 5 minutes
    DEFAULTS_TTL = 3600  # 1 hour

    # Cache key prefixes
    SYSTEM_PREFIX = "settings:system"
    CUSTOMER_PREFIX = "settings:customer"
    DEFAULTS_PREFIX = "settings:defaults"

    @staticmethod
    def _make_system_key(category: str) -> str:
        """Generate cache key for system settings"""
        return f"{SettingsCache.SYSTEM_PREFIX}:{category}"

    @staticmethod
    def _make_customer_key(customer_id: int) -> str:
        """Generate cache key for customer settings"""
        return f"{SettingsCache.CUSTOMER_PREFIX}:{customer_id}"

    @staticmethod
    def get_system_setting(category: str) -> Optional[Dict[str, Any]]:
        """
        Get system setting from cache

        Args:
            category: Settings category (e.g., 'general', 'api')

        Returns:
            Settings data or None if not cached
        """
        cache = get_cache()
        key = SettingsCache._make_system_key(category)
        value = cache.get(key)

        if value:
            logger.debug(f"System settings cache hit: {category}")
        else:
            logger.debug(f"System settings cache miss: {category}")

        return value

    @staticmethod
    def set_system_setting(category: str, data: Dict[str, Any]) -> None:
        """
        Set system setting in cache

        Args:
            category: Settings category
            data: Settings data to cache
        """
        cache = get_cache()
        key = SettingsCache._make_system_key(category)
        cache.set(key, data, SettingsCache.SYSTEM_SETTINGS_TTL)
        logger.debug(f"Cached system settings: {category}")

    @staticmethod
    def get_customer_setting(customer_id: int) -> Optional[Dict[str, Any]]:
        """
        Get customer setting from cache

        Args:
            customer_id: Customer ID

        Returns:
            Settings data or None if not cached
        """
        cache = get_cache()
        key = SettingsCache._make_customer_key(customer_id)
        value = cache.get(key)

        if value:
            logger.debug(f"Customer settings cache hit: {customer_id}")
        else:
            logger.debug(f"Customer settings cache miss: {customer_id}")

        return value

    @staticmethod
    def set_customer_setting(customer_id: int, data: Dict[str, Any]) -> None:
        """
        Set customer setting in cache

        Args:
            customer_id: Customer ID
            data: Settings data to cache
        """
        cache = get_cache()
        key = SettingsCache._make_customer_key(customer_id)
        cache.set(key, data, SettingsCache.CUSTOMER_SETTINGS_TTL)
        logger.debug(f"Cached customer settings: {customer_id}")

    @staticmethod
    def invalidate_system_setting(category: str) -> None:
        """
        Invalidate system setting cache

        Args:
            category: Settings category to invalidate
        """
        cache = get_cache()
        key = SettingsCache._make_system_key(category)
        cache.delete(key)
        logger.info(f"Invalidated system settings cache: {category}")

    @staticmethod
    def invalidate_customer_setting(customer_id: int) -> None:
        """
        Invalidate customer setting cache

        Args:
            customer_id: Customer ID to invalidate
        """
        cache = get_cache()
        key = SettingsCache._make_customer_key(customer_id)
        cache.delete(key)
        logger.info(f"Invalidated customer settings cache: {customer_id}")

    @staticmethod
    def invalidate_all_system_settings() -> int:
        """
        Invalidate all system settings caches

        Returns:
            Number of cache entries invalidated
        """
        count = invalidate_cache(SettingsCache.SYSTEM_PREFIX)
        logger.info(f"Invalidated all system settings ({count} entries)")
        return count

    @staticmethod
    def invalidate_all_customer_settings() -> int:
        """
        Invalidate all customer settings caches

        Returns:
            Number of cache entries invalidated
        """
        count = invalidate_cache(SettingsCache.CUSTOMER_PREFIX)
        logger.info(f"Invalidated all customer settings ({count} entries)")
        return count

    @staticmethod
    def warm_cache(settings_dict: Dict[str, Any]) -> None:
        """
        Warm cache with settings data

        Args:
            settings_dict: Dictionary with system settings by category
        """
        for category, data in settings_dict.items():
            SettingsCache.set_system_setting(category, data)
        logger.info(f"Warmed settings cache with {len(settings_dict)} categories")


def cache_system_setting(category: str):
    """
    Decorator to cache system setting retrieval

    Example:
        @cache_system_setting('general')
        def get_general_settings():
            return SystemSetting.query.filter_by(category='general').first()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Try to get from cache
            cached_value = SettingsCache.get_system_setting(category)
            if cached_value is not None:
                return cached_value

            # Execute function and cache result
            result = func(*args, **kwargs)
            if result is not None:
                # Convert to dict if it's a model object
                data = result.to_dict() if hasattr(result, 'to_dict') else result
                SettingsCache.set_system_setting(category, data)

            return result

        return wrapper
    return decorator


def cache_customer_setting(customer_id_param: str = 'customer_id'):
    """
    Decorator to cache customer setting retrieval

    Args:
        customer_id_param: Name of the parameter containing customer_id

    Example:
        @cache_customer_setting('customer_id')
        def get_customer_settings(customer_id):
            return CustomerSetting.query.filter_by(customer_id=customer_id).first()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract customer_id from kwargs or args
            customer_id = kwargs.get(customer_id_param)
            if customer_id is None and args:
                # Try to get from positional args (assumes first arg is customer_id)
                customer_id = args[0] if len(args) > 0 else None

            if customer_id is None:
                # Can't cache without customer_id
                return func(*args, **kwargs)

            # Try to get from cache
            cached_value = SettingsCache.get_customer_setting(customer_id)
            if cached_value is not None:
                return cached_value

            # Execute function and cache result
            result = func(*args, **kwargs)
            if result is not None:
                # Convert to dict if it's a model object
                data = result.to_dict() if hasattr(result, 'to_dict') else result
                SettingsCache.set_customer_setting(customer_id, data)

            return result

        return wrapper
    return decorator


def invalidate_on_update(setting_type: str, id_param: str = None):
    """
    Decorator to invalidate cache when settings are updated

    Args:
        setting_type: 'system' or 'customer'
        id_param: Parameter name containing the ID (for customer settings)

    Example:
        @invalidate_on_update('system', 'category')
        def update_system_settings(category, data):
            # Update logic
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Execute the function first
            result = func(*args, **kwargs)

            # Invalidate cache after successful update
            if setting_type == 'system':
                # Get category from kwargs or args
                category = kwargs.get('category') or (args[0] if args else None)
                if category:
                    SettingsCache.invalidate_system_setting(category)

            elif setting_type == 'customer':
                # Get customer_id from kwargs or args
                customer_id = kwargs.get(id_param or 'customer_id')
                if customer_id is None and args:
                    customer_id = args[0] if len(args) > 0 else None

                if customer_id:
                    SettingsCache.invalidate_customer_setting(customer_id)

            return result

        return wrapper
    return decorator
