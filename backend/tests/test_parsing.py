import os
import pytest
from models.customer import Customer, Rule

def test_rule_parsing_via_upload(client, db, app):
    """
    Test that a rule file is correctly parsed and stored in the database
    after being uploaded via the API.
    """
    # 1. Create a test customer
    customer = Customer(name="Parsing Test Customer")
    db.session.add(customer)
    db.session.commit()

    # 2. Create a dummy rule XML file
    xml_content = """
    <nitro_policy>
        <rules count="1">
            <rule>
                <id>47-12345</id>
                <message>Test Rule</message>
                <description>A test rule for parsing</description>
                <severity>80</severity>
                <text><![CDATA[
                    <ruleset id="47-12345" name="Test Rule">
                        <property>
                            <n>sigid</n>
                            <value>12345</value>
                        </property>
                    </ruleset>
                ]]></text>
            </rule>
        </rules>
    </nitro_policy>
    """
    # Create a temporary file in the test upload directory
    customer_upload_dir = os.path.join(app.config['UPLOAD_DIR'], str(customer.id))
    os.makedirs(customer_upload_dir, exist_ok=True)
    file_path = os.path.join(customer_upload_dir, 'test_rule.xml')
    with open(file_path, 'w') as f:
        f.write(xml_content)

    # 3. Simulate file upload
    with open(file_path, 'rb') as f:
        data = {
            'file': (f, 'test_rule.xml'),
            'file_type': 'rule'
        }
        response = client.post(
            f'/api/customers/{customer.id}/files/upload',
            headers={'X-Customer-ID': str(customer.id)},
            content_type='multipart/form-data',
            data=data
        )

    # 4. Assert the response
    assert response.status_code == 201
    json_response = response.get_json()
    assert json_response['success'] is True
    assert 'file' in json_response
    assert 'rules_added' in json_response
    assert json_response['rules_added'] == 1

    # 5. Assert the database state
    rules = Rule.query.filter_by(customer_id=customer.id).all()
    assert len(rules) == 1
    rule = rules[0]
    assert rule.rule_id == '47-12345'
    assert rule.sig_id == '12345'
    assert rule.name == 'Test Rule'
    assert rule.severity == 80