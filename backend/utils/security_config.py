"""
Centralized security configuration and utilities.

Provides a single source of truth for security settings across the application.
"""

import os
from datetime import timedelta


class SecurityConfig:
    """
    Security configuration constants and utilities.
    """

    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED = os.environ.get('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
    RATE_LIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')

    # Default rate limits (requests per time period)
    RATE_LIMIT_DEFAULT = os.environ.get('RATE_LIMIT_DEFAULT', '200 per hour, 50 per minute')
    RATE_LIMIT_STRICT = os.environ.get('RATE_LIMIT_STRICT', '10 per minute, 50 per hour')
    RATE_LIMIT_MODERATE = os.environ.get('RATE_LIMIT_MODERATE', '30 per minute, 500 per hour')
    RATE_LIMIT_LENIENT = os.environ.get('RATE_LIMIT_LENIENT', '60 per minute, 1000 per hour')

    # Session Management Configuration
    SESSION_TYPE = os.environ.get('SESSION_TYPE', 'redis')
    SESSION_TIMEOUT_MINUTES = int(os.environ.get('SESSION_TIMEOUT_MINUTES', 60))
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'true').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_VALIDATE_IP = os.environ.get('SESSION_VALIDATE_IP', 'false').lower() == 'true'
    SESSION_VALIDATE_USER_AGENT = os.environ.get('SESSION_VALIDATE_USER_AGENT', 'true').lower() == 'true'

    # CSRF Protection
    CSRF_ENABLED = os.environ.get('CSRF_ENABLED', 'true').lower() == 'true'
    CSRF_TOKEN_LENGTH = 32

    # Input Validation
    MAX_REQUEST_SIZE = int(os.environ.get('MAX_REQUEST_SIZE', 16 * 1024 * 1024))  # 16MB
    MAX_JSON_DEPTH = int(os.environ.get('MAX_JSON_DEPTH', 10))
    MAX_STRING_LENGTH = int(os.environ.get('MAX_STRING_LENGTH', 10000))

    # XSS Protection
    XSS_PROTECTION_ENABLED = os.environ.get('XSS_PROTECTION_ENABLED', 'true').lower() == 'true'
    SANITIZE_HTML = os.environ.get('SANITIZE_HTML', 'true').lower() == 'true'

    # Content Security Policy
    CSP_ENABLED = os.environ.get('CSP_ENABLED', 'true').lower() == 'true'
    CSP_POLICY = os.environ.get('CSP_POLICY', (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    ))

    # SQL Injection Prevention
    SQL_INJECTION_DETECTION_ENABLED = os.environ.get('SQL_INJECTION_DETECTION_ENABLED', 'true').lower() == 'true'
    ALLOW_RAW_SQL = os.environ.get('ALLOW_RAW_SQL', 'false').lower() == 'true'

    # Audit Logging
    AUDIT_LOG_ENABLED = os.environ.get('AUDIT_LOG_ENABLED', 'true').lower() == 'true'
    AUDIT_LOG_RETENTION_DAYS = int(os.environ.get('AUDIT_LOG_RETENTION_DAYS', 365))

    # Password Policy (for future authentication)
    PASSWORD_MIN_LENGTH = int(os.environ.get('PASSWORD_MIN_LENGTH', 12))
    PASSWORD_REQUIRE_UPPERCASE = os.environ.get('PASSWORD_REQUIRE_UPPERCASE', 'true').lower() == 'true'
    PASSWORD_REQUIRE_LOWERCASE = os.environ.get('PASSWORD_REQUIRE_LOWERCASE', 'true').lower() == 'true'
    PASSWORD_REQUIRE_DIGIT = os.environ.get('PASSWORD_REQUIRE_DIGIT', 'true').lower() == 'true'
    PASSWORD_REQUIRE_SPECIAL = os.environ.get('PASSWORD_REQUIRE_SPECIAL', 'true').lower() == 'true'

    # API Security
    API_KEY_REQUIRED = os.environ.get('API_KEY_REQUIRED', 'false').lower() == 'true'
    INTERNAL_SERVICE_TOKEN = os.environ.get('INTERNAL_SERVICE_TOKEN')

    # CORS Configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(',')
    CORS_ALLOW_CREDENTIALS = os.environ.get('CORS_ALLOW_CREDENTIALS', 'true').lower() == 'true'

    # SSL/TLS Configuration
    FORCE_HTTPS = os.environ.get('FORCE_HTTPS', 'false').lower() == 'true'
    HSTS_ENABLED = os.environ.get('HSTS_ENABLED', 'true').lower() == 'true'
    HSTS_MAX_AGE = int(os.environ.get('HSTS_MAX_AGE', 31536000))  # 1 year

    # File Upload Security
    ALLOWED_EXTENSIONS = set(os.environ.get('ALLOWED_EXTENSIONS', 'xml').split(','))
    MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', 16 * 1024 * 1024))  # 16MB
    SCAN_UPLOADS = os.environ.get('SCAN_UPLOADS', 'false').lower() == 'true'

    # Security Headers
    SECURITY_HEADERS_ENABLED = os.environ.get('SECURITY_HEADERS_ENABLED', 'true').lower() == 'true'

    @classmethod
    def get_session_config(cls):
        """Get session configuration dictionary."""
        return {
            'SESSION_TYPE': cls.SESSION_TYPE,
            'SESSION_PERMANENT': True,
            'SESSION_USE_SIGNER': True,
            'SESSION_KEY_PREFIX': 'trellix_session:',
            'PERMANENT_SESSION_LIFETIME': timedelta(minutes=cls.SESSION_TIMEOUT_MINUTES),
            'SESSION_COOKIE_NAME': 'trellix_session',
            'SESSION_COOKIE_HTTPONLY': cls.SESSION_COOKIE_HTTPONLY,
            'SESSION_COOKIE_SECURE': cls.SESSION_COOKIE_SECURE,
            'SESSION_COOKIE_SAMESITE': cls.SESSION_COOKIE_SAMESITE,
        }

    @classmethod
    def get_security_headers(cls):
        """Get security headers dictionary."""
        headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': (
                'geolocation=(), microphone=(), camera=(), '
                'payment=(), usb=(), magnetometer=(), '
                'gyroscope=(), accelerometer=()'
            ),
        }

        if cls.CSP_ENABLED:
            headers['Content-Security-Policy'] = cls.CSP_POLICY

        if cls.HSTS_ENABLED and cls.FORCE_HTTPS:
            headers['Strict-Transport-Security'] = f'max-age={cls.HSTS_MAX_AGE}; includeSubDomains'

        if cls.XSS_PROTECTION_ENABLED:
            headers['X-XSS-Protection'] = '1; mode=block'

        return headers

    @classmethod
    def validate_configuration(cls):
        """
        Validate security configuration.

        Raises warnings for insecure configurations in production.

        Returns:
            list: List of configuration warnings
        """
        warnings = []

        # Check if running in production mode
        is_production = os.environ.get('FLASK_ENV') == 'production'

        if is_production:
            # Production-specific checks
            if not cls.RATE_LIMIT_ENABLED:
                warnings.append("Rate limiting is disabled in production")

            if not cls.CSRF_ENABLED:
                warnings.append("CSRF protection is disabled in production")

            if not cls.SESSION_COOKIE_SECURE:
                warnings.append("Session cookies are not marked as secure in production")

            if not cls.FORCE_HTTPS:
                warnings.append("HTTPS is not enforced in production")

            if cls.ALLOW_RAW_SQL:
                warnings.append("Raw SQL is allowed in production - this is dangerous")

            if not cls.AUDIT_LOG_ENABLED:
                warnings.append("Audit logging is disabled in production")

            if cls.SESSION_TYPE == 'filesystem':
                warnings.append("Using filesystem sessions in production - consider Redis")

            if not cls.INTERNAL_SERVICE_TOKEN:
                warnings.append("Internal service token not configured")

        return warnings

    @classmethod
    def print_security_status(cls):
        """Print security configuration status for debugging."""
        print("\n=== Security Configuration Status ===")
        print(f"Rate Limiting: {'Enabled' if cls.RATE_LIMIT_ENABLED else 'DISABLED'}")
        print(f"CSRF Protection: {'Enabled' if cls.CSRF_ENABLED else 'DISABLED'}")
        print(f"XSS Protection: {'Enabled' if cls.XSS_PROTECTION_ENABLED else 'DISABLED'}")
        print(f"SQL Injection Detection: {'Enabled' if cls.SQL_INJECTION_DETECTION_ENABLED else 'DISABLED'}")
        print(f"Audit Logging: {'Enabled' if cls.AUDIT_LOG_ENABLED else 'DISABLED'}")
        print(f"Session Type: {cls.SESSION_TYPE}")
        print(f"Session Timeout: {cls.SESSION_TIMEOUT_MINUTES} minutes")
        print(f"Secure Cookies: {'Enabled' if cls.SESSION_COOKIE_SECURE else 'DISABLED'}")
        print(f"Force HTTPS: {'Enabled' if cls.FORCE_HTTPS else 'DISABLED'}")
        print(f"CSP: {'Enabled' if cls.CSP_ENABLED else 'DISABLED'}")

        warnings = cls.validate_configuration()
        if warnings:
            print("\n⚠️  Configuration Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        else:
            print("\n✓ No security configuration warnings")

        print("=====================================\n")


# Security utilities
def get_client_ip():
    """
    Get client IP address, handling proxy headers.

    Returns:
        str: Client IP address
    """
    # Check for proxy headers
    if 'X-Forwarded-For' in os.environ:
        # Get first IP in the chain (the original client)
        forwarded_for = os.environ.get('X-Forwarded-For', '').split(',')
        if forwarded_for:
            return forwarded_for[0].strip()

    if 'X-Real-IP' in os.environ:
        return os.environ.get('X-Real-IP')

    # Fallback to direct connection
    from flask import request
    return request.remote_addr if request else 'unknown'


def is_safe_redirect_url(url, allowed_hosts=None):
    """
    Check if a redirect URL is safe.

    Args:
        url: URL to validate
        allowed_hosts: List of allowed hostnames

    Returns:
        bool: True if URL is safe
    """
    from urllib.parse import urlparse

    if not url:
        return False

    try:
        parsed = urlparse(url)

        # Relative URLs are always safe
        if not parsed.netloc:
            return True

        # Check scheme
        if parsed.scheme not in ['http', 'https']:
            return False

        # Check against allowed hosts
        if allowed_hosts:
            return parsed.netloc in allowed_hosts

        # If no allowed hosts specified, only allow relative URLs
        return False

    except Exception:
        return False


def generate_nonce():
    """
    Generate a cryptographic nonce for CSP.

    Returns:
        str: Base64-encoded nonce
    """
    import secrets
    return secrets.token_urlsafe(16)


# Environment-specific security profiles
class DevelopmentSecurityConfig(SecurityConfig):
    """Relaxed security for development."""
    RATE_LIMIT_ENABLED = False
    SESSION_COOKIE_SECURE = False
    FORCE_HTTPS = False
    SESSION_VALIDATE_IP = False


class ProductionSecurityConfig(SecurityConfig):
    """Strict security for production."""
    RATE_LIMIT_ENABLED = True
    SESSION_COOKIE_SECURE = True
    FORCE_HTTPS = True
    CSRF_ENABLED = True
    AUDIT_LOG_ENABLED = True
    ALLOW_RAW_SQL = False


def get_security_config(environment=None):
    """
    Get security configuration for environment.

    Args:
        environment: Environment name (development, production)

    Returns:
        SecurityConfig: Configuration class
    """
    if environment is None:
        environment = os.environ.get('FLASK_ENV', 'development')

    if environment == 'production':
        return ProductionSecurityConfig
    else:
        return DevelopmentSecurityConfig
