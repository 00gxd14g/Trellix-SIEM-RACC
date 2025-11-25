-- Migration: 002_add_settings_indexes
-- Description: Add indexes for settings tables to improve lookup performance
-- Author: Database Optimizer Agent
-- Date: 2025-01-11

-- ============================================================
-- UPGRADE: Add Settings Table Indexes
-- ============================================================

-- Index for system_settings updated_at (for cache invalidation checks)
CREATE INDEX IF NOT EXISTS idx_system_settings_updated ON system_settings (updated_at DESC);

-- Index for customer_settings updated_at (for cache invalidation checks)
CREATE INDEX IF NOT EXISTS idx_customer_settings_updated ON customer_settings (updated_at DESC);

-- Index for customer_settings foreign key (for joins with customers table)
CREATE INDEX IF NOT EXISTS idx_customer_settings_customer_id ON customer_settings (customer_id);

-- ============================================================
-- ANALYZE TABLES FOR QUERY PLANNER
-- ============================================================

-- Update statistics for query planner optimization
ANALYZE system_settings;
ANALYZE customer_settings;

-- ============================================================
-- DOWNGRADE: Remove Settings Indexes
-- ============================================================

-- To rollback, uncomment and execute these DROP INDEX statements:

/*
DROP INDEX IF EXISTS idx_system_settings_updated;
DROP INDEX IF EXISTS idx_customer_settings_updated;
DROP INDEX IF EXISTS idx_customer_settings_customer_id;
*/

-- ============================================================
-- VERIFICATION QUERIES
-- ============================================================

-- Verify indexes were created:
-- SELECT name FROM sqlite_master WHERE type='index' AND tbl_name IN ('system_settings', 'customer_settings');

-- Test query performance:
-- EXPLAIN QUERY PLAN SELECT * FROM customer_settings WHERE customer_id = 1;
-- EXPLAIN QUERY PLAN SELECT * FROM system_settings WHERE category = 'general';
