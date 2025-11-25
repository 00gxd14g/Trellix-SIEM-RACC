"""
Comprehensive security test suite.

Tests all security features including:
- Rate limiting
- Input validation
- SQL injection prevention
- XSS protection
- Audit logging
- Session management
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Import security utilities
from utils.validation_schemas import (
    validate_request_data,
    SystemSettingsUpdateSchema,
    APITestConfigSchema,
    sanitize_string_input,
    sanitize_dict,
)
from utils.sql_security import (
    detect_sql_injection_patterns,
    validate_column_name,
    validate_table_name,
    safe_like_pattern,
    SQLInjectionError,
)
from utils.xss_protection import (
    sanitize_html,
    sanitize_json_string,
    detect_xss_patterns,
)
from utils.audit_logger import AuditLogger, AuditAction, track_changes
from utils.security_config import SecurityConfig


class TestInputValidation:
    """Test input validation schemas."""

    def test_general_settings_validation_success(self):
        """Test valid general settings pass validation."""
        data = {
            'appName': 'Test App',
            'maxFileSize': 16,
            'sessionTimeout': 60,
        }

        result = validate_request_data(SystemSettingsUpdateSchema, {'general': data})
        assert result['general']['appName'] == 'Test App'

    def test_general_settings_validation_failure(self):
        """Test invalid general settings fail validation."""
        data = {
            'maxFileSize': 200,  # Too large (max 100)
        }

        with pytest.raises(Exception):
            validate_request_data(SystemSettingsUpdateSchema, {'general': data})

    def test_api_settings_url_validation(self):
        """Test API URL validation."""
        # Valid URL
        data = {
            'apiBaseUrl': 'https://api.example.com',
            'timeout': 15,
        }

        result = validate_request_data(SystemSettingsUpdateSchema, {'api': data})
        assert result['api']['apiBaseUrl'] == 'https://api.example.com'

    def test_api_settings_invalid_url(self):
        """Test invalid URL is rejected."""
        data = {
            'apiBaseUrl': 'javascript:alert(1)',  # Invalid scheme
        }

        with pytest.raises(Exception):
            validate_request_data(SystemSettingsUpdateSchema, {'api': data})

    def test_localhost_url_blocked(self):
        """Test localhost URLs are blocked."""
        data = {
            'apiBaseUrl': 'http://localhost:8080',
        }

        with pytest.raises(Exception):
            validate_request_data(SystemSettingsUpdateSchema, {'api': data})

    def test_sanitize_string_input(self):
        """Test string sanitization."""
        # Null bytes
        assert sanitize_string_input('test\x00data') == 'testdata'

        # Control characters
        input_str = 'test\x01\x02\x03data'
        result = sanitize_string_input(input_str)
        assert '\x01' not in result

        # Max length
        long_string = 'a' * 1000
        result = sanitize_string_input(long_string, max_length=100)
        assert len(result) == 100

    def test_sanitize_dict_nested(self):
        """Test nested dictionary sanitization."""
        data = {
            'key1': 'value\x00with\x00nulls',
            'nested': {
                'key2': 'nested\x01value',
            }
        }

        result = sanitize_dict(data)
        assert '\x00' not in result['key1']
        assert '\x01' not in result['nested']['key2']

    def test_sanitize_dict_max_depth(self):
        """Test max depth protection."""
        # Create deeply nested dict
        data = {'level1': {}}
        current = data['level1']
        for i in range(15):
            current['next'] = {}
            current = current['next']

        with pytest.raises(Exception):
            sanitize_dict(data, max_depth=10)


class TestSQLInjectionPrevention:
    """Test SQL injection prevention measures."""

    def test_detect_sql_injection_union_select(self):
        """Test detection of UNION SELECT attacks."""
        suspicious, pattern = detect_sql_injection_patterns("' UNION SELECT * FROM users --")
        assert suspicious is True
        assert pattern is not None

    def test_detect_sql_injection_drop_table(self):
        """Test detection of DROP TABLE attacks."""
        suspicious, pattern = detect_sql_injection_patterns("'; DROP TABLE users; --")
        assert suspicious is True

    def test_detect_sql_injection_or_bypass(self):
        """Test detection of OR bypass attacks."""
        suspicious, pattern = detect_sql_injection_patterns("admin' OR '1'='1")
        assert suspicious is True

    def test_detect_sql_injection_comments(self):
        """Test detection of SQL comments."""
        suspicious, pattern = detect_sql_injection_patterns("test -- comment")
        assert suspicious is True

    def test_safe_input_passes(self):
        """Test that safe input is not flagged."""
        suspicious, pattern = detect_sql_injection_patterns("normal search term")
        assert suspicious is False
        assert pattern is None

    def test_validate_column_name_valid(self):
        """Test valid column names are accepted."""
        assert validate_column_name('customer_id') == 'customer_id'
        assert validate_column_name('user_name') == 'user_name'
        assert validate_column_name('_private') == '_private'

    def test_validate_column_name_invalid(self):
        """Test invalid column names are rejected."""
        with pytest.raises(SQLInjectionError):
            validate_column_name('customer-id')  # Hyphen not allowed

        with pytest.raises(SQLInjectionError):
            validate_column_name('user.name')  # Dot not allowed

        with pytest.raises(SQLInjectionError):
            validate_column_name('SELECT')  # SQL keyword

    def test_validate_column_name_allowlist(self):
        """Test column name allowlist enforcement."""
        allowed = ['id', 'name', 'email']

        assert validate_column_name('name', allowed) == 'name'

        with pytest.raises(SQLInjectionError):
            validate_column_name('password', allowed)

    def test_validate_table_name_valid(self):
        """Test valid table names are accepted."""
        assert validate_table_name('customers') == 'customers'
        assert validate_table_name('user_profiles') == 'user_profiles'

    def test_validate_table_name_invalid(self):
        """Test invalid table names are rejected."""
        with pytest.raises(SQLInjectionError):
            validate_table_name('users; DROP TABLE')

    def test_safe_like_pattern(self):
        """Test LIKE pattern escaping."""
        assert safe_like_pattern('test%') == 'test\\%'
        assert safe_like_pattern('test_') == 'test\\_'
        assert safe_like_pattern('test\\') == 'test\\\\'


class TestXSSProtection:
    """Test XSS protection measures."""

    def test_sanitize_html_strips_scripts(self):
        """Test that script tags are removed."""
        html = '<script>alert("XSS")</script><p>Safe content</p>'
        result = sanitize_html(html, strip=False)
        assert '<script>' not in result
        assert '<p>Safe content</p>' in result

    def test_sanitize_html_strips_all(self):
        """Test complete HTML stripping."""
        html = '<script>alert("XSS")</script><p>Content</p>'
        result = sanitize_html(html, strip=True)
        assert '<' not in result
        assert 'Content' in result

    def test_sanitize_json_string_removes_scripts(self):
        """Test script removal from JSON strings."""
        text = 'Hello <script>alert(1)</script> World'
        result = sanitize_json_string(text)
        assert '<script>' not in result
        assert 'Hello' in result
        assert 'World' in result

    def test_sanitize_json_string_removes_event_handlers(self):
        """Test event handler removal."""
        text = '<div onclick="alert(1)">Click me</div>'
        result = sanitize_json_string(text)
        assert 'onclick=' not in result.lower()

    def test_detect_xss_script_tag(self):
        """Test XSS pattern detection for script tags."""
        suspicious, pattern = detect_xss_patterns('<script>alert(1)</script>')
        assert suspicious is True
        assert pattern == 'script tag'

    def test_detect_xss_javascript_protocol(self):
        """Test XSS pattern detection for javascript: protocol."""
        suspicious, pattern = detect_xss_patterns('javascript:alert(1)')
        assert suspicious is True
        assert pattern == 'javascript protocol'

    def test_detect_xss_event_handler(self):
        """Test XSS pattern detection for event handlers."""
        suspicious, pattern = detect_xss_patterns('<img onerror="alert(1)">')
        assert suspicious is True
        assert pattern == 'event handler'

    def test_safe_content_passes(self):
        """Test that safe content is not flagged."""
        suspicious, pattern = detect_xss_patterns('This is normal text')
        assert suspicious is False


class TestAuditLogging:
    """Test audit logging functionality."""

    def test_track_changes_detects_modifications(self):
        """Test change tracking detects modifications."""
        old_data = {'name': 'Old Name', 'value': 100}
        new_data = {'name': 'New Name', 'value': 100}

        changes = track_changes(old_data, new_data)

        assert changes is not None
        assert 'name' in changes
        assert changes['name']['before'] == 'Old Name'
        assert changes['name']['after'] == 'New Name'
        assert 'value' not in changes  # Unchanged

    def test_track_changes_detects_additions(self):
        """Test change tracking detects additions."""
        old_data = {'name': 'Test'}
        new_data = {'name': 'Test', 'email': 'test@example.com'}

        changes = track_changes(old_data, new_data)

        assert 'email' in changes
        assert changes['email']['before'] is None
        assert changes['email']['after'] == 'test@example.com'

    def test_track_changes_detects_deletions(self):
        """Test change tracking detects deletions."""
        old_data = {'name': 'Test', 'email': 'test@example.com'}
        new_data = {'name': 'Test'}

        changes = track_changes(old_data, new_data)

        assert 'email' in changes
        assert changes['email']['before'] == 'test@example.com'
        assert changes['email']['after'] is None

    def test_track_changes_no_changes(self):
        """Test change tracking returns None when no changes."""
        old_data = {'name': 'Test', 'value': 100}
        new_data = {'name': 'Test', 'value': 100}

        changes = track_changes(old_data, new_data)

        assert changes is None


class TestSecurityConfiguration:
    """Test security configuration."""

    def test_security_config_defaults(self):
        """Test default security configuration."""
        assert SecurityConfig.RATE_LIMIT_ENABLED is not None
        assert SecurityConfig.CSRF_ENABLED is not None
        assert SecurityConfig.AUDIT_LOG_ENABLED is not None

    def test_get_security_headers(self):
        """Test security headers generation."""
        headers = SecurityConfig.get_security_headers()

        assert 'X-Content-Type-Options' in headers
        assert headers['X-Content-Type-Options'] == 'nosniff'
        assert 'X-Frame-Options' in headers
        assert headers['X-Frame-Options'] == 'DENY'

    def test_validate_configuration_production(self):
        """Test configuration validation in production."""
        with patch.dict('os.environ', {'FLASK_ENV': 'production'}):
            warnings = SecurityConfig.validate_configuration()
            # Should have warnings if not properly configured
            assert isinstance(warnings, list)

    def test_session_config(self):
        """Test session configuration."""
        config = SecurityConfig.get_session_config()

        assert 'SESSION_TYPE' in config
        assert 'SESSION_COOKIE_HTTPONLY' in config
        assert config['SESSION_COOKIE_HTTPONLY'] is True


class TestRateLimiting:
    """Test rate limiting functionality."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis for testing."""
        with patch('redis.Redis') as mock:
            yield mock

    def test_rate_limit_key_generation(self):
        """Test rate limit key generation."""
        from utils.rate_limiter import get_request_identifier
        from main import create_app
        
        app = create_app('testing')
        
        with app.test_request_context(environ_base={'REMOTE_ADDR': '192.168.1.1'}, headers={'X-Customer-ID': '123'}):
            key = get_request_identifier()
            assert '123' in key
            assert '192.168.1.1' in key


