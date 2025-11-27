import os
import re
from html import escape
from lxml import etree
from typing import Dict, List, Optional, Tuple, Any


def _create_text_element(parent, tag: str, value: Optional[str]):
    if value is None:
        return None
    elem = etree.SubElement(parent, tag)
    elem.text = value
    return elem


def generate_rules_xml(rules: List[Any]) -> str:
    """Generate a normalized rule export XML from database models."""
    root = etree.Element('nitro_policy', 
                         esm="6F26:4000", 
                         time="06/05/2025 16:48:08",
                         user="NGCP", 
                         build="11.6.14 20250324053645",
                         model="ETM-VM4", 
                         version="11006014")
    rules_container = etree.SubElement(root, 'rules')
    rules_container.set('count', str(len(rules)))

    for rule in rules:
        rule_elem = etree.SubElement(rules_container, 'rule')
        _create_text_element(rule_elem, 'id', rule.rule_id)
        _create_text_element(rule_elem, 'normid', rule.normid)
        if rule.revision is not None:
            _create_text_element(rule_elem, 'revision', str(rule.revision))
        _create_text_element(rule_elem, 'sid', str(rule.sid) if rule.sid is not None else '0')
        _create_text_element(rule_elem, 'class', str(rule.rule_class) if rule.rule_class is not None else '0')
        _create_text_element(rule_elem, 'message', rule.name)
        _create_text_element(rule_elem, 'description', rule.description or '')
        if rule.origin is not None:
            _create_text_element(rule_elem, 'origin', str(rule.origin))
        if rule.severity is not None:
            _create_text_element(rule_elem, 'severity', str(rule.severity))
        if rule.rule_type is not None:
            _create_text_element(rule_elem, 'type', str(rule.rule_type))
        if rule.action is not None:
            _create_text_element(rule_elem, 'action', str(rule.action))
        
        _create_text_element(rule_elem, 'action_initial', str(rule.action_initial) if rule.action_initial is not None else '255')
        _create_text_element(rule_elem, 'action_disallowed', str(rule.action_disallowed) if rule.action_disallowed is not None else '0')
        _create_text_element(rule_elem, 'other_bits_default', str(rule.other_bits_default) if rule.other_bits_default is not None else '4')
        _create_text_element(rule_elem, 'other_bits_disallowed', str(rule.other_bits_disallowed) if rule.other_bits_disallowed is not None else '0')

        text_elem = etree.SubElement(rule_elem, 'text')
        
        # Ensure consistency between outer ID and inner sigid property
        xml_content = rule.xml_content
        if xml_content and rule.sig_id:
            try:
                # Parse the inner XML
                inner_root = etree.fromstring(xml_content.encode('utf-8'))
                
                # Update ruleset ID
                if 'id' in inner_root.attrib and rule.rule_id:
                    inner_root.set('id', rule.rule_id)
                
                # Update sigid property
                # Look for <property><name>sigid</name><value>...</value></property>
                for prop in inner_root.findall('.//property'):
                    name_elem = prop.find('name')
                    if name_elem is not None and name_elem.text == 'sigid':
                        value_elem = prop.find('value')
                        if value_elem is not None:
                            value_elem.text = str(rule.sig_id)
                        break
                
                # Serialize back to string
                xml_content = etree.tostring(inner_root, encoding='utf-8').decode('utf-8')
            except Exception as e:
                # If parsing fails, fallback to original content but log/print error (or just ignore for now)
                pass

        if xml_content:
            text_elem.text = etree.CDATA(xml_content)
        else:
            placeholder = f"<ruleset id=\"{rule.rule_id or ''}\" name=\"{rule.name or ''}\"></ruleset>"
            text_elem.text = etree.CDATA(placeholder)

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='utf-8').decode('utf-8')


