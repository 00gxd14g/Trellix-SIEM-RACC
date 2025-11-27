from models.customer import db, Rule, Alarm, RuleAlarmRelationship
import logging

logger = logging.getLogger(__name__)

def detect_relationships(customer_id):
    """Detect and create relationships between existing rules and alarms"""
    try:
        with db.session.begin_nested():
            rules = Rule.query.filter(Rule.customer_id == customer_id, Rule.sig_id.isnot(None)).all()
            alarms = Alarm.query.filter_by(customer_id=customer_id).all()
            new_relationships = []
            
            # Create a map of alarms by match_value for faster lookup
            # Note: Multiple alarms might have the same match_value, so we use a list
            alarms_by_match_value = {}
            for alarm in alarms:
                if alarm.match_value:
                    if alarm.match_value not in alarms_by_match_value:
                        alarms_by_match_value[alarm.match_value] = []
                    alarms_by_match_value[alarm.match_value].append(alarm)
            
            for rule in rules:
                # Determine prefix from rule_id (e.g. "47-6000114" -> "47")
                prefix = "47"
                if rule.rule_id and '-' in rule.rule_id:
                    parts = rule.rule_id.split('-')
                    if parts[0].isdigit():
                        prefix = parts[0]
                
                expected_match_value = f"{prefix}|{rule.sig_id}"
                
                # Check if we have alarms matching this rule
                matching_alarms = alarms_by_match_value.get(expected_match_value, [])
                
                for alarm in matching_alarms:
                    # Check if relationship already exists
                    existing_rel = RuleAlarmRelationship.query.filter_by(
                        rule_id=rule.id, 
                        alarm_id=alarm.id
                    ).first()
                    
                    if not existing_rel:
                        relationship = RuleAlarmRelationship(
                            customer_id=customer_id, 
                            rule_id=rule.id, 
                            alarm_id=alarm.id, 
                            sig_id=rule.sig_id, 
                            match_value=expected_match_value,
                            relationship_type='sig_id_match'
                        )
                        db.session.add(relationship)
                        new_relationships.append({
                            'rule_id': rule.id,
                            'alarm_id': alarm.id,
                            'sig_id': rule.sig_id,
                            'match_value': expected_match_value
                        })
                        
        db.session.commit()
        return {
            'success': True, 
            'message': f'Detected {len(new_relationships)} new relationships', 
            'new_relationships': new_relationships, 
            'relationship_count': len(new_relationships)
        }
    except Exception as e:
        logger.error(f"Error detecting relationships for customer {customer_id}: {e}")
        # Don't raise, just return error dict so caller can handle gracefully
        return {'success': False, 'error': str(e)}
