"""
Settings Import/Export Functionality

Provides utilities to export and import settings data for:
- Backup and restore
- Environment migration (dev -> staging -> prod)
- Settings templates and presets

Author: Database Optimizer Agent
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class SettingsExporter:
    """Export settings to various formats"""

    @staticmethod
    def export_system_settings(settings_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Export system settings to JSON-serializable format

        Args:
            settings_data: Dictionary of system settings by category

        Returns:
            Exportable settings dictionary with metadata
        """
        export_data = {
            'export_type': 'system_settings',
            'export_version': '1.0',
            'exported_at': datetime.utcnow().isoformat(),
            'settings': settings_data
        }

        logger.info("Exported system settings")
        return export_data

    @staticmethod
    def export_customer_settings(
        customer_id: int,
        customer_name: str,
        settings_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Export customer settings to JSON-serializable format

        Args:
            customer_id: Customer ID
            customer_name: Customer name
            settings_data: Customer settings data

        Returns:
            Exportable settings dictionary with metadata
        """
        export_data = {
            'export_type': 'customer_settings',
            'export_version': '1.0',
            'exported_at': datetime.utcnow().isoformat(),
            'customer_id': customer_id,
            'customer_name': customer_name,
            'settings': settings_data
        }

        logger.info(f"Exported settings for customer {customer_id}")
        return export_data

    @staticmethod
    def export_all_customer_settings(customers_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Export all customer settings to JSON-serializable format

        Args:
            customers_data: List of customer settings dictionaries

        Returns:
            Exportable settings dictionary with metadata
        """
        export_data = {
            'export_type': 'all_customer_settings',
            'export_version': '1.0',
            'exported_at': datetime.utcnow().isoformat(),
            'total_customers': len(customers_data),
            'customers': customers_data
        }

        logger.info(f"Exported settings for {len(customers_data)} customers")
        return export_data

    @staticmethod
    def save_to_file(export_data: Dict[str, Any], file_path: str) -> bool:
        """
        Save exported settings to a JSON file

        Args:
            export_data: Exported settings data
            file_path: Path to save the file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            # Write JSON file
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2, sort_keys=True)

            logger.info(f"Settings saved to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save settings to {file_path}: {e}")
            return False


class SettingsImporter:
    """Import settings from various formats"""

    @staticmethod
    def validate_import_data(import_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate imported settings data

        Args:
            import_data: Imported settings dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        if 'export_type' not in import_data:
            return False, "Missing 'export_type' field"

        if 'export_version' not in import_data:
            return False, "Missing 'export_version' field"

        if 'settings' not in import_data and 'customers' not in import_data:
            return False, "Missing 'settings' or 'customers' field"

        # Check version compatibility
        supported_versions = ['1.0']
        if import_data['export_version'] not in supported_versions:
            return False, f"Unsupported export version: {import_data['export_version']}"

        # Validate export type
        valid_types = ['system_settings', 'customer_settings', 'all_customer_settings']
        if import_data['export_type'] not in valid_types:
            return False, f"Invalid export type: {import_data['export_type']}"

        return True, None

    @staticmethod
    def load_from_file(file_path: str) -> Optional[Dict[str, Any]]:
        """
        Load settings from a JSON file

        Args:
            file_path: Path to the JSON file

        Returns:
            Loaded settings dictionary or None if failed
        """
        try:
            with open(file_path, 'r') as f:
                import_data = json.load(f)

            # Validate data
            is_valid, error = SettingsImporter.validate_import_data(import_data)
            if not is_valid:
                logger.error(f"Invalid import data: {error}")
                return None

            logger.info(f"Settings loaded from {file_path}")
            return import_data

        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load settings from {file_path}: {e}")
            return None

    @staticmethod
    def import_system_settings(
        import_data: Dict[str, Any],
        merge_mode: str = 'replace'
    ) -> Dict[str, Any]:
        """
        Prepare system settings for import

        Args:
            import_data: Imported settings data
            merge_mode: 'replace' to overwrite, 'merge' to update existing

        Returns:
            Dictionary of settings ready for database update
        """
        if import_data.get('export_type') != 'system_settings':
            raise ValueError("Import data is not system settings")

        settings = import_data.get('settings', {})

        if merge_mode == 'replace':
            return settings
        elif merge_mode == 'merge':
            # For merge mode, the caller should merge with existing settings
            return settings
        else:
            raise ValueError(f"Invalid merge mode: {merge_mode}")

    @staticmethod
    def import_customer_settings(
        import_data: Dict[str, Any],
        merge_mode: str = 'replace'
    ) -> Dict[str, Any]:
        """
        Prepare customer settings for import

        Args:
            import_data: Imported settings data
            merge_mode: 'replace' to overwrite, 'merge' to update existing

        Returns:
            Dictionary with customer settings data
        """
        if import_data.get('export_type') != 'customer_settings':
            raise ValueError("Import data is not customer settings")

        result = {
            'customer_id': import_data.get('customer_id'),
            'customer_name': import_data.get('customer_name'),
            'settings': import_data.get('settings', {}),
            'merge_mode': merge_mode
        }

        return result


class SettingsBackup:
    """Automated settings backup functionality"""

    def __init__(self, backup_dir: str):
        """
        Initialize settings backup manager

        Args:
            backup_dir: Directory to store backups
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self,
        settings_data: Dict[str, Any],
        backup_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a backup of settings

        Args:
            settings_data: Settings data to backup
            backup_name: Optional custom backup name

        Returns:
            Path to backup file or None if failed
        """
        try:
            # Generate backup filename
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            if backup_name:
                filename = f"{backup_name}_{timestamp}.json"
            else:
                export_type = settings_data.get('export_type', 'settings')
                filename = f"backup_{export_type}_{timestamp}.json"

            file_path = self.backup_dir / filename

            # Save backup
            if SettingsExporter.save_to_file(settings_data, str(file_path)):
                logger.info(f"Backup created: {file_path}")
                return str(file_path)

            return None

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None

    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups

        Returns:
            List of backup information dictionaries
        """
        backups = []

        try:
            for backup_file in sorted(self.backup_dir.glob('*.json'), reverse=True):
                stat = backup_file.stat()
                backups.append({
                    'filename': backup_file.name,
                    'path': str(backup_file),
                    'size_bytes': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

        except Exception as e:
            logger.error(f"Failed to list backups: {e}")

        return backups

    def restore_backup(self, backup_path: str) -> Optional[Dict[str, Any]]:
        """
        Restore settings from a backup

        Args:
            backup_path: Path to backup file

        Returns:
            Restored settings data or None if failed
        """
        return SettingsImporter.load_from_file(backup_path)

    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """
        Remove old backups, keeping only the most recent ones

        Args:
            keep_count: Number of recent backups to keep

        Returns:
            Number of backups deleted
        """
        try:
            backups = sorted(self.backup_dir.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)

            deleted = 0
            for backup in backups[keep_count:]:
                backup.unlink()
                deleted += 1
                logger.info(f"Deleted old backup: {backup.name}")

            return deleted

        except Exception as e:
            logger.error(f"Failed to cleanup backups: {e}")
            return 0


class SettingsTemplate:
    """Settings template management for different environments"""

    TEMPLATES = {
        'development': {
            'general': {
                'maxFileSize': 16,
                'enableNotifications': True,
                'enableAuditLog': True,
                'sessionTimeout': 120,
                'theme': 'system'
            },
            'api': {
                'apiBaseUrl': 'http://localhost:5000/api',
                'timeout': 30,
                'verifySsl': False,
                'pollInterval': 60
            }
        },
        'production': {
            'general': {
                'maxFileSize': 50,
                'enableNotifications': True,
                'enableAuditLog': True,
                'sessionTimeout': 60,
                'theme': 'light'
            },
            'api': {
                'apiBaseUrl': 'https://api.example.com/api',
                'timeout': 15,
                'verifySsl': True,
                'pollInterval': 300
            }
        },
        'testing': {
            'general': {
                'maxFileSize': 5,
                'enableNotifications': False,
                'enableAuditLog': False,
                'sessionTimeout': 30,
                'theme': 'system'
            },
            'api': {
                'apiBaseUrl': 'http://localhost:5000/api',
                'timeout': 10,
                'verifySsl': False,
                'pollInterval': 30
            }
        }
    }

    @classmethod
    def get_template(cls, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a settings template by name

        Args:
            template_name: Template name (development, production, testing)

        Returns:
            Template settings dictionary or None if not found
        """
        return cls.TEMPLATES.get(template_name)

    @classmethod
    def list_templates(cls) -> List[str]:
        """Get list of available template names"""
        return list(cls.TEMPLATES.keys())
