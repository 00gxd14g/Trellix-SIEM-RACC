"""
Utility functions for exporting rules and alarms to HTML and PDF formats.
"""
from lxml import etree
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def generate_mermaid_diagram_from_rule_xml(xml_content: str) -> str:
    """
    Generate a Mermaid flowchart diagram from rule XML content.
    This creates a visual representation of the correlation logic flow.
    
    Args:
        xml_content: The XML content of the rule
        
    Returns:
        A Mermaid diagram string
    """
    try:
        root = etree.fromstring(xml_content.encode('utf-8'))
        
        # Start building the Mermaid diagram
        diagram_lines = ["graph TD"]
        node_counter = 0
        
        # Find all filter components
        match_filters = root.xpath('.//matchFilter')
        
        if not match_filters:
            return ""
        
        for filter_idx, match_filter in enumerate(match_filters):
            filter_type = match_filter.get('type', 'and').upper()
            
            # Create main filter node
            filter_node_id = f"F{node_counter}"
            node_counter += 1
            diagram_lines.append(f'    {filter_node_id}["{filter_type}"]')
            
            # Add style for filter node
            if filter_type == 'AND':
                diagram_lines.append(f'    style {filter_node_id} fill:#dcfce7,stroke:#16a34a,stroke-width:2px')
            else:
                diagram_lines.append(f'    style {filter_node_id} fill:#fef3c7,stroke:#d97706,stroke-width:2px')
            
            # Find all single filter components
            components = match_filter.xpath('.//singleFilterComponent')
            
            for comp_idx, component in enumerate(components):
                comp_type = component.get('type', 'Unknown')
                
                # Get filter data
                value_elem = component.xpath('.//filterData[@name="value"]')
                operator_elem = component.xpath('.//filterData[@name="operator"]')
                
                value = value_elem[0].get('value', '') if value_elem else ''
                operator = operator_elem[0].get('value', 'EQUALS') if operator_elem else 'EQUALS'
                
                # Truncate long values
                display_value = value[:30] + '...' if len(value) > 30 else value
                
                # Create component node
                comp_node_id = f"C{node_counter}"
                node_counter += 1
                
                # Escape special characters for Mermaid
                safe_type = comp_type.replace('"', "'")
                safe_operator = operator.replace('"', "'")
                safe_value = display_value.replace('"', "'").replace('\n', ' ')
                
                diagram_lines.append(f'    {comp_node_id}["Type: {safe_type}<br/>Operator: {safe_operator}<br/>Value: {safe_value}"]')
                diagram_lines.append(f'    style {comp_node_id} fill:#f3e8ff,stroke:#8b5cf6,stroke-width:2px')
                
                # Connect filter to component
                diagram_lines.append(f'    {filter_node_id} --> {comp_node_id}')
            
            # Check for threshold
            threshold_elem = match_filter.xpath('.//threshold')
            if threshold_elem:
                threshold_value = threshold_elem[0].get('value', '1')
                threshold_node_id = f"T{node_counter}"
                node_counter += 1
                diagram_lines.append(f'    {threshold_node_id}["Threshold: {threshold_value}"]')
                diagram_lines.append(f'    style {threshold_node_id} fill:#fef3c7,stroke:#f59e0b,stroke-width:2px')
                diagram_lines.append(f'    {filter_node_id} --> {threshold_node_id}')
            
            # Check for time window
            time_window_elem = match_filter.xpath('.//timeWindow')
            if time_window_elem:
                time_value = time_window_elem[0].get('value', '300')
                time_node_id = f"TW{node_counter}"
                node_counter += 1
                diagram_lines.append(f'    {time_node_id}["Time Window: {time_value}s"]')
                diagram_lines.append(f'    style {time_node_id} fill:#dbeafe,stroke:#3b82f6,stroke-width:2px')
                diagram_lines.append(f'    {filter_node_id} --> {time_node_id}')
            
            # Check for group by
            group_by_elems = match_filter.xpath('.//groupByFilter')
            for gb_elem in group_by_elems:
                gb_type = gb_elem.get('type', 'Unknown')
                gb_node_id = f"GB{node_counter}"
                node_counter += 1
                safe_gb_type = gb_type.replace('"', "'")
                diagram_lines.append(f'    {gb_node_id}["Group By: {safe_gb_type}"]')
                diagram_lines.append(f'    style {gb_node_id} fill:#e0e7ff,stroke:#6366f1,stroke-width:2px')
                diagram_lines.append(f'    {filter_node_id} --> {gb_node_id}')
        
        return '\n'.join(diagram_lines)
        
    except Exception as e:
        logger.error(f"Error generating Mermaid diagram: {e}")
        return ""


