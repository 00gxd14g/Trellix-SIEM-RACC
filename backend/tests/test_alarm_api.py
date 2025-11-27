import pytest
import json
from backend.models.customer import Customer, Alarm

@pytest.fixture
def setup_customer_with_alarm(db):
    """Fixture to create a customer and an alarm."""
    customer = Customer(name="Alarm API Customer")
    db.session.add(customer)
    db.session.commit()

    alarm = Alarm(
        customer_id=customer.id,
        name="Test Alarm for API",
        severity=90,
        match_value="47|ALARM001",
        xml_content="<alarm></alarm>"
    )
    db.session.add(alarm)
    db.session.commit()

    return customer, alarm

def test_get_alarms_for_customer(client, setup_customer_with_alarm):
    """Test getting all alarms for a specific customer."""
    customer, alarm = setup_customer_with_alarm
    response = client.get(f'/api/customers/{customer.id}/alarms',
                          headers={'X-Customer-ID': str(customer.id)})

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert len(data['alarms']) == 1
    assert data['alarms'][0]['name'] == "Test Alarm for API"

def test_get_single_alarm(client, setup_customer_with_alarm):
    """Test getting a single alarm by its ID."""
    customer, alarm = setup_customer_with_alarm
    response = client.get(f'/api/customers/{customer.id}/alarms/{alarm.id}',
                          headers={'X-Customer-ID': str(customer.id)})

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['alarm']['name'] == "Test Alarm for API"

def test_update_alarm(client, db, setup_customer_with_alarm):
    """Test updating an alarm's properties."""
    customer, alarm = setup_customer_with_alarm

    update_data = {'name': 'Updated Alarm Name', 'severity': 95}
    response = client.put(f'/api/customers/{customer.id}/alarms/{alarm.id}',
                          headers={'X-Customer-ID': str(customer.id)},
                          json=update_data)

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['alarm']['name'] == 'Updated Alarm Name'
    assert data['alarm']['severity'] == 95

    # Verify in DB
    updated_alarm = db.session.get(Alarm, alarm.id)
    assert updated_alarm.name == 'Updated Alarm Name'

def test_update_alarm_partial_none(client, db, setup_customer_with_alarm):
    """Test updating an alarm with partial data where some fields might be None (simulating issue)."""
    customer, alarm = setup_customer_with_alarm
    
    # Payload with only name, other fields implicitly None in logic if not handled
    update_data = {'name': 'Partial Update'}
    response = client.put(f'/api/customers/{customer.id}/alarms/{alarm.id}',
                          headers={'X-Customer-ID': str(customer.id)},
                          json=update_data)

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['alarm']['name'] == 'Partial Update'
    # Severity should remain unchanged
    assert data['alarm']['severity'] == 90

def test_delete_alarm(client, db, setup_customer_with_alarm):
    """Test deleting an alarm."""
    customer, alarm = setup_customer_with_alarm
    alarm_id = alarm.id

    response = client.delete(f'/api/customers/{customer.id}/alarms/{alarm_id}',
                             headers={'X-Customer-ID': str(customer.id)})

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True

    # Verify deletion
    deleted_alarm = db.session.get(Alarm, alarm_id)
    assert deleted_alarm is None
