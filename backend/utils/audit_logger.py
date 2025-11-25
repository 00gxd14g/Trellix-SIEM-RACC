import logging
import json
from datetime import datetime, timezone
from functools import wraps
from flask import request, g, current_app
from models import AuditLog, db

logger = logging.getLogger(__name__)


# Audit event types
class AuditAction:
    """Enumeration of auditable actions."""

    # Authentication & Authorization
    LOGIN_SUCCESS = 'login_success'
    LOGIN_FAILURE = 'login_failure'
    LOGOUT = 'logout'
    SESSION_EXPIRED = 'session_expired'
    UNAUTHORIZED_ACCESS = 'unauthorized_access'

    # Customer operations
    CUSTOMER_CREATE = 'customer_create'
    CUSTOMER_READ = 'customer_read'
    CUSTOMER_UPDATE = 'customer_update'
    CUSTOMER_DELETE = 'customer_delete'

    # File operations
    FILE_UPLOAD = 'file_upload'
    FILE_DOWNLOAD = 'file_download'
    FILE_DELETE = 'file_delete'
    FILE_VALIDATE = 'file_validate'
    FILE_PARSE = 'file_parse'

    # Rule operations
    RULE_CREATE = 'rule_create'
    RULE_READ = 'rule_read'
    RULE_UPDATE = 'rule_update'
    RULE_DELETE = 'rule_delete'
    RULE_IMPORT = 'rule_import'
    RULE_EXPORT = 'rule_export'

    # Alarm operations
    ALARM_CREATE = 'alarm_create'
    ALARM_READ = 'alarm_read'
    ALARM_UPDATE = 'alarm_update'
    ALARM_DELETE = 'alarm_delete'
    ALARM_IMPORT = 'alarm_import'
    ALARM_EXPORT = 'alarm_export'
    ALARM_GENERATE = 'alarm_generate'
    ALARM_TRANSFORM = 'alarm_transform'

    # Settings operations
    SETTINGS_READ = 'settings_read'
    SETTINGS_UPDATE = 'settings_update'
    SETTINGS_API_TEST = 'settings_api_test'

    # Security events
    RATE_LIMIT_EXCEEDED = 'rate_limit_exceeded'
    SUSPICIOUS_INPUT_DETECTED = 'suspicious_input_detected'
    SQL_INJECTION_ATTEMPT = 'sql_injection_attempt'
    XSS_ATTEMPT = 'xss_attempt'
    CSRF_VIOLATION = 'csrf_violation'
    INVALID_TOKEN = 'invalid_token'

    # System events
    CONFIGURATION_CHANGE = 'configuration_change'
    BACKUP_CREATED = 'backup_created'
    BACKUP_RESTORED = 'backup_restored'
    DATA_EXPORT = 'data_export'
    DATA_IMPORT = 'data_import'


