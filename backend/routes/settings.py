"""
Settings API Routes Module

Provides comprehensive endpoints for managing system-wide and per-customer configuration settings.
Supports hierarchical settings with three levels:
1. Built-in defaults (immutable)
2. System settings (global overrides)
3. Customer settings (per-customer overrides)

Configuration Flow:
  defaults -> system_settings -> customer_settings (final effective settings)

All timestamps are managed in UTC for consistent auditing across time zones.
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
import ssl
from urllib.parse import urljoin
from urllib import request as urllib_request
from typing import Union

from flask import Blueprint, jsonify, request
from werkzeug.exceptions import NotFound

from models import Customer, CustomerSetting, SystemSetting, db
from utils.settings_defaults import (
    DEFAULT_GENERAL_SETTINGS,
    DEFAULT_API_SETTINGS,
    DEFAULT_CUSTOMER_SETTINGS,
    get_all_defaults,
)
from utils.tenant_auth import require_customer_token
from utils.validation_schemas import (
    validate_request_data,
    SystemSettingsUpdateSchema,
    CustomerSettingsUpdateSchema,
    APITestConfigSchema
)
from marshmallow import ValidationError

settings_bp = Blueprint('settings', __name__)


def _utcnow():
    """
    Get current UTC time.

    Returns:
        datetime: Current time in UTC timezone.
    """
    return datetime.now(timezone.utc)


def _ensure_system_setting(category: str, defaults: dict) -> SystemSetting:
    """
    Ensure a system setting exists, creating if necessary and merging with defaults.

    This function implements the idempotent ensure pattern for system settings:
    - If setting doesn't exist, creates it with defaults
    - If setting exists, merges it with current defaults (handles schema evolution)
    - Automatically commits to database

    Args:
        category (str): Setting category (e.g., 'general', 'api', 'customer_defaults')
        defaults (dict): Default values to merge with persisted settings

    Returns:
        SystemSetting: The ensured system setting object (may have been created or updated)

    Database Behavior:
        - Creates new record if category doesn't exist
        - Merges defaults with existing data (new keys are added, existing preserved)
        - Commits transaction immediately to ensure atomicity
    """
    setting = SystemSetting.query.filter_by(category=category).first()
    merged = deepcopy(defaults)
    if setting is None:
        setting = SystemSetting(category=category, data=merged, updated_at=_utcnow())
        db.session.add(setting)
        db.session.commit()
        return setting

    current = setting.data or {}
    merged.update(current)
    if merged != current:
        setting.data = merged
        db.session.commit()
    return setting


def _ensure_customer_setting(customer_id: int) -> CustomerSetting:
    """
    Ensure a customer setting record exists, creating if necessary.

    Implements the idempotent ensure pattern for customer settings:
    - If customer setting doesn't exist, creates empty one (customer inherits defaults)
    - If setting exists, returns it unchanged
    - Automatically commits to database on creation

    Args:
        customer_id (int): The customer ID

    Returns:
        CustomerSetting: The ensured customer setting object

    Database Behavior:
        - Creates new record with empty data dict if customer setting doesn't exist
        - Uses multi-tenant constraint: each customer has max one setting record
        - Commits transaction immediately on creation
    """
    setting = CustomerSetting.query.filter_by(customer_id=customer_id).first()
    if setting is None:
        setting = CustomerSetting(customer_id=customer_id, data={}, updated_at=_utcnow())
        db.session.add(setting)
        db.session.commit()
    return setting


def _merge_with_defaults(defaults: dict, overrides: Union[dict, None]) -> dict:
    """
    Merge override settings with defaults to produce effective settings.

    Creates a new dict with defaults as base, then overlays any provided overrides.
    Implements copy-on-write pattern to avoid mutating inputs.

    Args:
        defaults (dict): Base default settings
        overrides (dict | None): Settings to override defaults (can be None)

    Returns:
        dict: Merged settings (defaults + overrides)

    Merge Precedence:
        1. Start with defaults (copied to avoid mutation)
        2. Apply overrides on top (if provided)
        3. Return merged result

    Example:
        >>> defaults = {'a': 1, 'b': 2}
        >>> overrides = {'b': 3, 'c': 4}
        >>> _merge_with_defaults(defaults, overrides)
        {'a': 1, 'b': 3, 'c': 4}
    """
    data = deepcopy(defaults)
    if overrides:
        data.update(overrides)
    return data


@settings_bp.route('/settings', methods=['GET'])
def get_system_settings():
    """
    Retrieve all system-level settings.

    Fetches and returns system settings across three categories:
    - general: General application settings (appName, sessionTimeout, theme, etc.)
    - api: API connectivity settings (baseUrl, key, timeout, verifySsl, etc.)
    - customer_defaults: Default settings for new customers (severity, assignees, etc.)

    Response includes both the effective settings (merged with defaults) and the
    immutable built-in defaults for reference.

    Returns:
        Response: JSON object with keys:
            - success (bool): Always True for successful retrieval
            - settings (dict): Effective settings by category
            - defaults (dict): Built-in default values

    HTTP Responses:
        - 200: Successfully retrieved all settings
        - 500: Database or internal error

    Security:
        - No authentication required (system settings are readable)
        - Consider adding admin-only access control in future versions

    Example Response:
        {
            "success": true,
            "settings": {
                "general": {"appName": "...", "maxFileSize": 16, ...},
                "api": {"apiBaseUrl": "...", "timeout": 15, ...},
                "customer_defaults": {"defaultSeverity": 50, ...}
            },
            "defaults": { ... }
        }
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


