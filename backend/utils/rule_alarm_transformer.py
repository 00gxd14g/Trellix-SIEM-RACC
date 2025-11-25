#!/usr/bin/env python3
import hashlib
import logging
import os
import tempfile
import shutil
import copy
import csv
from dataclasses import dataclass
from typing import List, Optional, Tuple
from datetime import datetime
from lxml import etree

@dataclass
class Rule:
    id_text: str
    prefix: str
    severity: str
    message: str
    description: str

@dataclass
class Alarm:
    name: str
    min_version: str
    severity: str
    description: str
    match_value: str

class RuleAlarmTransformer:
    """Transform McAfee SIEM rules to alarms using the specified algorithm"""
    
    def __init__(self, max_len: int = 128, version: str = "11.6.14"):
        self.max_len = max_len
        self.version = version
        self.logger = logging.getLogger(__name__)
        
    def parse_rules(self, tree: etree._ElementTree) -> Tuple[str, List[Rule]]:
        """Parse rules from XML tree"""
        root = tree.getroot()
        version = (root.get('version') or root.get('build') or self.version).split()[0]
        rules_parent = root.find('rules')
        
        if rules_parent is None:
            raise ValueError('Missing <rules> element')
            
        rules: List[Rule] = []
        for rule_el in rules_parent.findall('rule'):
            rid = (rule_el.findtext('id') or '').strip()
            if not rid:
                continue
                
            prefix = rid.split('-', 1)[0]
            sev = (rule_el.findtext('severity') or '').strip()
            msg = (rule_el.findtext('message') or '').strip()
            desc = (rule_el.findtext('description') or '').strip()
            
            rules.append(Rule(rid, prefix, sev, msg, desc))
            
        if not rules:
            raise ValueError('No valid rules parsed')
            
        return version, rules
    
    def transform(self, rule: Rule, max_len: int, version: str, sig_id: str = None) -> Alarm:
        """Transform a single rule to an alarm"""
        name = rule.message or rule.id_text
        if len(name) > max_len:
            suffix = hashlib.sha1(name.encode()).hexdigest()[:8]
            name = f"{name[:max_len-9]}_{suffix}"
        
        # Create match_value in format "47|sigid" or use rule.id_text as fallback
        if sig_id:
            match_value = f"47|{sig_id}"
        else:
            # Extract SigID from rule.id_text if possible (format: "47-6000114")
            if '-' in rule.id_text:
                prefix, potential_sig = rule.id_text.split('-', 1)
                match_value = f"{prefix}|{potential_sig}"
            else:
                match_value = rule.id_text
            
        return Alarm(name, version, rule.severity, rule.description, match_value)
    
    def build_alarms(self, template: Optional[etree._Element], alarms: List[Alarm]) -> etree._ElementTree:
        """Build alarms XML tree"""
        root = etree.Element('alarms')
        
        for a in alarms:
            if template is not None:
                el = copy.deepcopy(template)
                el.set('name', a.name)
                el.set('minVersion', a.min_version)
                
                # Update note
                note = el.find('alarmData/note')
                if note is not None:
                    note.text = a.description
                    
                # Update matchValue only
                mv = el.find('conditionData/matchValue')
                if mv is not None:
                    mv.text = a.match_value
            else:
                el = etree.SubElement(root, 'alarm')
                el.set('name', a.name)
                el.set('minVersion', a.min_version)
                
                # Build alarmData
                ad = etree.SubElement(el, 'alarmData')
                etree.SubElement(ad, 'filters')
                note = etree.SubElement(ad, 'note')
                note.text = a.description
                etree.SubElement(ad, 'notificationType').text = '0'
                etree.SubElement(ad, 'severity').text = a.severity
                etree.SubElement(ad, 'escEnabled').text = 'F'
                etree.SubElement(ad, 'escSeverity').text = '50'
                etree.SubElement(ad, 'escMin').text = '0'
                
                # Summary template
                st = etree.SubElement(ad, 'summaryTemplate')
                st.text = (
                    "Destination IP: [$Destination IP]\n"
                    "Source IP: [$Source IP]\n"
                    "Source Port: [$Source Port]\n"
                    "Destination Port: [$Destination Port]\n"
                    "Alarm Name: [$Alarm Name]\n"
                    "Condition Type: [$Condition Type]\n"
                    "Alarm Note: [$Alarm Note]\n"
                    "Trigger Date: [$Trigger Date]\n"
                    "Alarm Severity: [$Alarm Severity]\n"
                    "Traffic Type: L2L / R2L"
                )
                
                etree.SubElement(ad, 'assignee').text = '8199'
                etree.SubElement(ad, 'assigneeType').text = '1'
                etree.SubElement(ad, 'escAssignee').text = '57355'
                etree.SubElement(ad, 'escAssigneeType').text = '0'
                
                # Device IDs
                deviceIDs = etree.SubElement(ad, 'deviceIDs')
                df = etree.SubElement(deviceIDs, 'deviceFilter', mask='40')
                etree.SubElement(df, 'constraintFilter', type='ID', value='144118486627516416')
                
                # Build conditionData
                cd = etree.SubElement(el, 'conditionData')
                etree.SubElement(cd, 'conditionType').text = '14'
                etree.SubElement(cd, 'queryID').text = '213'
                etree.SubElement(cd, 'alertRateMin').text = '10'
                etree.SubElement(cd, 'alertRateCount').text = '0'
                etree.SubElement(cd, 'pctAbove').text = '10'
                etree.SubElement(cd, 'pctBelow').text = '10'
                etree.SubElement(cd, 'offsetMin').text = '0'
                etree.SubElement(cd, 'timeFilter')
                etree.SubElement(cd, 'xMin').text = '1'
                etree.SubElement(cd, 'useWatchlist').text = 'F'
                etree.SubElement(cd, 'matchField').text = 'DSIDSigID'
                mv = etree.SubElement(cd, 'matchValue')
                mv.text = a.match_value
                etree.SubElement(cd, 'matchNot').text = 'F'
                
                # Build actions
                actions = etree.SubElement(el, 'actions')
                for atype, proc in [(0,6),(0,1),(1,1)]:
                    adata = etree.SubElement(actions, 'actionData')
                    etree.SubElement(adata, 'actionType').text = str(atype)
                    etree.SubElement(adata, 'actionProcess').text = str(proc)
                    etree.SubElement(adata, 'actionAttributes')
                    
            root.append(el)
            
        return etree.ElementTree(root)
    
    def write_xml(self, tree: etree._ElementTree, path: str):
        """Write XML tree to file"""
        tmp = tempfile.NamedTemporaryFile('wb', delete=False)
        tree.write(tmp, xml_declaration=True, encoding='utf-8', pretty_print=True)
        tmp.close()
        shutil.move(tmp.name, path)
    
    def write_reports(self, rules: List[Rule], alarms: List[Alarm], prefix: str):
        """Write CSV and HTML reports"""
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        csvf = f'{prefix}_{ts}.csv'
        htmlf = f'{prefix}_{ts}.html'
        
        headers = [
            'Rule ID','Alarm Name','Severity','Match Value','Description',
            'Condition Type','Alert Rate Min','Alert Rate Count','Pct Above',
            'Pct Below','Offset Min','X Min','Match Field'
        ]
        
        # Write CSV report
        with open(csvf, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(headers)
            for r, a in zip(rules, alarms):
                w.writerow([
                    r.id_text, a.name, a.severity, a.match_value, a.description,
                    '14','10','0','10','10','0','1','DSIDSigID'
                ])
        
        # Write HTML report
        with open(htmlf, 'w', encoding='utf-8') as f:
            f.write('<html><head><meta charset="utf-8">')
            f.write('<style>table{border-collapse:collapse;}th,td{border:1px solid #ccc;padding:5px;}</style>')
            f.write('</head><body>\n')
            f.write(f'<h2>Alarm Report - {datetime.now().isoformat()}</h2>\n')
            f.write('<table><tr>' + ''.join(f'<th>{h}</th>' for h in headers) + '</tr>\n')
            
            for r, a in zip(rules, alarms):
                f.write('<tr>' + ''.join([
                    f'<td>{r.id_text}</td>',
                    f'<td>{a.name}</td>',
                    f'<td>{a.severity}</td>',
                    f'<td>{a.match_value}</td>',
                    f'<td>{a.description}</td>',
                    '<td>14</td><td>10</td><td>0</td><td>10</td><td>10</td><td>0</td><td>1</td><td>DSIDSigID</td>'
                ]) + '</tr>\n')
            f.write('</table></body></html>')
        
        return csvf, htmlf
    
    def transform_rules_to_alarms(self, rule_file_path: str, output_path: str = None, 
                                template_path: str = None, report_prefix: str = "report") -> dict:
        """Main transformation method"""
        try:
            # Load template if provided
            tpl_el = None
            if template_path:
                tpl_tree = etree.parse(template_path)
                tpl_el = tpl_tree.getroot().find('alarm')
                if tpl_el is None:
                    raise ValueError("Template must have <alarm> element")
            
            # Parse rules
            doc = etree.parse(rule_file_path)
            version, rules = self.parse_rules(doc)
            
            # Transform rules to alarms
            alarms = [self.transform(r, self.max_len, version) for r in rules]
            
            # Build alarms XML
            tree = self.build_alarms(tpl_el, alarms)
            
            # Write output XML
            if output_path:
                self.write_xml(tree, output_path)
            
            # Write reports
            csv_file, html_file = self.write_reports(rules, alarms, report_prefix)
            
            return {
                'success': True,
                'rules_processed': len(rules),
                'alarms_generated': len(alarms),
                'output_file': output_path,
                'csv_report': csv_file,
                'html_report': html_file,
                'version': version
            }
            
        except Exception as e:
            self.logger.error(f"Error transforming rules to alarms: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'rules_processed': 0,
                'alarms_generated': 0
            }