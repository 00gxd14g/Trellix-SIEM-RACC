/**
 * Parse rule XML content to extract filter logic for visualization
 */

export function parseRuleFilters(xmlContent) {
  if (!xmlContent) return null;

  try {
    // Create a temporary div to parse XML
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(xmlContent, 'text/xml');
    
    // Check for parsing errors
    const parserError = xmlDoc.querySelector('parsererror');
    if (parserError) {
      console.error('XML parsing error:', parserError.textContent);
      return null;
    }

    const nodes = [];
    const edges = [];
    let nodeId = 0;

    // Find ruleset
    const ruleset = xmlDoc.querySelector('ruleset');
    if (!ruleset) return null;

    // Add root trigger node
    const triggers = xmlDoc.querySelectorAll('trigger');
    triggers.forEach((trigger, index) => {
      const triggerName = trigger.getAttribute('name') || `trigger_${index + 1}`;
      const count = trigger.getAttribute('count') || '1';
      const timeout = trigger.getAttribute('timeout') || '60';
      
      nodes.push({
        id: `trigger_${nodeId}`,
        type: 'default',
        position: { x: 250, y: 50 + index * 100 },
        data: { 
          label: `${triggerName}\nCount: ${count}, Timeout: ${timeout}s`,
          type: 'trigger'
        },
        style: {
          background: '#fef3c7',
          border: '2px solid #d97706',
          borderRadius: '8px',
          fontSize: '12px',
          width: 200
        }
      });
      nodeId++;
    });

    // Find all rule elements
    const rules = xmlDoc.querySelectorAll('rule[name]:not([name="Root Rule"])');
    rules.forEach((rule, index) => {
      const ruleName = rule.getAttribute('name') || `rule_${index + 1}`;
      
      // Add rule node
      nodes.push({
        id: `rule_${nodeId}`,
        type: 'default',
        position: { x: 50, y: 150 + index * 200 },
        data: { 
          label: ruleName,
          type: 'rule'
        },
        style: {
          background: '#dbeafe',
          border: '2px solid #3b82f6',
          borderRadius: '8px',
          fontSize: '12px',
          width: 150
        }
      });

      const ruleNodeId = `rule_${nodeId}`;
      nodeId++;

      // Parse match filters
      const matchFilter = rule.querySelector('matchFilter');
      if (matchFilter) {
        const filterType = matchFilter.getAttribute('type') || 'and';
        
        // Add filter group node
        const filterGroupId = `filter_${nodeId}`;
        nodes.push({
          id: filterGroupId,
          type: 'default',
          position: { x: 300, y: 150 + index * 200 },
          data: { 
            label: `${filterType.toUpperCase()} Filter`,
            type: 'filterGroup'
          },
          style: {
            background: filterType === 'and' ? '#dcfce7' : '#fef3c7',
            border: filterType === 'and' ? '2px solid #16a34a' : '2px solid #d97706',
            borderRadius: '8px',
            fontSize: '12px',
            width: 120
          }
        });
        nodeId++;

        // Connect rule to filter group
        edges.push({
          id: `edge_${ruleNodeId}_${filterGroupId}`,
          source: ruleNodeId,
          target: filterGroupId,
          animated: true
        });

        // Parse individual filter components
        const filterComponents = matchFilter.querySelectorAll('singleFilterComponent');
        filterComponents.forEach((component, filterIndex) => {
          const filterType = component.getAttribute('type');
          const valueElem = component.querySelector('filterData[name="value"]');
          const operatorElem = component.querySelector('filterData[name="operator"]');
          
          const value = valueElem?.getAttribute('value') || '';
          const operator = operatorElem?.getAttribute('value') || 'EQUALS';

          // Add filter component node
          const componentId = `component_${nodeId}`;
          nodes.push({
            id: componentId,
            type: 'default',
            position: { x: 500, y: 100 + index * 200 + filterIndex * 80 },
            data: { 
              label: `${filterType}\n${operator}\n${value.length > 20 ? value.substring(0, 20) + '...' : value}`,
              type: 'filterComponent',
              details: { filterType, operator, value }
            },
            style: {
              background: '#f3e8ff',
              border: '2px solid #8b5cf6',
              borderRadius: '8px',
              fontSize: '10px',
              width: 180
            }
          });
          nodeId++;

          // Connect filter group to component
          edges.push({
            id: `edge_${filterGroupId}_${componentId}`,
            source: filterGroupId,
            target: componentId,
            animated: false
          });
        });

        // Connect filter group to trigger if trigger reference exists
        const actionElem = rule.querySelector('action[type="TRIGGER"]');
        if (actionElem && triggers.length > 0) {
          const triggerAttr = actionElem.getAttribute('trigger');
          const triggerNode = nodes.find(n => n.data.label.includes(triggerAttr) && n.data.type === 'trigger');
          if (triggerNode) {
            edges.push({
              id: `edge_${filterGroupId}_${triggerNode.id}`,
              source: filterGroupId,
              target: triggerNode.id,
              animated: true,
              style: { stroke: '#10b981', strokeWidth: 2 }
            });
          }
        }
      }
    });

    return { nodes, edges };
  } catch (error) {
    console.error('Error parsing rule filters:', error);
    return null;
  }
}

export function getRuleStatistics(xmlContent) {
  if (!xmlContent) return {};

  try {
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(xmlContent, 'text/xml');
    
    const triggers = xmlDoc.querySelectorAll('trigger').length;
    const rules = xmlDoc.querySelectorAll('rule[name]:not([name="Root Rule"])').length;
    const filters = xmlDoc.querySelectorAll('singleFilterComponent').length;
    const andFilters = xmlDoc.querySelectorAll('matchFilter[type="and"]').length;
    const orFilters = xmlDoc.querySelectorAll('matchFilter[type="or"]').length;

    return {
      triggers,
      rules,
      filters,
      andFilters,
      orFilters
    };
  } catch (error) {
    console.error('Error getting rule statistics:', error);
    return {};
  }
}