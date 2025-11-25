import pytest
import json
from backend.models.customer import Customer, CustomerFile

def test_create_customer(client):
    """Test creating a new customer."""
    response = client.post('/api/customers', json={
        'name': 'New API Customer',
        'description': 'A customer created via API test.'
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['success'] is True
    assert data['customer']['name'] == 'New API Customer'

def test_update_customer(client, db):
    """Test updating an existing customer."""
    customer = Customer(name="Customer to Update")
    db.session.add(customer)
    db.session.commit()

    response = client.put(f'/api/customers/{customer.id}',
                          headers={'X-Customer-ID': str(customer.id)},
                          json={'name': 'Updated Customer Name'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['customer']['name'] == 'Updated Customer Name'

    # Verify the change in the database
    updated_customer = db.session.get(Customer, customer.id)
    assert updated_customer.name == 'Updated Customer Name'

def test_delete_customer(client, db):
    """Test deleting a customer."""
    customer = Customer(name="Customer to Delete")
    db.session.add(customer)
    db.session.commit()
    customer_id = customer.id

    response = client.delete(f'/api/customers/{customer_id}',
                             headers={'X-Customer-ID': str(customer_id)})
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True

    # Verify the customer is deleted from the database
    deleted_customer = db.session.get(Customer, customer_id)
    assert deleted_customer is None

def test_get_customer_files(client, db):
    """Test getting a list of files for a customer."""
    customer = Customer(name="File Customer")
    db.session.add(customer)
    db.session.commit()

    file = CustomerFile(customer_id=customer.id, filename="test.xml", file_type="rule", file_path="/fake/path")
    db.session.add(file)
    db.session.commit()

    response = client.get(f'/api/customers/{customer.id}/files',
                          headers={'X-Customer-ID': str(customer.id)})

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert len(data['files']) == 1
    assert data['files'][0]['filename'] == 'test.xml'

def test_update_customer_case_insensitive_duplicate(client, db):
    """Test updating a customer with a case-insensitive duplicate name."""
    customer1 = Customer(name="Unique Customer")
    customer2 = Customer(name="Another Customer")
    db.session.add(customer1)
    db.session.add(customer2)
    db.session.commit()

    response = client.put(
        f'/api/customers/{customer2.id}',
        headers={'X-Customer-ID': str(customer2.id)},
        json={'name': 'unique customer'}  # Case-insensitive duplicate
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert 'already exists' in data['error']

def test_create_customer_case_insensitive_duplicate(client, db):
    """Test creating a customer with a case-insensitive duplicate name."""
    customer = Customer(name="Existing Customer")
    db.session.add(customer)
    db.session.commit()

    response = client.post('/api/customers', json={
        'name': 'existing customer',  # Case-insensitive duplicate
        'description': 'This should fail.'
    })

    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert 'already exists' in data['error']