def generate_alarms_xml(alarms: List[Any]) -> str:
    """Generate alarm export XML from database models."""
    root = etree.Element('alarms')

    for alarm in alarms:
        if alarm.xml_content:
            try:
                alarm_node = etree.fromstring(alarm.xml_content.encode('utf-8'))
            except etree.XMLSyntaxError:
                alarm_node = etree.Element('alarm')
                if alarm.name:
                    alarm_node.set('name', alarm.name)
        else:
            alarm_node = etree.Element('alarm')
            if alarm.name:
                alarm_node.set('name', alarm.name)

        if not alarm_node.get('name') and alarm.name:
            alarm_node.set('name', alarm.name)
        if alarm.min_version:
            alarm_node.set('minVersion', alarm.min_version)

        alarm_data = alarm_node.find('alarmData')
        if alarm_data is None:
            alarm_data = etree.SubElement(alarm_node, 'alarmData')
        if alarm.severity is not None and alarm_data.find('severity') is None:
            _create_text_element(alarm_data, 'severity', str(alarm.severity))
        if alarm.note and alarm_data.find('note') is None:
            _create_text_element(alarm_data, 'note', alarm.note)
        if alarm.assignee_id and alarm_data.find('assignee') is None:
            _create_text_element(alarm_data, 'assignee', str(alarm.assignee_id))
        if alarm.esc_assignee_id and alarm_data.find('escAssignee') is None:
            _create_text_element(alarm_data, 'escAssignee', str(alarm.esc_assignee_id))

        condition_data = alarm_node.find('conditionData')
        if condition_data is None:
            condition_data = etree.SubElement(alarm_node, 'conditionData')
        if alarm.match_field and condition_data.find('matchField') is None:
            _create_text_element(condition_data, 'matchField', alarm.match_field)
        if alarm.match_value and condition_data.find('matchValue') is None:
            _create_text_element(condition_data, 'matchValue', alarm.match_value)
        if alarm.condition_type is not None and condition_data.find('conditionType') is None:
            _create_text_element(condition_data, 'conditionType', str(alarm.condition_type))

        root.append(alarm_node)

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='utf-8').decode('utf-8')

