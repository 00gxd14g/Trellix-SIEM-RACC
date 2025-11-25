from flask import Blueprint, request, jsonify
import logging
from datetime import datetime
from utils.audit_logger import AuditLogger
from models.audit_log import AuditLog
from utils.tenant_auth import require_customer_token

logs_bp = Blueprint('logs', __name__)
logger = logging.getLogger(__name__)

@logs_bp.route('/logs/audit', methods=['GET'])
def get_audit_logs():
    """Get audit logs with filtering and category support"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        # Filters
        customer_id = request.args.get('customer_id')
        action = request.args.get('action')
        resource_type = request.args.get('resource_type')
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        category = request.args.get('category')  # New: filter by category

        # Build query
        query = AuditLog.query

        if customer_id:
            query = query.filter(AuditLog.customer_id == customer_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if status:
            query = query.filter(AuditLog.status == status)
        if start_date:
            query = query.filter(AuditLog.timestamp >= datetime.fromisoformat(start_date))
        if end_date:
            query = query.filter(AuditLog.timestamp <= datetime.fromisoformat(end_date))
        
        # Category-based filtering (groups multiple resource types)
        if category:
            category_mapping = {
                'customer': ['customer'],
                'rule': ['rule'],
                'alarm': ['alarm'],
                'file': ['file'],
                'analysis': ['analysis'],
                'settings': ['settings'],
                'security': ['security'],
                'frontend': ['frontend'],
                'debug': ['debug'],
                'system': ['system'],
                'other': ['other']
            }
            if category in category_mapping:
                query = query.filter(AuditLog.resource_type.in_(category_mapping[category]))

        # Sort by timestamp desc
        query = query.order_by(AuditLog.timestamp.desc())

        # Paginate
        total = query.count()
        logs = query.offset((page - 1) * per_page).limit(per_page).all()
        
        # Group logs by category for better organization
        logs_by_category = {}
        for log in logs:
            log_dict = log.to_dict()
            cat = log_dict.get('resource_type', 'other')
            if cat not in logs_by_category:
                logs_by_category[cat] = []
            logs_by_category[cat].append(log_dict)

        return jsonify({
            'success': True,
            'logs': [log.to_dict() for log in logs],
            'logs_by_category': logs_by_category,
            'total': total,
            'page': page,
            'per_page': per_page
        })

    except Exception as e:
        logger.error(f'Failed to fetch audit logs: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to fetch audit logs'}), 500

@logs_bp.route('/logs/categories', methods=['GET'])
def get_log_categories():
    """Get available log categories with counts"""
    try:
        customer_id = request.args.get('customer_id')
        
        # Build base query
        query = AuditLog.query
        if customer_id:
            query = query.filter(AuditLog.customer_id == customer_id)
        
        # Get all logs to categorize
        all_logs = query.all()
        
        # Count by category
        categories = {}
        for log in all_logs:
            resource_type = log.resource_type or 'other'
            categories[resource_type] = categories.get(resource_type, 0) + 1
        
        # Sort by count
        sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        
        return jsonify({
            'success': True,
            'categories': dict(sorted_categories),
            'total': len(all_logs)
        })
        
    except Exception as e:
        logger.error(f'Failed to fetch log categories: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to fetch log categories'}), 500

@logs_bp.route('/logs', methods=['POST'])
def receive_frontend_log():
    """Receive and process frontend logs"""
    try:
        log_data = request.get_json()
        
        # Extract log information
        timestamp = log_data.get('timestamp', datetime.now().isoformat())
        level = log_data.get('level', 'INFO')
        message = log_data.get('message', '')
        data = log_data.get('data', {})
        user_agent = log_data.get('userAgent', '')
        url = log_data.get('url', '')
        
        # Create formatted log message
        log_message = f"[FRONTEND] {timestamp} - {url} - {message}"
        
        # Log based on level
        if level == 'DEBUG':
            logger.debug(log_message, extra={'data': data, 'user_agent': user_agent})
            # Also save DEBUG logs to audit for visibility
            AuditLogger.log_event(
                action='FRONTEND_DEBUG',
                resource_type='debug',
                status='success',
                metadata={'message': message, 'data': data, 'url': url, 'user_agent': user_agent}
            )
        elif level == 'INFO':
            logger.info(log_message, extra={'data': data, 'user_agent': user_agent})
        elif level == 'WARN':
            logger.warning(log_message, extra={'data': data, 'user_agent': user_agent})
        elif level == 'ERROR':
            logger.error(log_message, extra={'data': data, 'user_agent': user_agent})
        elif level == 'CRITICAL':
            logger.critical(log_message, extra={'data': data, 'user_agent': user_agent})
        else:
            logger.info(log_message, extra={'data': data, 'user_agent': user_agent})
        
        # Save to AuditLog for UI visibility
        try:
            status = 'failure' if level in ['ERROR', 'CRITICAL'] else 'success'
            
            # Map frontend log to AuditLog structure
            AuditLogger.log_event(
                action='FRONTEND_LOG',
                resource_type='frontend',
                status=status,
                resource_id=None,
                customer_id=None,
                metadata={
                    'level': level,
                    'data': data,
                    'user_agent': user_agent,
                    'url': url
                },
                error_message=message if status == 'failure' else None
            )
        except Exception as db_e:
            logger.error(f"Failed to save frontend log to DB: {db_e}")

        return jsonify({'success': True, 'message': 'Log received'}), 200
        
    except Exception as e:
        logger.error(f'Failed to process frontend log: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to process log'}), 500

@logs_bp.route('/logs/export', methods=['GET'])
def export_logs():
    """Export logs for debugging"""
    try:
        # This would typically read from log files
        # For now, return a simple response
        return jsonify({
            'success': True,
            'message': 'Log export endpoint - implement based on your logging setup'
        }), 200
    except Exception as e:
        logger.error(f'Failed to export logs: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to export logs'}), 500

@logs_bp.route('/logs/stats', methods=['GET'])
def get_log_stats():
    """Get log statistics"""
    try:
        customer_id = request.args.get('customer_id')
        
        # Build base query
        query = AuditLog.query
        if customer_id:
            query = query.filter(AuditLog.customer_id == customer_id)
        
        # Get all logs
        all_logs = query.all()
        
        # Calculate statistics
        stats = {
            'total': len(all_logs),
            'by_status': {},
            'by_resource_type': {},
            'by_action': {},
            'recent_errors': []
        }
        
        for log in all_logs:
            # Count by status
            status = log.status or 'unknown'
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            
            # Count by resource type
            resource_type = log.resource_type or 'other'
            stats['by_resource_type'][resource_type] = stats['by_resource_type'].get(resource_type, 0) + 1
            
            # Count by action
            action = log.action or 'unknown'
            stats['by_action'][action] = stats['by_action'].get(action, 0) + 1
            
            # Collect recent errors
            if status in ['failure', 'error'] and len(stats['recent_errors']) < 10:
                stats['recent_errors'].append(log.to_dict())
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f'Failed to fetch log stats: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to fetch log stats'}), 500