-- Migration: Create Settings Tables
-- Created: 2025-11-11
-- Description: Creates system_settings and customer_settings tables for configuration management

-- Create system_settings table
CREATE TABLE IF NOT EXISTS system_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category VARCHAR(64) UNIQUE NOT NULL,
    data JSON NOT NULL DEFAULT '{}',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (json_valid(data))
);

-- Create index for category lookups
CREATE INDEX IF NOT EXISTS idx_system_settings_category ON system_settings(category);
CREATE INDEX IF NOT EXISTS idx_system_settings_updated_at ON system_settings(updated_at);

-- Create customer_settings table
CREATE TABLE IF NOT EXISTS customer_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL UNIQUE,
    data JSON NOT NULL DEFAULT '{}',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    CHECK (json_valid(data))
);

-- Create indexes for customer settings
CREATE INDEX IF NOT EXISTS idx_customer_settings_customer_id ON customer_settings(customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_settings_updated_at ON customer_settings(updated_at);

-- Create audit_logs table for security tracking
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    customer_id INTEGER,
    user_id VARCHAR(128),
    ip_address VARCHAR(45),
    action VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64),
    entity_id INTEGER,
    old_value JSON,
    new_value JSON,
    status VARCHAR(20) DEFAULT 'success',
    error_message TEXT,
    metadata JSON,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL,
    CHECK (json_valid(old_value) OR old_value IS NULL),
    CHECK (json_valid(new_value) OR new_value IS NULL),
    CHECK (json_valid(metadata) OR metadata IS NULL)
);

-- Create indexes for audit logs
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_customer_id ON audit_logs(customer_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_status ON audit_logs(status);

-- Insert default system settings
INSERT OR IGNORE INTO system_settings (category, data) VALUES
    ('general', '{"appName": "Trellix SIEM Alarm Editor", "maxFileSize": 16, "defaultPageSize": 50, "enableNotifications": true, "backupEnabled": true, "backupFrequency": "daily", "enableAuditLog": true, "sessionTimeout": 60, "theme": "system"}'),
    ('api', '{"apiBaseUrl": "http://localhost:5000/api", "healthEndpoint": "/health", "apiKey": "", "authHeader": "Authorization", "timeout": 15, "verifySsl": false, "pollInterval": 60}'),
    ('customer_defaults', '{"defaultSeverity": "Low", "throttle": 300, "eventThrottle": 20, "matchField": "msg", "autoGenerateAlarms": false, "enableValidation": true, "preserveOriginalFile": true, "emailNotifications": false, "apiIntegration": false}');

-- Add migration version tracking
CREATE TABLE IF NOT EXISTS migration_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checksum VARCHAR(64)
);

INSERT OR IGNORE INTO migration_versions (version, description, checksum)
VALUES ('001_create_settings_tables', 'Create system_settings, customer_settings, and audit_logs tables', 'sha256:a1b2c3d4e5f6');