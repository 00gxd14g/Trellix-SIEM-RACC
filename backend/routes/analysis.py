from collections import Counter

from flask import Blueprint, request, jsonify, render_template, make_response
import os
from datetime import datetime
from werkzeug.exceptions import NotFound
from sqlalchemy.exc import SQLAlchemyError
from models.customer import db, Customer, Rule, Alarm, RuleAlarmRelationship
from utils.signature_mapping import get_alarm_event_ids, get_event_details, get_rule_event_ids
from utils.xml_utils import AlarmGenerator
from utils.tenant_auth import require_customer_token, log_tenant_access
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

analysis_bp = Blueprint('analysis', __name__)


@analysis_bp.route('/customers/<int:customer_id>/analysis/event-usage', methods=['GET'])
@require_customer_token
def get_event_usage(customer_id):
    """Aggregate Windows event usage counts for the customer."""
    try:
        Customer.query.get_or_404(customer_id)

        limit = request.args.get('limit', type=int)

        rules = Rule.query.filter_by(customer_id=customer_id).all()
        alarms = Alarm.query.filter_by(customer_id=customer_id).all()

        rule_counter: Counter[str] = Counter()
        alarm_counter: Counter[str] = Counter()

        for rule in rules:
            for event_id in get_rule_event_ids(rule):
                rule_counter[event_id] += 1

        for alarm in alarms:
            for event_id in get_alarm_event_ids(alarm):
                alarm_counter[event_id] += 1

        combined_counter = rule_counter + alarm_counter

        if not combined_counter:
            return jsonify({
                'success': True,
                'event_usage': {
                    'total_unique_events': 0,
                    'events': []
                }
            })

        event_details_map = {
            detail['id']: detail
            for detail in get_event_details(combined_counter.keys())
        }

        sorted_events = sorted(
            combined_counter.items(),
            key=lambda item: (-item[1], item[0])
        )

        if limit and limit > 0:
            sorted_events = sorted_events[:limit]

        events_payload = []
        for event_id, total in sorted_events:
            details = event_details_map.get(event_id, {})
            events_payload.append({
                'event_id': event_id,
                'total_references': total,
                'rule_count': rule_counter.get(event_id, 0),
                'alarm_count': alarm_counter.get(event_id, 0),
                'description': details.get('description'),
                'audit_policy': details.get('audit_policy'),
            })

        return jsonify({
            'success': True,
            'event_usage': {
                'total_unique_events': len(combined_counter),
                'events': events_payload
            }
        })
    except NotFound:
        return jsonify({'success': False, 'error': 'Customer not found'}), 404
    except SQLAlchemyError as e:
        logger.error(f"Database error computing event usage for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'Database error during event usage analysis.'}), 500
    except Exception as e:
        logger.error(f"Error computing event usage for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'An unexpected error occurred.'}), 500


@analysis_bp.route('/customers/<int:customer_id>/analysis/coverage', methods=['GET'])
@require_customer_token
def get_coverage_analysis(customer_id):
    """Get rule-alarm coverage analysis"""
    try:
        Customer.query.get_or_404(customer_id)

        total_rules = Rule.query.filter_by(customer_id=customer_id).count()
        total_alarms = Alarm.query.filter_by(customer_id=customer_id).count()
        rules_with_sig_id = Rule.query.filter(Rule.customer_id == customer_id, Rule.sig_id.isnot(None)).count()
        rules_with_alarms = db.session.query(Rule.id).join(RuleAlarmRelationship, Rule.id == RuleAlarmRelationship.rule_id).filter(Rule.customer_id == customer_id).distinct().count()
        alarms_with_rules = db.session.query(Alarm.id).join(RuleAlarmRelationship, Alarm.id == RuleAlarmRelationship.alarm_id).filter(Alarm.customer_id == customer_id).distinct().count()

        rule_coverage = (rules_with_alarms / rules_with_sig_id * 100) if rules_with_sig_id > 0 else 0
        alarm_coverage = (alarms_with_rules / total_alarms * 100) if total_alarms > 0 else 0

        return jsonify({
            'success': True,
            'coverage': {
                'total_rules': total_rules,
                'total_alarms': total_alarms,
                'matched_rules': rules_with_alarms,
                'matched_alarms': alarms_with_rules,
                'rules_with_sig_id': rules_with_sig_id,
                'rules_without_sig_id': total_rules - rules_with_sig_id,
                'rules_with_alarms': rules_with_alarms,
                'rules_without_alarms': rules_with_sig_id - rules_with_alarms,
                'alarms_with_rules': alarms_with_rules,
                'alarms_without_rules': total_alarms - alarms_with_rules,
                'coverage_percentage': round(rule_coverage, 2),
                'rule_coverage_percentage': round(rule_coverage, 2),
                'alarm_coverage_percentage': round(alarm_coverage, 2),
                'total_relationships': rules_with_alarms
            }
        })
    except NotFound:
        return jsonify({'success': False, 'error': 'Customer not found'}), 404
    except SQLAlchemyError as e:
        logger.error(f"Database error on coverage analysis for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'Database error during coverage analysis.'}), 500
    except Exception as e:
        logger.error(f"Error on coverage analysis for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'An unexpected error occurred.'}), 500

@analysis_bp.route('/customers/<int:customer_id>/analysis/relationships', methods=['GET'])
@require_customer_token
def get_relationships(customer_id):
    """Get rule-alarm relationships"""
    try:
        Customer.query.get_or_404(customer_id)
        relationships = db.session.query(
            RuleAlarmRelationship, Rule.name, Rule.rule_id, Rule.severity, Alarm.name, Alarm.severity
        ).join(Rule, RuleAlarmRelationship.rule_id == Rule.id).join(
            Alarm, RuleAlarmRelationship.alarm_id == Alarm.id
        ).filter(RuleAlarmRelationship.customer_id == customer_id).all()

        formatted_relationships = []
        for rel, rule_name, rule_identifier, rule_severity, alarm_name, alarm_severity in relationships:
            formatted_relationships.append({
                'rule_id': rel.rule_id,
                'rule_identifier': rule_identifier,
                'alarm_id': rel.alarm_id,
                'rule_name': rule_name,
                'alarm_name': alarm_name,
                'sig_id': rel.sig_id,
                'match_value': rel.match_value,
                'relationship_type': rel.relationship_type,
                'matched_fields': ['sig_id', 'match_value'],  # Mock matched fields for UI
                'created_at': rel.created_at.isoformat() if rel.created_at else None
            })

        return jsonify({
            'success': True,
            'relationships': formatted_relationships,
            'count': len(formatted_relationships)
        })
    except NotFound:
        return jsonify({'success': False, 'error': 'Customer not found'}), 404
    except Exception as e:
        logger.error(f"Error getting relationships for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'An error occurred while fetching relationships.'}), 500

@analysis_bp.route('/customers/<int:customer_id>/analysis/unmatched-rules', methods=['GET'])
@require_customer_token
def get_unmatched_rules(customer_id):
    """Get rules that don't have corresponding alarms"""
    try:
        Customer.query.get_or_404(customer_id)
        unmatched_rules = Rule.query.filter(
            Rule.customer_id == customer_id,
            Rule.sig_id.isnot(None),
            ~Rule.alarms.any()
        ).all()
        return jsonify({
            'success': True,
            'unmatched_rules': [rule.to_dict() for rule in unmatched_rules],
            'count': len(unmatched_rules)
        })
    except NotFound:
        return jsonify({'success': False, 'error': 'Customer not found'}), 404
    except Exception as e:
        logger.error(f"Error getting unmatched rules for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'An error occurred while fetching unmatched rules.'}), 500

@analysis_bp.route('/customers/<int:customer_id>/analysis/unmatched-alarms', methods=['GET'])
@require_customer_token
def get_unmatched_alarms(customer_id):
    """Get alarms that don't have corresponding rules"""
    try:
        Customer.query.get_or_404(customer_id)
        unmatched_alarms = Alarm.query.filter(
            Alarm.customer_id == customer_id,
            ~Alarm.rules.any()
        ).all()
        return jsonify({
            'success': True,
            'unmatched_alarms': [alarm.to_dict() for alarm in unmatched_alarms],
            'count': len(unmatched_alarms)
        })
    except NotFound:
        return jsonify({'success': False, 'error': 'Customer not found'}), 404
    except Exception as e:
        logger.error(f"Error getting unmatched alarms for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'An error occurred while fetching unmatched alarms.'}), 500

@analysis_bp.route('/customers/<int:customer_id>/analysis/generate-missing', methods=['POST'])
@require_customer_token
def generate_missing_alarms(customer_id):
    """Generate alarms for rules that don't have them"""
    data = request.get_json() or {}
    try:
        with db.session.begin_nested():
            query = Rule.query.filter(
                Rule.customer_id == customer_id,
                Rule.sig_id.isnot(None),
                ~Rule.alarms.any()
            )
            if data.get('min_severity') is not None:
                query = query.filter(Rule.severity >= data['min_severity'])
            if data.get('max_severity') is not None:
                query = query.filter(Rule.severity <= data['max_severity'])
            if data.get('rule_types'):
                query = query.filter(Rule.rule_type.in_(data['rule_types']))
            
            unmatched_rules = query.all()
            if not unmatched_rules:
                return jsonify({'success': True, 'message': 'No unmatched rules found with the specified criteria', 'generated_count': 0})

            generator = AlarmGenerator()
            generated_alarms = []
            for rule in unmatched_rules:
                alarm_xml = generator.generate_alarm_from_rule(rule.to_dict())
                alarm = Alarm(customer_id=customer_id, name=f"Auto-Generated: {rule.name}", severity=rule.severity, match_value=f"47|{rule.sig_id}", xml_content=alarm_xml)
                db.session.add(alarm)
                db.session.flush()
                relationship = RuleAlarmRelationship(customer_id=customer_id, rule_id=rule.id, alarm_id=alarm.id, sig_id=rule.sig_id, match_value=f"47|{rule.sig_id}")
                db.session.add(relationship)
                generated_alarms.append(alarm.to_dict())

        db.session.commit()
        return jsonify({'success': True, 'message': f'Generated {len(generated_alarms)} alarms successfully', 'generated_count': len(generated_alarms), 'generated_alarms': generated_alarms})
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"DB error generating missing alarms for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'Database error during alarm generation.'}), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error generating missing alarms for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'An unexpected error occurred.'}), 500

from utils.analysis_utils import detect_relationships as detect_relationships_util

@analysis_bp.route('/customers/<int:customer_id>/analysis/detect-relationships', methods=['POST'])
@require_customer_token
def detect_relationships(customer_id):
    """Detect and create relationships between existing rules and alarms"""
    result = detect_relationships_util(customer_id)
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500

@analysis_bp.route('/customers/<int:customer_id>/analysis/report', methods=['GET'])
@require_customer_token
def generate_report(customer_id):
    """Generate HTML report for the customer"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        
        # 1. General Stats
        total_rules = Rule.query.filter_by(customer_id=customer_id).count()
        total_alarms = Alarm.query.filter_by(customer_id=customer_id).count()
        
        rules_with_sig_id = Rule.query.filter(Rule.customer_id == customer_id, Rule.sig_id.isnot(None)).count()
        rules_with_alarms = db.session.query(Rule.id).join(RuleAlarmRelationship, Rule.id == RuleAlarmRelationship.rule_id).filter(Rule.customer_id == customer_id).distinct().count()
        coverage_score = round((rules_with_alarms / rules_with_sig_id * 100), 1) if rules_with_sig_id > 0 else 0
        
        # 2. Severity Distributions
        # Rules
        rule_severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        rules = Rule.query.filter_by(customer_id=customer_id).all()
        for rule in rules:
            if rule.severity >= 90: rule_severity_counts['critical'] += 1
            elif rule.severity >= 70: rule_severity_counts['high'] += 1
            elif rule.severity >= 40: rule_severity_counts['medium'] += 1
            else: rule_severity_counts['low'] += 1
            
        total_rules_denom = len(rules) or 1
        rule_severity_pct = {k: round((v / total_rules_denom) * 100) for k, v in rule_severity_counts.items()}
        
        # Alarms
        alarm_severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        alarms = Alarm.query.filter_by(customer_id=customer_id).all()
        for alarm in alarms:
            if alarm.severity >= 90: alarm_severity_counts['critical'] += 1
            elif alarm.severity >= 70: alarm_severity_counts['high'] += 1
            elif alarm.severity >= 40: alarm_severity_counts['medium'] += 1
            else: alarm_severity_counts['low'] += 1
            
        # 3. Top Windows Events
        rule_counter = Counter()
        alarm_counter = Counter()
        
        for rule in rules:
            for event_id in get_rule_event_ids(rule):
                rule_counter[event_id] += 1
                
        for alarm in alarms:
            for event_id in get_alarm_event_ids(alarm):
                alarm_counter[event_id] += 1
                
        combined_counter = rule_counter + alarm_counter
        top_5_events = combined_counter.most_common(5)
        
        event_details_map = {
            detail['id']: detail
            for detail in get_event_details([e[0] for e in top_5_events])
        }
        
        top_events_data = []
        for event_id, count in top_5_events:
            details = event_details_map.get(event_id, {})
            top_events_data.append({
                'event_id': event_id,
                'description': details.get('description', 'Unknown Event'),
                'total_references': count
            })
            
        # 4. Render Template
        rendered_html = render_template(
            'report_template.html',
            customer_name=customer.name,
            generated_date=datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
            total_rules=f"{total_rules:,}",
            total_alarms=f"{total_alarms:,}",
            coverage_score=coverage_score,
            
            rule_severity_critical_pct=rule_severity_pct['critical'],
            rule_severity_high_pct=rule_severity_pct['high'],
            rule_severity_medium_pct=rule_severity_pct['medium'],
            rule_severity_low_pct=rule_severity_pct['low'],
            
            alarm_severity_critical_count=f"{alarm_severity_counts['critical']:,}",
            alarm_severity_high_count=f"{alarm_severity_counts['high']:,}",
            alarm_severity_medium_count=f"{alarm_severity_counts['medium']:,}",
            alarm_severity_low_count=f"{alarm_severity_counts['low']:,}",
            
            top_events=top_events_data
        )
        
        response = make_response(rendered_html)
        response.headers['Content-Type'] = 'text/html'
        response.headers['Content-Disposition'] = f'attachment; filename="analysis-report-{customer.name.replace(" ", "_")}-{datetime.utcnow().strftime("%Y%m%d")}.html"'
        return response
        
    except NotFound:
        return jsonify({'success': False, 'error': 'Customer not found'}), 404
    except Exception as e:
        logger.error(f"Error generating report for customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': f'An error occurred: {str(e)}'}), 500
