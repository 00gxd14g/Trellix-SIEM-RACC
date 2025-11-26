"""
Input validation schemas for API endpoints.

Provides comprehensive validation for all user inputs to prevent
injection attacks, data corruption, and invalid state transitions.
"""

from marshmallow import Schema, fields, validates, validates_schema, ValidationError, EXCLUDE
from marshmallow.validate import Range, OneOf
import re
from urllib.parse import urlparse


# Custom validators
def validate_url(value):
    """Validate URL format and allowed schemes."""
    if not value:
        return

    try:
        parsed = urlparse(value)
        if parsed.scheme not in ['http', 'https']:
            raise ValidationError('URL must use http or https scheme')

        # Prevent SSRF to localhost/private IPs in production
        hostname = parsed.hostname
        if hostname:
            # Block common localhost patterns
            forbidden_hosts = ['localhost', '127.0.0.1', '0.0.0.0', '::1']
            if hostname.lower() in forbidden_hosts:
                raise ValidationError('URL cannot point to localhost')

            # Block private IP ranges (basic check)
            if hostname.startswith('192.168.') or hostname.startswith('10.') or hostname.startswith('172.'):
                raise ValidationError('URL cannot point to private IP addresses')

    except Exception as e:
        raise ValidationError(f'Invalid URL format: {str(e)}')


def validate_no_sql_keywords(value):
    """Prevent basic SQL injection patterns in text fields."""
    if not value:
        return

    # Common SQL injection patterns
    sql_patterns = [
        r'\b(union|select|insert|delete|drop|alter|exec|execute)\b',
        r'--',
        r'/\*',
        r'\*/',
        r';.*--',
        r"'.*or.*'.*=.*'",
        r'1.*=.*1',
    ]

    value_lower = value.lower()
    for pattern in sql_patterns:
        if re.search(pattern, value_lower, re.IGNORECASE):
            raise ValidationError('Input contains potentially malicious SQL patterns')


def validate_no_script_tags(value):
    """Prevent script tag injection in text fields."""
    if not value:
        return

    dangerous_patterns = [
        r'<script',
        r'javascript:',
        r'onerror=',
        r'onload=',
        r'onclick=',
        r'<iframe',
        r'<embed',
        r'<object',
    ]

    value_lower = value.lower()
    for pattern in dangerous_patterns:
        if pattern in value_lower:
            raise ValidationError('Input contains potentially malicious HTML/JavaScript')


def validate_safe_filename(value):
    """Validate filename to prevent directory traversal."""
    if not value:
        return

    # Check for directory traversal patterns
    dangerous_patterns = ['..', '/', '\\', '\x00']
    for pattern in dangerous_patterns:
        if pattern in value:
            raise ValidationError('Filename contains invalid characters')

    # Ensure filename has valid extension
    if '.' not in value:
        raise ValidationError('Filename must have an extension')


# General Settings Schema
class GeneralSettingsSchema(Schema):
    class Meta:
        unknown = EXCLUDE  # Ignore unknown fields

    appName = fields.Str(
        required=False,
        validate=[
            validate_no_script_tags,
        ],
        metadata={'description': 'Application display name'}
    )
    maxFileSize = fields.Integer(
        required=False,
        validate=Range(min=1, max=100),
        metadata={'description': 'Maximum file upload size in MB'}
    )
    defaultPageSize = fields.Integer(
        required=False,
        validate=Range(min=10, max=1000),
        metadata={'description': 'Default pagination size'}
    )
    enableNotifications = fields.Boolean(required=False)
    notificationEmail = fields.Email(
        required=False,
        allow_none=True,
        metadata={'description': 'Email for system notifications'}
    )
    backupEnabled = fields.Boolean(required=False)
    backupFrequency = fields.Str(
        required=False,
        validate=OneOf(['hourly', 'daily', 'weekly', 'monthly']),
        metadata={'description': 'Backup frequency'}
    )
    enableAuditLog = fields.Boolean(required=False)
    sessionTimeout = fields.Integer(
        required=False,
        validate=Range(min=5, max=1440),  # 5 minutes to 24 hours
        metadata={'description': 'Session timeout in minutes'}
    )
    theme = fields.Str(
        required=False,
        validate=OneOf(['light', 'dark', 'system']),
        metadata={'description': 'UI theme preference'}
    )


# API Settings Schema
class APISettingsSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    apiBaseUrl = fields.Str(
        required=False,
        validate=validate_url,
        metadata={'description': 'Base URL for external API'}
    )
    healthEndpoint = fields.Str(
        required=False,
        validate=lambda x: x.startswith('/'),
        metadata={'description': 'Health check endpoint path'}
    )
    apiKey = fields.Str(
        required=False,
        allow_none=True,
        validate=lambda x: len(x) <= 500 if x else True,
        metadata={'description': 'API authentication key'}
    )
    authHeader = fields.Str(
        required=False,
        validate=lambda x: len(x) <= 100,
        metadata={'description': 'Authorization header name'}
    )
    timeout = fields.Integer(
        required=False,
        validate=lambda x: 1 <= x <= 300,  # 1 second to 5 minutes
        metadata={'description': 'Request timeout in seconds'}
    )
    verifySsl = fields.Boolean(
        required=False,
        metadata={'description': 'Enable SSL certificate verification'}
    )
    pollInterval = fields.Integer(
        required=False,
        validate=lambda x: 10 <= x <= 3600,  # 10 seconds to 1 hour
        metadata={'description': 'Polling interval in seconds'}
    )


