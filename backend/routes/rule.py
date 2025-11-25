from flask import Blueprint, request, jsonify, make_response
from werkzeug.exceptions import NotFound
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from models.customer import db, Customer, Rule, Alarm, RuleAlarmRelationship
from utils.xml_utils import AlarmGenerator, generate_rules_xml
from utils.rule_alarm_transformer import RuleAlarmTransformer
from utils.tenant_auth import require_customer_token, log_tenant_access
from utils.audit_logger import AuditLogger, AuditAction, audit_log
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

rule_bp = Blueprint('rule', __name__)

@rule_bp.route('/customers/<int:customer_id>/rules', methods=['GET'])
@require_customer_token
def get_rules(customer_id):
    """Get all rules for a customer (optionally paginated)"""
    try:
        Customer.query.get_or_404(customer_id)

        search = request.args.get('search', '')
        severity_min = request.args.get('severity_min', type=int)
        severity_max = request.args.get('severity_max', type=int)
        page = request.args.get('page', type=int)
        per_page = request.args.get('per_page', type=int)

        query = Rule.query.filter_by(customer_id=customer_id)

        if search:
            search_term = f"%{search}%"
            query = query.filter(db.or_(
                Rule.name.ilike(search_term),
                Rule.rule_id.ilike(search_term),
                Rule.sig_id.ilike(search_term),
                Rule.description.ilike(search_term)
            ))

        if severity_min is not None:
            query = query.filter(Rule.severity >= severity_min)

        if severity_max is not None:
            query = query.filter(Rule.severity <= severity_max)

        ordered_query = query.order_by(Rule.severity.desc(), Rule.name)

        if page is not None or per_page is not None:
            page = page or 1
            per_page = per_page or 50
            total = ordered_query.count()
            rules = ordered_query.offset((page - 1) * per_page).limit(per_page).all()
        else:
            rules = ordered_query.all()
            total = len(rules)

        return jsonify({
            'success': True,
            'rules': [rule.to_dict() for rule in rules],
            'count': len(rules),
            'total': total,
            'page': page or 1,
            'per_page': per_page or total
        })

    except NotFound:
        return jsonify({'success': False, 'error': 'Customer not found'}), 404
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching rules for customer {customer_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve rules due to a database error.'
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error fetching rules for customer {customer_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred.'
        }), 500

