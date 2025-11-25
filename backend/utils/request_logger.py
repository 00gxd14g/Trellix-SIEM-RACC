"""
Request/Response Logging Middleware
Logs all incoming requests and outgoing responses with detailed information
"""

import logging
import time
from functools import wraps
from flask import request, g
from datetime import datetime
from utils.audit_logger import AuditLogger

logger = logging.getLogger(__name__)

# API endpoint categories for classification
API_CATEGORIES = {
    'customer': ['customers'],
    'rule': ['rules', 'transform'],
    'alarm': ['alarms', 'generate'],
    'file': ['upload', 'download', 'files'],
    'analysis': ['analysis', 'coverage', 'relationships', 'event-usage'],
    'settings': ['settings'],
    'logs': ['logs', 'audit'],
    'health': ['health', 'docs'],
}

def get_api_category(endpoint: str) -> str:
    """Determine API category based on endpoint with proper prioritization"""
    endpoint_lower = endpoint.lower()
    
    # Check in order of specificity (most specific first)
    # This prevents /customers/1/alarms from being categorized as 'customer'
    if 'alarms' in endpoint_lower or 'generate' in endpoint_lower:
        return 'alarm'
    if 'rules' in endpoint_lower or 'transform' in endpoint_lower:
        return 'rule'
    if 'analysis' in endpoint_lower or 'coverage' in endpoint_lower or 'relationships' in endpoint_lower or 'event-usage' in endpoint_lower:
        return 'analysis'
    if 'settings' in endpoint_lower:
        return 'settings'
    if 'logs' in endpoint_lower or 'audit' in endpoint_lower:
        return 'logs'
    if 'upload' in endpoint_lower or 'download' in endpoint_lower or 'files' in endpoint_lower:
        return 'file'
    if 'customers' in endpoint_lower:
        return 'customer'
    if 'health' in endpoint_lower or 'docs' in endpoint_lower:
        return 'health'
    
    return 'other'