# Customer Settings Schema
class CustomerSettingsSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    maxAlarmNameLength = fields.Integer(
        required=False,
        validate=lambda x: 1 <= x <= 500,
        metadata={'description': 'Maximum alarm name length'}
    )
    defaultSeverity = fields.Integer(
        required=False,
        validate=lambda x: 0 <= x <= 100,
        metadata={'description': 'Default alarm severity (0-100)'}
    )
    defaultConditionType = fields.Integer(
        required=False,
        validate=lambda x: 0 <= x <= 100,
        metadata={'description': 'Default condition type identifier'}
    )
    matchField = fields.Str(
        required=False,
        validate=[
            lambda x: len(x) <= 100,
        ],
        metadata={'description': 'Field name for alarm matching'}
    )
    summaryTemplate = fields.Str(
        required=False,
        validate=lambda x: len(x) <= 5000,
        metadata={'description': 'Alarm summary template'}
    )
    defaultAssignee = fields.Integer(
        required=False,
        metadata={'description': 'Default assignee ID'}
    )
    defaultEscAssignee = fields.Integer(
        required=False,
        metadata={'description': 'Default escalation assignee ID'}
    )
    defaultMinVersion = fields.Str(
        required=False,
        validate=lambda x: re.match(r'^\d+\.\d+\.\d+$', x) if x else True,
        metadata={'description': 'Minimum version (semantic versioning)'}
    )


# System Settings Update Schema
class SystemSettingsUpdateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    general = fields.Nested(GeneralSettingsSchema, required=False, allow_none=True)
    api = fields.Nested(APISettingsSchema, required=False, allow_none=True)
    customer_defaults = fields.Nested(CustomerSettingsSchema, required=False, allow_none=True)


# Customer Settings Update Schema
class CustomerSettingsUpdateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    overrides = fields.Nested(CustomerSettingsSchema, required=False, allow_none=True)


# API Test Configuration Schema
class APITestConfigSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    config = fields.Nested(APISettingsSchema, required=False, allow_none=True)

    @validates_schema
    def validate_test_config(self, data, **kwargs):
        """Validate that config contains necessary fields for testing."""
        config = data.get('config')
        if config and not config.get('apiBaseUrl'):
            raise ValidationError(
                'API base URL is required for testing',
                field_name='config.apiBaseUrl'
            )


# Customer Creation Schema
class CustomerCreateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.Str(
        required=True,
        validate=[
            lambda x: 1 <= len(x) <= 200,
            validate_no_sql_keywords,
            validate_no_script_tags,
        ],
        metadata={'description': 'Customer name'}
    )
    description = fields.Str(
        required=False,
        allow_none=True,
        validate=[
            lambda x: len(x) <= 1000 if x else True,
            validate_no_sql_keywords,
            validate_no_script_tags,
        ],
        metadata={'description': 'Customer description'}
    )
    contact_email = fields.Email(
        required=False,
        allow_none=True,
        metadata={'description': 'Customer contact email'}
    )
    contact_phone = fields.Str(
        required=False,
        allow_none=True,
        validate=lambda x: len(x) <= 50 if x else True,
        metadata={'description': 'Customer contact phone'}
    )


# File Upload Schema
class FileUploadSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    filename = fields.Str(
        required=True,
        validate=[
            validate_safe_filename,
            lambda x: x.lower().endswith('.xml'),
        ],
        metadata={'description': 'Name of the uploaded file'}
    )


# Helper function to validate request data
def validate_request_data(schema_class, data, partial=False):
    """
    Validate request data against a schema.

    Args:
        schema_class: Marshmallow schema class to use for validation
        data: Dictionary of data to validate
        partial: If True, allow partial updates (don't require all fields)

    Returns:
        dict: Validated and sanitized data

    Raises:
        ValidationError: If validation fails
    """
    schema = schema_class(partial=partial)
    try:
        validated_data = schema.load(data)
        return validated_data
    except ValidationError as e:
        # Re-raise with detailed error messages
        raise ValidationError(e.messages)


# Sanitization utilities
def sanitize_string_input(value, max_length=None):
    """
    Sanitize string input by removing control characters.

    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length

    Returns:
        str: Sanitized string
    """
    if not isinstance(value, str):
        return value

    # Remove null bytes and control characters
    sanitized = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')

    # Trim to max length if specified
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized.strip()


def sanitize_dict(data, max_depth=10, current_depth=0):
    """
    Recursively sanitize dictionary values.

    Args:
        data: Dictionary to sanitize
        max_depth: Maximum recursion depth
        current_depth: Current recursion depth

    Returns:
        dict: Sanitized dictionary
    """
    if current_depth >= max_depth:
        raise ValidationError('Input nested too deeply')

    if not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        # Sanitize keys
        safe_key = sanitize_string_input(str(key), max_length=200)

        # Sanitize values
        if isinstance(value, str):
            sanitized[safe_key] = sanitize_string_input(value, max_length=10000)
        elif isinstance(value, dict):
            sanitized[safe_key] = sanitize_dict(value, max_depth, current_depth + 1)
        elif isinstance(value, list):
            sanitized[safe_key] = [
                sanitize_dict(item, max_depth, current_depth + 1) if isinstance(item, dict)
                else sanitize_string_input(item) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            sanitized[safe_key] = value

    return sanitized
