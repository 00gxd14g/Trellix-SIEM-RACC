import pytest
import os
from memory_profiler import memory_usage
from backend.utils.xml_utils import RuleParser

def generate_large_rule_file(file_path, num_rules):
    """Generates a large rule.xml file for testing."""
    with open(file_path, 'w') as f:
        f.write('<nitro_policy><rules count="{}">'.format(num_rules))
        for i in range(num_rules):
            f.write(f"""
            <rule>
                <id>47-{i}</id>
                <message>Test Rule {i}</message>
                <severity>{i % 100}</severity>
                <text><![CDATA[<ruleset id="47-{i}"></ruleset>]]></text>
            </rule>
            """)
        f.write('</rules></nitro_policy>')

@pytest.fixture
def large_rule_file(tmp_path):
    """Fixture to create a large rule file."""
    file_path = tmp_path / "large_rules.xml"
    generate_large_rule_file(file_path, 10000)
    return str(file_path)

def test_rule_parser_performance(benchmark, large_rule_file):
    """Benchmark the performance of the stream-based rule parser."""
    parser = RuleParser()

    # Benchmark the parsing function
    result = benchmark(parser.parse_rule_file, large_rule_file)

    # Assert that the correct number of rules were parsed
    assert len(result) == 10000

def test_rule_parser_memory_usage(large_rule_file):
    """
    Test the memory usage of the stream-based rule parser.
    This is a simple test and may vary depending on the system.
    """
    parser = RuleParser()

    # Measure memory usage of the parsing function
    mem_usage = memory_usage((parser.parse_rule_file, (large_rule_file,)), max_usage=True)

    # Assert that memory usage is reasonably low (e.g., less than 100 MiB)
    # This is a generous threshold, but it will catch major memory regressions.
    print(f"Memory usage for parsing 10,000 rules: {mem_usage:.2f} MiB")
    assert mem_usage < 100