def generate_simple_text_diagram(xml_content: str) -> str:
    """
    Generate a simple text-based representation of the rule logic.
    Used as fallback when Mermaid is not available.
    
    Args:
        xml_content: The XML content of the rule
        
    Returns:
        A text diagram string
    """
    try:
        root = etree.fromstring(xml_content.encode('utf-8'))
        lines = []
        
        match_filters = root.xpath('.//matchFilter')
        
        for match_filter in match_filters:
            filter_type = match_filter.get('type', 'and').upper()
            lines.append(f"Filter Type: {filter_type}")
            lines.append("├─ Components:")
            
            components = match_filter.xpath('.//singleFilterComponent')
            for idx, component in enumerate(components):
                comp_type = component.get('type', 'Unknown')
                value_elem = component.xpath('.//filterData[@name="value"]')
                operator_elem = component.xpath('.//filterData[@name="operator"]')
                
                value = value_elem[0].get('value', '') if value_elem else ''
                operator = operator_elem[0].get('value', 'EQUALS') if operator_elem else 'EQUALS'
                
                prefix = "└─" if idx == len(components) - 1 else "├─"
                lines.append(f"   {prefix} {comp_type}: {operator} '{value}'")
            
            # Add threshold info
            threshold_elem = match_filter.xpath('.//threshold')
            if threshold_elem:
                threshold_value = threshold_elem[0].get('value', '1')
                lines.append(f"├─ Threshold: {threshold_value}")
            
            # Add time window info
            time_window_elem = match_filter.xpath('.//timeWindow')
            if time_window_elem:
                time_value = time_window_elem[0].get('value', '300')
                lines.append(f"├─ Time Window: {time_value}s")
            
            # Add group by info
            group_by_elems = match_filter.xpath('.//groupByFilter')
            for gb_elem in group_by_elems:
                gb_type = gb_elem.get('type', 'Unknown')
                lines.append(f"└─ Group By: {gb_type}")
        
        return '\n'.join(lines)
        
    except Exception as e:
        logger.error(f"Error generating text diagram: {e}")
        return "Unable to parse rule logic"


def html_to_pdf(html_content: str) -> bytes:
    """
    Convert HTML content to PDF using WeasyPrint.
    
    Args:
        html_content: The HTML content to convert
        
    Returns:
        PDF content as bytes
    """
    try:
        from weasyprint import HTML, CSS
        from io import BytesIO
        
        # Create a BytesIO object to store the PDF
        pdf_buffer = BytesIO()
        
        # Additional CSS for better PDF rendering
        pdf_css = CSS(string='''
            @page {
                size: A4;
                margin: 2cm;
            }
            body {
                font-size: 10pt;
            }
            .no-print {
                display: none;
            }
        ''')
        
        # Generate PDF
        HTML(string=html_content).write_pdf(pdf_buffer, stylesheets=[pdf_css])
        
        # Get the PDF content
        pdf_content = pdf_buffer.getvalue()
        pdf_buffer.close()
        
        return pdf_content
        
    except ImportError:
        logger.error("WeasyPrint is not installed. Cannot generate PDF.")
        raise Exception("PDF generation library not available. Please install WeasyPrint.")
    except Exception as e:
        logger.error(f"Error converting HTML to PDF: {e}")
        raise Exception(f"Failed to generate PDF: {str(e)}")


def prepare_alarm_export_data(alarms: List[Any], customer_name: str) -> Dict[str, Any]:
    """
    Prepare data for alarm export template.
    
    Args:
        alarms: List of Alarm model instances
        customer_name: Name of the customer
        
    Returns:
        Dictionary with template data
    """
    from datetime import datetime
    
    # Calculate severity counts
    severity_counts = {
        'critical': 0,
        'high': 0,
        'medium': 0,
        'low': 0
    }
    
    alarm_data = []
    for alarm in alarms:
        # Count severities
        if alarm.severity >= 90:
            severity_counts['critical'] += 1
        elif alarm.severity >= 70:
            severity_counts['high'] += 1
        elif alarm.severity >= 40:
            severity_counts['medium'] += 1
        else:
            severity_counts['low'] += 1
        
        # Prepare alarm data
        alarm_dict = alarm.to_dict()
        alarm_data.append(alarm_dict)
    
    return {
        'customer_name': customer_name,
        'generated_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
        'total_alarms': len(alarms),
        'severity_critical_count': severity_counts['critical'],
        'severity_high_count': severity_counts['high'],
        'severity_other_count': severity_counts['medium'] + severity_counts['low'],
        'alarms': alarm_data
    }


def prepare_rule_export_data(rules: List[Any], customer_name: str) -> Dict[str, Any]:
    """
    Prepare data for rule export template.
    
    Args:
        rules: List of Rule model instances
        customer_name: Name of the customer
        
    Returns:
        Dictionary with template data
    """
    from datetime import datetime
    
    # Calculate severity counts
    severity_counts = {
        'critical': 0,
        'high': 0,
        'medium': 0,
        'low': 0
    }
    
    rule_data = []
    for rule in rules:
        # Count severities
        if rule.severity >= 90:
            severity_counts['critical'] += 1
        elif rule.severity >= 70:
            severity_counts['high'] += 1
        elif rule.severity >= 40:
            severity_counts['medium'] += 1
        else:
            severity_counts['low'] += 1
        
        # Prepare rule data
        rule_dict = rule.to_dict()
        
        # Generate Mermaid diagram for correlation logic
        mermaid_diagram = generate_mermaid_diagram_from_rule_xml(rule.xml_content)
        rule_dict['mermaid_diagram'] = mermaid_diagram
        
        # Get matched alarms
        rule_dict['matched_alarms'] = [
            {
                'name': alarm.name,
                'match_value': alarm.match_value
            }
            for alarm in rule.alarms
        ]
        
        rule_data.append(rule_dict)
    
    return {
        'customer_name': customer_name,
        'generated_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
        'total_rules': len(rules),
        'severity_critical_count': severity_counts['critical'],
        'severity_high_count': severity_counts['high'],
        'severity_other_count': severity_counts['medium'] + severity_counts['low'],
        'rules': rule_data
    }
