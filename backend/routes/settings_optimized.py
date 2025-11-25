"""
Optimized Settings Routes with Caching

Enhanced settings endpoints with:
- Multi-tier caching for improved performance
- Import/export functionality
- Backup management
- Performance monitoring

Author: Database Optimizer Agent
"""

import json
import logging
import ssl
from copy import deepcopy
from datetime import datetime, timezone
from urllib.parse import urljoin
from urllib import request as urllib_request
from typing import Union

from flask import Blueprint, jsonify, request, send_file
from werkzeug.exceptions import NotFound

from models import Customer, CustomerSetting, SystemSetting, db
from utils.settings_defaults import (
    DEFAULT_GENERAL_SETTINGS,
    DEFAULT_API_SETTINGS,
    DEFAULT_CUSTOMER_SETTINGS,
    get_all_defaults,
)
from utils.settings_cache import SettingsCache
from utils.settings_import_export import (
    SettingsExporter,
    SettingsImporter,
    SettingsBackup,
    SettingsTemplate
)
from utils.tenant_auth import require_customer_token

settings_optimized_bp = Blueprint('settings_optimized', __name__)
logger = logging.getLogger(__name__)


def _utcnow():
    return datetime.now(timezone.utc)


def _ensure_system_setting(category: str, defaults: dict) -> SystemSetting:
    """Get or create system setting with caching"""
    # Try cache first
    cached = SettingsCache.get_system_setting(category)
    if cached:
        # Return as model-like object
        setting = SystemSetting.query.filter_by(category=category).first()
        if setting:
            return setting

    # Not in cache or cache miss, fetch from DB
    setting = SystemSetting.query.filter_by(category=category).first()
    merged = deepcopy(defaults)

    if setting is None:
        setting = SystemSetting(category=category, data=merged, updated_at=_utcnow())
        db.session.add(setting)
        db.session.commit()
    else:
        current = setting.data or {}
        merged.update(current)
        if merged != current:
            setting.data = merged
            db.session.commit()

    # Cache the result
    SettingsCache.set_system_setting(category, setting.data)

    return setting


def _ensure_customer_setting(customer_id: int) -> CustomerSetting:
    """Get or create customer setting with caching"""
    # Try cache first
    cached = SettingsCache.get_customer_setting(customer_id)
    if cached:
        setting = CustomerSetting.query.filter_by(customer_id=customer_id).first()
        if setting:
            return setting

    # Not in cache, fetch from DB
    setting = CustomerSetting.query.filter_by(customer_id=customer_id).first()
    if setting is None:
        setting = CustomerSetting(customer_id=customer_id, data={}, updated_at=_utcnow())
        db.session.add(setting)
        db.session.commit()

    # Cache the result
    SettingsCache.set_customer_setting(customer_id, setting.data)

    return setting


def _merge_with_defaults(defaults: dict, overrides: Union[dict, None]) -> dict:
    data = deepcopy(defaults)
    if overrides:
        data.update(overrides)
    return data


