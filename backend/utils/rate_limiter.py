"""
Rate limiting utilities for API endpoints.

Implements configurable rate limiting with Redis backend support
and in-memory fallback for development environments.
"""

import os
import logging
from functools import wraps
from flask import request, jsonify, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime

logger = logging.getLogger(__name__)


def get_request_identifier():
    """
    Generate a unique identifier for rate limiting.

    Combines IP address with X-Customer-ID for tenant-aware rate limiting.
    Falls back to IP-only for endpoints without tenant context.
    """
    ip_address = get_remote_address()
    customer_id = request.headers.get('X-Customer-ID', 'anonymous')

    # For authenticated tenant requests, rate limit per customer+IP
    # This prevents a single customer from exhausting the global rate limit
    if customer_id != 'anonymous':
        return f"{customer_id}:{ip_address}"

    return ip_address


def get_rate_limit_storage_uri():
    """
    Get the storage URI for rate limiting.

    Returns Redis URI if configured, otherwise uses in-memory storage.
    """
    redis_url = os.environ.get('REDIS_URL')

    if redis_url:
        logger.info(f"Using Redis for rate limiting: {redis_url}")
        return redis_url
    else:
        logger.warning("Redis not configured, using in-memory rate limiting. "
                      "This is not suitable for production with multiple instances.")
        return "memory://"


# Initialize rate limiter
# Note: The limiter will be initialized in create_app() to access app config
limiter = None


def init_rate_limiter(app):
    """
    Initialize the rate limiter with the Flask app.

    Args:
        app: Flask application instance
    """
    global limiter

    storage_uri = get_rate_limit_storage_uri()

    limiter = Limiter(
        app=app,
        key_func=get_request_identifier,
        storage_uri=storage_uri,
        default_limits=["200 per hour", "50 per minute"],
        # Provide informative error messages
        headers_enabled=True,
        swallow_errors=False,  # Raise errors in development, log in production
        strategy="fixed-window-elastic-expiry",  # More forgiving than fixed-window
    )

    # Custom error handler for rate limit exceeded
    @app.errorhandler(429)
    def rate_limit_handler(e):
        logger.warning(
            f"Rate limit exceeded for {get_request_identifier()} "
            f"on {request.endpoint} from IP {get_remote_address()}"
        )

        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded. Please try again later.',
            'retry_after': e.description
        }), 429

    logger.info("Rate limiter initialized successfully")
    return limiter


# Decorator for custom rate limits on specific endpoints
def rate_limit(limit_string):
    """
    Decorator to apply custom rate limits to specific endpoints.

    Args:
        limit_string: Rate limit specification (e.g., "5 per minute")

    Example:
        @rate_limit("5 per minute")
        def sensitive_endpoint():
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if limiter is None:
                logger.warning("Rate limiter not initialized, skipping rate limit check")
                return f(*args, **kwargs)

            # Apply the rate limit using the limiter
            limiter.limit(limit_string)(f)(*args, **kwargs)

            return f(*args, **kwargs)

        return decorated_function
    return decorator


# Pre-configured rate limit decorators for common use cases
def strict_rate_limit(f):
    """
    Strict rate limiting for sensitive operations.

    Limits: 10 requests per minute, 50 per hour
    Use for: Authentication, password resets, API testing endpoints
    """
    if limiter:
        return limiter.limit("10 per minute;50 per hour")(f)
    return f


def moderate_rate_limit(f):
    """
    Moderate rate limiting for standard API operations.

    Limits: 30 requests per minute, 500 per hour
    Use for: CRUD operations, file uploads
    """
    if limiter:
        return limiter.limit("30 per minute;500 per hour")(f)
    return f


def lenient_rate_limit(f):
    """
    Lenient rate limiting for read-only operations.

    Limits: 60 requests per minute, 1000 per hour
    Use for: GET requests, listing data
    """
    if limiter:
        return limiter.limit("60 per minute;1000 per hour")(f)
    return f


# Rate limit exemption for internal services
def is_exempt_from_rate_limiting():
    """
    Check if the current request should be exempt from rate limiting.

    Returns:
        bool: True if request should be exempt
    """
    # Exempt requests from localhost in development
    if current_app.debug and get_remote_address() in ['127.0.0.1', '::1', 'localhost']:
        return True

    # Exempt requests with valid internal service token
    internal_token = request.headers.get('X-Internal-Service-Token')
    expected_token = os.environ.get('INTERNAL_SERVICE_TOKEN')

    if internal_token and expected_token and internal_token == expected_token:
        return True

    return False


def log_rate_limit_status():
    """
    Log current rate limit status for monitoring.

    This can be called periodically to track rate limit usage.
    """
    if limiter:
        logger.info(f"Rate limiter status: {limiter.storage}")
