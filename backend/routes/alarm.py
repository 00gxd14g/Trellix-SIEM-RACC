from flask import Blueprint, request, jsonify, current_app, make_response
from werkzeug.exceptions import NotFound
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from models.customer import db, Customer, Alarm, Rule, RuleAlarmRelationship
from utils.tenant_auth import require_customer_token, log_tenant_access
from utils.audit_logger import AuditLogger, AuditAction, audit_log
from utils.xml_utils import generate_alarms_xml, AlarmGenerator
from lxml import etree
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

alarm_bp = Blueprint('alarm', __name__)

@alarm_bp.route('/customers/<int:customer_id>/alarms', methods=['GET'])
@require_customer_token
def get_alarms(customer_id):
    """Get all alarms for a customer (optionally paginated)"""
    try:
        Customer.query.get_or_404(customer_id)

        query = Alarm.query.filter_by(customer_id=customer_id)
        page = request.args.get('page', type=int)
        per_page = request.args.get('per_page', type=int)

        # Apply filters from request arguments
        if request.args.get('search'):
            search_term = f"%{request.args.get('search')}%"
            query = query.filter(db.or_(
                Alarm.name.ilike(search_term),
                Alarm.match_value.ilike(search_term),
                Alarm.note.ilike(search_term)
            ))
        if request.args.get('severity_min', type=int) is not None:
            query = query.filter(Alarm.severity >= request.args.get('severity_min', type=int))
        if request.args.get('severity_max', type=int) is not None:
            query = query.filter(Alarm.severity <= request.args.get('severity_max', type=int))

        ordered_query = query.order_by(Alarm.severity.desc(), Alarm.name)

        if page is not None or per_page is not None:
            page = page or 1
            per_page = per_page or 50
            total = ordered_query.count()
            alarms = ordered_query.offset((page - 1) * per_page).limit(per_page).all()
        else:
            alarms = ordered_query.all()
            total = len(alarms)

        return jsonify({
            'success': True,
            'alarms': [alarm.to_dict() for alarm in alarms],
            'total': total,
            'page': page or 1,
            'per_page': per_page or total
        })

    except NotFound:
        return jsonify({'success': False, 'error': 'Customer not found'}), 404
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching alarms for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'Failed to retrieve alarms due to a database error.'}), 500
    except Exception as e:
        logger.error(f"Unexpected error fetching alarms for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'An unexpected error occurred.'}), 500

@alarm_bp.route('/customers/<int:customer_id>/alarms/<int:alarm_id>', methods=['GET'])
@require_customer_token
def get_alarm(customer_id, alarm_id):
    """Get specific alarm details"""
    try:
        alarm = Alarm.query.filter_by(customer_id=customer_id, id=alarm_id).first_or_404()
        return jsonify({
            'success': True,
            'alarm': alarm.to_dict(),
            'xml_content': alarm.xml_content
        })
    except NotFound:
        return jsonify({'success': False, 'error': 'Alarm not found'}), 404
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching alarm {alarm_id} for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'A database error occurred.'}), 500
    except Exception as e:
        logger.error(f"Unexpected error fetching alarm {alarm_id} for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'An unexpected error occurred.'}), 500

@alarm_bp.route('/customers/<int:customer_id>/alarms', methods=['POST'])
@require_customer_token
def create_alarm(customer_id):
    """Create a new alarm"""
    data = request.get_json()
    if not data or not all(k in data for k in ['name', 'severity', 'match_value']):
        return jsonify({'success': False, 'error': 'Missing required fields: name, severity, match_value'}), 400

    try:
        alarm_xml = AlarmGenerator().generate_alarm_xml(data)
        alarm = Alarm(customer_id=customer_id, xml_content=alarm_xml, **data)
        
        db.session.add(alarm)
        db.session.commit()
        
        AuditLogger.log_success(
            action=AuditAction.ALARM_CREATE,
            resource_type='alarm',
            resource_id=alarm.id,
            customer_id=customer_id,
            changes={'after': alarm.to_dict()}
        )

        return jsonify({'success': True, 'alarm': alarm.to_dict()}), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'An alarm with this configuration may already exist.'}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error creating alarm for customer {customer_id}: {e}")
        logger.error(f"Error updating alarm {alarm_id} for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'An unexpected error occurred.'}), 500

def _clean_str(v):
    if v is None:
        return None
    if not isinstance(v, str):
        return v
    return v.replace("\x00", "")

@alarm_bp.route('/customers/<int:customer_id>/alarms/<int:alarm_id>', methods=['PUT'])
@require_customer_token
def update_alarm(customer_id, alarm_id):
    """Update an existing alarm"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Request data is required'}), 400

    try:
        with db.session.begin_nested():
            alarm = Alarm.query.filter_by(customer_id=customer_id, id=alarm_id).first_or_404()
            old_data = alarm.to_dict()
            
            # Update fields if present in payload
            if 'name' in data:
                alarm.name = _clean_str(data['name'])
            if 'min_version' in data:
                alarm.min_version = _clean_str(data['min_version'])
            if 'severity' in data:
                alarm.severity = data['severity']
            if 'match_field' in data:
                alarm.match_field = _clean_str(data['match_field'])
            if 'match_value' in data:
                alarm.match_value = _clean_str(data['match_value'])
            if 'condition_type' in data:
                alarm.condition_type = data['condition_type']
            if 'assignee_id' in data:
                alarm.assignee_id = data['assignee_id']
            if 'esc_assignee_id' in data:
                alarm.esc_assignee_id = data['esc_assignee_id']
            if 'note' in data:
                alarm.note = _clean_str(data['note'])
            if 'xml_content' in data:
                alarm.xml_content = _clean_str(data['xml_content'])
            
            # Regenerate XML if needed (optional, depending on requirements)
            # alarm.xml_content = AlarmGenerator().generate_alarm_xml(alarm.to_dict())
        
        db.session.commit()

        AuditLogger.log_success(
            action=AuditAction.ALARM_UPDATE,
            resource_type='alarm',
            resource_id=alarm.id,
            customer_id=customer_id,
            changes={'before': old_data, 'after': alarm.to_dict()}
        )

        return jsonify({'success': True, 'alarm': alarm.to_dict()})

    except NotFound:
        return jsonify({'success': False, 'error': 'Alarm not found'}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error updating alarm {alarm_id} for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'Database error while updating alarm.'}), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating alarm {alarm_id} for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'An unexpected error occurred.'}), 500

@alarm_bp.route('/customers/<int:customer_id>/alarms/<int:alarm_id>', methods=['DELETE'])
@require_customer_token
def delete_alarm(customer_id, alarm_id):
    """Delete an alarm with retry logic for database lock handling"""
    import time
    from sqlite3 import OperationalError
    
    max_retries = 3
    retry_delay = 0.1  # 100ms
    
    for attempt in range(max_retries):
        try:
            with db.session.begin_nested():
                alarm = Alarm.query.filter_by(customer_id=customer_id, id=alarm_id).first_or_404()
                alarm_name = alarm.name
                # Filter relationship deletions by tenant to prevent cross-tenant data leaks
                RuleAlarmRelationship.query.filter_by(customer_id=customer_id, alarm_id=alarm_id).delete()
                db.session.delete(alarm)
            
            db.session.commit()

            AuditLogger.log_success(
                action=AuditAction.ALARM_DELETE,
                resource_type='alarm',
                resource_id=alarm_id,
                customer_id=customer_id,
                metadata={'alarm_name': alarm_name, 'retry_attempt': attempt + 1}
            )

            return jsonify({'success': True, 'message': 'Alarm deleted successfully'})

        except NotFound:
            return jsonify({'success': False, 'error': 'Alarm not found'}), 404
        except (SQLAlchemyError, OperationalError) as e:
            db.session.rollback()
            error_str = str(e)
            
            # Check if it's a database locked error
            if 'database is locked' in error_str.lower() and attempt < max_retries - 1:
                logger.warning(f"Database locked on attempt {attempt + 1}/{max_retries} for alarm {alarm_id}, retrying...")
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                continue
            else:
                logger.error(f"Database error deleting alarm {alarm_id} for customer {customer_id}: {e}")
                return jsonify({'success': False, 'error': 'Database error while deleting alarm.'}), 500
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting alarm {alarm_id} for customer {customer_id}: {e}")
            return jsonify({'success': False, 'error': 'An unexpected error occurred.'}), 500
    
    # If we've exhausted all retries
    return jsonify({'success': False, 'error': 'Database is busy, please try again.'}), 503

@alarm_bp.route('/customers/<int:customer_id>/alarms/stats', methods=['GET'])
@require_customer_token
def get_alarm_stats(customer_id):
    """Get alarm statistics for customer"""
    try:
        Customer.query.get_or_404(customer_id)
        
        total_alarms = Alarm.query.filter_by(customer_id=customer_id).count()
        alarms_with_rules = db.session.query(Alarm.id).join(RuleAlarmRelationship, Alarm.id == RuleAlarmRelationship.alarm_id).filter(Alarm.customer_id == customer_id).distinct().count()
        
        severity_stats = db.session.query(Alarm.severity, db.func.count(Alarm.id)).filter_by(customer_id=customer_id).group_by(Alarm.severity).all()
        condition_stats = db.session.query(Alarm.condition_type, db.func.count(Alarm.id)).filter_by(customer_id=customer_id).group_by(Alarm.condition_type).all()

        return jsonify({
            'success': True,
            'stats': {
                'total_alarms': total_alarms,
                'alarms_with_rules': alarms_with_rules,
                'alarms_without_rules': total_alarms - alarms_with_rules,
                'severity_distribution': [{'severity': s, 'count': c} for s, c in severity_stats],
                'condition_type_distribution': [{'type': t, 'count': c} for t, c in condition_stats]
            }
        })
    except NotFound:
        return jsonify({'success': False, 'error': 'Customer not found'}), 404
    except Exception as e:
        logger.error(f"Error getting alarm stats for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'An error occurred while fetching alarm stats.'}), 500


@alarm_bp.route('/customers/<int:customer_id>/alarms/export', methods=['GET'])
@require_customer_token
def export_alarms(customer_id):
    """Export alarms for a customer as XML (optionally filtered by IDs)."""
    try:
        customer = Customer.query.get_or_404(customer_id)
        
        query = Alarm.query.filter_by(customer_id=customer_id)
        
        # Check for specific alarm IDs to export
        alarm_ids_param = request.args.get('alarm_ids')
        if alarm_ids_param:
            try:
                alarm_ids = [int(id_str) for id_str in alarm_ids_param.split(',')]
                query = query.filter(Alarm.id.in_(alarm_ids))
            except ValueError:
                pass  # Ignore invalid IDs
                
        alarms = query.order_by(Alarm.created_at.asc()).all()

        xml_payload = generate_alarms_xml(alarms)
        response = make_response(xml_payload)
        response.headers['Content-Type'] = 'application/xml'
        filename = f"alarms-{customer.name.replace(' ', '_')}-{customer_id}.xml"
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except NotFound:
        return jsonify({'success': False, 'error': 'Customer not found'}), 404
    except Exception as e:
        logger.error(f"Error exporting alarms for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'Failed to export alarms.'}), 500



@alarm_bp.route('/customers/<int:customer_id>/alarms/bulk-delete', methods=['POST'])
@require_customer_token
def bulk_delete_alarms(customer_id):
    """Delete multiple alarms"""
    data = request.get_json()
    if not data or 'alarm_ids' not in data:
        return jsonify({'success': False, 'error': 'Missing alarm_ids'}), 400
    
    alarm_ids = data['alarm_ids']
    if not isinstance(alarm_ids, list):
         return jsonify({'success': False, 'error': 'alarm_ids must be a list'}), 400

    try:
        with db.session.begin_nested():
            # Filter by customer_id for security
            RuleAlarmRelationship.query.filter(
                RuleAlarmRelationship.customer_id == customer_id,
                RuleAlarmRelationship.alarm_id.in_(alarm_ids)
            ).delete(synchronize_session=False)
            
            deleted_count = Alarm.query.filter(
                Alarm.customer_id == customer_id,
                Alarm.id.in_(alarm_ids)
            ).delete(synchronize_session=False)
        
        db.session.commit()
        
        AuditLogger.log_success(
            action=AuditAction.ALARM_DELETE,
            resource_type='alarm',
            resource_id=0, # Bulk
            customer_id=customer_id,
            metadata={'count': deleted_count, 'alarm_ids': alarm_ids}
        )
        
        return jsonify({'success': True, 'deleted_count': deleted_count})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error bulk deleting alarms for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'An unexpected error occurred.'}), 500