@settings_bp.route('/settings', methods=['PUT'])
def update_system_settings():
    """
    Update system-level settings.

    Updates one or more setting categories (general, api, customer_defaults).
    Only categories present in the request payload are updated; others remain unchanged.
    Omitted properties retain their current values (sparse updates).

    Request Body:
        {
            "general": {...},         # Optional: general app settings
            "api": {...},             # Optional: API connectivity settings
            "customer_defaults": {...} # Optional: defaults for new customers
        }

    Merge Strategy:
        - Each category is merged with built-in defaults before saving
        - New properties are added, existing ones are replaced
        - No properties are deleted (use explicit empty/null to clear)

    Returns:
        Response: JSON object with keys:
            - success (bool): True if update succeeded
            - updated (dict): Updated settings by category (merged with defaults)

    HTTP Responses:
        - 200: Settings updated successfully
        - 400: Invalid request payload
        - 500: Database or internal error

    Transaction:
        - All updates are committed in a single transaction
        - Either all updates succeed or none (atomicity)
        - Timestamps are automatically set to current UTC

    Security:
        - No authentication required currently
        - Consider adding admin-only access control

    Example Request:
        {
            "general": {"appName": "Custom Manager", "sessionTimeout": 120},
            "api": {"timeout": 30}
        }

    Example Response:
        {
            "success": true,
            "updated": {
                "general": {"appName": "Custom Manager", "maxFileSize": 16, ...},
                "api": {"apiBaseUrl": "...", "timeout": 30, ...}
            }
        }
    """
    payload = request.get_json(force=True) or {}
    
    try:
        payload = validate_request_data(SystemSettingsUpdateSchema, payload)
    except ValidationError as e:
        return jsonify({'success': False, 'error': e.messages}), 400

    updated_categories = {}

    if 'general' in payload:
        setting = _ensure_system_setting('general', DEFAULT_GENERAL_SETTINGS)
        new_data = _merge_with_defaults(DEFAULT_GENERAL_SETTINGS, payload['general'] or {})
        setting.data = new_data
        setting.updated_at = _utcnow()
        updated_categories['general'] = new_data

    if 'api' in payload:
        setting = _ensure_system_setting('api', DEFAULT_API_SETTINGS)
        new_data = _merge_with_defaults(DEFAULT_API_SETTINGS, payload['api'] or {})
        setting.data = new_data
        setting.updated_at = _utcnow()
        updated_categories['api'] = new_data

    if 'customer_defaults' in payload:
        setting = _ensure_system_setting('customer_defaults', DEFAULT_CUSTOMER_SETTINGS)
        new_data = _merge_with_defaults(DEFAULT_CUSTOMER_SETTINGS, payload['customer_defaults'] or {})
        setting.data = new_data
        setting.updated_at = _utcnow()
        updated_categories['customer_defaults'] = new_data

    if updated_categories:
        db.session.commit()

    return jsonify({
        'success': True,
        'updated': updated_categories,
    })