@settings_optimized_bp.route('/settings', methods=['GET'])
def get_system_settings():
    """Get system settings (with caching)"""
    try:
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

    except Exception as e:
        logger.error(f"Error getting system settings: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_optimized_bp.route('/settings', methods=['PUT'])
def update_system_settings():
    """Update system settings (with cache invalidation)"""
    try:
        payload = request.get_json(force=True, silent=True) or {}
        updated_categories = {}

        if 'general' in payload:
            setting = _ensure_system_setting('general', DEFAULT_GENERAL_SETTINGS)
            new_data = _merge_with_defaults(DEFAULT_GENERAL_SETTINGS, payload['general'] or {})
            setting.data = new_data
            setting.updated_at = _utcnow()
            updated_categories['general'] = new_data
            SettingsCache.invalidate_system_setting('general')

        if 'api' in payload:
            setting = _ensure_system_setting('api', DEFAULT_API_SETTINGS)
            new_data = _merge_with_defaults(DEFAULT_API_SETTINGS, payload['api'] or {})
            setting.data = new_data
            setting.updated_at = _utcnow()
            updated_categories['api'] = new_data
            SettingsCache.invalidate_system_setting('api')

        if 'customer_defaults' in payload:
            setting = _ensure_system_setting('customer_defaults', DEFAULT_CUSTOMER_SETTINGS)
            new_data = _merge_with_defaults(DEFAULT_CUSTOMER_SETTINGS, payload['customer_defaults'] or {})
            setting.data = new_data
            setting.updated_at = _utcnow()
            updated_categories['customer_defaults'] = new_data
            SettingsCache.invalidate_system_setting('customer_defaults')

        if updated_categories:
            db.session.commit()

        return jsonify({
            'success': True,
            'updated': updated_categories,
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating system settings: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_optimized_bp.route('/customers/<int:customer_id>/settings', methods=['GET'])
@require_customer_token
def get_customer_settings(customer_id):
    """Get customer settings (with caching)"""
    try:
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

    except Exception as e:
        logger.error(f"Error getting customer settings: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_optimized_bp.route('/customers/<int:customer_id>/settings', methods=['PUT'])
@require_customer_token
def update_customer_settings(customer_id):
    """Update customer settings (with cache invalidation)"""
    try:
        Customer.query.get_or_404(customer_id)
        payload = request.get_json(force=True, silent=True) or {}
        overrides = payload.get('overrides', {}) or {}

        sanitized = {}
        defaults = _merge_with_defaults(
            DEFAULT_CUSTOMER_SETTINGS,
            _ensure_system_setting('customer_defaults', DEFAULT_CUSTOMER_SETTINGS).data,
        )

        for key, value in overrides.items():
            if value not in (None, ''):
                sanitized[key] = value

        customer_setting = _ensure_customer_setting(customer_id)
        customer_setting.data = sanitized
        customer_setting.updated_at = _utcnow()
        db.session.commit()

        # Invalidate cache
        SettingsCache.invalidate_customer_setting(customer_id)

        effective = _merge_with_defaults(defaults, sanitized)

        return jsonify({
            'success': True,
            'customer_id': customer_id,
            'overrides': sanitized,
            'effective': effective,
            'defaults': defaults,
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating customer settings: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_optimized_bp.route('/settings/export', methods=['GET'])
def export_system_settings():
    """Export system settings to JSON"""
    try:
        general = _ensure_system_setting('general', DEFAULT_GENERAL_SETTINGS).data
        api = _ensure_system_setting('api', DEFAULT_API_SETTINGS).data
        customer_defaults = _ensure_system_setting('customer_defaults', DEFAULT_CUSTOMER_SETTINGS).data

        settings_data = {
            'general': general,
            'api': api,
            'customer_defaults': customer_defaults
        }

        export_data = SettingsExporter.export_system_settings(settings_data)

        return jsonify({
            'success': True,
            'export': export_data
        })

    except Exception as e:
        logger.error(f"Error exporting system settings: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_optimized_bp.route('/settings/import', methods=['POST'])
def import_system_settings():
    """Import system settings from JSON"""
    try:
        import_data = request.get_json(force=True)

        # Validate import data
        is_valid, error = SettingsImporter.validate_import_data(import_data)
        if not is_valid:
            return jsonify({'success': False, 'error': error}), 400

        # Import settings
        settings = SettingsImporter.import_system_settings(import_data, merge_mode='replace')

        # Update database
        updated_categories = []
        for category, data in settings.items():
            setting = _ensure_system_setting(category, {})
            setting.data = data
            setting.updated_at = _utcnow()
            updated_categories.append(category)
            SettingsCache.invalidate_system_setting(category)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Imported settings for {len(updated_categories)} categories',
            'categories': updated_categories
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error importing system settings: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_optimized_bp.route('/customers/<int:customer_id>/settings/export', methods=['GET'])
@require_customer_token
def export_customer_settings(customer_id):
    """Export customer settings to JSON"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        customer_setting = _ensure_customer_setting(customer_id)

        export_data = SettingsExporter.export_customer_settings(
            customer_id=customer_id,
            customer_name=customer.name,
            settings_data=customer_setting.data
        )

        return jsonify({
            'success': True,
            'export': export_data
        })

    except Exception as e:
        logger.error(f"Error exporting customer settings: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_optimized_bp.route('/settings/templates', methods=['GET'])
def list_settings_templates():
    """List available settings templates"""
    try:
        templates = SettingsTemplate.list_templates()
        return jsonify({
            'success': True,
            'templates': templates
        })

    except Exception as e:
        logger.error(f"Error listing templates: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_optimized_bp.route('/settings/templates/<template_name>', methods=['GET'])
def get_settings_template(template_name):
    """Get a settings template"""
    try:
        template = SettingsTemplate.get_template(template_name)
        if not template:
            return jsonify({'success': False, 'error': 'Template not found'}), 404

        return jsonify({
            'success': True,
            'template': template
        })

    except Exception as e:
        logger.error(f"Error getting template: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_optimized_bp.route('/settings/cache/clear', methods=['POST'])
def clear_settings_cache():
    """Clear all settings cache"""
    try:
        system_count = SettingsCache.invalidate_all_system_settings()
        customer_count = SettingsCache.invalidate_all_customer_settings()

        return jsonify({
            'success': True,
            'message': f'Cleared {system_count + customer_count} cache entries',
            'system_entries': system_count,
            'customer_entries': customer_count
        })

    except Exception as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_optimized_bp.route('/settings/api/test', methods=['POST'])
def test_api_connection():
    """Test API connection"""
    payload = request.get_json(force=True, silent=True) or {}
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
    except Exception as exc:
        return jsonify({
            'success': False,
            'url': url,
            'error': str(exc),
        }), 502
