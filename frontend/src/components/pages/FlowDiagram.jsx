import { useCallback, useEffect, useState } from 'react';
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import "reactflow/dist/style.css";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { useAppContext } from '@/context/AppContext';
import { ruleAPI, alarmAPI, analysisAPI } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/loading';
import { parseRuleFilters } from '@/utils/ruleParser';
import {
  RefreshCw,
  Search,
  Network,
  FileText,
  Info,
  Eye
} from 'lucide-react';

const LAYOUT_COLUMNS = ['trigger', 'rule', 'filterGroup', 'filterComponent'];
const COLUMN_GAP = 180;
const FLOW_PADDING_X = 160;
const NODE_VERTICAL_GAP = 140;
const NODE_START_Y = 80;
const RULES_PER_PAGE = 12;

const getColumnIndex = (type) => {
  const idx = LAYOUT_COLUMNS.indexOf(type);
  if (idx === -1) {
    return LAYOUT_COLUMNS.indexOf('rule');
  }
  return idx;
};

export default function FlowDiagram() {
  const { selectedCustomerId } = useAppContext();
  const [loading, setLoading] = useState(false);
  const [rules, setRules] = useState([]);
  const [selectedRule, setSelectedRule] = useState(null);
  const [connectedAlarms, setConnectedAlarms] = useState([]);
  const [eventOverlapAlarms, setEventOverlapAlarms] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [flowInstance, setFlowInstance] = useState(null);

  const layoutRuleNodes = useCallback((inputNodes = []) => {
    if (!inputNodes.length) {
      return { nodes: [], primaryRuleId: 'rule-main' };
    }

    const columnBuckets = new Map();

    inputNodes.forEach(node => {
      const type = node.data?.type || 'rule';
      const columnIndex = getColumnIndex(type);
      if (!columnBuckets.has(columnIndex)) {
        columnBuckets.set(columnIndex, []);
      }
      columnBuckets.get(columnIndex).push({ ...node });
    });

    const maxItems = Math.max(
      ...Array.from(columnBuckets.values()).map(items => items.length),
      1
    );

    const arranged = [];
    let primaryRuleId = 'rule-main';

    Array.from(columnBuckets.entries())
      .sort((a, b) => a[0] - b[0])
      .forEach(([columnIndex, items]) => {
        const columnX = FLOW_PADDING_X + columnIndex * COLUMN_GAP;
        const offsetY = NODE_START_Y + ((maxItems - items.length) * NODE_VERTICAL_GAP) / 2;

        items
          .sort((a, b) => (a.data?.label || '').localeCompare(b.data?.label || ''))
          .forEach((node, order) => {
            const positioned = {
              ...node,
              position: {
                x: columnX,
                y: offsetY + order * NODE_VERTICAL_GAP,
              },
            };

            if (node.data?.type === 'rule' && primaryRuleId === 'rule-main') {
              primaryRuleId = node.id;
            }

            arranged.push(positioned);
          });
      });

    return { nodes: arranged, primaryRuleId };
  }, []);

  const fetchRules = useCallback(async () => {
    if (!selectedCustomerId) return;

    try {
      setLoading(true);
      const response = await ruleAPI.getAll(selectedCustomerId);
      setRules(response.data.rules || []);
    } catch (error) {
      console.error('Failed to fetch rules:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedCustomerId]);

  const generateFlowDiagram = useCallback((rule, alarms) => {
    const newNodes = [];
    const newEdges = [];

    // Parse rule XML for filter logic
    const ruleFlow = parseRuleFilters(rule.xml_content);

    let primaryRuleNodeId = 'rule-main';

    if (ruleFlow && ruleFlow.nodes && ruleFlow.nodes.length > 0) {
      const ruleEventLabel = rule.windows_event_ids?.length
        ? `\nEvents: ${rule.windows_event_ids.join(', ')}`
        : '';

      const { nodes: laidOutNodes, primaryRuleId } = layoutRuleNodes(
        ruleFlow.nodes.map(node => {
          if (node.data?.type === 'rule') {
            return {
              ...node,
              data: {
                ...node.data,
                label: `${node.data.label}${ruleEventLabel}`,
              },
            };
          }
          return node;
        })
      );

      newNodes.push(...laidOutNodes);
      primaryRuleNodeId = primaryRuleId;
      newEdges.push(...ruleFlow.edges);
    } else {
      // Fallback: Create a simple rule node when parsing fails
      newNodes.push({
        id: 'rule-main',
        type: 'default',
        position: { x: FLOW_PADDING_X + COLUMN_GAP, y: NODE_START_Y },
        data: {
          label: `${rule.name}\nID: ${rule.rule_id}\nSeverity: ${rule.severity}` +
            (rule.windows_event_ids?.length ? `\nEvents: ${rule.windows_event_ids.join(', ')}` : ''),
          type: 'rule'
        },
        style: {
          background: '#dbeafe',
          border: '2px solid #3b82f6',
          borderRadius: '8px',
          fontSize: '12px',
          width: 200,
          padding: '10px'
        }
      });
    }

    // Add alarm nodes
    alarms.forEach((alarm, index) => {
      const alarmEventLabel = alarm.windows_event_ids?.length
        ? `\nEvents: ${alarm.windows_event_ids.join(', ')}`
        : '';
      const alarmNode = {
        id: `alarm-${alarm.id}`,
        type: 'default',
        position: {
          x:
            FLOW_PADDING_X +
            (LAYOUT_COLUMNS.length + 0.8) * COLUMN_GAP,
          y: NODE_START_Y + index * NODE_VERTICAL_GAP,
        },
        data: {
          label: `${alarm.name}\nSeverity: ${alarm.severity}\nMatch: ${alarm.match_value}${alarmEventLabel}`,
          type: 'alarm',
          alarm
        },
        style: {
          background: '#fef3c7',
          border: '2px solid #d97706',
          borderRadius: '8px',
          fontSize: '11px',
          width: 180,
          padding: '8px'
        }
      };
      newNodes.push(alarmNode);

      // Connect rule to alarm
      newEdges.push({
        id: `edge-rule-alarm-${alarm.id}`,
        source: primaryRuleNodeId,
        target: `alarm-${alarm.id}`,
        animated: true,
        style: { stroke: '#10b981', strokeWidth: 2 },
        label: 'triggers'
      });
    });

    // Add summary node when no alarms are connected
    if (alarms.length === 0) {
      newNodes.push({
        id: 'no-alarms',
        type: 'default',
        position: {
          x: FLOW_PADDING_X + (LAYOUT_COLUMNS.length + 0.8) * COLUMN_GAP,
          y: NODE_START_Y,
        },
        data: {
          label: 'No matching alarms found',
          type: 'info'
        },
        style: {
          background: '#f3f4f6',
          border: '2px solid #9ca3af',
          borderRadius: '8px',
          fontSize: '12px',
          width: 180,
          padding: '10px'
        }
      });
    }

    setNodes([...newNodes]);
    setEdges([...newEdges]);
  }, [layoutRuleNodes, setEdges, setNodes]);

  const fetchRuleDetails = useCallback(async (ruleId) => {
    try {
      setLoading(true);
      setConnectedAlarms([]);
      setEventOverlapAlarms([]);
      const [ruleResponse, alarmsResponse, relationshipsResponse] = await Promise.all([
        ruleAPI.getById(selectedCustomerId, ruleId),
        alarmAPI.getAll(selectedCustomerId),
        analysisAPI.getRelationships(selectedCustomerId)
      ]);

      const rule = ruleResponse.data.rule;
      const allAlarms = alarmsResponse.data.alarms || [];
      const relationships = relationshipsResponse.data.relationships || [];

      const ruleEventIds = new Set(rule.windows_event_ids || []);
      const alarmMap = new Map(allAlarms.map(alarm => [alarm.id, alarm]));
      const directAlarmIds = relationships
        .filter(rel => rel.rule_id === rule.id)
        .map(rel => rel.alarm_id);
      const connected = directAlarmIds
        .map(id => alarmMap.get(id))
        .filter(Boolean);
      const connectedIdSet = new Set(connected.map(alarm => alarm.id));

      const overlapAlarms = allAlarms.filter(alarm => {
        if (connectedIdSet.has(alarm.id)) return false;
        const alarmEventIds = alarm.windows_event_ids || [];
        if (ruleEventIds.size === 0 || alarmEventIds.length === 0) return false;
        return alarmEventIds.some(eventId => ruleEventIds.has(eventId));
      });

      setSelectedRule(rule);
      setConnectedAlarms(connected);
      setEventOverlapAlarms(overlapAlarms);

      // Generate flow diagram
      generateFlowDiagram(rule, connected);
    } catch (error) {
      console.error('Failed to fetch rule details:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedCustomerId, generateFlowDiagram]);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  const filteredRules = rules.filter(rule =>
    rule.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    rule.rule_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  useEffect(() => {
    setPage(1);
  }, [searchTerm, selectedCustomerId]);

  const totalPages = Math.max(1, Math.ceil(filteredRules.length / RULES_PER_PAGE));
  const currentPage = Math.min(page, totalPages);
  const paginatedRules = filteredRules.slice(
    (currentPage - 1) * RULES_PER_PAGE,
    currentPage * RULES_PER_PAGE
  );

  useEffect(() => {
    if (flowInstance && nodes.length) {
      const id = requestAnimationFrame(() => {
        try {
          flowInstance.fitView({ padding: 0.2, duration: 400 });
        } catch (error) {
          console.warn('Unable to fit react flow view', error);
        }
      });
      return () => cancelAnimationFrame(id);
    }
  }, [flowInstance, nodes]);

  if (!selectedCustomerId) {
    return (
      <div className="flex items-center justify-center h-full">
        <Card className="max-w-md">
          <CardContent className="pt-6 text-center">
            <Info className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-lg font-medium">No Customer Selected</p>
            <p className="text-sm text-muted-foreground mt-1">
              Please select a customer to view flow diagrams.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col p-6 gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Flow Diagram</h1>
          <p className="text-muted-foreground mt-1">
            Visualize rule logic and alarm relationships
          </p>
        </div>
        <Button onClick={fetchRules} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-full">
        {/* Rule Selection Panel */}
        <Card className="lg:col-span-1 flex flex-col">
          <CardHeader>
            <CardTitle className="text-lg">Select Rule</CardTitle>
            <CardDescription>
              Choose a rule to visualize its logic and alarm relationships
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 flex-1 flex flex-col">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search rules..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            
            <div className="space-y-2 flex-1 overflow-auto pr-1">
              {loading ? (
                <div className="flex justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : (
                paginatedRules.map((rule) => (
                  <Card
                    key={rule.id}
                    className={`p-3 cursor-pointer transition-colors hover:bg-muted/50 ${
                      selectedRule?.id === rule.id ? 'bg-primary/10 border-primary' : ''
                    }`}
                    onClick={() => fetchRuleDetails(rule.id)}
                  >
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate">{rule.name}</p>
                        <p className="text-xs text-muted-foreground">{rule.rule_id}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant="secondary" className="text-xs">
                            Severity: {rule.severity}
                          </Badge>
                          {rule.windows_event_ids?.length > 0 && (
                            <Badge variant="outline" className="text-xs">
                              Events: {rule.windows_event_ids.join(', ')}
                            </Badge>
                          )}
                          {rule.sig_id && (
                            <Badge variant="outline" className="text-xs">
                              {rule.sig_id}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                  </Card>
                ))
              )}
            </div>
            {!loading && filteredRules.length > 0 && (
              <div className="flex items-center justify-between pt-2 text-xs text-muted-foreground">
                <span>
                  Page {currentPage} / {totalPages}
                </span>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={currentPage === 1}
                    onClick={() => setPage(prev => Math.max(1, prev - 1))}
                    className="h-7 px-2"
                  >
                    Prev
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={currentPage === totalPages}
                    onClick={() => setPage(prev => Math.min(totalPages, prev + 1))}
                    className="h-7 px-2"
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Flow Diagram Panel */}
        <Card className="lg:col-span-3 flex flex-col">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Network className="h-5 w-5" />
                  Flow Visualization
                </CardTitle>
                <CardDescription>
                  {selectedRule 
                    ? `Rule: ${selectedRule.name} | Connected Alarms: ${connectedAlarms.length}`
                    : 'Select a rule from the left panel to view its flow diagram'
                  }
                </CardDescription>
              </div>
              {selectedRule && (
                <div className="flex items-center gap-2">
                  <Badge variant="outline">
                    Rule ID: {selectedRule.rule_id}
                  </Badge>
                  <Badge variant="secondary">
                    Severity: {selectedRule.severity}
                  </Badge>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col gap-6 min-h-[520px]">
            {!selectedRule ? (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <Eye className="h-16 w-16 text-muted-foreground mb-4" />
                <p className="text-lg font-medium">No Rule Selected</p>
                <p className="text-sm text-muted-foreground">
                  Select a rule from the left panel to visualize its logic and alarm relationships
                </p>
              </div>
            ) : (
              <>
                <div className="flex-1 border rounded-lg bg-background min-h-[420px] max-h-[calc(100vh-280px)] overflow-auto">
                  <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    fitView
                    fitViewOptions={{ padding: 0.2 }}
                    nodesDraggable={false}
                    panOnScroll
                    minZoom={0.5}
                    style={{ width: '100%', height: '100%' }}
                    attributionPosition="bottom-left"
                    onInit={setFlowInstance}
                  >
                    <Background />
                    <Controls />
                    <MiniMap 
                      nodeStrokeColor={(n) => {
                        if (n.data?.type === 'rule') return '#3b82f6';
                        if (n.data?.type === 'alarm') return '#d97706';
                        if (n.data?.type === 'trigger') return '#10b981';
                        return '#8b5cf6';
                      }}
                      nodeColor={(n) => {
                        if (n.data?.type === 'rule') return '#dbeafe';
                        if (n.data?.type === 'alarm') return '#fef3c7';
                        if (n.data?.type === 'trigger') return '#dcfce7';
                        return '#f3e8ff';
                      }}
                      nodeBorderRadius={8}
                    />
                  </ReactFlow>
                </div>

                <div className="space-y-4">
                  <div className="grid gap-4 lg:grid-cols-3">
                    <div className="rounded-lg border bg-muted/30 p-4">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">Rule ID</p>
                      <p className="text-sm font-semibold text-foreground break-all">{selectedRule.rule_id}</p>
                    </div>
                    <div className="rounded-lg border bg-muted/30 p-4">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">Connected Alarms</p>
                      <p className="text-sm font-semibold text-foreground">{connectedAlarms.length}</p>
                    </div>
                    <div className="rounded-lg border bg-muted/30 p-4">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">Created</p>
                      <p className="text-sm font-semibold text-foreground">
                        {selectedRule.created_at ? new Date(selectedRule.created_at).toLocaleDateString() : 'Unknown'}
                      </p>
                    </div>
                  </div>

                  <div className="rounded-lg border p-4 bg-background/60">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground mb-2">Description</p>
                    <p className="text-sm text-foreground whitespace-pre-wrap">
                      {selectedRule.description || 'No description provided.'}
                    </p>
                  </div>

                  {selectedRule.windows_events?.length > 0 && (
                    <div className="rounded-lg border p-4 bg-background/60">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground mb-3">Windows Event Coverage</p>
                      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                        {selectedRule.windows_events.map((event) => (
                          <div key={event.id} className="rounded-md border bg-muted/20 p-3 text-xs">
                            <div className="font-semibold text-foreground">{event.id}</div>
                            {event.description && (
                              <p className="mt-1 text-muted-foreground leading-snug">
                                {event.description}
                              </p>
                            )}
                            {event.audit_policy && (
                              <p className="mt-1 text-[10px] text-muted-foreground uppercase tracking-wide">
                                {event.audit_policy}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {connectedAlarms.length > 0 && (
                    <div className="rounded-lg border p-4 bg-background/60">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground mb-3">Connected Alarms</p>
                      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                        {connectedAlarms.map((alarm) => (
                          <div key={alarm.id} className="rounded-md border bg-muted/20 p-3 text-xs">
                            <div className="font-semibold text-foreground line-clamp-2" title={alarm.name}>
                              {alarm.name}
                            </div>
                            <div className="mt-2 flex items-center gap-2 text-muted-foreground">
                              <Badge variant="secondary" className="text-[10px] uppercase tracking-wide">
                                Sev {alarm.severity}
                              </Badge>
                              {alarm.windows_event_ids?.length ? (
                                <span className="text-[10px]">
                                  {alarm.windows_event_ids.length} event{alarm.windows_event_ids.length > 1 ? 's' : ''}
                                </span>
                              ) : (
                                <span className="text-[10px]">No event mapping</span>
                              )}
                            </div>
                            {alarm.windows_event_ids?.length > 0 && (
                              <div className="mt-2 flex flex-wrap gap-1">
                                {alarm.windows_event_ids.slice(0, 3).map(eventId => (
                                  <Badge key={eventId} variant="outline" className="text-[10px]">
                                    {eventId}
                                  </Badge>
                                ))}
                                {alarm.windows_event_ids.length > 3 && (
                                  <span className="text-[10px] text-muted-foreground">+{alarm.windows_event_ids.length - 3} more</span>
                                )}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {eventOverlapAlarms.length > 0 && (
                    <div className="rounded-lg border p-4 bg-background/40">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground mb-2">
                        Alarms Sharing Windows Events (Not Linked)
                      </p>
                      <p className="text-[11px] text-muted-foreground mb-3">
                        These alarms monitor at least one of the same Windows events but are not directly connected to this rule.
                      </p>
                      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                        {eventOverlapAlarms.map((alarm) => (
                          <div key={`overlap-${alarm.id}`} className="rounded-md border bg-muted/10 p-3 text-xs">
                            <div className="font-semibold text-foreground line-clamp-2" title={alarm.name}>
                              {alarm.name}
                            </div>
                            <div className="mt-2 flex items-center gap-2 text-muted-foreground">
                              <Badge variant="outline" className="text-[10px] uppercase tracking-wide">
                                Sev {alarm.severity}
                              </Badge>
                              <span className="text-[10px]">
                                {alarm.windows_event_ids?.length || 0} event
                                {alarm.windows_event_ids && alarm.windows_event_ids.length === 1 ? '' : 's'}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
