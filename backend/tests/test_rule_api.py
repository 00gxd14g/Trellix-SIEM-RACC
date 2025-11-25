import pytest
import json
from backend.models.customer import Customer, Rule, Alarm

@pytest.fixture
def setup_customer_with_rule(db):
    """Fixture to create a customer and a rule."""
    customer = Customer(name="Rule API Customer")
    db.session.add(customer)
    db.session.commit()

    rule = Rule(
        customer_id=customer.id,
        rule_id="47-RULE001",
        name="Test Rule for API",
        severity=80,
        sig_id="RULE001",
        xml_content="<rule></rule>"
    )
    db.session.add(rule)
    db.session.commit()

    return customer, rule

def test_get_rules_for_customer(client, setup_customer_with_rule):
    """Test getting all rules for a specific customer."""
    customer, rule = setup_customer_with_rule
    response = client.get(f'/api/customers/{customer.id}/rules',
                          headers={'X-Customer-ID': str(customer.id)})

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert len(data['rules']) == 1
    assert data['rules'][0]['name'] == "Test Rule for API"

def test_get_single_rule(client, setup_customer_with_rule):
    """Test getting a single rule by its ID."""
    customer, rule = setup_customer_with_rule
    response = client.get(f'/api/customers/{customer.id}/rules/{rule.id}',
                          headers={'X-Customer-ID': str(customer.id)})

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['rule']['rule_id'] == "47-RULE001"

def test_update_rule(client, db, setup_customer_with_rule):
    """Test updating a rule's properties."""
    customer, rule = setup_customer_with_rule

    update_data = {'name': 'Updated Rule Name', 'severity': 99}
    response = client.put(f'/api/customers/{customer.id}/rules/{rule.id}',
                          headers={'X-Customer-ID': str(customer.id)},
                          json=update_data)

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['rule']['name'] == 'Updated Rule Name'
    assert data['rule']['severity'] == 99

    # Verify in DB
    updated_rule = db.session.get(Rule, rule.id)
    assert updated_rule.name == 'Updated Rule Name'

def test_delete_rule(client, db, setup_customer_with_rule):
    """Test deleting a rule."""
    customer, rule = setup_customer_with_rule
    rule_id = rule.id

    response = client.delete(f'/api/customers/{customer.id}/rules/{rule_id}',
                             headers={'X-Customer-ID': str(customer.id)})

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True

    # Verify deletion
    deleted_rule = db.session.get(Rule, rule_id)
    assert deleted_rule is None

def test_generate_alarms_from_rules(client, db, setup_customer_with_rule):
    """Test generating alarms from a selection of rules."""
    customer, rule = setup_customer_with_rule

    # Ensure no alarms exist initially
    assert db.session.query(Alarm).filter_by(customer_id=customer.id).count() == 0

    response = client.post(f'/api/customers/{customer.id}/rules/generate-alarms',
                           headers={'X-Customer-ID': str(customer.id)},
                           json={'rule_ids': [rule.id]})

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['generated_count'] == 1

    # Verify alarm was created in the DB
    alarms = db.session.query(Alarm).filter_by(customer_id=customer.id).all()
    assert len(alarms) == 1
    assert alarms[0].match_value == f"47|{rule.sig_id}"