class TestAPIEndpointSecurity:
    """Test API endpoint security integration."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from main import create_app
        app = create_app('testing')
        return app.test_client()

    def test_settings_endpoint_requires_valid_json(self, client):
        """Test settings endpoint validates JSON."""
        response = client.put(
            '/api/settings',
            data='invalid json',
            content_type='application/json'
        )

        # Should handle gracefully
        assert response.status_code in [400, 500]

    def test_settings_endpoint_rejects_sql_injection(self, client):
        """Test settings endpoint rejects SQL injection attempts."""
        malicious_data = {
            'general': {
                'appName': "'; DROP TABLE users; --"
            }
        }

        response = client.put(
            '/api/settings',
            data=json.dumps(malicious_data),
            content_type='application/json'
        )

        # Should be rejected
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    def test_api_test_endpoint_blocks_localhost(self, client):
        """Test API test endpoint blocks localhost."""
        test_data = {
            'config': {
                'apiBaseUrl': 'http://localhost:8080',
                'healthEndpoint': '/health'
            }
        }

        response = client.post(
            '/api/settings/api/test',
            data=json.dumps(test_data),
            content_type='application/json'
        )

        # Should be blocked
        assert response.status_code == 400


class TestSessionSecurity:
    """Test session security features."""

    def test_csrf_token_generation(self):
        """Test CSRF token generation."""
        from utils.session_manager import generate_session_token

        token1 = generate_session_token()
        token2 = generate_session_token()

        assert len(token1) > 0
        assert token1 != token2  # Should be unique

    def test_csrf_token_validation(self):
        """Test CSRF token validation."""
        from utils.session_manager import SessionManager
        from main import create_app
        from flask import session
        
        app = create_app('testing')
        
        with app.test_request_context():
            session['csrf_token'] = 'valid_token'
            
            # Valid token
            assert SessionManager.validate_csrf_token('valid_token') is True

            # Invalid token
            assert SessionManager.validate_csrf_token('invalid_token') is False

            # Empty token
            assert SessionManager.validate_csrf_token('') is False


# Performance and stress tests
class TestSecurityPerformance:
    """Test performance of security features."""

    def test_validation_performance(self):
        """Test input validation performance."""
        import time

        data = {
            'general': {
                'appName': 'Test App',
                'maxFileSize': 16,
                'sessionTimeout': 60,
            }
        }

        start = time.time()
        for _ in range(1000):
            validate_request_data(SystemSettingsUpdateSchema, data)
        elapsed = time.time() - start

        # Should complete 1000 validations in under 1 second
        assert elapsed < 1.0

    def test_sql_injection_detection_performance(self):
        """Test SQL injection detection performance."""
        import time

        test_strings = [
            "normal search term",
            "user@example.com",
            "customer-name-123",
            "product description",
        ]

        start = time.time()
        for _ in range(1000):
            for s in test_strings:
                detect_sql_injection_patterns(s)
        elapsed = time.time() - start

        # Should complete 4000 checks in under 1 second
        assert elapsed < 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