def get_client_ip():
    """Get client IP address, considering proxies"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr or 'unknown'

def log_request():
    """Log incoming request details"""
    g.start_time = time.time()
    g.request_id = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    
    # Get request details
    method = request.method
    endpoint = request.path
    category = get_api_category(endpoint)
    client_ip = get_client_ip()
    
    # Build log data
    log_data = {
        'request_id': g.request_id,
        'method': method,
        'endpoint': endpoint,
        'category': category,
        'client_ip': client_ip,
        'user_agent': request.headers.get('User-Agent', 'unknown'),
        'content_type': request.headers.get('Content-Type', ''),
        'content_length': request.headers.get('Content-Length', 0),
    }
    
    # Log query parameters
    if request.args:
        log_data['query_params'] = dict(request.args)
    
    # Log request body for non-GET requests (be careful with sensitive data)
    if method in ['POST', 'PUT', 'PATCH'] and request.is_json:
        try:
            # Don't log passwords or sensitive data
            body = request.get_json()
            if body:
                # Filter sensitive fields
                filtered_body = {k: v for k, v in body.items() 
                               if k not in ['password', 'token', 'secret', 'api_key']}
                log_data['request_body'] = filtered_body
        except Exception as e:
            logger.warning(f"Failed to parse request body: {e}")
    
    logger.debug(f"[REQUEST] {method} {endpoint} - Category: {category}", extra=log_data)
    
    return log_data

def log_response(response, request_data):
    """Log outgoing response details"""
    # Calculate request duration
    duration = time.time() - g.start_time if hasattr(g, 'start_time') else 0
    duration_ms = round(duration * 1000, 2)
    
    status_code = response.status_code
    endpoint = request.path
    method = request.method
    category = get_api_category(endpoint)
    
    # Determine log level based on status code
    if status_code >= 500:
        log_level = logging.ERROR
        status = 'error'
    elif status_code >= 400:
        log_level = logging.WARNING
        status = 'failure'
    else:
        log_level = logging.INFO
        status = 'success'
    
    # Build log data
    log_data = {
        'request_id': g.request_id if hasattr(g, 'request_id') else 'unknown',
        'method': method,
        'endpoint': endpoint,
        'category': category,
        'status_code': status_code,
        'duration_ms': duration_ms,
        'response_size': len(response.get_data()) if response.get_data() else 0,
        'client_ip': get_client_ip(),
    }
    
    # Log response body for errors (truncated)
    if status_code >= 400 and response.is_json:
        try:
            response_data = response.get_json()
            if response_data:
                log_data['error_message'] = response_data.get('error', 
                                                               response_data.get('message', ''))
        except Exception:
            pass
    
    logger.log(
        log_level,
        f"[RESPONSE] {method} {endpoint} - Status: {status_code} - Duration: {duration_ms}ms - Category: {category}",
        extra=log_data
    )
    
    # Save to audit log for tracking
    try:
        customer_id = request.view_args.get('customer_id') if request.view_args else None
        resource_id = request.view_args.get('rule_id') or request.view_args.get('alarm_id') or \
                     request.view_args.get('file_type') or None
        
        # Determine action from method and endpoint
        action = f"{method}_{endpoint.split('/')[-1].upper()}" if endpoint.split('/')[-1] else method
        
        # Prepare metadata with request and response details
        metadata = {
            'duration_ms': duration_ms,
            'status_code': status_code,
            'request_id': log_data['request_id'],
            'endpoint': endpoint,
        }

        # Add request body if available (only for errors as requested)
        if status_code >= 400 and request_data and 'request_body' in request_data:
            metadata['request'] = request_data['request_body']
        
        # Add response body for errors
        if status_code >= 400 and response.is_json:
            try:
                resp_json = response.get_json()
                if resp_json:
                    metadata['response'] = resp_json
            except Exception:
                pass

        AuditLogger.log_event(
            action=action,
            resource_type=category,
            status=status,
            resource_id=str(resource_id) if resource_id else None,
            customer_id=customer_id,
            metadata=metadata,
            error_message=log_data.get('error_message')
        )
    except Exception as e:
        logger.error(f"Failed to save audit log: {e}", exc_info=True)
    
    return log_data

def log_exception(error):
    """Log unhandled exceptions"""
    endpoint = request.path
    method = request.method
    category = get_api_category(endpoint)
    
    logger.error(
        f"[EXCEPTION] {method} {endpoint} - {type(error).__name__}: {str(error)}",
        extra={
            'request_id': g.request_id if hasattr(g, 'request_id') else 'unknown',
            'method': method,
            'endpoint': endpoint,
            'category': category,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'client_ip': get_client_ip(),
        },
        exc_info=True
    )
    
    # Save to audit log
    try:
        AuditLogger.log_event(
            action=f"{method}_ERROR",
            resource_type=category,
            status='error',
            resource_id=None,
            customer_id=None,
            metadata={
                'error_type': type(error).__name__,
                'endpoint': endpoint,
            },
            error_message=str(error)
        )
    except Exception as e:
        logger.error(f"Failed to save exception audit log: {e}")

def request_logger_middleware(app):
    """Setup request/response logging middleware"""
    
    @app.before_request
    def before_request():
        """Log before each request"""
        # Skip logging for static files
        if request.path.startswith('/static') or request.path.startswith('/assets'):
            return
        
        log_request()
    
    @app.after_request
    def after_request(response):
        """Log after each request"""
        # Skip logging for static files
        if request.path.startswith('/static') or request.path.startswith('/assets'):
            return response
        
        request_data = {}
        log_response(response, request_data)
        
        return response
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Log unhandled exceptions"""
        log_exception(error)
        # Re-raise to let Flask handle it
        raise error

def log_route(category: str = None):
    """
    Decorator to log specific route execution
    
    Usage:
        @log_route('customer')
        def get_customer(customer_id):
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            route_category = category or get_api_category(request.path)
            start_time = time.time()
            
            logger.info(
                f"[ROUTE ENTER] {f.__name__} - Category: {route_category}",
                extra={
                    'function': f.__name__,
                    'category': route_category,
                    'args': str(args) if args else None,
                    'kwargs': str(kwargs) if kwargs else None,
                }
            )
            
            try:
                result = f(*args, **kwargs)
                duration = round((time.time() - start_time) * 1000, 2)
                
                logger.info(
                    f"[ROUTE EXIT] {f.__name__} - Duration: {duration}ms",
                    extra={
                        'function': f.__name__,
                        'category': route_category,
                        'duration_ms': duration,
                        'success': True,
                    }
                )
                
                return result
            except Exception as e:
                duration = round((time.time() - start_time) * 1000, 2)
                
                logger.error(
                    f"[ROUTE ERROR] {f.__name__} - {type(e).__name__}: {str(e)} - Duration: {duration}ms",
                    extra={
                        'function': f.__name__,
                        'category': route_category,
                        'duration_ms': duration,
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                    },
                    exc_info=True
                )
                
                raise
        
        return wrapper
    return decorator
