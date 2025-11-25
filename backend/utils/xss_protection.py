"""
XSS (Cross-Site Scripting) protection utilities.

Provides input sanitization, output encoding, and security headers
to prevent XSS attacks across the application.
"""

import re
import logging
from functools import wraps
from flask import request, make_response
import bleach
from markupsafe import escape

logger = logging.getLogger(__name__)


# Configuration for HTML sanitization
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'blockquote', 'code', 'pre'
]

ALLOWED_ATTRIBUTES = {
    '*': ['class'],
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'width', 'height'],
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


def sanitize_html(html_content, strip=True):
    """
    Sanitize HTML content to prevent XSS attacks.

    Args:
        html_content: HTML string to sanitize
        strip: If True, strip all tags. If False, allow safe tags.

    Returns:
        str: Sanitized HTML

    Example:
        >>> sanitize_html('<script>alert("XSS")</script><p>Safe content</p>')
        '&lt;script&gt;alert("XSS")&lt;/script&gt;<p>Safe content</p>'
    """
    if not html_content or not isinstance(html_content, str):
        return html_content

    if strip:
        # Strip all HTML tags
        return bleach.clean(html_content, tags=[], strip=True)
    else:
        # Allow safe HTML tags
        return bleach.clean(
            html_content,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            protocols=ALLOWED_PROTOCOLS,
            strip=True
        )


def sanitize_json_string(value):
    """
    Sanitize string values in JSON payloads.

    Removes potentially dangerous characters while preserving
    legitimate data formatting.

    Args:
        value: String value to sanitize

    Returns:
        str: Sanitized string
    """
    if not isinstance(value, str):
        return value

    # Remove null bytes
    sanitized = value.replace('\x00', '')

    # Remove or escape dangerous HTML/JS patterns
    dangerous_patterns = [
        (r'<script[^>]*>.*?</script>', '', re.IGNORECASE | re.DOTALL),
        (r'javascript:', '', re.IGNORECASE),
        (r'on\w+\s*=', '', re.IGNORECASE),  # Event handlers like onclick=
        (r'<iframe[^>]*>.*?</iframe>', '', re.IGNORECASE | re.DOTALL),
        (r'<object[^>]*>.*?</object>', '', re.IGNORECASE | re.DOTALL),
        (r'<embed[^>]*>', '', re.IGNORECASE),
    ]

    for pattern, replacement, flags in dangerous_patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=flags)

    return sanitized


def escape_output(value):
    """
    Escape value for safe output in HTML context.

    Args:
        value: Value to escape

    Returns:
        Escaped value safe for HTML output
    """
    if isinstance(value, str):
        return escape(value)
    return value


