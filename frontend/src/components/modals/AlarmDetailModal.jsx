import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { X, Copy, Code2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { Badge } from '@/components/ui/badge';
import XMLEditor from '@/components/XMLEditor';

export default function AlarmDetailModal({ alarm, onClose, onSave }) {
  const { toast } = useToast();
  const [showXMLEditor, setShowXMLEditor] = useState(false);

  if (!alarm) return null;

  const handleCopyXml = () => {
    navigator.clipboard.writeText(alarm.xml_content);
    toast({ title: "Copied!", description: "Alarm XML content copied to clipboard." });
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
            <CardTitle className="text-2xl font-bold">Alarm Details: {alarm.name}</CardTitle>
            <CardDescription>ID: {alarm.id}</CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-muted-foreground">Severity:</p>
              <Badge variant={getSeverityColor(alarm.severity)}>{alarm.severity}</Badge>
            </div>
            <div>
              <p className="text-muted-foreground">Match Value:</p>
              <p className="font-medium break-all">{alarm.match_value}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Min Version:</p>
              <p className="font-medium">{alarm.min_version}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Match Field:</p>
              <p className="font-medium">{alarm.match_field}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Condition Type:</p>
              <p className="font-medium">{alarm.condition_type}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Assignee ID:</p>
              <p className="font-medium">{alarm.assignee_id}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Escalation Assignee ID:</p>
              <p className="font-medium">{alarm.esc_assignee_id}</p>
            </div>
            <div className="col-span-2">
              <p className="text-muted-foreground mb-1">Windows Event IDs:</p>
              {alarm.windows_event_ids?.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {alarm.windows_event_ids.map(eventId => {
                    const eventDetail = alarm.windows_events?.find(e => e.id === eventId);
                    const description = eventDetail?.description || `Event ${eventId}`;
                    return (
                      <Badge
                        key={eventId}
                        variant="outline"
                        className="text-xs font-mono cursor-help"
                        title={description}
                      >
                        {eventId}
                      </Badge>
                    );
                  })}
                </div>
              ) : (
                <p className="font-medium text-muted-foreground">None</p>
              )}
            </div>
          </div>
          <div>
            <p className="text-muted-foreground">Note:</p>
            <p className="font-medium whitespace-pre-wrap">{alarm.note || 'N/A'}</p>
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
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
            <pre className="bg-muted p-3 rounded-md text-xs overflow-auto max-h-60">
              <code>{alarm.xml_content}</code>
            </pre>
          </div>
        </CardContent>
      </Card>

      <XMLEditor
        open={showXMLEditor}
        onOpenChange={setShowXMLEditor}
        xmlContent={alarm.xml_content}
        title={`Edit XML - ${alarm.name}`}
        onSave={onSave}
        readOnly={!onSave}
      />
    </div>
  );
}
