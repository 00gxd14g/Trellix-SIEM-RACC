import sys
import os
import random
from datetime import datetime, timedelta

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from models.customer import db, Customer, Rule, Alarm, RuleAlarmRelationship
from utils.audit_logger import AuditLogger, AuditAction

def create_mock_data():
    with app.app_context():
        print("Creating mock data...")
        
        # Create Demo Customer
        customer = Customer.query.filter_by(name="Demo Customer").first()
        if not customer:
            customer = Customer(
                name="Demo Customer",
                description="A sample customer for demonstration purposes.",
                contact_email="demo@example.com",
                contact_phone="+1-555-0123"
            )
            db.session.add(customer)
            db.session.commit()
            print(f"Created customer: {customer.name}")
        else:
            print(f"Customer {customer.name} already exists")

        # Create Mock Rules
        rules_data = [
            {
                "rule_id": "47-1001",
                "name": "Brute Force Attempt",
                "description": "Detects multiple failed login attempts from the same IP.",
                "severity": 80,
                "sig_id": "1001",
                "rule_type": 1,
                "xml_content": "<rule><id>47-1001</id><name>Brute Force</name></rule>"
            },
            {
                "rule_id": "47-1002",
                "name": "Malware Beaconing",
                "description": "Identifies periodic connections to known malicious domains.",
                "severity": 95,
                "sig_id": "1002",
                "rule_type": 1,
                "xml_content": "<rule><id>47-1002</id><name>Beaconing</name></rule>"
            },
            {
                "rule_id": "47-1003",
                "name": "Policy Violation: P2P",
                "description": "Detects usage of Peer-to-Peer file sharing applications.",
                "severity": 40,
                "sig_id": "1003",
                "rule_type": 2,
                "xml_content": "<rule><id>47-1003</id><name>P2P Usage</name></rule>"
            }
        ]

        for r_data in rules_data:
            if not Rule.query.filter_by(customer_id=customer.id, rule_id=r_data["rule_id"]).first():
                rule = Rule(customer_id=customer.id, **r_data)
                db.session.add(rule)
                print(f"Created rule: {rule.name}")
        
        db.session.commit()

        # Create Mock Alarms linked to Rules
        rules = Rule.query.filter_by(customer_id=customer.id).all()
        for rule in rules:
            match_value = f"47|{rule.sig_id}"
            if not Alarm.query.filter_by(customer_id=customer.id, match_value=match_value).first():
                alarm = Alarm(
                    customer_id=customer.id,
                    name=f"Alarm: {rule.name}",
                    severity=rule.severity,
                    match_value=match_value,
                    note=f"Auto-generated alarm for {rule.name}",
                    xml_content=f"<alarm><name>{rule.name}</name></alarm>"
                )
                db.session.add(alarm)
                db.session.flush()

                # Link Rule and Alarm
                rel = RuleAlarmRelationship(
                    customer_id=customer.id,
                    rule_id=rule.id,
                    alarm_id=alarm.id,
                    sig_id=rule.sig_id,
                    match_value=match_value
                )
                db.session.add(rel)
                print(f"Created alarm and relationship for: {rule.name}")

        db.session.commit()
        print("Mock data generation complete!")

if __name__ == "__main__":
    create_mock_data()
