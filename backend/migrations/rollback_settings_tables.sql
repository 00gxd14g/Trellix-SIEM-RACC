-- Rollback Migration: Drop Settings Tables
-- Created: 2025-11-11
-- Description: Rollback script for settings tables migration

-- Drop indexes first
DROP INDEX IF EXISTS idx_audit_logs_status;
DROP INDEX IF EXISTS idx_audit_logs_entity;
DROP INDEX IF EXISTS idx_audit_logs_action;
DROP INDEX IF EXISTS idx_audit_logs_customer_id;
DROP INDEX IF EXISTS idx_audit_logs_timestamp;

DROP INDEX IF EXISTS idx_customer_settings_updated_at;
DROP INDEX IF EXISTS idx_customer_settings_customer_id;

DROP INDEX IF EXISTS idx_system_settings_updated_at;
DROP INDEX IF EXISTS idx_system_settings_category;

-- Drop tables
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS customer_settings;
DROP TABLE IF EXISTS system_settings;

-- Remove migration version
DELETE FROM migration_versions WHERE version = '001_create_settings_tables';