class XMLValidator:
    """XML validation utility for McAfee SIEM rule and alarm files"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_xml_structure(self, xml_content: str) -> Tuple[bool, List[str], List[str]]:
        """Validate basic XML structure"""
        self.errors = []
        self.warnings = []
        
        try:
            # Parse XML content
            root = etree.fromstring(xml_content.encode('utf-8'))
            return True, self.errors, self.warnings
        except etree.XMLSyntaxError as e:
            self.errors.append(f"XML Syntax Error: {str(e)}")
            return False, self.errors, self.warnings
        except Exception as e:
            self.errors.append(f"XML Parsing Error: {str(e)}")
            return False, self.errors, self.warnings
    
    def validate_rule_xml(self, file_path: str) -> Dict[str, Any]:
        """Validate rule.xml file structure and content using iterparse."""
        self.errors = []
        self.warnings = []
        rule_count = 0
        
        try:
            context = etree.iterparse(file_path, events=('end',), tag=('nitro_policy', 'rules', 'rule'))
            
            for event, elem in context:
                if elem.tag == 'rule':
                    rule_count += 1
                    self._validate_rule_element(elem, rule_count)
                    elem.clear()
            
            if rule_count == 0:
                self.warnings.append("No rules found in the file")

            # A full validation would require checking root element etc.
            # This streaming validation focuses on the rule elements themselves.
            # A schema-based validation (XSD) would be more robust for full structure.
            
            return {
                'valid': len(self.errors) == 0,
                'errors': self.errors,
                'warnings': self.warnings
            }

        except etree.XMLSyntaxError as e:
            self.errors.append(f"XML Syntax Error: {str(e)}")
            return {'valid': False, 'errors': self.errors, 'warnings': self.warnings}
        except Exception as e:
            self.errors.append(f"Validation Error: {str(e)}")
            return {'valid': False, 'errors': self.errors, 'warnings': self.warnings}
    
    def validate_alarm_xml(self, file_path: str) -> Dict[str, Any]:
        """Validate alarm.xml file structure and content using iterparse."""
        self.errors = []
        self.warnings = []
        alarm_count = 0
        
        try:
            context = etree.iterparse(file_path, events=('end',), tag='alarm')
            
            for event, elem in context:
                alarm_count += 1
                self._validate_alarm_element(elem, alarm_count)
                elem.clear()

            if alarm_count == 0:
                self.warnings.append("No alarms found in the file")

            return {
                'valid': len(self.errors) == 0,
                'errors': self.errors,
                'warnings': self.warnings
            }

        except etree.XMLSyntaxError as e:
            self.errors.append(f"XML Syntax Error: {str(e)}")
            return {'valid': False, 'errors': self.errors, 'warnings': self.warnings}
        except Exception as e:
            self.errors.append(f"Validation Error: {str(e)}")
            return {'valid': False, 'errors': self.errors, 'warnings': self.warnings}
    
    def _validate_rule_element(self, rule_element, rule_number: int):
        """Validate individual rule element"""
        prefix = f"Rule {rule_number}: "
        
        # Check required elements
        required_elements = ['id', 'message', 'severity', 'text']
        for elem_name in required_elements:
            elem = rule_element.find(elem_name)
            if elem is None:
                self.errors.append(f"{prefix}Missing required element '{elem_name}'")
            elif elem.text is None or elem.text.strip() == '':
                self.errors.append(f"{prefix}Element '{elem_name}' is empty")
        
        # Validate severity
        severity_elem = rule_element.find('severity')
        if severity_elem is not None and severity_elem.text:
            try:
                severity = int(severity_elem.text)
                if severity < 0 or severity > 100:
                    self.errors.append(f"{prefix}Severity must be between 0 and 100, got {severity}")
            except ValueError:
                self.errors.append(f"{prefix}Severity must be a number, got '{severity_elem.text}'")
        
        # Validate CDATA content and SigID availability
        text_elem = rule_element.find('text')
        if text_elem is not None and text_elem.text:
            self._validate_rule_cdata(text_elem.text, rule_number)
        
        # Check if SigID is available either from rule ID or CDATA
        has_sigid = False
        
        # Check if rule ID contains SigID (format: "47-6000114")
        id_elem = rule_element.find('id')
        if id_elem is not None and id_elem.text:
            import re
            match = re.search(r'(\d+)$', id_elem.text)
            if match:
                has_sigid = True
        
        # If not in rule ID, check CDATA
        if not has_sigid and text_elem is not None and text_elem.text:
            if self._extract_sig_id(text_elem.text):
                has_sigid = True
        
        if not has_sigid:
            prefix = f"Rule {rule_number}: "
            self.errors.append(f"{prefix}Missing SigID (not found in rule ID or CDATA properties)")
    
    def _validate_rule_cdata(self, cdata_content: str, rule_number: int):
        """Validate CDATA content in rule"""
        prefix = f"Rule {rule_number} CDATA: "
        
        try:
            # Parse CDATA content as XML
            cdata_root = etree.fromstring(cdata_content.encode('utf-8'))
            
            # Check if it's a ruleset
            if cdata_root.tag != 'ruleset':
                self.errors.append(f"{prefix}CDATA content must contain a 'ruleset' element")
                return
            
            # Check for sigid property (optional since it can come from rule ID)
            properties = cdata_root.findall('.//property')
            for prop in properties:
                # Check for 'n' or 'name' tag for property name
                n_elem = prop.find('n')
                if n_elem is None:
                    n_elem = prop.find('name')
                
                if n_elem is not None and n_elem.text == 'sigid':
                    value_elem = prop.find('value')
                    if value_elem is None or not value_elem.text:
                        self.errors.append(f"{prefix}SigID property has no value")
                    break
            
            # Note: We no longer require sigid in CDATA since it can come from rule ID
                
        except etree.XMLSyntaxError as e:
            self.errors.append(f"{prefix}Invalid XML in CDATA: {str(e)}")
        except Exception as e:
            self.errors.append(f"{prefix}CDATA validation error: {str(e)}")
    
    def _validate_alarm_element(self, alarm_element, alarm_number: int):
        """Validate individual alarm element"""
        prefix = f"Alarm {alarm_number}: "
        
        # Check required attributes
        if 'name' not in alarm_element.attrib:
            self.errors.append(f"{prefix}Missing required 'name' attribute")
        
        # Check alarmData
        alarm_data = alarm_element.find('alarmData')
        if alarm_data is None:
            self.errors.append(f"{prefix}Missing 'alarmData' element")
        else:
            # Validate severity in alarmData
            severity_elem = alarm_data.find('severity')
            if severity_elem is not None and severity_elem.text:
                try:
                    severity = int(severity_elem.text)
                    if severity < 0 or severity > 100:
                        self.errors.append(f"{prefix}Severity must be between 0 and 100, got {severity}")
                except ValueError:
                    self.errors.append(f"{prefix}Severity must be a number, got '{severity_elem.text}'")
        
        # Check conditionData
        condition_data = alarm_element.find('conditionData')
        if condition_data is None:
            self.errors.append(f"{prefix}Missing 'conditionData' element")
        else:
            # Check matchField and matchValue
            match_field = condition_data.find('matchField')
            match_value = condition_data.find('matchValue')
            
            if match_field is None:
                self.errors.append(f"{prefix}Missing 'matchField' in conditionData")
            if match_value is None:
                self.errors.append(f"{prefix}Missing 'matchValue' in conditionData")
            elif match_value.text:
                # Validate matchValue format (should be like "47|6000114")
                if not re.match(r'^\d+\|\d+$', match_value.text):
                    self.warnings.append(f"{prefix}matchValue format may be incorrect: '{match_value.text}'")
        
        # Check actions
        actions = alarm_element.find('actions')
        if actions is None:
            self.errors.append(f"{prefix}Missing 'actions' element")
        else:
            action_data_list = actions.findall('actionData')
            if not action_data_list:
                self.warnings.append(f"{prefix}No actionData elements found in actions")

class RuleParser:
    """Parser for McAfee SIEM rule.xml files"""
    
    def __init__(self):
        self.rules = []

    def parse_rule_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse rule.xml file using iterparse for memory efficiency."""
        self.rules = []
        try:
            context = etree.iterparse(file_path, events=('end',), tag='rule')
            for event, elem in context:
                rule_data = self._extract_rule_data(elem)
                if rule_data:
                    self.rules.append(rule_data)
                # Clear the element and its ancestors to save memory
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]
            return self.rules
        except etree.XMLSyntaxError as e:
            raise Exception(f"XML Syntax Error parsing rule file: {str(e)}")
        except Exception as e:
            raise Exception(f"Error parsing rule file: {str(e)}")

    def parse_rule_xml(self, xml_content: str) -> List[Dict[str, Any]]:
        """
        Parse rule.xml content and extract rule data.
        Note: This method loads the entire string into memory. For large files,
        use parse_rule_file for better performance.
        """
        self.rules = []
        try:
            # The fromstring method is inherently not memory-efficient for large strings
            # but we provide it for flexibility. The file-based method is preferred.
            root = etree.fromstring(xml_content.encode('utf-8'))
            rules_element = root.find('rules')
            
            if rules_element is not None:
                for rule_elem in rules_element.findall('rule'):
                    rule_data = self._extract_rule_data(rule_elem)
                    if rule_data:
                        self.rules.append(rule_data)
            
            return self.rules
        except Exception as e:
            raise Exception(f"Error parsing rule XML: {str(e)}")
    
    def _extract_rule_data(self, rule_element) -> Optional[Dict[str, Any]]:
        """Extract data from a single rule element"""
        try:
            rule_data = {}
            
            # Extract basic rule information
            rule_data['rule_id'] = self._get_element_text(rule_element, 'id')
            rule_data['name'] = self._get_element_text(rule_element, 'message')
            rule_data['description'] = self._get_element_text(rule_element, 'description')
            rule_data['severity'] = self._get_element_int(rule_element, 'severity')
            rule_data['rule_type'] = self._get_element_int(rule_element, 'type')
            rule_data['revision'] = self._get_element_int(rule_element, 'revision')
            rule_data['origin'] = self._get_element_int(rule_element, 'origin')
            rule_data['action'] = self._get_element_int(rule_element, 'action')
            
            # Extract SigID - try multiple sources
            sig_id = None
            
            # Method 1: Extract from rule ID (e.g., "47-6000114" -> "6000114")
            # This is the rule's own identifier, used for alarm generation
            # Different from event IDs in CDATA (like "43-263047320") which are trigger events
            rule_id = rule_data.get('rule_id')
            if rule_id:
                import re
                match = re.search(r'(\d+)$', rule_id)
                if match:
                    sig_id = match.group(1)
            
            # Method 2: Extract from CDATA if not found above
            text_elem = rule_element.find('text')
            if text_elem is not None and text_elem.text:
                cdata_sig_id = self._extract_sig_id(text_elem.text)
                if cdata_sig_id:
                    sig_id = cdata_sig_id
                rule_data['xml_content'] = text_elem.text
            
            rule_data['sig_id'] = sig_id
            
            return rule_data
            
        except Exception as e:
            print(f"Error extracting rule data: {str(e)}")
            return None
    
    def _get_element_text(self, parent, tag_name: str) -> Optional[str]:
        """Get text content of a child element"""
        elem = parent.find(tag_name)
        return elem.text if elem is not None else None
    
    def _get_element_int(self, parent, tag_name: str) -> Optional[int]:
        """Get integer content of a child element"""
        elem = parent.find(tag_name)
        if elem is not None and elem.text:
            try:
                return int(elem.text)
            except ValueError:
                return None
        return None
    
    def _extract_sig_id(self, cdata_content: str) -> Optional[str]:
        """Extract SigID from CDATA content"""
        try:
            cdata_root = etree.fromstring(cdata_content.encode('utf-8'))
            
            # Method 1: Look for <property><n>sigid</n><value>XXX</value></property>
            # OR <property><name>sigid</name><value>XXX</value></property>
            properties = cdata_root.findall('.//property')
            for prop in properties:
                # Check for 'n' or 'name' tag
                n_elem = prop.find('n')
                if n_elem is None:
                    n_elem = prop.find('name')
                
                if n_elem is not None and n_elem.text == 'sigid':
                    value_elem = prop.find('value')
                    if value_elem is not None and value_elem.text:
                        return value_elem.text
            
            # Method 2: Look for ruleset id attribute (fallback)
            if cdata_root.tag == 'ruleset' and 'id' in cdata_root.attrib:
                ruleset_id = cdata_root.attrib['id']
                # Extract numeric part from formats like "47-6000114"
                import re
                match = re.search(r'(\d+)$', ruleset_id)
                if match:
                    return match.group(1)
            
            # Method 3: Look for sig_id or sigID attributes or elements
            for xpath in ['.//sig_id', './/sigID', './/sigId']:
                elem = cdata_root.find(xpath)
                if elem is not None and elem.text:
                    return elem.text
            
            return None
            
        except Exception as e:
            print(f"Error extracting SigID: {e}")
            return None