@rule_bp.route('/customers/<int:customer_id>/rules/<int:rule_id>', methods=['GET'])
@require_customer_token
def get_rule(customer_id, rule_id):
    """Get specific rule details"""
    try:
        rule = Rule.query.filter_by(customer_id=customer_id, id=rule_id).first_or_404()
        return jsonify({
            'success': True,
            'rule': rule.to_dict(),
            'xml_content': rule.xml_content
        })
    except NotFound:
        return jsonify({'success': False, 'error': 'Rule not found'}), 404
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching rule {rule_id} for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'A database error occurred.'}), 500
    except Exception as e:
        logger.error(f"Unexpected error fetching rule {rule_id} for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'An unexpected error occurred.'}), 500

@rule_bp.route('/customers/<int:customer_id>/rules/search', methods=['GET'])
@require_customer_token
def search_rules(customer_id):
    """Search rules with advanced filters"""
    try:
        Customer.query.get_or_404(customer_id)
        
        query = Rule.query.filter_by(customer_id=customer_id)
        
        # Apply filters based on request arguments
        if request.args.get('q'):
            search_term = f"%{request.args.get('q')}%"
            query = query.filter(db.or_(
                Rule.name.ilike(search_term),
                Rule.rule_id.ilike(search_term),
                Rule.sig_id.ilike(search_term),
                Rule.description.ilike(search_term)
            ))
        if request.args.get('type', type=int) is not None:
            query = query.filter(Rule.rule_type == request.args.get('type', type=int))
        if request.args.get('severity_min', type=int) is not None:
            query = query.filter(Rule.severity >= request.args.get('severity_min', type=int))
        if request.args.get('severity_max', type=int) is not None:
            query = query.filter(Rule.severity <= request.args.get('severity_max', type=int))
        if request.args.get('has_sig_id', type=bool) is not None:
            query = query.filter(Rule.sig_id.isnot(None) if request.args.get('has_sig_id', type=bool) else Rule.sig_id.is_(None))

        rules = query.order_by(Rule.severity.desc(), Rule.name).all()
        
        return jsonify({
            'success': True,
            'rules': [rule.to_dict() for rule in rules],
            'count': len(rules)
        })

    except NotFound:
        return jsonify({'success': False, 'error': 'Customer not found'}), 404
    except Exception as e:
        logger.error(f"Error searching rules for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'An error occurred while searching rules.'}), 500

@rule_bp.route('/customers/<int:customer_id>/rules/generate-alarms', methods=['POST'])
@require_customer_token
def generate_alarms_from_rules(customer_id):
    """Generate alarms from selected rules"""
    data = request.get_json()
    if not data or 'rule_ids' not in data:
        return jsonify({'success': False, 'error': 'rule_ids array is required'}), 400

    try:
        with db.session.begin_nested():
            rules = Rule.query.filter(
                Rule.customer_id == customer_id,
                Rule.id.in_(data['rule_ids'])
            ).all()

            if not rules:
                return jsonify({'success': False, 'error': 'No valid rules found'}), 404

            generator = AlarmGenerator()
            generated_alarms = []
            errors = []

            for rule in rules:
                if not rule.sig_id:
                    errors.append(f"Rule {rule.rule_id} has no SigID")
                    continue

                if Alarm.query.filter_by(customer_id=customer_id, match_value=f"47|{rule.sig_id}").first():
                    errors.append(f"Alarm already exists for rule {rule.rule_id}")
                    continue

                alarm_xml = generator.generate_alarm_from_rule(rule.to_dict())
                alarm = Alarm(
                    customer_id=customer_id,
                    name=(f"Generated: {rule.name}")[:255],
                    severity=rule.severity,
                    match_value=f"47|{rule.sig_id}",
                    note=rule.description,  # Rule description -> Alarm note
                    xml_content=alarm_xml
                )
                db.session.add(alarm)
                db.session.flush()

                relationship = RuleAlarmRelationship(
                    customer_id=customer_id,
                    rule_id=rule.id,
                    alarm_id=alarm.id,
                    sig_id=rule.sig_id,
                    match_value=f"47|{rule.sig_id}",
                    relationship_type='auto'
                )
                db.session.add(relationship)
                generated_alarms.append(alarm.to_dict())

        db.session.commit()

        if generated_alarms:
            AuditLogger.log_success(
                action=AuditAction.ALARM_GENERATE,
                resource_type='alarm',
                customer_id=customer_id,
                metadata={'count': len(generated_alarms), 'source': 'legacy_generator'}
            )

        return jsonify({
            'success': True,
            'generated_alarms': generated_alarms,
            'generated_count': len(generated_alarms),
            'errors': errors
        })

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"DB error generating alarms for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'Database error during alarm generation.'}), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error generating alarms for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': f'An unexpected error occurred: {str(e)}'}), 500


@rule_bp.route('/customers/<int:customer_id>/rules/export', methods=['GET'])
@require_customer_token
def export_rules(customer_id):
    """Export rules for a customer as XML (optionally filtered by IDs)."""
    try:
        customer = Customer.query.get_or_404(customer_id)
        
        query = Rule.query.filter_by(customer_id=customer_id)
        
        # Check for specific rule IDs to export
        rule_ids_param = request.args.get('rule_ids')
        if rule_ids_param:
            try:
                rule_ids = [int(id_str) for id_str in rule_ids_param.split(',')]
                query = query.filter(Rule.id.in_(rule_ids))
            except ValueError:
                pass  # Ignore invalid IDs
                
        rules = query.order_by(Rule.created_at.asc()).all()

        xml_payload = generate_rules_xml(rules)
        response = make_response(xml_payload)
        response.headers['Content-Type'] = 'application/xml'
        customer_slug = (customer.name or f"customer-{customer_id}").replace(' ', '_')
        filename = f"rules-{customer_slug}-{customer_id}.xml"
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except NotFound:
        return jsonify({'success': False, 'error': 'Customer not found'}), 404
    except Exception as e:
        logger.error(f"Error exporting rules for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'Failed to export rules.'}), 500

@rule_bp.route('/customers/<int:customer_id>/rules/stats', methods=['GET'])
@require_customer_token
def get_rule_stats(customer_id):
    """Get rule statistics for customer"""
    try:
        Customer.query.get_or_404(customer_id)
        
        total_rules = Rule.query.filter_by(customer_id=customer_id).count()
        rules_with_sig_id = Rule.query.filter(Rule.customer_id == customer_id, Rule.sig_id.isnot(None)).count()
        
        severity_stats = db.session.query(Rule.severity, db.func.count(Rule.id)).filter_by(customer_id=customer_id).group_by(Rule.severity).all()
        type_stats = db.session.query(Rule.rule_type, db.func.count(Rule.id)).filter_by(customer_id=customer_id).group_by(Rule.rule_type).all()

        return jsonify({
            'success': True,
            'stats': {
                'total_rules': total_rules,
                'rules_with_sig_id': rules_with_sig_id,
                'rules_without_sig_id': total_rules - rules_with_sig_id,
                'severity_distribution': [{'severity': s, 'count': c} for s, c in severity_stats],
                'type_distribution': [{'type': t, 'count': c} for t, c in type_stats]
            }
        })
    except NotFound:
        return jsonify({'success': False, 'error': 'Customer not found'}), 404
    except Exception as e:
        logger.error(f"Error getting rule stats for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'An error occurred while fetching stats.'}), 500

@rule_bp.route('/customers/<int:customer_id>/rules/transform-bulk', methods=['POST'])
@require_customer_token
def transform_rules_bulk(customer_id):
    """Transform rules to alarms using the new algorithm"""
    data = request.get_json() or {}
    rule_ids = data.get('rule_ids', [])

    try:
        with db.session.begin_nested():
            query = Rule.query.filter_by(customer_id=customer_id)
            if rule_ids:
                query = query.filter(Rule.id.in_(rule_ids))
            rules = query.all()

            if not rules:
                return jsonify({'success': False, 'error': 'No rules found to transform'}), 404

            transformer = RuleAlarmTransformer()
            alarm_generator = AlarmGenerator()
            generated_alarms = []
            errors = []

            for rule in rules:
                if not rule.sig_id:
                    errors.append(f"Rule {rule.rule_id} has no SigID")
                    continue

                alarm_obj = transformer.transform(rule, data.get('max_len', 128), data.get('version', '11.6.14'), rule.sig_id)
                if Alarm.query.filter_by(customer_id=customer_id, match_value=alarm_obj.match_value).first():
                    errors.append(f"Alarm already exists for rule {rule.rule_id}")
                    continue

                alarm_xml = alarm_generator.generate_alarm_from_rule(alarm_obj.__dict__)
                alarm = Alarm(
                    customer_id=customer_id,
                    name=alarm_obj.name,
                    min_version=alarm_obj.min_version,
                    severity=int(alarm_obj.severity),
                    match_field='DSIDSigID',
                    match_value=alarm_obj.match_value,
                    note=alarm_obj.description,
                    xml_content=alarm_xml
                )
                db.session.add(alarm)
                db.session.flush()

                relationship = RuleAlarmRelationship(
                    customer_id=customer_id,
                    rule_id=rule.id,
                    alarm_id=alarm.id,
                    sig_id=rule.sig_id,
                    match_value=alarm_obj.match_value,
                    relationship_type='auto'
                )
                db.session.add(relationship)
                generated_alarms.append(alarm.to_dict())

        db.session.commit()

        if generated_alarms:
            AuditLogger.log_success(
                action=AuditAction.ALARM_TRANSFORM,
                resource_type='alarm',
                customer_id=customer_id,
                metadata={'count': len(generated_alarms), 'algorithm': 'new_transformer'}
            )

        return jsonify({
            'success': True,
            'generated_alarms': generated_alarms,
            'generated_count': len(generated_alarms),
            'errors': errors,
            'algorithm': 'new_transformer'
        })

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"DB error transforming rules for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'Database error during rule transformation.'}), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error transforming rules for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': f'An unexpected error occurred: {str(e)}'}), 500

@rule_bp.route('/customers/<int:customer_id>/rules/<int:rule_id>', methods=['PUT'])
@require_customer_token
def update_rule(customer_id, rule_id):
    """Update an existing rule"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Request data is required'}), 400

    try:
        with db.session.begin_nested():
            rule = Rule.query.filter_by(customer_id=customer_id, id=rule_id).first_or_404()
            old_data = rule.to_dict()
            for field, value in data.items():
                if hasattr(rule, field):
                    setattr(rule, field, value)

        db.session.commit()

        AuditLogger.log_success(
            action=AuditAction.RULE_UPDATE,
            resource_type='rule',
            resource_id=rule.id,
            customer_id=customer_id,
            changes={'before': old_data, 'after': rule.to_dict()}
        )

        return jsonify({'success': True, 'rule': rule.to_dict()})

    except NotFound:
        return jsonify({'success': False, 'error': 'Rule not found'}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"DB error updating rule {rule_id} for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'Database error while updating rule.'}), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating rule {rule_id} for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'An unexpected error occurred.'}), 500

@rule_bp.route('/customers/<int:customer_id>/rules', methods=['POST'])
@require_customer_token
def create_rule(customer_id):
    """Create a new rule"""
    data = request.get_json()
    if not data or not data.get('name') or not data.get('rule_id'):
        return jsonify({'success': False, 'error': 'Fields "name" and "rule_id" are required'}), 400

    try:
        # Filter out fields that are not in the Rule model
        valid_fields = [
            'rule_id', 'name', 'description', 'severity', 'sig_id', 
            'rule_type', 'revision', 'origin', 'action', 'xml_content'
        ]
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        rule = Rule(customer_id=customer_id, **filtered_data)
        db.session.add(rule)
        db.session.commit()

        AuditLogger.log_success(
            action=AuditAction.RULE_CREATE,
            resource_type='rule',
            resource_id=rule.id,
            customer_id=customer_id,
            changes={'after': rule.to_dict()}
        )

        return jsonify({'success': True, 'rule': rule.to_dict()}), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'A rule with this ID may already exist.'}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"DB error creating rule for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'Database error while creating rule.'}), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating rule for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'An unexpected error occurred.'}), 500

@rule_bp.route('/customers/<int:customer_id>/rules/<int:rule_id>', methods=['DELETE'])
@require_customer_token
def delete_rule(customer_id, rule_id):
    """Delete a rule"""
    try:
        with db.session.begin_nested():
            rule = Rule.query.filter_by(customer_id=customer_id, id=rule_id).first_or_404()
            rule_id_str = rule.rule_id
            # Filter relationship deletions by tenant to prevent cross-tenant data leaks
            RuleAlarmRelationship.query.filter_by(customer_id=customer_id, rule_id=rule_id).delete()
            db.session.delete(rule)
        
        db.session.commit()

        AuditLogger.log_success(
            action=AuditAction.RULE_DELETE,
            resource_type='rule',
            resource_id=rule_id,
            customer_id=customer_id,
            metadata={'rule_id_str': rule_id_str}
        )

        return jsonify({'success': True, 'message': 'Rule deleted successfully'})

    except NotFound:
        return jsonify({'success': False, 'error': 'Rule not found'}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error deleting rule {rule_id} for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'Database error while deleting rule.'}), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting rule {rule_id} for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'An unexpected error occurred.'}), 500
