-- Migration: 001_add_performance_indexes
-- Description: Add optimized indexes for frequently queried columns
-- Author: Database Optimizer Agent
-- Date: 2025-01-11

-- ============================================================
-- UPGRADE: Add Performance Indexes
-- ============================================================

-- Index for customer name lookups (case-insensitive searches)
CREATE INDEX IF NOT EXISTS idx_customers_name_lower ON customers (LOWER(name));

-- Index for customer email lookups
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers (contact_email);

-- Composite index for customer files by type and upload date (for filtering and sorting)
CREATE INDEX IF NOT EXISTS idx_customer_files_type_date ON customer_files (customer_id, file_type, upload_date DESC);

-- Index for file validation status (for filtering by status)
CREATE INDEX IF NOT EXISTS idx_customer_files_validation ON customer_files (customer_id, validation_status);

-- Composite index for rules by severity (for filtering high-severity rules)
CREATE INDEX IF NOT EXISTS idx_rules_customer_severity ON rules (customer_id, severity DESC);

-- Index for rule sig_id lookups (for relationship matching)
CREATE INDEX IF NOT EXISTS idx_rules_sig_id ON rules (sig_id) WHERE sig_id IS NOT NULL;

-- Index for rule name searches
CREATE INDEX IF NOT EXISTS idx_rules_name ON rules (name);

-- Composite index for alarms by severity
CREATE INDEX IF NOT EXISTS idx_alarms_customer_severity ON alarms (customer_id, severity DESC);

-- Index for alarm match_value lookups (for rule-alarm matching)
CREATE INDEX IF NOT EXISTS idx_alarms_match_value ON alarms (match_value);

-- Index for alarm match_field (for filtering by field type)
CREATE INDEX IF NOT EXISTS idx_alarms_match_field ON alarms (customer_id, match_field);

-- Composite index for alarm updated_at (for sorting by last update)
CREATE INDEX IF NOT EXISTS idx_alarms_updated ON alarms (customer_id, updated_at DESC);

-- Composite index for rule-alarm relationships by sig_id
CREATE INDEX IF NOT EXISTS idx_relationships_sig_id ON rule_alarm_relationships (customer_id, sig_id);

-- Composite index for rule-alarm relationships by match_value
CREATE INDEX IF NOT EXISTS idx_relationships_match_value ON rule_alarm_relationships (customer_id, match_value);

-- Index for relationship type filtering
CREATE INDEX IF NOT EXISTS idx_relationships_type ON rule_alarm_relationships (customer_id, relationship_type);

-- Composite index for validation logs by customer and status
CREATE INDEX IF NOT EXISTS idx_validation_logs_status ON validation_logs (customer_id, status, created_at DESC);

-- Composite index for validation logs by type and date
CREATE INDEX IF NOT EXISTS idx_validation_logs_type_date ON validation_logs (customer_id, file_type, created_at DESC);

-- Index for system settings category (already unique, but explicit for query planner)
-- No need to create - already covered by UNIQUE constraint

-- Composite index for customer settings lookup (already unique)
-- No need to create - already covered by UNIQUE constraint

-- ============================================================
-- DOWNGRADE: Remove Performance Indexes
-- ============================================================

-- To rollback, uncomment and execute these DROP INDEX statements:

/*
DROP INDEX IF EXISTS idx_customers_name_lower;
DROP INDEX IF EXISTS idx_customers_email;
DROP INDEX IF EXISTS idx_customer_files_type_date;
DROP INDEX IF EXISTS idx_customer_files_validation;
DROP INDEX IF EXISTS idx_rules_customer_severity;
DROP INDEX IF EXISTS idx_rules_sig_id;
DROP INDEX IF EXISTS idx_rules_name;
DROP INDEX IF EXISTS idx_alarms_customer_severity;
DROP INDEX IF EXISTS idx_alarms_match_value;
DROP INDEX IF EXISTS idx_alarms_match_field;
DROP INDEX IF EXISTS idx_alarms_updated;
DROP INDEX IF EXISTS idx_relationships_sig_id;
DROP INDEX IF EXISTS idx_relationships_match_value;
DROP INDEX IF EXISTS idx_relationships_type;
DROP INDEX IF EXISTS idx_validation_logs_status;
DROP INDEX IF EXISTS idx_validation_logs_type_date;
*/

-- ============================================================
-- VERIFICATION QUERIES
-- ============================================================

-- Verify indexes were created successfully:
-- SELECT name, tbl_name FROM sqlite_master WHERE type='index' ORDER BY name;

-- Check index usage with EXPLAIN QUERY PLAN:
-- EXPLAIN QUERY PLAN SELECT * FROM rules WHERE customer_id = 1 AND severity >= 50;