class AlarmParser:
    """Parser for McAfee SIEM alarm.xml files"""
    
    def __init__(self):
        self.alarms = []

    def parse_alarm_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse alarm.xml file using iterparse for memory efficiency."""
        self.alarms = []
        try:
            context = etree.iterparse(file_path, events=('end',), tag='alarm')
            for event, elem in context:
                alarm_data = self._extract_alarm_data(elem)
                if alarm_data:
                    self.alarms.append(alarm_data)
                # Clear the element and its ancestors to save memory
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]
            return self.alarms
        except etree.XMLSyntaxError as e:
            raise Exception(f"XML Syntax Error parsing alarm file: {str(e)}")
        except Exception as e:
            raise Exception(f"Error parsing alarm file: {str(e)}")

    def parse_alarm_xml(self, xml_content: str) -> List[Dict[str, Any]]:
        """
        Parse alarm.xml content and extract alarm data.
        Note: This method loads the entire string into memory. For large files,
        use parse_alarm_file for better performance.
        """
        self.alarms = []
        try:
            root = etree.fromstring(xml_content.encode('utf-8'))
            
            for alarm_elem in root.findall('alarm'):
                alarm_data = self._extract_alarm_data(alarm_elem)
                if alarm_data:
                    self.alarms.append(alarm_data)
            
            return self.alarms
        except Exception as e:
            raise Exception(f"Error parsing alarm XML: {str(e)}")
    
    def _extract_alarm_data(self, alarm_element) -> Optional[Dict[str, Any]]:
        """Extract data from a single alarm element"""
        try:
            alarm_data = {}
            
            # Extract alarm attributes
            alarm_data['name'] = alarm_element.get('name')
            alarm_data['min_version'] = alarm_element.get('minVersion')
            
            # Extract alarmData
            alarm_data_elem = alarm_element.find('alarmData')
            if alarm_data_elem is not None:
                alarm_data['severity'] = self._get_element_int(alarm_data_elem, 'severity')
                alarm_data['note'] = self._get_element_text(alarm_data_elem, 'note')
                alarm_data['assignee_id'] = self._get_element_int(alarm_data_elem, 'assignee')
                alarm_data['esc_assignee_id'] = self._get_element_int(alarm_data_elem, 'escAssignee')
            
            # Extract conditionData
            condition_data_elem = alarm_element.find('conditionData')
            if condition_data_elem is not None:
                alarm_data['match_field'] = self._get_element_text(condition_data_elem, 'matchField')
                alarm_data['match_value'] = self._get_element_text(condition_data_elem, 'matchValue')
                alarm_data['condition_type'] = self._get_element_int(condition_data_elem, 'conditionType')
            
            # Extract deviceIDs
            device_ids = []
            alarm_data_elem = alarm_element.find('alarmData')
            if alarm_data_elem is not None:
                device_ids_elem = alarm_data_elem.find('deviceIDs')
                if device_ids_elem is not None:
                    for device_filter in device_ids_elem.findall('deviceFilter'):
                        filter_data = {'mask': device_filter.get('mask'), 'constraints': []}
                        for constraint in device_filter.findall('constraintFilter'):
                            filter_data['constraints'].append({
                                'type': constraint.get('type'),
                                'value': constraint.get('value')
                            })
                        device_ids.append(filter_data)
            
            if device_ids:
                import json
                alarm_data['device_ids'] = json.dumps(device_ids)
            
            # Store the complete alarm XML
            alarm_data['xml_content'] = etree.tostring(alarm_element, encoding='unicode')
            
            return alarm_data
            
        except Exception as e:
            print(f"Error extracting alarm data: {str(e)}")
            return None
    
    def _get_element_text(self, parent, tag_name: str) -> Optional[str]:
        """Get text content of a child element"""
        elem = parent.find(tag_name)
        return elem.text if elem is not None else None
    
    def _get_element_int(self, parent, tag_name: str) -> Optional[int]:
        """Get integer content of a child element"""
        elem = parent.find(tag_name)
        if elem is not None and elem.text:
            try:
                return int(elem.text)
            except ValueError:
                return None
        return None

class AlarmGenerator:
    """Generate alarms from rules"""
    
    def __init__(self):
        self.default_assignee_id = 655372
        self.default_esc_assignee_id = 90118
        self.default_min_version = "11.6.14"
    
    def generate_alarm_from_rule(self, rule_data: Dict[str, Any]) -> str:
        """
        Generate alarm XML from rule data.
        
        Uses the rule's SigID (extracted from rule ID like "47-6000114" -> "6000114")
        to create an alarm with match_value format "47|{sig_id}".
        
        Note: This is different from event IDs in CDATA (like "43-263047320") 
        which are the events that trigger the rule, not the rule's own identifier.
        """
        if not rule_data.get('sig_id'):
            raise ValueError("Rule must have a SigID to generate alarm")
        
        alarm_name = rule_data.get('name', f"Generated Alarm for Rule {rule_data.get('rule_id', 'Unknown')}")
        severity = rule_data.get('severity', 50)
        sig_id = rule_data['sig_id']  # This comes from rule ID (e.g., "6000114" from "47-6000114")
        match_value = f"47|{sig_id}"  # Alarm match value format
        
        # Use the generic generation method
        return self.generate_alarm_xml({
            'name': alarm_name,
            'severity': severity,
            'match_value': match_value,
            'note': f"Auto-generated alarm for rule {rule_data.get('rule_id', 'Unknown')}"
        })

    def generate_alarm_xml(self, data: Dict[str, Any]) -> str:
        """Generate alarm XML from dictionary data"""
        
        name = escape(data.get('name', 'New Alarm'))
        min_version = escape(data.get('min_version', self.default_min_version))
        severity = data.get('severity', 50)
        match_field = escape(data.get('match_field', 'DSIDSigID'))
        match_value = escape(data.get('match_value', ''))
        condition_type = data.get('condition_type', 14)
        assignee_id = data.get('assignee_id', self.default_assignee_id)
        esc_assignee_id = data.get('esc_assignee_id', self.default_esc_assignee_id)
        note = escape(data.get('note', '') or '')
        
        # Default summary template from schema
        summary_template = """Alarm Name: [$Rule Message]

