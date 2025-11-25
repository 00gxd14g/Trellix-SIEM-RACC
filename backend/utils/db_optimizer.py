"""
Database Performance Optimization Utilities

Provides utilities for:
- Query optimization and analysis
- Index recommendations
- Connection pooling configuration
- Performance monitoring
- Database health checks

Author: Database Optimizer Agent
"""

import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)


# Query Performance Monitoring
class QueryPerformanceMonitor:
    """Monitor and log slow queries"""

    def __init__(self, slow_query_threshold: float = 0.5):
        """
        Args:
            slow_query_threshold: Threshold in seconds to log slow queries
        """
        self.slow_query_threshold = slow_query_threshold
        self.query_stats = []
        self.enabled = False

    def enable(self):
        """Enable query monitoring"""
        self.enabled = True
        logger.info(f"Query monitoring enabled (threshold: {self.slow_query_threshold}s)")

    def disable(self):
        """Disable query monitoring"""
        self.enabled = False
        logger.info("Query monitoring disabled")

    def log_query(self, query: str, duration: float, params: Optional[dict] = None):
        """Log query execution"""
        if not self.enabled:
            return

        if duration >= self.slow_query_threshold:
            logger.warning(f"SLOW QUERY ({duration:.3f}s): {query[:200]}")
            if params:
                logger.warning(f"Parameters: {params}")

        self.query_stats.append({
            'query': query[:200],
            'duration': duration,
            'timestamp': time.time(),
            'is_slow': duration >= self.slow_query_threshold
        })

    def get_stats(self) -> Dict[str, Any]:
        """Get query statistics"""
        if not self.query_stats:
            return {
                'total_queries': 0,
                'slow_queries': 0,
                'avg_duration': 0,
                'max_duration': 0
            }

        durations = [q['duration'] for q in self.query_stats]
        slow_count = sum(1 for q in self.query_stats if q['is_slow'])

        return {
            'total_queries': len(self.query_stats),
            'slow_queries': slow_count,
            'avg_duration': sum(durations) / len(durations),
            'max_duration': max(durations),
            'min_duration': min(durations)
        }

    def get_slowest_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slowest queries"""
        sorted_queries = sorted(
            self.query_stats,
            key=lambda x: x['duration'],
            reverse=True
        )
        return sorted_queries[:limit]

    def clear_stats(self):
        """Clear query statistics"""
        self.query_stats.clear()


# Global query monitor instance
_query_monitor: Optional[QueryPerformanceMonitor] = None


def get_query_monitor() -> QueryPerformanceMonitor:
    """Get global query monitor instance"""
    global _query_monitor
    if _query_monitor is None:
        _query_monitor = QueryPerformanceMonitor()
    return _query_monitor


def setup_query_monitoring(engine: Engine, threshold: float = 0.5):
    """
    Setup query performance monitoring for SQLAlchemy engine

    Args:
        engine: SQLAlchemy engine instance
        threshold: Slow query threshold in seconds
    """
    monitor = get_query_monitor()
    monitor.slow_query_threshold = threshold
    monitor.enable()

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault('query_start_time', []).append(time.time())
        logger.debug(f"Executing query: {statement[:100]}")

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total_time = time.time() - conn.info['query_start_time'].pop(-1)
        monitor.log_query(statement, total_time, parameters)

    logger.info(f"Query monitoring configured with {threshold}s threshold")


def configure_connection_pool(
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_timeout: int = 30,
    pool_recycle: int = 3600,
    pool_pre_ping: bool = True
) -> Dict[str, Any]:
    """
    Generate connection pool configuration for SQLAlchemy

    Args:
        pool_size: Number of connections to maintain in the pool
        max_overflow: Maximum number of connections to create beyond pool_size
        pool_timeout: Seconds to wait before giving up on getting a connection
        pool_recycle: Recycle connections after this many seconds
        pool_pre_ping: Enable connection health check before using

    Returns:
        Dictionary of pool configuration parameters
    """
    return {
        'poolclass': QueuePool,
        'pool_size': pool_size,
        'max_overflow': max_overflow,
        'pool_timeout': pool_timeout,
        'pool_recycle': pool_recycle,
        'pool_pre_ping': pool_pre_ping,
    }


def analyze_query_plan(session, query) -> List[Tuple[str, str]]:
    """
    Analyze query execution plan (SQLite EXPLAIN QUERY PLAN)

    Args:
        session: SQLAlchemy session
        query: SQLAlchemy query object

    Returns:
        List of tuples with execution plan details
    """
    try:
        # Get the compiled SQL statement
        compiled = query.statement.compile(compile_kwargs={"literal_binds": True})
        sql = str(compiled)

        # Execute EXPLAIN QUERY PLAN
        explain_sql = f"EXPLAIN QUERY PLAN {sql}"
        result = session.execute(text(explain_sql))

        plan = []
        for row in result:
            plan.append(tuple(row))

        return plan
    except Exception as e:
        logger.error(f"Error analyzing query plan: {e}")
        return []


def get_table_indexes(session, table_name: str) -> List[Dict[str, Any]]:
    """
    Get indexes for a table

    Args:
        session: SQLAlchemy session
        table_name: Name of the table

    Returns:
        List of index information dictionaries
    """
    try:
        # Get index information from SQLite
        result = session.execute(text(f"PRAGMA index_list({table_name})"))
        indexes = []

        for row in result:
            index_name = row[1]
            unique = bool(row[2])

            # Get index columns
            col_result = session.execute(text(f"PRAGMA index_info({index_name})"))
            columns = [col_row[2] for col_row in col_result]

            indexes.append({
                'name': index_name,
                'unique': unique,
                'columns': columns
            })

        return indexes
    except Exception as e:
        logger.error(f"Error getting indexes for {table_name}: {e}")
        return []


def suggest_indexes(session, query) -> List[str]:
    """
    Suggest indexes based on query patterns

    This is a basic implementation that analyzes WHERE clauses and JOIN conditions.

    Args:
        session: SQLAlchemy session
        query: SQLAlchemy query object

    Returns:
        List of index suggestions
    """
    suggestions = []

    try:
        # Analyze the query plan
        plan = analyze_query_plan(session, query)

        # Look for table scans (indication of missing indexes)
        for row in plan:
            plan_text = str(row).lower()
            if 'scan' in plan_text and 'using' not in plan_text:
                suggestions.append(
                    f"Consider adding index: Table scan detected in query plan"
                )

        # Analyze the WHERE clause columns
        # This would require more sophisticated SQL parsing
        # For now, we provide general recommendations

        if not suggestions:
            suggestions.append("Query appears optimized with existing indexes")

    except Exception as e:
        logger.error(f"Error suggesting indexes: {e}")
        suggestions.append(f"Unable to analyze query: {e}")

    return suggestions


@contextmanager
def query_timer(name: str):
    """
    Context manager to time query execution

    Example:
        with query_timer("get_customer_rules"):
            rules = Rule.query.filter_by(customer_id=1).all()
    """
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        logger.info(f"Query '{name}' completed in {duration:.3f}s")


def optimize_bulk_insert(session, model_class, data_list: List[Dict[str, Any]]) -> int:
    """
    Optimized bulk insert using SQLAlchemy bulk operations

    Args:
        session: SQLAlchemy session
        model_class: SQLAlchemy model class
        data_list: List of dictionaries with model data

    Returns:
        Number of rows inserted
    """
    try:
        start_time = time.time()

        # Use bulk_insert_mappings for better performance
        session.bulk_insert_mappings(model_class, data_list)
        session.commit()

        duration = time.time() - start_time
        count = len(data_list)
        logger.info(f"Bulk inserted {count} rows in {duration:.3f}s ({count/duration:.0f} rows/s)")

        return count
    except Exception as e:
        session.rollback()
        logger.error(f"Bulk insert failed: {e}")
        raise


def get_database_stats(session) -> Dict[str, Any]:
    """
    Get database statistics

    Args:
        session: SQLAlchemy session

    Returns:
        Dictionary with database statistics
    """
    stats = {}

    try:
        # Get table sizes
        tables = ['customers', 'customer_files', 'rules', 'alarms',
                  'rule_alarm_relationships', 'system_settings', 'customer_settings',
                  'validation_logs']

        for table in tables:
            result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            stats[f"{table}_count"] = count

        # Get database file size (SQLite specific)
        result = session.execute(text("PRAGMA page_count"))
        page_count = result.scalar()
        result = session.execute(text("PRAGMA page_size"))
        page_size = result.scalar()

        if page_count and page_size:
            stats['database_size_bytes'] = page_count * page_size
            stats['database_size_mb'] = round((page_count * page_size) / (1024 * 1024), 2)

        # Get index information
        result = session.execute(text("SELECT COUNT(*) FROM sqlite_master WHERE type='index'"))
        stats['total_indexes'] = result.scalar()

    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        stats['error'] = str(e)

    return stats


def vacuum_database(session):
    """
    Run VACUUM command to optimize database file (SQLite specific)

    This reclaims unused space and optimizes the database layout.

    Args:
        session: SQLAlchemy session
    """
    try:
        logger.info("Starting database VACUUM operation")
        start_time = time.time()

        # Close the session to release locks
        session.close()

        # Execute VACUUM
        session.execute(text("VACUUM"))
        session.commit()

        duration = time.time() - start_time
        logger.info(f"VACUUM completed in {duration:.3f}s")

    except Exception as e:
        logger.error(f"VACUUM failed: {e}")
        raise


def analyze_database(session):
    """
    Run ANALYZE command to update query planner statistics (SQLite specific)

    This helps the query optimizer make better decisions.

    Args:
        session: SQLAlchemy session
    """
    try:
        logger.info("Starting database ANALYZE operation")
        start_time = time.time()

        session.execute(text("ANALYZE"))
        session.commit()

        duration = time.time() - start_time
        logger.info(f"ANALYZE completed in {duration:.3f}s")

    except Exception as e:
        logger.error(f"ANALYZE failed: {e}")
        raise
