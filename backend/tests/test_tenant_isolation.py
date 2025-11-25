"""
Tenant isolation test suite for the Trellix-Alarm-MNGT-WEB application.

This test suite verifies that multi-tenant isolation is properly implemented
across all components of the application, preventing cross-tenant data access.
"""

import pytest
import tempfile
import os
import json
from flask import Flask
from werkzeug.test import Client
from werkzeug.wrappers import Response

# Import your app and models
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import create_app
from models.customer import Customer, Rule, Alarm, RuleAlarmRelationship, CustomerFile


class TestTenantIsolation:
    @pytest.fixture(scope='function')
    def test_customers(self, db):
        """Create test customers."""
        customer1 = Customer(
            name="Customer 1",
            description="Test customer 1",
            contact_email="customer1@test.com"
        )
        customer2 = Customer(
            name="Customer 2",
            description="Test customer 2",
            contact_email="customer2@test.com"
        )
        db.session.add_all([customer1, customer2])
        db.session.commit()
        return {'customer1': customer1, 'customer2': customer2}

    @pytest.fixture(scope='function')
    def test_rules(self, db, test_customers):
        """Create test rules for each customer."""
        rule1 = Rule(
            customer_id=test_customers['customer1'].id,
            rule_id="47-6000001",
            name="Customer 1 Rule",
            description="Rule for customer 1",
            severity=75,
            sig_id="6000001",
            xml_content="<rule>content1</rule>"
        )
        rule2 = Rule(
            customer_id=test_customers['customer2'].id,
            rule_id="47-6000002",
            name="Customer 2 Rule",
            description="Rule for customer 2",
            severity=85,
            sig_id="6000002",
            xml_content="<rule>content2</rule>"
        )
        db.session.add_all([rule1, rule2])
        db.session.commit()
        return {'rule1': rule1, 'rule2': rule2}

    @pytest.fixture(scope='function')
    def test_alarms(self, db, test_customers):
        """Create test alarms for each customer."""
        alarm1 = Alarm(
            customer_id=test_customers['customer1'].id,
            name="Customer 1 Alarm",
            severity=75,
            match_value="47|6000001",
            xml_content="<alarm>content1</alarm>"
        )
        alarm2 = Alarm(
            customer_id=test_customers['customer2'].id,
            name="Customer 2 Alarm",
            severity=85,
            match_value="47|6000002",
            xml_content="<alarm>content2</alarm>"
        )
        db.session.add_all([alarm1, alarm2])
        db.session.commit()
        return {'alarm1': alarm1, 'alarm2': alarm2}

    def test_customer_header_validation(self, client, test_customers):
        """Test that X-Customer-ID header is properly validated."""
        customer1_id = test_customers['customer1'].id
        customer2_id = test_customers['customer2'].id
        # Valid request with matching header and URL
        response = client.get(
            f'/api/customers/{customer1_id}',
            headers={'X-Customer-ID': str(customer1_id)}
        )
        assert response.status_code == 200
        # Invalid request with mismatched header and URL
        response = client.get(
            f'/api/customers/{customer1_id}',
            headers={'X-Customer-ID': str(customer2_id)}
        )
        assert response.status_code == 403
        assert b'Customer ID mismatch' in response.data
        # Request without header
        response = client.get(f'/api/customers/{customer1_id}')
        assert response.status_code == 403
        assert b'Missing X-Customer-ID header' in response.data

    def test_rule_tenant_isolation(self, client, test_customers, test_rules):
        """Test that rules are properly isolated by tenant."""
        customer1_id = test_customers['customer1'].id
        customer2_id = test_customers['customer2'].id
        rule2_id = test_rules['rule2'].id
        # Customer 1 should only see their own rules
        response = client.get(
            f'/api/customers/{customer1_id}/rules',
            headers={'X-Customer-ID': str(customer1_id)}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['rules']) == 1
        assert data['rules'][0]['name'] == "Customer 1 Rule"
        # Customer 1 should not be able to access Customer 2's rule
        response = client.get(
            f'/api/customers/{customer1_id}/rules/{rule2_id}',
            headers={'X-Customer-ID': str(customer1_id)}
        )
        assert response.status_code == 404
        # Customer 2 cannot access Customer 1's data even with correct header
        response = client.get(
            f'/api/customers/{customer1_id}/rules',
            headers={'X-Customer-ID': str(customer2_id)}
        )
        assert response.status_code == 403

    def test_alarm_tenant_isolation(self, client, test_customers, test_alarms):
        """Test that alarms are properly isolated by tenant."""
        customer1_id = test_customers['customer1'].id
        alarm2_id = test_alarms['alarm2'].id
        # Customer 1 should only see their own alarms
        response = client.get(
            f'/api/customers/{customer1_id}/alarms',
            headers={'X-Customer-ID': str(customer1_id)}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['alarms']) == 1
        assert data['alarms'][0]['name'] == "Customer 1 Alarm"
        # Customer 1 should not be able to access Customer 2's alarm
        response = client.get(
            f'/api/customers/{customer1_id}/alarms/{alarm2_id}',
            headers={'X-Customer-ID': str(customer1_id)}
        )
        assert response.status_code == 404

    def test_relationship_tenant_isolation(self, db, client, test_customers, test_rules, test_alarms):
        """Test that rule-alarm relationships are properly isolated by tenant."""
        customer1_id = test_customers['customer1'].id
        customer2_id = test_customers['customer2'].id
        # Create relationships for each customer
        rel1 = RuleAlarmRelationship(
            customer_id=customer1_id,
            rule_id=test_rules['rule1'].id,
            alarm_id=test_alarms['alarm1'].id,
            sig_id="6000001",
            match_value="47|6000001"
        )
        rel2 = RuleAlarmRelationship(
            customer_id=customer2_id,
            rule_id=test_rules['rule2'].id,
            alarm_id=test_alarms['alarm2'].id,
            sig_id="6000002",
            match_value="47|6000002"
        )
        db.session.add_all([rel1, rel2])
        db.session.commit()
        # Customer 1 should only see their own relationships
        response = client.get(
            f'/api/customers/{customer1_id}/analysis/relationships',
            headers={'X-Customer-ID': str(customer1_id)}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['relationships']) == 1
        assert data['relationships'][0]['sig_id'] == "6000001"

    def test_file_tenant_isolation(self, db, client, test_customers, app):
        """Test that file operations are properly isolated by tenant."""
        customer1_id = test_customers['customer1'].id
        customer2_id = test_customers['customer2'].id
        # Create test files for each customer
        from utils.file_utils import get_secure_file_path, generate_secure_filename
        filename1 = generate_secure_filename(customer1_id, "test1.xml", "rule")
        filepath1 = get_secure_file_path(customer1_id, filename1)
        os.makedirs(os.path.dirname(filepath1), exist_ok=True)
        with open(filepath1, 'w') as f:
            f.write("<rules><rule>content1</rule></rules>")
        file1 = CustomerFile(
            customer_id=customer1_id,
            file_type="rule",
            filename="test1.xml",
            file_path=filepath1,
            file_size=100
        )
        filename2 = generate_secure_filename(customer2_id, "test2.xml", "rule")
        filepath2 = get_secure_file_path(customer2_id, filename2)
        os.makedirs(os.path.dirname(filepath2), exist_ok=True)
        with open(filepath2, 'w') as f:
            f.write("<rules><rule>content2</rule></rules>")
        file2 = CustomerFile(
            customer_id=customer2_id,
            file_type="rule",
            filename="test2.xml",
            file_path=filepath2,
            file_size=100
        )
        db.session.add_all([file1, file2])
        db.session.commit()
        # Customer 1 should only see their own files
        response = client.get(
            f'/api/customers/{customer1_id}/files',
            headers={'X-Customer-ID': str(customer1_id)}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['files']) == 1
        assert data['files'][0]['filename'] == "test1.xml"

    def test_analysis_tenant_isolation(self, client, test_customers, test_rules, test_alarms):
        """Test that analysis endpoints are properly isolated by tenant."""
        customer1_id = test_customers['customer1'].id
        # Test coverage analysis isolation
        response = client.get(
            f'/api/customers/{customer1_id}/analysis/coverage',
            headers={'X-Customer-ID': str(customer1_id)}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['coverage']['total_rules'] == 1
        # Test unmatched rules isolation
        response = client.get(
            f'/api/customers/{customer1_id}/analysis/unmatched-rules',
            headers={'X-Customer-ID': str(customer1_id)}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_database_constraints_isolation(self, db, app, test_customers):
        """Test that database constraints enforce tenant isolation."""
        customer1_id = test_customers['customer1'].id
        customer2_id = test_customers['customer2'].id
        # Test unique constraint across tenants
        rule1 = Rule(
            customer_id=customer1_id,
            rule_id="47-6000999",
            name="Same Rule ID Different Customer",
            description="Test rule",
            severity=50,
            xml_content="<rule>test</rule>"
        )
        rule2 = Rule(
            customer_id=customer2_id,
            rule_id="47-6000999",
            name="Same Rule ID Different Customer 2",
            description="Test rule 2",
            severity=60,
            xml_content="<rule>test2</rule>"
        )
        db.session.add_all([rule1, rule2])
        db.session.commit()
        # Verify both rules exist
        assert Rule.query.filter_by(customer_id=customer1_id, rule_id="47-6000999").first() is not None
        assert Rule.query.filter_by(customer_id=customer2_id, rule_id="47-6000999").first() is not None

    def test_cross_tenant_data_modification_prevention(self, client, test_customers, test_rules):
        """Test that tenants cannot modify each other's data."""
        customer1_id = test_customers['customer1'].id
        rule2_id = test_rules['rule2'].id
        # Customer 1 tries to update Customer 2's rule
        response = client.put(
            f'/api/customers/{customer1_id}/rules/{rule2_id}',
            headers={'X-Customer-ID': str(customer1_id)},
            json={'name': 'Modified Rule Name'}
        )
        assert response.status_code == 404
        # Verify the rule was not modified
        with client.application.app_context():
            rule = Rule.query.get(rule2_id)
            assert rule.name == "Customer 2 Rule"

    def test_cross_tenant_deletion_prevention(self, db, client, test_customers, test_rules, test_alarms):
        """Test that tenants cannot delete each other's data."""
        customer1_id = test_customers['customer1'].id
        customer2_id = test_customers['customer2'].id
        rule2_id = test_rules['rule2'].id
        alarm2_id = test_alarms['alarm2'].id
        # Create a relationship for customer 2
        rel = RuleAlarmRelationship(
            customer_id=customer2_id,
            rule_id=rule2_id,
            alarm_id=alarm2_id,
            sig_id="6000002",
            match_value="47|6000002"
        )
        db.session.add(rel)
        db.session.commit()
        rel_id = rel.id
        # Customer 1 tries to delete Customer 2's rule
        response = client.delete(
            f'/api/customers/{customer1_id}/rules/{rule2_id}',
            headers={'X-Customer-ID': str(customer1_id)}
        )
        assert response.status_code == 404
        # Verify the rule and relationship still exist
        with client.application.app_context():
            rule = Rule.query.get(rule2_id)
            assert rule is not None
            relationship = RuleAlarmRelationship.query.get(rel_id)
            assert relationship is not None

if __name__ == '__main__':
    pytest.main([__file__, '-v'])