The following events were found

[$REPEAT_START]----------
EventID         = [$Event ID]
Action          = [$Event Subtype]
Source User     = [$%UserIDSrc]
Source IP       = [$Source IP]
Source Port     = [$Source Port]
Destination IP  = [$Destination IP]
Destination Port= [$Destination Port]
Domain          = [$%External_Hostname]
Count           = [$Event Count]
Rule            = [$Rule Message]
[$REPEAT_END]"""

        alarm_xml = f"""<alarm name="{name}" minVersion="{min_version}">
  <alarmData>
    <filters></filters>
    <note>{note}</note>
    <notificationType>0</notificationType>
    <severity>{severity}</severity>
    <escEnabled>F</escEnabled>
    <escSeverity>{severity}</escSeverity>
    <escMin>0</escMin>
    <summaryTemplate>{escape(summary_template)}</summaryTemplate>
    <assignee>{assignee_id}</assignee>
    <assigneeType>1</assigneeType>
    <escAssignee>{esc_assignee_id}</escAssignee>
    <escAssigneeType>0</escAssigneeType>
    <deviceIDs>
      <deviceFilter mask="40">
        <constraintFilter type="ID" value="144116287604260864"/>
      </deviceFilter>
    </deviceIDs>
  </alarmData>
  <conditionData>
    <conditionType>{condition_type}</conditionType>
    <queryID>0</queryID>
    <alertRateMin>0</alertRateMin>
    <alertRateCount>0</alertRateCount>
    <pctAbove>0</pctAbove>
    <pctBelow>0</pctBelow>
    <offsetMin>0</offsetMin>
    <timeFilter></timeFilter>
    <xMin>10</xMin>
    <useWatchlist>F</useWatchlist>
    <matchField>{match_field}</matchField>
    <matchValue>{match_value}</matchValue>
    <matchNot>F</matchNot>
  </conditionData>
  <actions>
    <actionData>
      <actionType>0</actionType>
      <actionProcess>9</actionProcess>
      <actionAttributes>
        <attribute name="TimeZoneID">77</attribute>
        <attribute name="SyslogTemplateID">0</attribute>
        <attribute name="SNMPTemplateID">0</attribute>
        <attribute name="SMSTemplateID">0</attribute>
        <attribute name="EmailTemplateID">8206</attribute>
        <attribute name="UserIDs"></attribute>
        <attribute name="EmailGroupIDs">1</attribute>
        <attribute name="EmailIDs"></attribute>
        <attribute name="MsgEnabled">F</attribute>
        <attribute name="TimeDateFormat">12</attribute>
      </actionAttributes>
    </actionData>
    <actionData>
      <actionType>0</actionType>
      <actionProcess>7</actionProcess>
      <actionAttributes>
        <attribute name="AudioFileName">audio/YWxlcnQubXAz</attribute>
      </actionAttributes>
    </actionData>
    <actionData>
      <actionType>0</actionType>
      <actionProcess>6</actionProcess>
      <actionAttributes></actionAttributes>
    </actionData>
    <actionData>
      <actionType>0</actionType>
      <actionProcess>1</actionProcess>
      <actionAttributes></actionAttributes>
    </actionData>
    <actionData>
      <actionType>1</actionType>
      <actionProcess>1</actionProcess>
      <actionAttributes></actionAttributes>
    </actionData>
  </actions>
</alarm>"""
        return alarm_xml
