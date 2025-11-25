import React, { useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { X, Copy, Network, Code2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { Badge } from '@/components/ui/badge';
import ReactFlow, { Controls, Background, MiniMap } from 'reactflow';
import 'reactflow/dist/style.css';
import { parseRuleFilters, getRuleStatistics } from '@/utils/ruleParser';
import XMLEditor from '@/components/XMLEditor';

export default function RuleDetailModal({ rule, onClose, onSave }) {
  const { toast } = useToast();
  const [showXMLEditor, setShowXMLEditor] = useState(false);

  const flowData = useMemo(() => {
    if (rule?.xml_content) {
      return parseRuleFilters(rule.xml_content);
    }
    return null;
  }, [rule?.xml_content]);

  const ruleStats = useMemo(() => {
    if (rule?.xml_content) {
      return getRuleStatistics(rule.xml_content);
    }
    return {};
  }, [rule?.xml_content]);

  if (!rule) return null;

  const handleCopyXml = () => {
    navigator.clipboard.writeText(rule.xml_content);
    toast({ title: "Copied!", description: "Rule XML content copied to clipboard." });
  };

  const getSeverityColor = (severity) => {
    if (severity >= 80) return 'destructive';
    if (severity >= 60) return 'warning';
    if (severity >= 40) return 'default';
    return 'secondary';
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <Card className="w-full max-w-3xl max-h-[90vh] overflow-auto">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div>
            <CardTitle className="text-2xl font-bold">Rule Details: {rule.name}</CardTitle>
            <CardDescription>ID: {rule.rule_id}</CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent className="text-sm">
          <Tabs defaultValue="overview" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="filters">Filter Logic</TabsTrigger>
              <TabsTrigger value="xml">XML Content</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-muted-foreground">Sig ID:</p>
                  <p className="font-medium">{rule.sig_id || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Severity:</p>
                  <Badge variant={getSeverityColor(rule.severity)}>{rule.severity}</Badge>
                </div>
                <div>
                  <p className="text-muted-foreground">Rule Type:</p>
                  <p className="font-medium">{rule.rule_type || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Revision:</p>
                  <p className="font-medium">{rule.revision || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Origin:</p>
                  <p className="font-medium">{rule.origin || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Action:</p>
                  <p className="font-medium">{rule.action || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Created At:</p>
                  <p className="font-medium">{rule.created_at ? new Date(rule.created_at).toLocaleString() : 'N/A'}</p>
                </div>
              </div>
              <div>
                <p className="text-muted-foreground">Description:</p>
                <p className="font-medium whitespace-pre-wrap">{rule.description || 'N/A'}</p>
              </div>

              {/* Rule Statistics */}
              {Object.keys(ruleStats).length > 0 && (
                <div className="border-t pt-4">
                  <p className="text-muted-foreground mb-2">Rule Statistics:</p>
                  <div className="grid grid-cols-5 gap-2 text-xs">
                    <div className="text-center">
                      <div className="font-medium">{ruleStats.triggers || 0}</div>
                      <div className="text-muted-foreground">Triggers</div>
                    </div>
                    <div className="text-center">
                      <div className="font-medium">{ruleStats.rules || 0}</div>
                      <div className="text-muted-foreground">Rules</div>
                    </div>
                    <div className="text-center">
                      <div className="font-medium">{ruleStats.filters || 0}</div>
                      <div className="text-muted-foreground">Filters</div>
                    </div>
                    <div className="text-center">
                      <div className="font-medium">{ruleStats.andFilters || 0}</div>
                      <div className="text-muted-foreground">AND</div>
                    </div>
                    <div className="text-center">
                      <div className="font-medium">{ruleStats.orFilters || 0}</div>
                      <div className="text-muted-foreground">OR</div>
                    </div>
                  </div>
                </div>
              )}
            </TabsContent>

            <TabsContent value="filters" className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <Network className="h-5 w-5" />
                <h3 className="font-semibold">Rule Filter Logic</h3>
              </div>

              {flowData && flowData.nodes && flowData.nodes.length > 0 ? (
                <div className="h-96 border rounded-lg">
                  <ReactFlow
                    nodes={flowData.nodes}
                    edges={flowData.edges}
                    fitView
                    attributionPosition="bottom-left"
                  >
                    <Background />
                    <Controls />
                    <MiniMap
                      nodeStrokeColor={(n) => {
                        if (n.data?.type === 'trigger') return '#d97706';
                        if (n.data?.type === 'rule') return '#3b82f6';
                        if (n.data?.type === 'filterGroup') return '#16a34a';
                        return '#8b5cf6';
                      }}
                      nodeColor={(n) => {
                        if (n.data?.type === 'trigger') return '#fef3c7';
                        if (n.data?.type === 'rule') return '#dbeafe';
                        if (n.data?.type === 'filterGroup') return '#dcfce7';
                        return '#f3e8ff';
                      }}
                      nodeBorderRadius={8}
                    />
                  </ReactFlow>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-64 text-center">
                  <Network className="h-12 w-12 text-muted-foreground mb-2" />
                  <p className="text-muted-foreground">No filter logic found in this rule</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    The rule may not contain complex filter structures
                  </p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="xml" className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-muted-foreground">XML Content:</p>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={handleCopyXml}>
                    <Copy className="h-4 w-4 mr-2" /> Copy XML
                  </Button>
                  <Button variant="default" size="sm" onClick={() => setShowXMLEditor(true)}>
                    <Code2 className="h-4 w-4 mr-2" /> {onSave ? 'Edit XML' : 'View XML'}
                  </Button>
                </div>
              </div>
              <pre className="bg-muted p-3 rounded-md text-xs overflow-auto max-h-80">
                <code>{rule.xml_content}</code>
              </pre>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* XML Editor Modal */}
      <XMLEditor
        open={showXMLEditor}
        onOpenChange={setShowXMLEditor}
        xmlContent={rule.xml_content}
        title={`Edit XML - ${rule.name}`}
        onSave={onSave}
        readOnly={!onSave}
      />
    </div>
  );
}
