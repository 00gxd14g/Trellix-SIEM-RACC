"""
Secure session management utilities.

Provides server-side session storage with Redis backend,
session validation, and secure cookie configuration.
"""

import os
import secrets
import logging
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import session, request, current_app
from flask_session import Session

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages secure server-side sessions with Redis backend.
    """

    def __init__(self, app=None):
        """
        Initialize session manager.

        Args:
            app: Flask application instance
        """
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """
        Configure Flask-Session with secure settings.

        Args:
            app: Flask application instance
        """
        # Session configuration
        app.config['SESSION_TYPE'] = os.environ.get('SESSION_TYPE', 'redis')
        app.config['SESSION_PERMANENT'] = True
        app.config['SESSION_USE_SIGNER'] = True  # Sign session cookies
        app.config['SESSION_KEY_PREFIX'] = 'trellix_session:'

        # Redis configuration for sessions
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        if app.config['SESSION_TYPE'] == 'redis':
            try:
                from redis import Redis
                app.config['SESSION_REDIS'] = Redis.from_url(redis_url)
                logger.info(f"Session storage configured with Redis: {redis_url}")
            except ImportError:
                logger.warning("Redis not available, falling back to filesystem sessions")
                app.config['SESSION_TYPE'] = 'filesystem'
                app.config['SESSION_FILE_DIR'] = os.path.join(
                    os.path.dirname(app.root_path), 'flask_session'
                )

        # Session lifetime (from settings or default to 60 minutes)
        session_timeout = int(os.environ.get('SESSION_TIMEOUT_MINUTES', 60))
        app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=session_timeout)

        # Secure cookie settings
        app.config['SESSION_COOKIE_NAME'] = 'trellix_session'
        app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
        app.config['SESSION_COOKIE_SECURE'] = not app.debug  # HTTPS only in production
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection

        # Initialize Flask-Session
        Session(app)

        # Register session validation before each request
        @app.before_request
        def validate_session():
            if session:
                self._validate_session_security()

        logger.info("Secure session management initialized")

    @staticmethod
    def _validate_session_security():
        """
        Validate session security attributes.

        Checks for session fixation, session hijacking, and expired sessions.
        """
        # Check if session has been initialized
        if 'initialized' not in session:
            session['initialized'] = True
            session['created_at'] = datetime.now(timezone.utc).isoformat()
            session['ip_address'] = request.remote_addr
            session['user_agent'] = request.headers.get('User-Agent', '')
            session['csrf_token'] = secrets.token_urlsafe(32)
            return

        # Validate IP address hasn't changed (prevent session hijacking)
        # Note: This is strict and may cause issues with load balancers
        # Consider disabling in production if clients have dynamic IPs
        if current_app.config.get('SESSION_VALIDATE_IP', False):
            stored_ip = session.get('ip_address')
            current_ip = request.remote_addr

            if stored_ip and stored_ip != current_ip:
                logger.warning(
                    f"Session IP mismatch: stored={stored_ip}, current={current_ip}"
                )
                SessionManager.invalidate_session()
                return

        # Validate User-Agent hasn't changed (detect session hijacking)
        if current_app.config.get('SESSION_VALIDATE_USER_AGENT', True):
            stored_ua = session.get('user_agent', '')
            current_ua = request.headers.get('User-Agent', '')

            if stored_ua and stored_ua != current_ua:
                logger.warning("Session User-Agent mismatch detected")
                SessionManager.invalidate_session()
                return

        # Update last activity timestamp
        session['last_activity'] = datetime.now(timezone.utc).isoformat()

    @staticmethod
    def create_session(user_id=None, customer_id=None, additional_data=None):
        """
        Create a new secure session.

        Args:
            user_id: User identifier
            customer_id: Customer/tenant identifier
            additional_data: Additional session data

        Returns:
            str: Session ID
        """
        # Generate new session ID
        session.clear()
        session.permanent = True

        # Set session data
        session['initialized'] = True
        session['created_at'] = datetime.now(timezone.utc).isoformat()
        session['ip_address'] = request.remote_addr
        session['user_agent'] = request.headers.get('User-Agent', '')
        session['csrf_token'] = secrets.token_urlsafe(32)
        session['session_id'] = secrets.token_urlsafe(32)

        if user_id:
            session['user_id'] = user_id

        if customer_id:
            session['customer_id'] = customer_id

        if additional_data:
            session.update(additional_data)

        logger.info(f"New session created: {session.get('session_id')}")

        return session.get('session_id')

    @staticmethod
    def invalidate_session():
        """
        Invalidate the current session.

        Clears all session data and forces re-authentication.
        """
        session_id = session.get('session_id', 'unknown')
        session.clear()
        logger.info(f"Session invalidated: {session_id}")

    @staticmethod
    def refresh_session():
        """
        Refresh session to prevent expiration.

        Updates the last activity timestamp and extends the session lifetime.
        """
        session['last_activity'] = datetime.now(timezone.utc).isoformat()
        session.modified = True

    @staticmethod
    def get_csrf_token():
        """
        Get CSRF token for the current session.

        Returns:
            str: CSRF token
        """
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_urlsafe(32)

        return session['csrf_token']

    @staticmethod
    def validate_csrf_token(token):
        """
        Validate CSRF token.

        Args:
            token: Token to validate

        Returns:
            bool: True if token is valid
        """
        session_token = session.get('csrf_token')

        if not session_token or not token:
            return False

        return secrets.compare_digest(session_token, token)

    @staticmethod
    def get_session_info():
        """
        Get information about the current session.

        Returns:
            dict: Session information
        """
        return {
            'session_id': session.get('session_id'),
            'user_id': session.get('user_id'),
            'customer_id': session.get('customer_id'),
            'created_at': session.get('created_at'),
            'last_activity': session.get('last_activity'),
            'ip_address': session.get('ip_address'),
        }


# Decorators for session management
def require_session(f):
    """
    Decorator to require a valid session.

    Usage:
        @app.route('/protected')
        @require_session
        def protected_route():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'initialized' not in session:
            return {
                'success': False,
                'error': 'No valid session found. Please authenticate.'
            }, 401

        return f(*args, **kwargs)

    return decorated_function