class AuditLogger:
    """
    Central audit logging service for RACC.

    Provides methods to log various types of audit events with
    consistent formatting and automatic context capture.
    """

    @staticmethod
    def _get_request_context():
        """Extract context information from current request."""
        if not request:
            return {
                'ip_address': 'system',
                'user_agent': 'system',
                'endpoint': 'system',
                'method': 'SYSTEM',
            }

        return {
            'ip_address': request.remote_addr or 'unknown',
            'user_agent': request.headers.get('User-Agent', 'unknown')[:500],
            'endpoint': request.endpoint or request.path,
            'method': request.method,
            'customer_id': request.headers.get('X-Customer-ID'),
        }

    @staticmethod
    def _get_user_id():
        """Get current user ID from request context."""
        # For future authentication implementation
        # Currently returns None or customer_id as proxy
        return getattr(g, 'user_id', None)

    @staticmethod
    def log_event(
        action,
        resource_type,
        status='success',
        resource_id=None,
        customer_id=None,
        changes=None,
        metadata=None,
        error_message=None,
        status_code=None
    ):
        """
        Log an audit event.

        Args:
            action: Action being performed (use AuditAction constants)
            resource_type: Type of resource (customer, rule, alarm, etc.)
            status: Event status (success, failure, error)
            resource_id: ID of the resource being acted upon
            customer_id: Customer/tenant ID
            changes: Dictionary of before/after values for modifications
            metadata: Additional context data
            error_message: Error message if status is failure/error
            status_code: HTTP status code

        Returns:
            AuditLog: Created audit log entry
        """
        try:
            context = AuditLogger._get_request_context()

            # Override customer_id if provided
            if customer_id is not None:
                context['customer_id'] = customer_id

            # Create audit log entry
            audit_entry = AuditLog(
                timestamp=datetime.now(timezone.utc),
                user_id=AuditLogger._get_user_id(),
                customer_id=context.get('customer_id'),
                ip_address=context['ip_address'],
                user_agent=context['user_agent'],
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                endpoint=context['endpoint'],
                method=context['method'],
                status=status,
                status_code=status_code,
                error_message=error_message,
                changes=changes,
                audit_metadata=metadata,
            )

            db.session.add(audit_entry)
            db.session.commit()

            # Also log to application logger for real-time monitoring
            log_message = (
                f"AUDIT: {action} on {resource_type}"
                f"{f' (ID: {resource_id})' if resource_id else ''} "
                f"by {context.get('customer_id', 'unknown')} "
                f"from {context['ip_address']} - {status}"
            )

            if status == 'success':
                logger.info(log_message)
            elif status == 'failure':
                logger.warning(f"{log_message} - {error_message}")
            else:
                logger.error(f"{log_message} - {error_message}")

            return audit_entry

        except Exception as e:
            # Never let audit logging break the application
            logger.error(f"Failed to write audit log: {e}", exc_info=True)
            return None

    @staticmethod
    def log_success(action, resource_type, resource_id=None, customer_id=None, changes=None, metadata=None):
        """Log a successful operation."""
        return AuditLogger.log_event(
            action=action,
            resource_type=resource_type,
            status='success',
            resource_id=resource_id,
            customer_id=customer_id,
            changes=changes,
            metadata=metadata,
            status_code=200
        )

    @staticmethod
    def log_failure(action, resource_type, error_message, resource_id=None, customer_id=None, status_code=400):
        """Log a failed operation."""
        return AuditLogger.log_event(
            action=action,
            resource_type=resource_type,
            status='failure',
            resource_id=resource_id,
            customer_id=customer_id,
            error_message=error_message,
            status_code=status_code
        )

    @staticmethod
    def log_security_event(action, details, severity='warning'):
        """
        Log a security event (suspicious activity, attacks, etc.).

        Args:
            action: Security event type (use AuditAction constants)
            details: Description of the security event
            severity: Event severity (info, warning, critical)
        """
        metadata = {
            'severity': severity,
            'details': details,
            'request_headers': dict(request.headers) if request else {},
        }

        return AuditLogger.log_event(
            action=action,
            resource_type='security',
            status='failure',
            error_message=details,
            metadata=metadata,
            status_code=403
        )

    @staticmethod
    def query_logs(
        start_date=None,
        end_date=None,
        customer_id=None,
        action=None,
        resource_type=None,
        status=None,
        ip_address=None,
        limit=100
    ):
        """
        Query audit logs with filters.

        Args:
            start_date: Start of date range
            end_date: End of date range
            customer_id: Filter by customer ID
            action: Filter by action type
            resource_type: Filter by resource type
            status: Filter by status
            ip_address: Filter by IP address
            limit: Maximum number of results

        Returns:
            list: List of matching audit log entries
        """
        query = AuditLog.query

        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)
        if customer_id:
            query = query.filter(AuditLog.customer_id == customer_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if status:
            query = query.filter(AuditLog.status == status)
        if ip_address:
            query = query.filter(AuditLog.ip_address == ip_address)

        return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()


# Decorator for automatic audit logging
def audit_log(action, resource_type, extract_resource_id=None, extract_customer_id=None):
    """
    Decorator to automatically log operations.

    Args:
        action: Action being performed (use AuditAction constants)
        resource_type: Type of resource
        extract_resource_id: Function to extract resource ID from route kwargs
        extract_customer_id: Function to extract customer ID from route kwargs

    Example:
        @audit_log(AuditAction.RULE_READ, 'rule', lambda kwargs: kwargs.get('rule_id'))
        def get_rule(rule_id):
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            resource_id = extract_resource_id(kwargs) if extract_resource_id else None
            customer_id = extract_customer_id(kwargs) if extract_customer_id else kwargs.get('customer_id')

            try:
                # Execute the route handler
                result = f(*args, **kwargs)

                # Determine success based on response
                if isinstance(result, tuple):
                    response, status_code = result[0], result[1]
                    success = 200 <= status_code < 400
                else:
                    response = result
                    status_code = 200
                    success = True

                # Log the operation
                if success:
                    AuditLogger.log_success(
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        customer_id=customer_id
                    )
                else:
                    error_msg = response.get('error', 'Unknown error') if isinstance(response, dict) else str(response)
                    AuditLogger.log_failure(
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        customer_id=customer_id,
                        error_message=error_msg,
                        status_code=status_code
                    )

                return result

            except Exception as e:
                # Log the error
                AuditLogger.log_failure(
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    customer_id=customer_id,
                    error_message=str(e),
                    status_code=500
                )
                raise

        return decorated_function
    return decorator


# Helper to track data changes
def track_changes(old_data, new_data):
    """
    Track changes between old and new data.

    Args:
        old_data: Dictionary of old values
        new_data: Dictionary of new values

    Returns:
        dict: Dictionary of changes with before/after values
    """
    changes = {}

    # Find modified fields
    all_keys = set(old_data.keys()) | set(new_data.keys())

    for key in all_keys:
        old_value = old_data.get(key)
        new_value = new_data.get(key)

        if old_value != new_value:
            changes[key] = {
                'before': old_value,
                'after': new_value
            }

    return changes if changes else None


# Retention policy for audit logs
def cleanup_old_audit_logs(days_to_keep=365):
    """
    Clean up audit logs older than specified days.

    Args:
        days_to_keep: Number of days to retain logs (default 365)

    Returns:
        int: Number of logs deleted
    """
    from datetime import timedelta

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

    try:
        deleted_count = AuditLog.query.filter(
            AuditLog.timestamp < cutoff_date
        ).delete()

        db.session.commit()

        logger.info(f"Cleaned up {deleted_count} audit logs older than {days_to_keep} days")
        return deleted_count

    except Exception as e:
        logger.error(f"Failed to clean up audit logs: {e}")
        db.session.rollback()
        return 0
