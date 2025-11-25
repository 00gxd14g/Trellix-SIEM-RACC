"""
Tenant authentication and authorization utilities.

This module provides decorators and utilities to ensure proper tenant isolation
by validating that the X-Customer-ID header matches the customer_id URL parameter.
"""

from functools import wraps
from flask import request, abort, current_app
import logging

logger = logging.getLogger(__name__)


def require_customer_token(f):
    """
    Decorator to validate tenant identity on every request.
    
    Compares the X-Customer-ID request header with the customer_id path parameter
    and aborts with 403 when they differ.
    
    This prevents malicious or buggy clients from requesting another tenant's data
    even when using the correct URL structure.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract customer_id from URL parameters
        customer_id_from_url = kwargs.get('customer_id')
        if customer_id_from_url is None:
            # This decorator should only be used on routes with customer_id parameter
            logger.error(f"Route {request.endpoint} missing customer_id parameter")
            abort(500, description="Internal server error: missing customer_id parameter")
        
        # Get X-Customer-ID header
        customer_id_from_header = request.headers.get('X-Customer-ID')
        if customer_id_from_header is None:
            logger.warning(f"Missing X-Customer-ID header for customer {customer_id_from_url}")
            abort(403, description="Missing X-Customer-ID header")
        
        # Convert both to integers for comparison
        try:
            url_customer_id = int(customer_id_from_url)
            header_customer_id = int(customer_id_from_header)
        except (ValueError, TypeError):
            logger.warning(f"Invalid customer ID format. URL: {customer_id_from_url}, Header: {customer_id_from_header}")
            abort(403, description="Invalid customer ID format")
        
        # Compare customer IDs
        if url_customer_id != header_customer_id:
            logger.warning(
                f"Customer ID mismatch. URL: {url_customer_id}, Header: {header_customer_id}. "
                f"Client IP: {request.remote_addr}, User-Agent: {request.headers.get('User-Agent', 'Unknown')}"
            )
            abort(403, description="Customer ID mismatch between URL and header")
        
        # Log successful validation in debug mode
        if current_app.debug:
            logger.debug(f"Customer ID validation successful for customer {url_customer_id}")
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_validated_customer_id():
    """
    Get the validated customer ID from the current request context.
    
    This should only be called within a route decorated with @require_customer_token.
    Returns the customer ID as an integer.
    """
    customer_id_header = request.headers.get('X-Customer-ID')
    if customer_id_header is None:
        raise ValueError("No X-Customer-ID header found in request")
    
    try:
        return int(customer_id_header)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid customer ID format: {customer_id_header}")


def log_tenant_access(customer_id, resource_type, action, resource_id=None):
    """
    Log tenant access for audit purposes.
    
    Args:
        customer_id (int): The tenant/customer ID
        resource_type (str): Type of resource being accessed (e.g., 'rule', 'alarm')
        action (str): Action being performed (e.g., 'create', 'read', 'update', 'delete')
        resource_id (int, optional): ID of the specific resource being accessed
    """
    log_message = f"Tenant {customer_id} performed {action} on {resource_type}"
    if resource_id:
        log_message += f" (ID: {resource_id})"
    
    log_message += f" - IP: {request.remote_addr}"
    
    logger.info(log_message)