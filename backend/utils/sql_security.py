"""
SQL injection prevention utilities and safe query helpers.

Provides wrapper functions and validators to ensure all database
operations use parameterized queries and proper escaping.
"""

import logging
import re
from functools import wraps
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app

logger = logging.getLogger(__name__)


class SQLInjectionError(Exception):
    """Exception raised when potential SQL injection is detected."""
    pass


def detect_sql_injection_patterns(value):
    """
    Detect common SQL injection patterns in input strings.

    Args:
        value: String to check for SQL injection patterns

    Returns:
        tuple: (is_suspicious, pattern_found)

    This is a defense-in-depth measure. The primary defense is
    parameterized queries, but this catches obvious attack attempts.
    """
    if not isinstance(value, str):
        return False, None

    # Common SQL injection patterns
    patterns = [
        (r"(\bUNION\b.*\bSELECT\b)", "UNION SELECT"),
        (r"(\bSELECT\b.*\bFROM\b.*\bWHERE\b)", "SELECT FROM WHERE"),
        (r";\s*DROP\s+TABLE", "DROP TABLE"),
        (r";\s*DELETE\s+FROM", "DELETE FROM"),
        (r";\s*UPDATE\s+.*\bSET\b", "UPDATE SET"),
        (r";\s*INSERT\s+INTO", "INSERT INTO"),
        (r"'.*OR.*'.*=.*'", "OR condition bypass"),
        (r"1\s*=\s*1", "Always true condition"),
        (r"--.*$", "SQL comment"),
        (r"/\*.*\*/", "Block comment"),
        (r"\bEXEC\b.*\(", "EXEC function"),
        (r"\bEXECUTE\b.*\(", "EXECUTE function"),
        (r"xp_cmdshell", "Command execution"),
        (r"\bCAST\b.*\bAS\b", "Type casting"),
        (r"CHAR\s*\(\s*\d+\s*\)", "CHAR encoding"),
    ]

    value_upper = value.upper()

    for pattern, description in patterns:
        if re.search(pattern, value_upper, re.IGNORECASE):
            return True, description

    return False, None


def validate_column_name(column_name, allowed_columns=None):
    """
    Validate that a column name is safe for use in queries.

    Args:
        column_name: Column name to validate
        allowed_columns: Optional list of explicitly allowed column names

    Returns:
        str: Validated column name

    Raises:
        SQLInjectionError: If column name is invalid or suspicious
    """
    if not column_name:
        raise SQLInjectionError("Column name cannot be empty")

    # Check against allowlist if provided
    if allowed_columns and column_name not in allowed_columns:
        raise SQLInjectionError(
            f"Column '{column_name}' not in allowed list: {allowed_columns}"
        )

    # Column names should only contain alphanumeric characters and underscores
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', column_name):
        raise SQLInjectionError(
            f"Invalid column name format: '{column_name}'. "
            "Only alphanumeric characters and underscores are allowed."
        )

    # Check for SQL keywords (basic check)
    sql_keywords = [
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
        'EXEC', 'EXECUTE', 'UNION', 'WHERE', 'FROM', 'JOIN'
    ]

    if column_name.upper() in sql_keywords:
        raise SQLInjectionError(
            f"Column name '{column_name}' conflicts with SQL keyword"
        )

    return column_name


def validate_table_name(table_name, allowed_tables=None):
    """
    Validate that a table name is safe for use in queries.

    Args:
        table_name: Table name to validate
        allowed_tables: Optional list of explicitly allowed table names

    Returns:
        str: Validated table name

    Raises:
        SQLInjectionError: If table name is invalid or suspicious
    """
    if not table_name:
        raise SQLInjectionError("Table name cannot be empty")

    # Check against allowlist if provided
    if allowed_tables and table_name not in allowed_tables:
        raise SQLInjectionError(
            f"Table '{table_name}' not in allowed list: {allowed_tables}"
        )

    # Table names should only contain alphanumeric characters and underscores
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
        raise SQLInjectionError(
            f"Invalid table name format: '{table_name}'. "
            "Only alphanumeric characters and underscores are allowed."
        )

    return table_name


