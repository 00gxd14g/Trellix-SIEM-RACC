from models.customer import Customer
from main import create_app

def verify_export():
    app = create_app()
    with app.app_context():
        customer = Customer.query.filter_by(name="Mock Corp").first()
        if not customer:
            print("Customer not found")
            return
        
        headers = {'X-Customer-ID': str(customer.id)}
        client = app.test_client()
        
        print(f"Exporting rules for customer {customer.id}...")
        response = client.get(f'/api/customers/{customer.id}/rules/export', headers=headers)
        
        if response.status_code == 200:
            print("Rule Export successful!")
            print("--- XML OUTPUT START ---")
            print(response.data.decode('utf-8'))
            print("--- XML OUTPUT END ---")
            
            xml_content = response.data.decode('utf-8')
            if '<nitro_policy' in xml_content and 'esm="6F26:4000"' in xml_content:
                print("Basic Rule XML structure verified.")
            else:
                print("Rule XML structure verification failed.")
                
            if '<normid>4026531840</normid>' in xml_content:
                print("normid verified.")
            else:
                print("normid NOT found.")
                
            if '<action_initial>255</action_initial>' in xml_content:
                print("action_initial verified.")
            else:
                print("action_initial NOT found.")
                
            if '<![CDATA[<ruleset' in xml_content:
                print("CDATA ruleset verified.")
            else:
                print("CDATA ruleset NOT found.")

        else:
            print(f"Rule Export failed with status {response.status_code}")
            print(response.data.decode('utf-8'))

if __name__ == '__main__':
    verify_export()
