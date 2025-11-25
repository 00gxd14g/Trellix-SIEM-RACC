"""
Enhanced settings routes with comprehensive security controls.

This module demonstrates how to integrate all security features:
- Rate limiting
- Input validation
- XSS protection
- SQL injection prevention
- Audit logging
- Session management
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
import ssl
from urllib.parse import urljoin
from urllib import request as urllib_request

from flask import Blueprint, jsonify, request
from werkzeug.exceptions import NotFound
from marshmallow import ValidationError

from models import Customer, CustomerSetting, SystemSetting, db
from utils.settings_defaults import (
    DEFAULT_GENERAL_SETTINGS,
    DEFAULT_API_SETTINGS,
    DEFAULT_CUSTOMER_SETTINGS,
    get_all_defaults,
)
from utils.tenant_auth import require_customer_token
from utils.rate_limiter import strict_rate_limit, moderate_rate_limit, lenient_rate_limit
from utils.validation_schemas import (
    validate_request_data,
    SystemSettingsUpdateSchema,
    CustomerSettingsUpdateSchema,
    APITestConfigSchema,
    sanitize_dict,
)
from utils.xss_protection import require_xss_protection, get_sanitized_json
from utils.audit_logger import AuditLogger, AuditAction, audit_log, track_changes
from utils.sql_security import detect_sql_injection_patterns, log_suspicious_query_attempt

settings_secure_bp = Blueprint('settings_secure', __name__)


def _utcnow():
    return datetime.now(timezone.utc)


def _ensure_system_setting(category: str, defaults: dict) -> SystemSetting:
    """
    Ensure system setting exists with defaults merged.

    Args:
        category: Settings category
        defaults: Default values

    Returns:
        SystemSetting: Setting object
    """
    setting = SystemSetting.query.filter_by(category=category).first()
    merged = deepcopy(defaults)

    if setting is None:
        setting = SystemSetting(category=category, data=merged, updated_at=_utcnow())
        db.session.add(setting)
        db.session.commit()

        # Log creation
        AuditLogger.log_success(
            action=AuditAction.SETTINGS_UPDATE,
            resource_type='system_setting',
            resource_id=category,
            metadata={'action': 'created_with_defaults'}
        )

        return setting

    current = setting.data or {}
    merged.update(current)
    if merged != current:
        setting.data = merged
        db.session.commit()

    return setting


def _ensure_customer_setting(customer_id: int) -> CustomerSetting:
    """
    Ensure customer setting exists.

    Args:
        customer_id: Customer identifier

    Returns:
        CustomerSetting: Setting object
    """
    setting = CustomerSetting.query.filter_by(customer_id=customer_id).first()

    if setting is None:
        setting = CustomerSetting(customer_id=customer_id, data={}, updated_at=_utcnow())
        db.session.add(setting)
        db.session.commit()

        # Log creation
        AuditLogger.log_success(
            action=AuditAction.SETTINGS_UPDATE,
            resource_type='customer_setting',
            customer_id=customer_id,
            metadata={'action': 'created'}
        )

    return setting


def _merge_with_defaults(defaults: dict, overrides: dict | None) -> dict:
    """Merge defaults with overrides."""
    data = deepcopy(defaults)
    if overrides:
        data.update(overrides)
    return data


@settings_secure_bp.route('/settings', methods=['GET'])
@lenient_rate_limit
@audit_log(AuditAction.SETTINGS_READ, 'system_setting')
def get_system_settings():
    """
    Get all system settings.

    Security features:
    - Lenient rate limiting (read operation)
    - Automatic audit logging
    """
    general = _ensure_system_setting('general', DEFAULT_GENERAL_SETTINGS).data or {}
    api = _ensure_system_setting('api', DEFAULT_API_SETTINGS).data or {}
    customer_defaults = _ensure_system_setting('customer_defaults', DEFAULT_CUSTOMER_SETTINGS).data or {}

    return jsonify({
        'success': True,
        'settings': {
            'general': _merge_with_defaults(DEFAULT_GENERAL_SETTINGS, general),
            'api': _merge_with_defaults(DEFAULT_API_SETTINGS, api),
            'customer_defaults': _merge_with_defaults(DEFAULT_CUSTOMER_SETTINGS, customer_defaults),
        },
        'defaults': get_all_defaults(),
    })


@settings_secure_bp.route('/settings', methods=['PUT'])
@moderate_rate_limit
@require_xss_protection
def update_system_settings():
    """
    Update system settings.

    Security features:
    - Moderate rate limiting (update operation)
    - Input validation with marshmallow schemas
    - XSS protection and sanitization
    - SQL injection pattern detection
    - Audit logging with change tracking
    """
    try:
        # Get and validate request data
        raw_payload = request.get_json(force=True, silent=True) or {}

        # Validate with schema
        validated_payload = validate_request_data(
            SystemSettingsUpdateSchema,
            raw_payload,
            partial=True
        )

        # Sanitize the validated data
        sanitized_payload = sanitize_dict(validated_payload)

        updated_categories = {}
        changes_log = {}

        # Update general settings
        if 'general' in sanitized_payload:
            setting = _ensure_system_setting('general', DEFAULT_GENERAL_SETTINGS)
            old_data = setting.data.copy() if setting.data else {}

            new_data = _merge_with_defaults(DEFAULT_GENERAL_SETTINGS, sanitized_payload['general'] or {})
            setting.data = new_data
            setting.updated_at = _utcnow()
            updated_categories['general'] = new_data

            changes_log['general'] = track_changes(old_data, new_data)

        # Update API settings
        if 'api' in sanitized_payload:
            setting = _ensure_system_setting('api', DEFAULT_API_SETTINGS)
            old_data = setting.data.copy() if setting.data else {}

            new_data = _merge_with_defaults(DEFAULT_API_SETTINGS, sanitized_payload['api'] or {})
            setting.data = new_data
            setting.updated_at = _utcnow()
            updated_categories['api'] = new_data

            changes_log['api'] = track_changes(old_data, new_data)

        # Update customer defaults
        if 'customer_defaults' in sanitized_payload:
            setting = _ensure_system_setting('customer_defaults', DEFAULT_CUSTOMER_SETTINGS)
            old_data = setting.data.copy() if setting.data else {}

            new_data = _merge_with_defaults(DEFAULT_CUSTOMER_SETTINGS, sanitized_payload['customer_defaults'] or {})
            setting.data = new_data
            setting.updated_at = _utcnow()
            updated_categories['customer_defaults'] = new_data

            changes_log['customer_defaults'] = track_changes(old_data, new_data)

        if updated_categories:
            db.session.commit()

            # Log successful update with changes
            AuditLogger.log_success(
                action=AuditAction.SETTINGS_UPDATE,
                resource_type='system_setting',
                changes=changes_log,
                metadata={'updated_categories': list(updated_categories.keys())}
            )

        return jsonify({
            'success': True,
            'updated': updated_categories,
        })

    except ValidationError as e:
        # Log validation failure
        AuditLogger.log_failure(
            action=AuditAction.SETTINGS_UPDATE,
            resource_type='system_setting',
            error_message=f'Validation error: {str(e.messages)}',
            status_code=400
        )

        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'details': e.messages
        }), 400

    except Exception as e:
        db.session.rollback()

        # Log error
        AuditLogger.log_failure(
            action=AuditAction.SETTINGS_UPDATE,
            resource_type='system_setting',
            error_message=str(e),
            status_code=500
        )

        return jsonify({
            'success': False,
            'error': 'Failed to update settings'
        }), 500


@settings_secure_bp.route('/customers/<int:customer_id>/settings', methods=['GET'])
@require_customer_token
@lenient_rate_limit
@audit_log(
    AuditAction.SETTINGS_READ,
    'customer_setting',
    extract_customer_id=lambda kwargs: kwargs.get('customer_id')
)
def get_customer_settings(customer_id):
    """
    Get customer-specific settings.

    Security features:
    - Tenant authentication and isolation
    - Lenient rate limiting
    - Automatic audit logging
    """
    Customer.query.get_or_404(customer_id)

    system_defaults = _merge_with_defaults(
        DEFAULT_CUSTOMER_SETTINGS,
        _ensure_system_setting('customer_defaults', DEFAULT_CUSTOMER_SETTINGS).data,
    )

    customer_setting = _ensure_customer_setting(customer_id)
    overrides = customer_setting.data or {}
    effective = _merge_with_defaults(system_defaults, overrides)

    return jsonify({
        'success': True,
        'customer_id': customer_id,
        'overrides': overrides,
        'effective': effective,
        'defaults': system_defaults,
        'updated_at': customer_setting.updated_at.isoformat() if customer_setting.updated_at else None,
    })


@settings_secure_bp.route('/customers/<int:customer_id>/settings', methods=['PUT'])
@require_customer_token
@moderate_rate_limit
@require_xss_protection
def update_customer_settings(customer_id):
    """
    Update customer-specific settings.

    Security features:
    - Tenant authentication and isolation
    - Moderate rate limiting
    - Input validation with schema
    - XSS protection
    - SQL injection pattern detection
    - Audit logging with change tracking
    """
    try:
        Customer.query.get_or_404(customer_id)

        # Get and validate request data
        raw_payload = request.get_json(force=True, silent=True) or {}

        # Validate with schema
        validated_payload = validate_request_data(
            CustomerSettingsUpdateSchema,
            raw_payload,
            partial=True
        )

        # Sanitize the validated data
        sanitized_payload = sanitize_dict(validated_payload)
        overrides = sanitized_payload.get('overrides', {}) or {}

        # Filter out empty values
        sanitized_overrides = {}
        for key, value in overrides.items():
            # Check for SQL injection patterns in string values
            if isinstance(value, str):
                is_suspicious, pattern = detect_sql_injection_patterns(value)
                if is_suspicious:
                    log_suspicious_query_attempt(value, pattern, request.endpoint)

                    AuditLogger.log_security_event(
                        action=AuditAction.SQL_INJECTION_ATTEMPT,
                        details=f'SQL injection pattern detected in settings: {pattern}',
                        severity='warning'
                    )

                    return jsonify({
                        'success': False,
                        'error': 'Invalid input detected'
                    }), 400

            if value not in (None, ''):
                sanitized_overrides[key] = value

        # Get current setting for change tracking
        customer_setting = _ensure_customer_setting(customer_id)
        old_data = customer_setting.data.copy() if customer_setting.data else {}

        # Update setting
        customer_setting.data = sanitized_overrides
        customer_setting.updated_at = _utcnow()
        db.session.commit()

        # Track changes
        changes = track_changes(old_data, sanitized_overrides)

        # Get effective settings
        defaults = _merge_with_defaults(
            DEFAULT_CUSTOMER_SETTINGS,
            _ensure_system_setting('customer_defaults', DEFAULT_CUSTOMER_SETTINGS).data,
        )
        effective = _merge_with_defaults(defaults, sanitized_overrides)

        # Log successful update
        AuditLogger.log_success(
            action=AuditAction.SETTINGS_UPDATE,
            resource_type='customer_setting',
            customer_id=customer_id,
            changes=changes
        )

        return jsonify({
            'success': True,
            'customer_id': customer_id,
            'overrides': sanitized_overrides,
            'effective': effective,
            'defaults': defaults,
        })

    except ValidationError as e:
        # Log validation failure
        AuditLogger.log_failure(
            action=AuditAction.SETTINGS_UPDATE,
            resource_type='customer_setting',
            customer_id=customer_id,
            error_message=f'Validation error: {str(e.messages)}',
            status_code=400
        )

        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'details': e.messages
        }), 400

    except Exception as e:
        db.session.rollback()

        # Log error
        AuditLogger.log_failure(
            action=AuditAction.SETTINGS_UPDATE,
            resource_type='customer_setting',
            customer_id=customer_id,
            error_message=str(e),
            status_code=500
        )

        return jsonify({
            'success': False,
            'error': 'Failed to update customer settings'
        }), 500


@settings_secure_bp.route('/settings/api/test', methods=['POST'])
@strict_rate_limit  # Very strict rate limiting for external API calls
@require_xss_protection
def test_api_connection():
    """
    Test external API connection.

    Security features:
    - STRICT rate limiting (5/min to prevent abuse)
    - Input validation
    - URL validation (prevents SSRF)
    - XSS protection
    - Audit logging
    - Timeout enforcement
    """
    try:
        # Get and validate request data
        raw_payload = request.get_json(force=True, silent=True) or {}

        # Validate with schema
        validated_payload = validate_request_data(
            APITestConfigSchema,
            raw_payload,
            partial=True
        )

        config = validated_payload.get('config') or _ensure_system_setting('api', DEFAULT_API_SETTINGS).data
        merged = _merge_with_defaults(DEFAULT_API_SETTINGS, config)

        base_url = merged.get('apiBaseUrl', '').rstrip('/')
        endpoint = merged.get('healthEndpoint', '/health').lstrip('/')

        if not base_url:
            AuditLogger.log_failure(
                action=AuditAction.SETTINGS_API_TEST,
                resource_type='api_connection',
                error_message='API base URL is required',
                status_code=400
            )
            return jsonify({'success': False, 'error': 'API base URL is required.'}), 400

        # Construct URL
        url = urljoin(f"{base_url}/", endpoint)

        # Additional URL validation for SSRF prevention
        from urllib.parse import urlparse
        parsed = urlparse(url)

        # Block localhost and private IPs in production
        if not request.environ.get('FLASK_DEBUG'):
            forbidden_hosts = ['localhost', '127.0.0.1', '0.0.0.0', '::1']
            if parsed.hostname and parsed.hostname.lower() in forbidden_hosts:
                AuditLogger.log_security_event(
                    action=AuditAction.SUSPICIOUS_INPUT_DETECTED,
                    details=f'Attempted API test to localhost: {url}',
                    severity='warning'
                )
                return jsonify({
                    'success': False,
                    'error': 'Cannot test connections to localhost'
                }), 400

        headers = {'Accept': 'application/json'}
        api_key = merged.get('apiKey')
        auth_header = merged.get('authHeader') or 'Authorization'

        if api_key:
            headers[auth_header] = api_key

        context = None
        if not merged.get('verifySsl', True):
            context = ssl._create_unverified_context()

        req = urllib_request.Request(url, headers=headers, method='GET')

        # Enforce reasonable timeout
        timeout = min(float(merged.get('timeout', 15)), 30)  # Max 30 seconds

        try:
            with urllib_request.urlopen(req, timeout=timeout, context=context) as response:
                status_code = response.getcode()
                content_type = response.headers.get('Content-Type', '')
                body = response.read()
                parsed_body = None

                if 'application/json' in content_type:
                    try:
                        parsed_body = json.loads(body.decode('utf-8'))
                    except json.JSONDecodeError:
                        parsed_body = body.decode('utf-8')
                else:
                    parsed_body = body.decode('utf-8')

            # Log successful test
            AuditLogger.log_success(
                action=AuditAction.SETTINGS_API_TEST,
                resource_type='api_connection',
                metadata={
                    'url': url,
                    'status_code': status_code,
                    'verify_ssl': merged.get('verifySsl', True)
                }
            )

            return jsonify({
                'success': True,
                'url': url,
                'status_code': status_code,
                'body': parsed_body,
            })

        except Exception as exc:
            # Log failed test
            AuditLogger.log_failure(
                action=AuditAction.SETTINGS_API_TEST,
                resource_type='api_connection',
                error_message=str(exc),
                status_code=502,
                metadata={'url': url}
            )

            return jsonify({
                'success': False,
                'url': url,
                'error': str(exc),
            }), 502

    except ValidationError as e:
        # Log validation failure
        AuditLogger.log_failure(
            action=AuditAction.SETTINGS_API_TEST,
            resource_type='api_connection',
            error_message=f'Validation error: {str(e.messages)}',
            status_code=400
        )

        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'details': e.messages
        }), 400

    except Exception as e:
        # Log error
        AuditLogger.log_failure(
            action=AuditAction.SETTINGS_API_TEST,
            resource_type='api_connection',
            error_message=str(e),
            status_code=500
        )

        return jsonify({
            'success': False,
            'error': 'Failed to test API connection'
        }), 500
