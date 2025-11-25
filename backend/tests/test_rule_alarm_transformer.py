import pytest
from lxml import etree
from backend.utils.rule_alarm_transformer import RuleAlarmTransformer, Rule

@pytest.fixture
def transformer():
    """Returns a RuleAlarmTransformer instance."""
    return RuleAlarmTransformer()

@pytest.fixture
def sample_rule_xml():
    """Provides a sample rule XML tree."""
    xml_content = """
    <nitro_policy version="11.6.14">
        <rules>
            <rule>
                <id>47-12345</id>
                <message>Test Rule One</message>
                <severity>75</severity>
                <description>Description for rule one.</description>
            </rule>
            <rule>
                <id>47-67890</id>
                <message>Test Rule Two</message>
                <severity>90</severity>
                <description>Description for rule two.</description>
            </rule>
        </rules>
    </nitro_policy>
    """
    return etree.fromstring(xml_content.encode('utf-8')).getroottree()

class TestRuleAlarmTransformer:
    def test_parse_rules_valid(self, transformer, sample_rule_xml):
        """Test parsing rules from a valid XML tree."""
        version, rules = transformer.parse_rules(sample_rule_xml)
        assert version == "11.6.14"
        assert len(rules) == 2
        assert rules[0].id_text == "47-12345"
        assert rules[0].message == "Test Rule One"
        assert rules[1].severity == "90"

    def test_parse_rules_no_rules_element(self, transformer):
        """Test parsing XML with no <rules> element."""
        xml_content = "<nitro_policy></nitro_policy>"
        xml_tree = etree.fromstring(xml_content.encode('utf-8')).getroottree()
        with pytest.raises(ValueError, match="Missing <rules> element"):
            transformer.parse_rules(xml_tree)

    def test_parse_rules_no_rule_elements(self, transformer):
        """Test parsing XML with an empty <rules> element."""
        xml_content = "<nitro_policy><rules></rules></nitro_policy>"
        xml_tree = etree.fromstring(xml_content.encode('utf-8')).getroottree()
        with pytest.raises(ValueError, match="No valid rules parsed"):
            transformer.parse_rules(xml_tree)

    def test_transform_single_rule(self, transformer):
        """Test the transformation of a single Rule object to an Alarm object."""
        rule = Rule(
            id_text="47-54321",
            prefix="47",
            severity="80",
            message="A sample rule for transformation.",
            description="Detailed description."
        )
        alarm = transformer.transform(rule, max_len=128, version="11.6.14")
        assert alarm.name == "A sample rule for transformation."
        assert alarm.severity == "80"
        assert alarm.match_value == "47|54321"
        assert alarm.description == "Detailed description."

    def test_transform_rule_with_long_name(self, transformer):
        """Test the name truncation logic during transformation."""
        import hashlib
        long_message = "This is a very long rule message that is definitely going to exceed the maximum length of 128 characters set for the alarm name."
        rule = Rule(id_text="47-11111", prefix="47", severity="50", message=long_message, description="")

        # Calculate the expected suffix
        expected_suffix = hashlib.sha1(long_message.encode()).hexdigest()[:8]

        alarm = transformer.transform(rule, max_len=50, version="11.6.14")

        assert len(alarm.name) <= 50
        assert alarm.name.endswith(f"_{expected_suffix}")

    def test_build_alarms_without_template(self, transformer):
        """Test building an alarm XML tree without a template."""
        from backend.utils.rule_alarm_transformer import Alarm
        alarms = [
            Alarm(name="Alarm1", min_version="1.0", severity="50", description="Desc1", match_value="47|1"),
            Alarm(name="Alarm2", min_version="1.0", severity="60", description="Desc2", match_value="47|2"),
        ]
        tree = transformer.build_alarms(None, alarms)
        root = tree.getroot()
        assert root.tag == "alarms"
        alarm_elements = root.findall("alarm")
        assert len(alarm_elements) == 2
        assert alarm_elements[0].get("name") == "Alarm1"
        assert alarm_elements[1].find("alarmData/severity").text == "60"
        assert alarm_elements[1].find("conditionData/matchValue").text == "47|2"

    def test_transform_rules_to_alarms_e2e(self, transformer, tmp_path):
        """End-to-end test for the main transformation method."""
        rule_xml_content = """
        <nitro_policy version="11.6.14">
            <rules>
                <rule>
                    <id>47-12345</id>
                    <message>Test Rule One</message>
                    <severity>75</severity>
                </rule>
            </rules>
        </nitro_policy>
        """
        rule_file = tmp_path / "rules.xml"
        rule_file.write_text(rule_xml_content)

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        output_file = output_dir / "alarms.xml"
        report_prefix = output_dir / "report"

        result = transformer.transform_rules_to_alarms(
            rule_file_path=str(rule_file),
            output_path=str(output_file),
            report_prefix=str(report_prefix)
        )

        assert result['success'] is True
        assert result['rules_processed'] == 1
        assert result['alarms_generated'] == 1
        assert output_file.exists()

        # Check for report files
        assert len(list(output_dir.glob("report_*.csv"))) == 1
        assert len(list(output_dir.glob("report_*.html"))) == 1

        # Check content of generated alarm file
        alarm_tree = etree.parse(str(output_file))
        alarms = alarm_tree.findall("alarm")
        assert len(alarms) == 1
        assert alarms[0].get("name") == "Test Rule One"
        assert alarms[0].find("conditionData/matchValue").text == "47|12345"