def require_csrf_token(f):
    """
    Decorator to require and validate CSRF token.

    Expects CSRF token in X-CSRF-Token header for state-changing operations.

    Usage:
        @app.route('/api/update', methods=['POST'])
        @require_csrf_token
        def update_data():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Only check CSRF for state-changing methods
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            csrf_token = request.headers.get('X-CSRF-Token')

            if not SessionManager.validate_csrf_token(csrf_token):
                logger.warning(
                    f"CSRF token validation failed for {request.endpoint} "
                    f"from {request.remote_addr}"
                )

                # Log security event
                from utils.audit_logger import AuditLogger, AuditAction
                AuditLogger.log_security_event(
                    action=AuditAction.CSRF_VIOLATION,
                    details=f"CSRF validation failed for {request.endpoint}",
                    severity='warning'
                )

                return {
                    'success': False,
                    'error': 'CSRF token validation failed'
                }, 403

        return f(*args, **kwargs)

    return decorated_function


def session_activity(f):
    """
    Decorator to refresh session on activity.

    Updates last activity timestamp for active sessions.

    Usage:
        @app.route('/api/data')
        @session_activity
        def get_data():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'initialized' in session:
            SessionManager.refresh_session()

        return f(*args, **kwargs)

    return decorated_function


# Session security utilities
def generate_session_token():
    """
    Generate a cryptographically secure session token.

    Returns:
        str: Secure random token
    """
    return secrets.token_urlsafe(32)


def validate_session_timeout():
    """
    Check if the current session has timed out.

    Returns:
        bool: True if session is still valid, False if timed out
    """
    if 'last_activity' not in session:
        return True  # No activity tracked, assume valid

    try:
        last_activity = datetime.fromisoformat(session['last_activity'])
        timeout_minutes = current_app.config.get(
            'PERMANENT_SESSION_LIFETIME',
            timedelta(minutes=60)
        ).total_seconds() / 60

        elapsed_minutes = (
            datetime.now(timezone.utc) - last_activity
        ).total_seconds() / 60

        if elapsed_minutes > timeout_minutes:
            logger.info(f"Session timed out after {elapsed_minutes:.1f} minutes")
            return False

        return True

    except Exception as e:
        logger.error(f"Error validating session timeout: {e}")
        return False


def cleanup_expired_sessions():
    """
    Clean up expired sessions from storage.

    This should be run periodically as a background task.

    Returns:
        int: Number of sessions cleaned up
    """
    # Implementation depends on session backend
    # For Redis, sessions expire automatically
    # For filesystem, manual cleanup is needed

    session_type = current_app.config.get('SESSION_TYPE')

    if session_type == 'filesystem':
        try:
            import os
            import time
            from pathlib import Path

            session_dir = Path(current_app.config.get('SESSION_FILE_DIR', 'flask_session'))
            if not session_dir.exists():
                return 0

            timeout_seconds = current_app.config.get(
                'PERMANENT_SESSION_LIFETIME',
                timedelta(minutes=60)
            ).total_seconds()

            current_time = time.time()
            cleaned_count = 0

            for session_file in session_dir.glob('*'):
                if session_file.is_file():
                    file_age = current_time - session_file.stat().st_mtime
                    if file_age > timeout_seconds:
                        session_file.unlink()
                        cleaned_count += 1

            logger.info(f"Cleaned up {cleaned_count} expired filesystem sessions")
            return cleaned_count

        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            return 0

    return 0  # Redis handles expiration automatically


# Session monitoring
def get_active_sessions_count():
    """
    Get count of active sessions.

    Returns:
        int: Number of active sessions
    """
    session_type = current_app.config.get('SESSION_TYPE')

    if session_type == 'redis':
        try:
            redis_client = current_app.config.get('SESSION_REDIS')
            if redis_client:
                key_pattern = current_app.config.get('SESSION_KEY_PREFIX', 'session:') + '*'
                return len(redis_client.keys(key_pattern))
        except Exception as e:
            logger.error(f"Error counting active sessions: {e}")

    elif session_type == 'filesystem':
        try:
            from pathlib import Path
            session_dir = Path(current_app.config.get('SESSION_FILE_DIR', 'flask_session'))
            if session_dir.exists():
                return len(list(session_dir.glob('*')))
        except Exception as e:
            logger.error(f"Error counting active sessions: {e}")

    return 0
