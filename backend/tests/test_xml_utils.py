import pytest
from backend.utils.xml_utils import XMLValidator, RuleParser, AlarmParser, AlarmGenerator

@pytest.fixture
def create_xml_file(tmp_path):
    """A fixture to create a temporary XML file."""
    def _create_xml_file(content, filename="test.xml"):
        file_path = tmp_path / filename
        file_path.write_text(content, encoding='utf-8')
        return str(file_path)
    return _create_xml_file

class TestXMLValidator:
    def test_validate_rule_xml_valid(self, create_xml_file):
        """Test validation of a valid rule.xml file."""
        xml_content = """
        <nitro_policy>
            <rules>
                <rule>
                    <id>47-12345</id>
                    <message>Test Rule</message>
                    <severity>50</severity>
                    <text><![CDATA[<ruleset id="47-12345"><property><n>sigid</n><value>12345</value></property></ruleset>]]></text>
                </rule>
            </rules>
        </nitro_policy>
        """
        file_path = create_xml_file(xml_content)
        validator = XMLValidator()
        result = validator.validate_rule_xml(file_path)
        assert result['valid'] is True
        assert not result['errors']

    def test_validate_rule_xml_invalid_syntax(self, create_xml_file):
        """Test validation of a rule.xml file with syntax errors."""
        # iterparse is more lenient and may not fail on a missing root closing tag,
        # but it will report errors on the content.
        xml_content = "<nitro_policy><rules><rule></rule></rules>"
        file_path = create_xml_file(xml_content)
        validator = XMLValidator()
        result = validator.validate_rule_xml(file_path)
        assert result['valid'] is False
        # The streaming validator will report the missing elements inside the rule
        assert "Missing required element 'id'" in result['errors'][0]

    def test_validate_rule_xml_missing_required_element(self, create_xml_file):
        """Test validation of a rule.xml file with a missing required element."""
        xml_content = """
        <nitro_policy>
            <rules>
                <rule>
                    <id>47-12345</id>
                    <severity>50</severity>
                    <text><![CDATA[<ruleset id="47-12345"></ruleset>]]></text>
                </rule>
            </rules>
        </nitro_policy>
        """
        file_path = create_xml_file(xml_content)
        validator = XMLValidator()
        result = validator.validate_rule_xml(file_path)
        assert result['valid'] is False
        assert "Missing required element 'message'" in result['errors'][0]

    def test_validate_alarm_xml_valid(self, create_xml_file):
        """Test validation of a valid alarm.xml file."""
        xml_content = """
        <alarms>
            <alarm name="Test Alarm">
                <alarmData><severity>50</severity></alarmData>
                <conditionData><matchField>DSIDSigID</matchField><matchValue>47|12345</matchValue></conditionData>
                <actions><actionData></actionData></actions>
            </alarm>
        </alarms>
        """
        file_path = create_xml_file(xml_content)
        validator = XMLValidator()
        result = validator.validate_alarm_xml(file_path)
        assert result['valid'] is True
        assert not result['errors']

    def test_validate_alarm_xml_missing_required_element(self, create_xml_file):
        """Test validation of an alarm.xml file with a missing required element."""
        xml_content = """
        <alarms>
            <alarm name="Test Alarm">
                <alarmData><severity>50</severity></alarmData>
                <actions><actionData></actionData></actions>
            </alarm>
        </alarms>
        """
        file_path = create_xml_file(xml_content)
        validator = XMLValidator()
        result = validator.validate_alarm_xml(file_path)
        assert result['valid'] is False
        assert "Missing 'conditionData' element" in result['errors'][0]

class TestRuleParser:
    def test_parse_valid_rule(self):
        xml_content = """
        <nitro_policy>
            <rules>
                <rule>
                    <id>47-12345</id>
                    <message>Test Rule</message>
                    <severity>75</severity>
                    <text><![CDATA[<ruleset id="47-12345"></ruleset>]]></text>
                </rule>
            </rules>
        </nitro_policy>
        """
        parser = RuleParser()
        rules = parser.parse_rule_xml(xml_content)
        assert len(rules) == 1
        rule = rules[0]
        assert rule['rule_id'] == '47-12345'
        assert rule['name'] == 'Test Rule'
        assert rule['severity'] == 75
        assert rule['sig_id'] == '12345'

    def test_parse_rule_with_cdata_sigid(self):
        xml_content = """
        <nitro_policy>
            <rules>
                <rule>
                    <id>47-ABCDE</id>
                    <message>Test Rule</message>
                    <severity>75</severity>
                    <text><![CDATA[
                        <ruleset id="47-ABCDE">
                            <property><n>sigid</n><value>54321</value></property>
                        </ruleset>
                    ]]></text>
                </rule>
            </rules>
        </nitro_policy>
        """
        parser = RuleParser()
        rules = parser.parse_rule_xml(xml_content)
        assert len(rules) == 1
        assert rules[0]['sig_id'] == '54321'

    def test_parse_malformed_rule(self):
        xml_content = "<nitro_policy><rules>"
        parser = RuleParser()
        with pytest.raises(Exception, match="Error parsing rule XML"):
            parser.parse_rule_xml(xml_content)

class TestAlarmParser:
    def test_parse_valid_alarm(self):
        xml_content = """
        <alarms>
            <alarm name="Test Alarm" minVersion="1.0">
                <alarmData><severity>80</severity></alarmData>
                <conditionData><matchValue>47|12345</matchValue></conditionData>
            </alarm>
        </alarms>
        """
        parser = AlarmParser()
        alarms = parser.parse_alarm_xml(xml_content)
        assert len(alarms) == 1
        alarm = alarms[0]
        assert alarm['name'] == 'Test Alarm'
        assert alarm['severity'] == 80
        assert alarm['match_value'] == '47|12345'

    def test_parse_malformed_alarm(self):
        xml_content = "<alarms><alarm>"
        parser = AlarmParser()
        with pytest.raises(Exception, match="Error parsing alarm XML"):
            parser.parse_alarm_xml(xml_content)

class TestAlarmGenerator:
    def test_generate_alarm_from_rule(self):
        rule_data = {
            'rule_id': '47-98765',
            'sig_id': '98765',
            'name': 'My Test Rule',
            'severity': 90
        }
        generator = AlarmGenerator()
        alarm_xml = generator.generate_alarm_from_rule(rule_data)

        # Test if the generated XML is well-formed
        from lxml import etree
        try:
            root = etree.fromstring(alarm_xml.encode('utf-8'))
            assert root.tag == 'alarm'
        except etree.XMLSyntaxError as e:
            pytest.fail(f"Generated alarm XML is not well-formed: {e}")

        # Test if the matchValue is correct
        match_value_elem = root.find('.//conditionData/matchValue')
        assert match_value_elem is not None
        assert match_value_elem.text == '47|98765'