def safe_like_pattern(pattern):
    """
    Escape special characters in LIKE patterns to prevent injection.

    Args:
        pattern: User-provided pattern for LIKE query

    Returns:
        str: Escaped pattern safe for use in LIKE clause

    Example:
        safe_like_pattern("test%") -> "test\\%"
    """
    if not isinstance(pattern, str):
        return pattern

    # Escape special LIKE characters
    escaped = pattern.replace('\\', '\\\\')  # Escape backslash first
    escaped = escaped.replace('%', '\\%')    # Escape wildcard
    escaped = escaped.replace('_', '\\_')    # Escape single-char wildcard

    return escaped


def validate_order_by(order_by, allowed_columns):
    """
    Validate ORDER BY clause to prevent SQL injection.

    Args:
        order_by: Order by clause (e.g., "name ASC" or "created_at DESC")
        allowed_columns: List of allowed column names

    Returns:
        tuple: (column_name, direction)

    Raises:
        SQLInjectionError: If order by clause is invalid
    """
    if not order_by:
        raise SQLInjectionError("Order by clause cannot be empty")

    # Parse order by clause
    parts = order_by.strip().split()

    if len(parts) == 0:
        raise SQLInjectionError("Invalid order by clause")

    column_name = parts[0]

    # Validate column name
    validate_column_name(column_name, allowed_columns)

    # Validate direction if provided
    direction = 'ASC'  # Default
    if len(parts) > 1:
        direction = parts[1].upper()
        if direction not in ['ASC', 'DESC']:
            raise SQLInjectionError(
                f"Invalid sort direction: {direction}. Must be ASC or DESC."
            )

    return column_name, direction


def safe_pagination(page, per_page, max_per_page=1000):
    """
    Validate and sanitize pagination parameters.

    Args:
        page: Page number (1-indexed)
        per_page: Items per page
        max_per_page: Maximum allowed items per page

    Returns:
        tuple: (validated_page, validated_per_page, offset)

    Raises:
        ValueError: If pagination parameters are invalid
    """
    try:
        page = int(page) if page else 1
        per_page = int(per_page) if per_page else 50
    except (ValueError, TypeError):
        raise ValueError("Page and per_page must be valid integers")

    # Validate ranges
    if page < 1:
        raise ValueError("Page must be >= 1")

    if per_page < 1:
        raise ValueError("Per page must be >= 1")

    if per_page > max_per_page:
        raise ValueError(f"Per page cannot exceed {max_per_page}")

    # Calculate offset
    offset = (page - 1) * per_page

    return page, per_page, offset


def log_suspicious_query_attempt(user_input, detected_pattern, endpoint=None):
    """
    Log attempts to inject SQL for security monitoring.

    Args:
        user_input: The suspicious user input
        detected_pattern: The SQL pattern that was detected
        endpoint: API endpoint where the attempt occurred
    """
    logger.warning(
        f"Potential SQL injection attempt detected: "
        f"Pattern='{detected_pattern}', "
        f"Input='{user_input[:100]}...', "
        f"Endpoint={endpoint}"
    )