@settings_bp.route('/customers/<int:customer_id>/settings', methods=['GET'])
@require_customer_token
def get_customer_settings(customer_id):
    """
    Retrieve customer-specific settings.

    Fetches effective settings for a customer by merging:
    1. Built-in defaults (immutable)
    2. System-level defaults (from customer_defaults category)
    3. Customer-specific overrides

    Response includes:
    - overrides: Sparse dict with customer-specific overrides only
    - effective: Final merged settings (all three levels combined)
    - defaults: System defaults already merged with built-in defaults
    - updated_at: ISO 8601 UTC timestamp of last modification

    Security:
        - Requires customer authentication via X-Customer-ID header
        - Header must match the customer_id path parameter
        - Automatically validates customer exists (404 if not found)

    Args:
        customer_id (int): The customer ID (from URL path)

    Returns:
        Response: JSON object with keys:
            - success (bool): True for successful retrieval
            - customer_id (int): The requested customer ID
            - overrides (dict): Sparse dict of customer-specific overrides
            - effective (dict): Final merged settings
            - defaults (dict): System defaults with customer_defaults applied
            - updated_at (str): ISO 8601 UTC timestamp or null

    HTTP Responses:
        - 200: Successfully retrieved customer settings
        - 403: X-Customer-ID header missing or doesn't match customer_id
        - 404: Customer not found
        - 500: Database or internal error

    Configuration Hierarchy:
        defaults -> (system customer_defaults) -> (customer overrides) = effective

    Example Response:
        {
            "success": true,
            "customer_id": 1,
            "overrides": {
                "defaultSeverity": 85,
                "defaultAssignee": 9000
            },
            "effective": {
                "maxAlarmNameLength": 128,
                "defaultSeverity": 85,
                "defaultConditionType": 14,
                "matchField": "DSIDSigID",
                ...
            },
            "defaults": {
                "maxAlarmNameLength": 128,
                "defaultSeverity": 50,
                ...
            },
            "updated_at": "2024-11-11T15:30:45.123456+00:00"
        }
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


@settings_bp.route('/customers/<int:customer_id>/settings', methods=['PUT'])
@require_customer_token
def update_customer_settings(customer_id):
    """
    Update customer-specific setting overrides.

    Updates or clears customer-specific setting overrides. Only properties in the
    overrides object are modified; other settings remain unchanged.

    Request Body:
        {
            "overrides": {
                "defaultSeverity": 85,      # Override with new value
                "defaultAssignee": null,    # Clear override (use defaults)
                "matchField": ""            # Clear override (use defaults)
            }
        }

    Override Behavior:
        - Provided values are set as overrides
        - null or empty string ('') values clear existing overrides
        - Cleared properties revert to system defaults
        - Omitted properties retain their current state

    Security:
        - Requires customer authentication via X-Customer-ID header
        - Header must match the customer_id path parameter
        - Automatically validates customer exists (404 if not found)
        - Changes are isolated to the specified customer

    Args:
        customer_id (int): The customer ID (from URL path)

    Returns:
        Response: JSON object with keys:
            - success (bool): True if update succeeded
            - customer_id (int): The updated customer ID
            - overrides (dict): Updated overrides (sparse dict)
            - effective (dict): Final merged settings after update
            - defaults (dict): System defaults with customer_defaults applied

    HTTP Responses:
        - 200: Settings updated successfully
        - 403: X-Customer-ID header missing or doesn't match customer_id
        - 404: Customer not found
        - 500: Database or internal error

    Multi-Tenant Isolation:
        - Updates only affect the specified customer
        - Each customer has max one settings record
        - Database-level unique constraint on customer_id

    Example Request:
        {
            "overrides": {
                "defaultSeverity": 85,
                "defaultAssignee": 9000,
                "matchField": "CustomField"
            }
        }

    Example Response:
        {
            "success": true,
            "customer_id": 1,
            "overrides": {
                "defaultSeverity": 85,
                "defaultAssignee": 9000,
                "matchField": "CustomField"
            },
            "effective": {
                "maxAlarmNameLength": 128,
                "defaultSeverity": 85,
                "defaultConditionType": 14,
                "matchField": "CustomField",
                ...
            },
            "defaults": {...}
        }
    """
    Customer.query.get_or_404(customer_id)
    payload = request.get_json(force=True) or {}
    
    try:
        payload = validate_request_data(CustomerSettingsUpdateSchema, payload)
    except ValidationError as e:
        return jsonify({'success': False, 'error': e.messages}), 400

    overrides = payload.get('overrides', {}) or {}

    sanitized = {}
    defaults = _merge_with_defaults(
        DEFAULT_CUSTOMER_SETTINGS,
        _ensure_system_setting('customer_defaults', DEFAULT_CUSTOMER_SETTINGS).data,
    )

    for key, value in overrides.items():
        if value in (None, ''):
            continue
        sanitized[key] = value

    customer_setting = _ensure_customer_setting(customer_id)
    customer_setting.data = sanitized
    customer_setting.updated_at = _utcnow()
    db.session.commit()

    effective = _merge_with_defaults(defaults, sanitized)

    return jsonify({
        'success': True,
        'customer_id': customer_id,
        'overrides': sanitized,
        'effective': effective,
        'defaults': defaults,
    })


@settings_bp.route('/settings/api/test', methods=['POST'])
def test_api_connection():
    """
    Test connectivity to an external API endpoint.

    Validates API configuration by making a test request to the configured
    health endpoint. Useful for verifying connectivity and authentication
    settings before saving them.

    Request Body (optional):
        {
            "config": {
                "apiBaseUrl": "http://api.example.com",
                "healthEndpoint": "/health",
                "apiKey": "sk-1234567890abcdef",
                "authHeader": "Authorization",
                "timeout": 10,
                "verifySsl": true
            }
        }

    If config is omitted, uses current system API settings.

    Configuration Details:
        - apiBaseUrl: Base URL of the API (required)
        - healthEndpoint: Relative path to health check endpoint (default: "/health")
        - apiKey: Authentication key (optional, sends in authHeader)
        - authHeader: HTTP header name for API key (default: "Authorization")
        - timeout: Request timeout in seconds (default: 15)
        - verifySsl: Whether to verify SSL certificates (default: true)

    HTTP Request:
        - Method: GET
        - URL: {apiBaseUrl}/{healthEndpoint}
        - Headers: Accept: application/json
        - If apiKey provided: {authHeader}: {apiKey}
        - Timeout: configured timeout

    Returns:
        Response: JSON with test result details
            Success (200):
                {
                    "success": true,
                    "url": "http://api.example.com/health",
                    "status_code": 200,
                    "body": { ... } or "..."  # parsed if JSON, else raw string
                }

            Failure (502):
                {
                    "success": false,
                    "url": "http://api.example.com/health",
                    "error": "Connection refused" or other error message
                }

    HTTP Responses:
        - 200: Successfully connected to API
        - 400: Invalid configuration (missing required fields)
        - 502: Connection failed (timeout, connection refused, etc.)
        - 500: Internal server error

    Error Handling:
        - Connection errors: timeout, connection refused, DNS failure
        - SSL errors: certificate verification failure
        - HTTP errors: bad status codes (converted to exceptions)
        - Parsing errors: JSON decode failures (returns raw string)

    Security Considerations:
        - API keys are transmitted in HTTP headers (use HTTPS in production)
        - No authentication required to test (consider adding admin restriction)
        - SSL verification can be disabled (for testing only, not production)
        - Responses include full error details (may leak info in production)

    Use Cases:
        - Validate API settings before saving
        - Diagnose connectivity issues
        - Test authentication configuration
        - Verify health endpoint functionality

    Example Request:
        curl -X POST http://localhost:5000/api/settings/api/test \
          -H "Content-Type: application/json" \
          -d '{
            "config": {
              "apiBaseUrl": "http://localhost:5000/api",
              "healthEndpoint": "/health",
              "timeout": 5,
              "verifySsl": false
            }
          }'

    Example Success Response:
        {
            "success": true,
            "url": "http://localhost:5000/api/health",
            "status_code": 200,
            "body": {
                "status": "healthy",
                "message": "API is running",
                "version": "1.0.0"
            }
        }

    Example Failure Response:
        {
            "success": false,
            "url": "http://127.0.0.1:9/api/health",
            "error": "[Errno 111] Connection refused"
        }
    """
    payload = request.get_json(force=True) or {}
    
    try:
        payload = validate_request_data(APITestConfigSchema, payload)
    except ValidationError as e:
        return jsonify({'success': False, 'error': e.messages}), 400

    config = payload.get('config') or _ensure_system_setting('api', DEFAULT_API_SETTINGS).data
    merged = _merge_with_defaults(DEFAULT_API_SETTINGS, config)

    base_url = merged.get('apiBaseUrl', '').rstrip('/')
    endpoint = merged.get('healthEndpoint', '/health').lstrip('/')

    if not base_url:
        return jsonify({'success': False, 'error': 'API base URL is required.'}), 400

    url = urljoin(f"{base_url}/", endpoint)
    headers = {'Accept': 'application/json'}
    api_key = merged.get('apiKey')
    auth_header = merged.get('authHeader') or 'Authorization'
    if api_key:
        headers[auth_header] = api_key

    context = None
    if not merged.get('verifySsl', True):
        context = ssl._create_unverified_context()

    req = urllib_request.Request(url, headers=headers, method='GET')

    try:
        with urllib_request.urlopen(req, timeout=float(merged.get('timeout', 15)), context=context) as response:
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

        return jsonify({
            'success': True,
            'url': url,
            'status_code': status_code,
            'body': parsed_body,
        })
    except Exception as exc:  # pylint: disable=broad-except
        return jsonify({
            'success': False,
            'url': url,
            'error': str(exc),
        }), 502
