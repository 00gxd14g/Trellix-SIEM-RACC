import os
import sys
from lxml import etree
from flask import Flask
from models.customer import db, Customer, Rule, Alarm, RuleAlarmRelationship
from main import create_app

def create_mock_data():
    app = create_app()
    with app.app_context():
        # Clear existing data and recreate tables to apply schema changes
        print("Recreating database tables...")
        db.drop_all()
        db.create_all()

        # Create Customer
        print("Creating customer...")
        customer = Customer(
            name="Mock Corp",
            description="A mock customer for testing",
            contact_email="admin@mockcorp.com"
        )
        db.session.add(customer)
        db.session.commit()

        # Paths to XML files
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        rule_xml_path = os.path.join(base_dir, 'example-alarms-rules', 'rule-correct.xml')
        alarm_xml_path = os.path.join(base_dir, 'example-alarms-rules', 'Alarm-example.xml')

        # Parse Rules
        print(f"Parsing rules from {rule_xml_path}...")
        try:
            tree = etree.parse(rule_xml_path)
            root = tree.getroot()
            
            rules_map = {} # Map sig_id to rule object
            
            for rule_elem in root.findall('.//rule'):
                rule_id = rule_elem.find('id').text
                name = rule_elem.find('message').text
                severity = int(rule_elem.find('severity').text)
                
                # Extract SigID from rule ID (e.g., 47-6000002 -> 6000002)
                sig_id = rule_id.split('-')[-1] if '-' in rule_id else rule_id
                
                # Extract new fields
                normid = rule_elem.find('normid').text if rule_elem.find('normid') is not None else None
                print(f"Extracted normid for {rule_id}: {normid}")
                sid = int(rule_elem.find('sid').text) if rule_elem.find('sid') is not None else 0
                rule_class = int(rule_elem.find('class').text) if rule_elem.find('class') is not None else 0
                action_initial = int(rule_elem.find('action_initial').text) if rule_elem.find('action_initial') is not None else 255
                action_disallowed = int(rule_elem.find('action_disallowed').text) if rule_elem.find('action_disallowed') is not None else 0
                other_bits_default = int(rule_elem.find('other_bits_default').text) if rule_elem.find('other_bits_default') is not None else 4
                other_bits_disallowed = int(rule_elem.find('other_bits_disallowed').text) if rule_elem.find('other_bits_disallowed') is not None else 0

                # Get XML content (ruleset) from <text> tag
                # We want the inner text of the <text> tag, which is the CDATA content
                text_elem = rule_elem.find('text')
                xml_content = ""
                if text_elem is not None and text_elem.text:
                    xml_content = text_elem.text.strip()
                
                rule = Rule(
                    customer_id=customer.id,
                    rule_id=rule_id,
                    name=name,
                    description=f"Imported rule {rule_id}",
                    severity=severity,
                    sig_id=sig_id,
                    rule_type=int(rule_elem.find('type').text),
                    revision=int(rule_elem.find('revision').text),
                    origin=int(rule_elem.find('origin').text),
                    action=int(rule_elem.find('action').text),
                    normid=normid,
                    sid=sid,
                    rule_class=rule_class,
                    action_initial=action_initial,
                    action_disallowed=action_disallowed,
                    other_bits_default=other_bits_default,
                    other_bits_disallowed=other_bits_disallowed,
                    xml_content=xml_content
                )
                db.session.add(rule)
                rules_map[sig_id] = rule
                print(f"Added rule: {name} (SigID: {sig_id})")
            
            db.session.commit()
            
        except Exception as e:
            print(f"Error parsing rules: {e}")
            return

        # Parse Alarms
        print(f"Parsing alarms from {alarm_xml_path}...")
        try:
            tree = etree.parse(alarm_xml_path)
            root = tree.getroot()
            
            for alarm_elem in root.findall('alarm'):
                name = alarm_elem.get('name')
                min_version = alarm_elem.get('minVersion')
                
                alarm_data = alarm_elem.find('alarmData')
                condition_data = alarm_elem.find('conditionData')
                
                severity = int(alarm_data.find('severity').text)
                note = alarm_data.find('note').text
                assignee_id = int(alarm_data.find('assignee').text)
                esc_assignee_id = int(alarm_data.find('escAssignee').text)
                
                match_field = condition_data.find('matchField').text
                match_value = condition_data.find('matchValue').text
                condition_type = int(condition_data.find('conditionType').text)
                
                # Get full XML content for this alarm
                xml_content = etree.tostring(alarm_elem, encoding='unicode')
                
                alarm = Alarm(
                    customer_id=customer.id,
                    name=name,
                    min_version=min_version,
                    severity=severity,
                    match_field=match_field,
                    match_value=match_value,
                    condition_type=condition_type,
                    assignee_id=assignee_id,
                    esc_assignee_id=esc_assignee_id,
                    note=note,
                    xml_content=xml_content
                )
                db.session.add(alarm)
                try:
                    print(f"Added alarm: {name}")
                except UnicodeEncodeError:
                    print(f"Added alarm: {name.encode('ascii', 'replace').decode('ascii')}")
                
                # Create relationship if match_value contains a known SigID
                # match_value format is usually "47|6000002"
                if '|' in match_value:
                    sig_id_in_alarm = match_value.split('|')[-1]
                    if sig_id_in_alarm in rules_map:
                        rule = rules_map[sig_id_in_alarm]
                        rel = RuleAlarmRelationship(
                            customer_id=customer.id,
                            rule_id=rule.id,
                            alarm_id=alarm.id, # alarm.id is not available yet, need flush
                        )
                        # We need to flush to get the ID
                        db.session.flush()
                        rel.alarm_id = alarm.id
                        rel.sig_id = sig_id_in_alarm
                        rel.match_value = match_value
                        db.session.add(rel)
                        print(f"  Linked to rule: {rule.name}")

            db.session.commit()
            print("Mock data generation complete.")

        except Exception as e:
            print(f"Error parsing alarms: {e}")
            db.session.rollback()

if __name__ == '__main__':
    create_mock_data()