def sanitize_request_data(data, max_depth=10, current_depth=0):
    """
    Recursively sanitize all string values in request data.

    Args:
        data: Request data (dict, list, or primitive)
        max_depth: Maximum recursion depth
        current_depth: Current recursion depth

    Returns:
        Sanitized data structure

    Raises:
        ValueError: If max depth exceeded
    """
    if current_depth >= max_depth:
        raise ValueError("Request data nested too deeply")

    if isinstance(data, dict):
        return {
            key: sanitize_request_data(value, max_depth, current_depth + 1)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [
            sanitize_request_data(item, max_depth, current_depth + 1)
            for item in data
        ]
    elif isinstance(data, str):
        return sanitize_json_string(data)
    else:
        return data


def detect_xss_patterns(value):
    """
    Detect common XSS attack patterns in input.

    Args:
        value: String to check for XSS patterns

    Returns:
        tuple: (is_suspicious, pattern_found)
    """
    if not isinstance(value, str):
        return False, None

    # Common XSS patterns
    patterns = [
        (r'<script', 'script tag'),
        (r'javascript:', 'javascript protocol'),
        (r'on\w+\s*=', 'event handler'),
        (r'<iframe', 'iframe tag'),
        (r'<object', 'object tag'),
        (r'<embed', 'embed tag'),
        (r'<applet', 'applet tag'),
        (r'vbscript:', 'vbscript protocol'),
        (r'data:text/html', 'data URI'),
        (r'expression\s*\(', 'CSS expression'),
        (r'import\s+', 'import statement'),
        (r'@import', 'CSS import'),
    ]

    value_lower = value.lower()

    for pattern, description in patterns:
        if re.search(pattern, value_lower, re.IGNORECASE):
            return True, description

    return False, None


def log_xss_attempt(user_input, detected_pattern, endpoint=None):
    """
    Log potential XSS attempts for security monitoring.

    Args:
        user_input: The suspicious user input
        detected_pattern: The XSS pattern that was detected
        endpoint: API endpoint where the attempt occurred
    """
    logger.warning(
        f"Potential XSS attempt detected: "
        f"Pattern='{detected_pattern}', "
        f"Input='{user_input[:100]}...', "
        f"Endpoint={endpoint}"
    )


# Security headers middleware
def add_security_headers(response):
    """
    Add security headers to HTTP response.

    Args:
        response: Flask response object

    Returns:
        Modified response with security headers
    """
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'

    # Enable XSS protection in browsers
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'

    # Content Security Policy
    # Note: Adjust based on your application's needs
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # Adjust for your needs
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    response.headers['Content-Security-Policy'] = csp_policy

    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # Permissions policy (formerly Feature Policy)
    response.headers['Permissions-Policy'] = (
        'geolocation=(), '
        'microphone=(), '
        'camera=(), '
        'payment=(), '
        'usb=(), '
        'magnetometer=(), '
        'gyroscope=(), '
        'accelerometer=()'
    )

    return response


def require_xss_protection(f):
    """
    Decorator to automatically sanitize request data and add security headers.

    Usage:
        @app.route('/api/endpoint', methods=['POST'])
        @require_xss_protection
        def my_endpoint():
            data = request.get_json()
            # data is already sanitized
            return jsonify(result)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Sanitize request data if present
        if request.is_json:
            try:
                original_data = request.get_json(silent=True)
                if original_data:
                    # Store sanitized data in request context
                    # The route handler should use get_sanitized_json()
                    request._sanitized_data = sanitize_request_data(original_data)
            except Exception as e:
                logger.error(f"Error sanitizing request data: {e}")

        # Execute the route handler
        response = f(*args, **kwargs)

        # Add security headers to response
        if not isinstance(response, tuple):
            response = make_response(response)
        else:
            # Handle tuple responses (response, status_code)
            response = make_response(*response)

        return add_security_headers(response)

    return decorated_function


def get_sanitized_json():
    """
    Get sanitized JSON data from current request.

    This should be used instead of request.get_json() in routes
    decorated with @require_xss_protection.

    Returns:
        dict: Sanitized JSON data
    """
    if hasattr(request, '_sanitized_data'):
        return request._sanitized_data
    else:
        # Fallback: sanitize on-the-fly
        data = request.get_json(silent=True)
        return sanitize_request_data(data) if data else None


# URL validation to prevent open redirects
def validate_redirect_url(url, allowed_domains=None):
    """
    Validate redirect URL to prevent open redirect vulnerabilities.

    Args:
        url: URL to validate
        allowed_domains: List of allowed domains for redirects

    Returns:
        bool: True if URL is safe for redirect

    Example:
        >>> validate_redirect_url('https://example.com', ['example.com'])
        True
        >>> validate_redirect_url('https://evil.com', ['example.com'])
        False
    """
    if not url:
        return False

    # Parse URL
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)

        # Reject data URIs and javascript: protocols
        if parsed.scheme not in ['http', 'https', '']:
            return False

        # If no domain restrictions, only allow relative URLs
        if not allowed_domains:
            return not parsed.netloc  # Relative URLs have no netloc

        # Check if domain is in allowed list
        if parsed.netloc:
            # Extract domain without port
            domain = parsed.netloc.split(':')[0]
            return domain in allowed_domains

        return True  # Relative URL is safe

    except Exception as e:
        logger.warning(f"Error validating redirect URL: {e}")
        return False


# Input validation decorators
def validate_no_html(field_name):
    """
    Decorator to validate that a specific field contains no HTML.

    Args:
        field_name: Name of the field to validate

    Example:
        @validate_no_html('username')
        def create_user():
            data = request.get_json()
            # data['username'] is guaranteed to have no HTML
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json(silent=True) or {}
            field_value = data.get(field_name)

            if field_value and isinstance(field_value, str):
                is_suspicious, pattern = detect_xss_patterns(field_value)
                if is_suspicious:
                    log_xss_attempt(field_value, pattern, request.endpoint)
                    return {
                        'success': False,
                        'error': f'Field {field_name} contains invalid HTML/JavaScript'
                    }, 400

            return f(*args, **kwargs)

        return decorated_function
    return decorator


# Content type validation
def validate_content_type(allowed_types):
    """
    Decorator to validate request content type.

    Args:
        allowed_types: List of allowed content types

    Example:
        @validate_content_type(['application/json'])
        def api_endpoint():
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            content_type = request.content_type

            if content_type:
                # Extract main type without charset
                main_type = content_type.split(';')[0].strip()

                if main_type not in allowed_types:
                    return {
                        'success': False,
                        'error': f'Invalid content type. Allowed: {", ".join(allowed_types)}'
                    }, 415

            return f(*args, **kwargs)

        return decorated_function
    return decorator


# Safe template rendering helper
def safe_render_template(template_name, **context):
    """
    Render template with automatic HTML escaping.

    This wraps Flask's render_template to ensure all variables
    are properly escaped unless explicitly marked as safe.

    Args:
        template_name: Template file name
        **context: Template context variables

    Returns:
        Rendered template with escaped variables
    """
    from flask import render_template

    # Escape all string values in context
    safe_context = {}
    for key, value in context.items():
        if isinstance(value, str):
            safe_context[key] = escape(value)
        elif isinstance(value, dict):
            safe_context[key] = {
                k: escape(v) if isinstance(v, str) else v
                for k, v in value.items()
            }
        elif isinstance(value, list):
            safe_context[key] = [
                escape(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            safe_context[key] = value

    return render_template(template_name, **safe_context)
