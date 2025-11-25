import pytest
import json
from backend.models.customer import Customer, Rule, Alarm, RuleAlarmRelationship

@pytest.fixture
def setup_analysis_data(db):
    """Fixture to create a customer with a mix of matched and unmatched rules/alarms."""
    customer = Customer(name="Analysis API Customer")
    db.session.add(customer)
    db.session.commit()

    # Matched rule and alarm
    rule1 = Rule(customer_id=customer.id, rule_id="47-MATCH01", name="Matched Rule", sig_id="MATCH01", xml_content="<rule></rule>", severity=70)
    alarm1 = Alarm(customer_id=customer.id, name="Matched Alarm", match_value="47|MATCH01", xml_content="<alarm></alarm>", severity=70)

    # Unmatched rule
    rule2 = Rule(customer_id=customer.id, rule_id="47-UNMATCH02", name="Unmatched Rule", sig_id="UNMATCH02", xml_content="<rule></rule>", severity=80)

    # Unmatched alarm
    alarm2 = Alarm(customer_id=customer.id, name="Unmatched Alarm", match_value="47|UNMATCH03", xml_content="<alarm></alarm>", severity=90)

    db.session.add_all([rule1, alarm1, rule2, alarm2])
    db.session.commit()

    # Relationship
    rel = RuleAlarmRelationship(customer_id=customer.id, rule_id=rule1.id, alarm_id=alarm1.id, sig_id="MATCH01", match_value="47|MATCH01")
    db.session.add(rel)
    db.session.commit()

    customer._test_primary_rule_id = rule1.id  # for test assertions

    return customer


@pytest.fixture
def setup_event_usage_data(db):
    customer = Customer(name="Event Usage Customer")
    db.session.add(customer)
    db.session.commit()

    rule = Rule(
        customer_id=customer.id,
        rule_id="47-263047680",
        name="Kerberos TGT Requested",
        sig_id="263047680",
        xml_content="<rule></rule>",
        severity=60
    )

    alarm = Alarm(
        customer_id=customer.id,
        name="Kerberos TGT Alarm",
        match_value="47|263047680",
        xml_content="<alarm></alarm>",
        severity=60
    )

    db.session.add_all([rule, alarm])
    db.session.commit()

    relationship = RuleAlarmRelationship(
        customer_id=customer.id,
        rule_id=rule.id,
        alarm_id=alarm.id,
        sig_id="263047680",
        match_value="47|263047680"
    )
    db.session.add(relationship)
    db.session.commit()

    return customer

def test_get_coverage_analysis(client, setup_analysis_data):
    """Test the rule coverage analysis endpoint."""
    customer = setup_analysis_data
    response = client.get(f'/api/customers/{customer.id}/analysis/coverage',
                          headers={'X-Customer-ID': str(customer.id)})

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['coverage']['total_rules'] == 2
    assert data['coverage']['matched_rules'] == 1
    assert data['coverage']['coverage_percentage'] == 50.0

def test_get_unmatched_rules(client, setup_analysis_data):
    """Test the unmatched rules analysis endpoint."""
    customer = setup_analysis_data
    response = client.get(f'/api/customers/{customer.id}/analysis/unmatched-rules',
                          headers={'X-Customer-ID': str(customer.id)})

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert len(data['unmatched_rules']) == 1
    assert data['unmatched_rules'][0]['name'] == "Unmatched Rule"

def test_get_unmatched_alarms(client, setup_analysis_data):
    """Test the unmatched alarms analysis endpoint."""
    customer = setup_analysis_data
    response = client.get(f'/api/customers/{customer.id}/analysis/unmatched-alarms',
                          headers={'X-Customer-ID': str(customer.id)})

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert len(data['unmatched_alarms']) == 1
    assert data['unmatched_alarms'][0]['name'] == "Unmatched Alarm"

def test_get_relationships(client, setup_analysis_data, db):
    """Test the rule-alarm relationships endpoint."""
    customer = setup_analysis_data
    response = client.get(f'/api/customers/{customer.id}/analysis/relationships',
                          headers={'X-Customer-ID': str(customer.id)})

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert len(data['relationships']) == 1
    relationship = data['relationships'][0]
    assert relationship['sig_id'] == "MATCH01"

    # Ensure human-readable rule identifier is included
    assert relationship['rule_identifier'] == "47-MATCH01"

    # Underlying database ID remains available for compatibility
    assert relationship['rule_id'] == getattr(customer, '_test_primary_rule_id')


def test_get_event_usage(client, setup_event_usage_data):
    customer = setup_event_usage_data
    response = client.get(
        f'/api/customers/{customer.id}/analysis/event-usage',
        headers={'X-Customer-ID': str(customer.id)}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['event_usage']['total_unique_events'] == 1
    assert len(data['event_usage']['events']) == 1
    event_entry = data['event_usage']['events'][0]
    assert event_entry['event_id'] == '4768'
    assert event_entry['rule_count'] == 1
    assert event_entry['alarm_count'] == 1
    assert event_entry['total_references'] == 2


def test_event_usage_limit_and_sorting(client, setup_event_usage_data, app, db):
    customer = setup_event_usage_data

    with app.app_context():
        # Add another rule referencing a different Windows event
        rule_extra = Rule(
            customer_id=customer.id,
            rule_id="47-EXTRA",
            name="Extra Rule",
            sig_id="263047690",
            xml_content="<rule></rule>",
            severity=50,
        )
        db.session.add(rule_extra)

        # Add an alarm that references the original event to push its count higher
        alarm_extra = Alarm(
            customer_id=customer.id,
            name="Extra Alarm",
            severity=60,
            match_value="47|EXTRA",
            xml_content="<alarm><filters><filterData name=\"value\" value=\"43-263047680\"/></filters></alarm>",
        )
        db.session.add(alarm_extra)
        db.session.commit()

    # Request only the top event ID
    top_only = client.get(
        f'/api/customers/{customer.id}/analysis/event-usage?limit=1',
        headers={'X-Customer-ID': str(customer.id)}
    )
    assert top_only.status_code == 200
    top_payload = top_only.get_json()['event_usage']
    assert top_payload['total_unique_events'] >= 2
    assert len(top_payload['events']) == 1

    top_entry = top_payload['events'][0]
    # Event 4768 should remain first because it now has higher references (2 rules/2 alarms)
    assert top_entry['event_id'] == '4768'
    assert top_entry['total_references'] == top_entry['rule_count'] + top_entry['alarm_count']
    assert top_entry['rule_count'] >= 1
    assert top_entry['description']  # metadata pulled from mapping file

    # Request all events and ensure the second one corresponds to the new rule
    full_resp = client.get(
        f'/api/customers/{customer.id}/analysis/event-usage',
        headers={'X-Customer-ID': str(customer.id)}
    )
    assert full_resp.status_code == 200
    events = full_resp.get_json()['event_usage']['events']
    assert any(entry['event_id'] == '4769' for entry in events)