def require_parameterized_query(f):
    """
    Decorator to ensure a function only uses parameterized queries.

    This decorator doesn't enforce at runtime but serves as documentation
    and can be extended with runtime checks in development.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_app.debug:
            logger.debug(f"Executing parameterized query function: {f.__name__}")

        return f(*args, **kwargs)

    return decorated_function


# Safe query builder helpers
class SafeQueryBuilder:
    """
    Helper class for building safe SQL queries with validation.

    This class ensures all user inputs are properly parameterized
    and validated before being used in queries.
    """

    def __init__(self, base_table, allowed_columns):
        """
        Initialize query builder.

        Args:
            base_table: Base table name
            allowed_columns: List of allowed column names for this table
        """
        self.base_table = validate_table_name(base_table)
        self.allowed_columns = allowed_columns
        self.filters = []
        self.order_by_clause = None
        self.limit_value = None
        self.offset_value = None

    def add_filter(self, column, operator, value):
        """
        Add a filter condition.

        Args:
            column: Column name
            operator: Comparison operator (=, !=, <, >, <=, >=, LIKE)
            value: Value to compare against

        Returns:
            self for method chaining
        """
        # Validate column
        validate_column_name(column, self.allowed_columns)

        # Validate operator
        allowed_operators = ['=', '!=', '<', '>', '<=', '>=', 'LIKE', 'IN', 'IS NULL', 'IS NOT NULL']
        if operator not in allowed_operators:
            raise SQLInjectionError(f"Invalid operator: {operator}")

        # Store filter with parameter placeholder
        self.filters.append({
            'column': column,
            'operator': operator,
            'value': value
        })

        return self

    def set_order_by(self, column, direction='ASC'):
        """
        Set ORDER BY clause.

        Args:
            column: Column to sort by
            direction: Sort direction (ASC or DESC)

        Returns:
            self for method chaining
        """
        validate_column_name(column, self.allowed_columns)

        if direction.upper() not in ['ASC', 'DESC']:
            raise SQLInjectionError(f"Invalid sort direction: {direction}")

        self.order_by_clause = f"{column} {direction.upper()}"
        return self

    def set_limit(self, limit):
        """
        Set LIMIT clause.

        Args:
            limit: Maximum number of rows to return

        Returns:
            self for method chaining
        """
        try:
            self.limit_value = int(limit)
            if self.limit_value < 0:
                raise ValueError
        except (ValueError, TypeError):
            raise SQLInjectionError("Limit must be a positive integer")

        return self

    def set_offset(self, offset):
        """
        Set OFFSET clause.

        Args:
            offset: Number of rows to skip

        Returns:
            self for method chaining
        """
        try:
            self.offset_value = int(offset)
            if self.offset_value < 0:
                raise ValueError
        except (ValueError, TypeError):
            raise SQLInjectionError("Offset must be a non-negative integer")

        return self

    def build(self):
        """
        Build the SQL query string with parameter placeholders.

        Returns:
            tuple: (query_string, parameters_dict)
        """
        query_parts = [f"SELECT * FROM {self.base_table}"]
        parameters = {}

        # Add WHERE clause
        if self.filters:
            where_conditions = []
            for i, filter_spec in enumerate(self.filters):
                param_name = f"param_{i}"
                column = filter_spec['column']
                operator = filter_spec['operator']

                if operator in ['IS NULL', 'IS NOT NULL']:
                    where_conditions.append(f"{column} {operator}")
                elif operator == 'IN':
                    # Special handling for IN operator
                    placeholders = ', '.join([f":param_{i}_{j}" for j in range(len(filter_spec['value']))])
                    where_conditions.append(f"{column} IN ({placeholders})")
                    for j, val in enumerate(filter_spec['value']):
                        parameters[f"param_{i}_{j}"] = val
                else:
                    where_conditions.append(f"{column} {operator} :{param_name}")
                    parameters[param_name] = filter_spec['value']

            query_parts.append("WHERE " + " AND ".join(where_conditions))

        # Add ORDER BY
        if self.order_by_clause:
            query_parts.append(f"ORDER BY {self.order_by_clause}")

        # Add LIMIT
        if self.limit_value is not None:
            query_parts.append(f"LIMIT :limit_val")
            parameters['limit_val'] = self.limit_value

        # Add OFFSET
        if self.offset_value is not None:
            query_parts.append(f"OFFSET :offset_val")
            parameters['offset_val'] = self.offset_value

        query_string = " ".join(query_parts)
        return query_string, parameters


# Monitoring and auditing
def audit_raw_query_usage(query_string, stack_trace=None):
    """
    Audit usage of raw SQL queries for security review.

    Args:
        query_string: The raw SQL query being executed
        stack_trace: Optional stack trace for debugging
    """
    logger.info(
        f"Raw SQL query execution: {query_string[:200]}... "
        f"Stack: {stack_trace if stack_trace else 'N/A'}"
    )
