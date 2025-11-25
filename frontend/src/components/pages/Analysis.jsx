import { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { useAppContext } from '@/context/AppContext';
import { analysisAPI } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/loading';
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui';
import { useToast } from '@/hooks/use-toast';
import {
  BarChart3,
  TrendingUp,
  AlertTriangle,
  RefreshCw,
  Download,
  Shield,
  Activity,
  Eye,
  EyeOff
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  AreaChart,
  Area
} from 'recharts';

const COLORS = {
  primary: 'hsl(var(--primary))',
  secondary: 'hsl(var(--secondary))',
  warning: 'hsl(var(--warning))',
  danger: 'hsl(var(--destructive))',
  purple: 'hsl(var(--purple))',
  pink: 'hsl(var(--pink))',
  cyan: 'hsl(var(--cyan))',
  gray: 'hsl(var(--muted-foreground))',
  success: 'hsl(var(--success))',
};

export default function Analysis({ customerId: customerIdProp }) {
  const { selectedCustomerId } = useAppContext();
  const { toast } = useToast();
  const customerId = customerIdProp ?? selectedCustomerId;
  const [coverage, setCoverage] = useState(null);
  const [relationships, setRelationships] = useState([]);
  const [unmatchedRules, setUnmatchedRules] = useState([]);
  const [unmatchedAlarms, setUnmatchedAlarms] = useState([]);
  const [eventUsage, setEventUsage] = useState({ total_unique_events: 0, events: [] });
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [showRelationships, setShowRelationships] = useState(false);

  const fetchAnalysisData = useCallback(async () => {
    if (!customerId) {
      setCoverage(null);
      setRelationships([]);
      setUnmatchedRules([]);
      setUnmatchedAlarms([]);
      setEventUsage({ total_unique_events: 0, events: [] });
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const [coverageRes, relationshipsRes, unmatchedRulesRes, unmatchedAlarmsRes, eventUsageRes] = await Promise.all([
        analysisAPI.getCoverage(customerId),
        analysisAPI.getRelationships(customerId),
        analysisAPI.getUnmatchedRules(customerId),
        analysisAPI.getUnmatchedAlarms(customerId),
        analysisAPI.getEventUsage(customerId, { limit: 15 }),
      ]);

      setCoverage(coverageRes.data.coverage);
      setRelationships(relationshipsRes.data.relationships);
      setUnmatchedRules(unmatchedRulesRes.data.unmatched_rules);
      setUnmatchedAlarms(unmatchedAlarmsRes.data.unmatched_alarms);
      setEventUsage(eventUsageRes.data.event_usage || { total_unique_events: 0, events: [] });
    } catch (error) {
      console.error('Failed to fetch analysis data:', error);
      toast({ title: 'Analysis Refresh Failed', description: error.response?.data?.error || error.message, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [customerId, toast]);

  useEffect(() => {
    if (customerId) {
      fetchAnalysisData();
    }
  }, [customerId, fetchAnalysisData]);

  const handleGenerateAnalysis = async () => {
    if (!customerId) return;
    try {
      setGenerating(true);
      await analysisAPI.detectRelationships(customerId);
      await fetchAnalysisData();
      toast({ title: 'Analysis Updated', description: 'Rule-alarm relationships recalculated.' });
    } catch (error) {
      console.error('Failed to generate analysis:', error);
      toast({ title: 'Analysis Update Failed', description: error.response?.data?.error || error.message, variant: 'destructive' });
    } finally {
      setGenerating(false);
    }
  };

  const buildReportPayload = (format) => {
    const generatedAt = new Date().toISOString();
    const summary = {
      generatedAt,
      customerId,
      totalRules: coverage?.total_rules ?? 0,
      matchedRules: coverage?.matched_rules ?? 0,
      totalAlarms: coverage?.total_alarms ?? 0,
      matchedAlarms: coverage?.matched_alarms ?? 0,
      coverageRate: coverage?.coverage_percentage ?? 0,
      uniqueWindowsEvents: eventUsage.total_unique_events ?? 0,
    };

    const base = {
      summary,
      relationships,
      unmatchedRules,
      unmatchedAlarms,
      eventUsage: eventUsage.events,
    };

    if (format === 'json') {
      const blob = new Blob([JSON.stringify(base, null, 2)], { type: 'application/json' });
      return { blob, filename: `analysis-report-${customerId}-${generatedAt}.json` };
    }

    const title = `Analysis Report for Customer ${customerId}`;
    const summaryLines = [
      `Generated: ${summary.generatedAt}`,
      `Total Rules: ${summary.totalRules}`,
      `Matched Rules: ${summary.matchedRules}`,
      `Total Alarms: ${summary.totalAlarms}`,
      `Matched Alarms: ${summary.matchedAlarms}`,
      `Coverage Rate: ${summary.coverageRate?.toFixed?.(2) ?? summary.coverageRate}%`,
      `Unique Windows Events: ${summary.uniqueWindowsEvents}`,
    ];

    const relationshipItems = relationships.length
      ? relationships.map(rel => `${rel.rule_name} → ${rel.alarm_name} (match: ${rel.match_value})`)
      : ['None'];
    const unmatchedRuleItems = unmatchedRules.length
      ? unmatchedRules.map(rule => `${rule.name} (${rule.rule_id})`)
      : ['None'];
    const unmatchedAlarmItems = unmatchedAlarms.length
      ? unmatchedAlarms.map(alarm => `${alarm.name}`)
      : ['None'];
    const eventItems = eventUsage.events.length
      ? eventUsage.events.map(event => `${event.event_id} — rules: ${event.rule_count}, alarms: ${event.alarm_count}, total: ${event.total_references}`)
      : ['None'];

    if (format === 'md') {
      const mdSections = [
        `# ${title}`,
        '',
        '## Summary',
        ...summaryLines.map(line => `- ${line}`),
        '',
        '## Relationships',
        ...relationshipItems.map(item => `- ${item}`),
        '',
        '## Unmatched Rules',
        ...unmatchedRuleItems.map(item => `- ${item}`),
        '',
        '## Unmatched Alarms',
        ...unmatchedAlarmItems.map(item => `- ${item}`),
        '',
        '## Top Windows Events',
        ...eventItems.map(item => `- ${item}`),
      ];
      const blob = new Blob([mdSections.join('\n')], { type: 'text/markdown' });
      return { blob, filename: `analysis-report-${customerId}-${generatedAt}.md` };
    }

    const htmlSections = (heading, items) => items.length === 1 && items[0] === 'None'
      ? `<h2>${heading}</h2><p>None</p>`
      : `<h2>${heading}</h2><ul>${items.map(item => `<li>${item}</li>`).join('')}</ul>`;

    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"/><title>${title}</title><style>body{font-family:Inter,Arial,sans-serif;margin:32px;line-height:1.6;color:#111}h1{font-size:28px;margin-bottom:16px}h2{font-size:20px;margin-top:24px;margin-bottom:8px}ul{padding-left:20px}li{margin-bottom:4px}p{margin-bottom:8px;border-left:3px solid #ddd;padding-left:10px;color:#555}</style></head><body><h1>${title}</h1>${htmlSections('Summary', summaryLines)}${htmlSections('Relationships', relationshipItems)}${htmlSections('Unmatched Rules', unmatchedRuleItems)}${htmlSections('Unmatched Alarms', unmatchedAlarmItems)}${htmlSections('Top Windows Events', eventItems)}</body></html>`;

    if (format === 'html') {
      const blob = new Blob([html], { type: 'text/html' });
      return { blob, filename: `analysis-report-${customerId}-${generatedAt}.html` };
    }

    const linesForPdf = [
      title,
      '',
      'Summary:',
      ...summaryLines,
      '',
      'Relationships:',
      ...relationshipItems,
      '',
      'Unmatched Rules:',
      ...unmatchedRuleItems,
      '',
      'Unmatched Alarms:',
      ...unmatchedAlarmItems,
      '',
      'Top Windows Events:',
      ...eventItems,
    ];

    const escapePdf = (input) => input.replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)');
    const startY = 740;
    const lineHeight = 16;
    const pdfCommands = [];
    linesForPdf.forEach((line, index) => {
      if (index === 0) {
        pdfCommands.push(`(${escapePdf(line)}) Tj`);
        return;
      }
      if (line === '') {
        pdfCommands.push(`0 -${lineHeight} Td`);
      } else {
        pdfCommands.push(`0 -${lineHeight} Td (${escapePdf(line)}) Tj`);
      }
    });

    const stream = `BT /F1 12 Tf 72 ${startY} Td ${pdfCommands.join(' ')} ET`;

    const objects = [];
    const addObject = (content) => {
      const index = objects.length + 1;
      objects.push(`${index} 0 obj${content}\nendobj\n`);
      return `${index} 0 R`;
    };

    const pageRef = addObject('<< /Type /Catalog /Pages 2 0 R >>');
    addObject('<< /Type /Pages /Kids [3 0 R] /Count 1 >>');
    addObject('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>');
    addObject(`<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`);
    addObject('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>');

    const header = '%PDF-1.4\n';
    let offset = header.length;
    const xrefEntries = ['0000000000 65535 f \n'];
    const body = objects.map(item => {
      const entry = offset.toString().padStart(10, '0') + ' 00000 n \n';
      xrefEntries.push(entry);
      offset += item.length;
      return item;
    }).join('');
    const xref = `xref\n0 ${objects.length + 1}\n${xrefEntries.join('')}trailer<< /Size ${objects.length + 1} /Root ${pageRef} >>\nstartxref\n${offset}\n%%EOF`;
    const pdfContent = header + body + xref;
    const blob = new Blob([pdfContent], { type: 'application/pdf' });
    return { blob, filename: `analysis-report-${customerId}-${generatedAt}.pdf` };
  };

  const handleExportAnalysis = async (format) => {
    if (!customerId) return;

    if (format === 'html') {
      try {
        // Use backend generation for HTML to get the full template
        const response = await analysisAPI.getReport(customerId);

        // Create a blob from the response
        const blob = new Blob([response.data], { type: 'text/html' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;

        // Try to get filename from content-disposition header
        const contentDisposition = response.headers['content-disposition'];
        let filename = `analysis-report-${customerId}.html`;
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
          if (filenameMatch && filenameMatch.length === 2)
            filename = filenameMatch[1];
        }

        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
        toast({ title: 'Analysis Exported', description: 'HTML report downloaded successfully.' });
      } catch (error) {
        console.error('Export failed:', error);
        toast({ title: 'Export Failed', description: 'Failed to generate HTML report.', variant: 'destructive' });
      }
      return;
    }

    const { blob, filename } = buildReportPayload(format);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast({ title: 'Analysis Exported', description: `Report downloaded as ${format.toUpperCase()}.` });
  };

  const handleRefresh = async () => {
    await fetchAnalysisData();
    toast({ title: 'Analysis Refreshed' });
  };

  if (!customerId) {
    return (
      <div className="flex items-center justify-center h-full">
        <Card className="max-w-md">
          <CardContent className="pt-6">
            <div className="text-center space-y-4">
              <AlertTriangle className="h-12 w-12 mx-auto text-yellow-500" />
              <p className="text-lg font-medium">No Customer Selected</p>
              <p className="text-sm text-muted-foreground">
                Please select a customer from the sidebar to view analysis.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner />
      </div>
    );
  }

  // Prepare data for charts
  const safeRatio = (part, total) => {
    if (!total || total <= 0) return 0;
    return (part / total) * 100;
  };

  const coverageData = coverage ? [
    { name: 'Matched', value: coverage.matched_rules, color: COLORS.secondary },
    { name: 'Unmatched', value: coverage.total_rules - coverage.matched_rules, color: COLORS.danger }
  ] : [];

  const alarmCoverageData = coverage ? [
    { name: 'Covered', value: coverage.matched_alarms, color: COLORS.primary },
    { name: 'Uncovered', value: coverage.total_alarms - coverage.matched_alarms, color: COLORS.warning }
  ] : [];

  const eventUsageBarData = eventUsage.events.slice(0, 10).map((item) => ({
    event: item.event_id,
    rules: item.rule_count,
    alarms: item.alarm_count,
    total: item.total_references,
    description: item.description,
    audit_policy: item.audit_policy,
  }));

  const eventUsageSummary = {
    totalUnique: eventUsage.total_unique_events || 0,
    topEvent: eventUsage.events.length > 0 ? eventUsage.events[0] : null,
    heavyRuleDependence: eventUsage.events.filter(ev => ev.rule_count && ev.rule_count > ev.alarm_count * 2).length,
    heavyAlarmDependence: eventUsage.events.filter(ev => ev.alarm_count && ev.alarm_count > ev.rule_count * 2).length,
  };

  const comparisonData = coverage ? [
    { name: 'Rules', total: coverage.total_rules, matched: coverage.matched_rules },
    { name: 'Alarms', total: coverage.total_alarms, matched: coverage.matched_alarms }
  ] : [];

  const radarData = [
    {
      category: 'Coverage',
      value: coverage?.coverage_percentage || 0,
      fullMark: 100
    },
    {
      category: 'Rule Efficiency',
      value: coverage ? safeRatio(coverage.matched_rules, coverage.total_rules) : 0,
      fullMark: 100
    },
    {
      category: 'Alarm Coverage',
      value: coverage ? safeRatio(coverage.matched_alarms, coverage.total_alarms) : 0,
      fullMark: 100
    },
    {
      category: 'Optimization Score',
      value: coverage ? 100 - safeRatio(unmatchedRules.length, coverage.total_rules) : 0,
      fullMark: 100
    }
  ];

  // Group relationships by matched fields count
  const relationshipStats = relationships.reduce((acc, rel) => {
    const fieldCount = rel.matched_fields.length;
    acc[fieldCount] = (acc[fieldCount] || 0) + 1;
    return acc;
  }, {});

  const matchQualityData = Object.entries(relationshipStats).map(([fields, count]) => ({
    fields: `${fields} fields`,
    count,
    quality: fields >= 3 ? 'High' : fields >= 2 ? 'Medium' : 'Low'
  }));

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Analysis Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Comprehensive analysis of rule-alarm relationships and coverage
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleRefresh} disabled={loading || generating || !customerId} variant="outline">
            <RefreshCw className="mr-2 h-4 w-4" /> Refresh
          </Button>
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" disabled={!customerId}>
                <Download className="mr-2 h-4 w-4" /> Export
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-48 space-y-2">
              <p className="text-xs text-muted-foreground">Export as:</p>
              {[
                { label: 'PDF', value: 'pdf' },
                { label: 'HTML', value: 'html' },
                { label: 'Markdown', value: 'md' },
                { label: 'JSON', value: 'json' },
              ].map(option => (
                <Button
                  key={option.value}
                  variant="ghost"
                  className="w-full justify-start"
                  onClick={() => handleExportAnalysis(option.value)}
                >
                  {option.label}
                </Button>
              ))}
            </PopoverContent>
          </Popover>
          <Button onClick={handleGenerateAnalysis} disabled={generating || !customerId}>
            {generating ? 'Generating...' : 'Generate Analysis'}
          </Button>
        </div>
      </div>

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Rules</p>
                <p className="text-2xl font-bold">{coverage?.total_rules || 0}</p>
              </div>
              <Shield className="h-8 w-8 text-blue-500" />
            </div>
            <Progress
              value={safeRatio(coverage?.matched_rules || 0, coverage?.total_rules || 0)}
              className="mt-3"
            />
            <p className="text-xs text-muted-foreground mt-1">
              {coverage?.matched_rules || 0} matched
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Alarms</p>
                <p className="text-2xl font-bold">{coverage?.total_alarms || 0}</p>
              </div>
              <Activity className="h-8 w-8 text-green-500" />
            </div>
            <Progress
              value={safeRatio(coverage?.matched_alarms || 0, coverage?.total_alarms || 0)}
              className="mt-3"
            />
            <p className="text-xs text-muted-foreground mt-1">
              {coverage?.matched_alarms || 0} covered
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Coverage Rate</p>
                <p className="text-2xl font-bold">
                  {coverage ? `${coverage.coverage_percentage.toFixed(1)}%` : '0%'}
                </p>
              </div>
              <BarChart3 className="h-8 w-8 text-purple-500" />
            </div>
            <div className="mt-3 flex items-center text-xs">
              <TrendingUp className="h-3 w-3 mr-1 text-green-500" />
              <span className="text-green-500">+5.2%</span>
              <span className="text-muted-foreground ml-1">from last analysis</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Relationships</p>
                <p className="text-2xl font-bold">{relationships.length}</p>
              </div>
              <TrendingUp className="h-8 w-8 text-cyan-500" />
            </div>
            <div className="mt-3">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowRelationships(!showRelationships)}
                className="text-xs"
              >
                {showRelationships ? (
                  <>
                    <EyeOff className="h-3 w-3 mr-1" /> Hide Details
                  </>
                ) : (
                  <>
                    <Eye className="h-3 w-3 mr-1" /> View Details
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Windows Events</p>
                <p className="text-2xl font-bold">{eventUsageSummary.totalUnique}</p>
              </div>
              <BarChart3 className="h-8 w-8 text-indigo-500" />
            </div>
            <div className="mt-3 text-xs text-muted-foreground space-y-1">
              {eventUsageSummary.topEvent ? (
                <p>
                  Top event: <span className="font-semibold text-foreground">{eventUsageSummary.topEvent.event_id}</span> ·
                  Total {eventUsageSummary.topEvent.total_references}
                </p>
              ) : (
                <p>No Windows event data.</p>
              )}
              {eventUsageSummary.totalUnique > 0 && (
                <p>
                  Rule-biased: {eventUsageSummary.heavyRuleDependence} · Alarm-biased: {eventUsageSummary.heavyAlarmDependence}
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Windows Event Usage */}
      <Card>
        <CardHeader>
          <CardTitle>Windows Event Utilization</CardTitle>
          <CardDescription>
            Top event IDs referenced by rules and alarms. Use this to spot over/under coverage.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {eventUsageBarData.length > 0 ? (
            <div className="grid gap-6 lg:grid-cols-2">
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={eventUsageBarData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="event" tick={{ fontSize: 12 }} angle={-15} height={60} dy={10} />
                  <YAxis allowDecimals={false} />
                  <Tooltip
                    labelFormatter={(label, payload) => {
                      const meta = payload && payload[0] ? payload[0].payload : {};
                      if (!meta.description) return label;
                      return `${label} — ${meta.description}`;
                    }}
                  />
                  <Legend />
                  <Bar dataKey="rules" stackId="stack" fill={COLORS.secondary} radius={[4, 4, 0, 0]} />
                  <Bar dataKey="alarms" stackId="stack" fill={COLORS.primary} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>

              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  Detailed breakdown of the same data. Counts represent how many rule or alarm definitions reference the Windows event ID.
                </p>
                <div className="rounded-lg border divide-y overflow-hidden">
                  <div className="grid grid-cols-5 gap-2 bg-muted/60 px-3 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    <span className="col-span-2">Event ID</span>
                    <span>Rules</span>
                    <span>Alarms</span>
                    <span>Total</span>
                  </div>
                  <div className="max-h-64 overflow-auto text-sm">
                    {eventUsageBarData.map(item => (
                      <div key={item.event} className="grid grid-cols-5 gap-2 px-3 py-2 hover:bg-muted/30">
                        <span className="col-span-2 font-medium text-foreground" title={item.description || undefined}>{item.event}</span>
                        <span>{item.rules}</span>
                        <span>{item.alarms}</span>
                        <span className="font-semibold">{item.total}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              No Windows event usage data available for this customer.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Rule Coverage Distribution</CardTitle>
            <CardDescription>Breakdown of matched vs unmatched rules</CardDescription>
          </CardHeader>
          <CardContent>
            {coverageData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={coverageData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    dataKey="value"
                  >
                    {coverageData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center py-10 text-muted-foreground">
                No rule coverage data available.
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Alarm Coverage Distribution</CardTitle>
            <CardDescription>Breakdown of covered vs uncovered alarms</CardDescription>
          </CardHeader>
          <CardContent>
            {alarmCoverageData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={alarmCoverageData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    dataKey="value"
                  >
                    {alarmCoverageData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center py-10 text-muted-foreground">
                No alarm coverage data available.
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Rules vs Alarms Comparison</CardTitle>
            <CardDescription>Total and matched comparison</CardDescription>
          </CardHeader>
          <CardContent>
            {comparisonData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={comparisonData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="total" fill={COLORS.gray} />
                  <Bar dataKey="matched" fill={COLORS.primary} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center py-10 text-muted-foreground">
                No comparison data available.
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Analysis Performance Metrics</CardTitle>
            <CardDescription>Overall system performance indicators</CardDescription>
          </CardHeader>
          <CardContent>
            {radarData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <RadarChart data={radarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="category" />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} />
                  <Radar name="Performance" dataKey="value" stroke={COLORS.purple} fill={COLORS.purple} fillOpacity={0.6} />
                  <Tooltip />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center py-10 text-muted-foreground">
                No performance data available.
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Match Quality Analysis */}
      {matchQualityData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Match Quality Distribution</CardTitle>
            <CardDescription>Analysis of relationship quality based on matched fields</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={matchQualityData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="fields" />
                <YAxis />
                <Tooltip />
                <Area type="monotone" dataKey="count" stroke={COLORS.cyan} fill={COLORS.cyan} fillOpacity={0.6} />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Relationships Details */}
      {showRelationships && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-6 w-6" /> Rule-Alarm Relationships
            </CardTitle>
            <CardDescription>
              Detailed relationships between rules and alarms
            </CardDescription>
          </CardHeader>
          <CardContent>
            {relationships.length > 0 ? (
              <div className="space-y-4 max-h-96 overflow-y-auto">
                {relationships.map((rel, index) => (
                  <div key={index} className="border p-4 rounded-lg hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between">
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">Rule</Badge>
                          <span className="font-medium">{rel.rule_name}</span>
                          <span className="text-sm text-muted-foreground">(ID: {rel.rule_identifier || rel.rule_id})</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">Alarm</Badge>
                          <span className="font-medium">{rel.alarm_name}</span>
                          <span className="text-sm text-muted-foreground">(ID: {rel.alarm_id})</span>
                        </div>
                      </div>
                      <Badge
                        className={`${rel.matched_fields.length >= 3 ? 'bg-green-500' :
                            rel.matched_fields.length >= 2 ? 'bg-yellow-500' :
                              'bg-red-500'
                          }`}
                      >
                        {rel.matched_fields.length} fields
                      </Badge>
                    </div>
                    <div className="mt-3">
                      <p className="text-sm text-muted-foreground">Matched Fields:</p>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {rel.matched_fields.map((field, idx) => (
                          <Badge key={idx} variant="secondary" className="text-xs">
                            {field}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center text-muted-foreground py-8">No relationships found.</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Unmatched Items */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-6 w-6 text-yellow-500" /> Unmatched Rules
            </CardTitle>
            <CardDescription>
              Rules that do not currently match any alarms
            </CardDescription>
          </CardHeader>
          <CardContent>
            {unmatchedRules.length > 0 ? (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {unmatchedRules.map((rule, index) => (
                  <div key={index} className="flex items-center justify-between p-2 hover:bg-accent rounded-md">
                    <span className="text-sm font-medium">{rule.name}</span>
                    <Badge variant="outline" className="text-xs">
                      ID: {rule.id}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Shield className="h-12 w-12 mx-auto text-green-500 mb-2" />
                <p className="text-sm text-muted-foreground">All rules are matched!</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-6 w-6 text-orange-500" /> Unmatched Alarms
            </CardTitle>
            <CardDescription>
              Alarms that are not currently covered by any rules
            </CardDescription>
          </CardHeader>
          <CardContent>
            {unmatchedAlarms.length > 0 ? (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {unmatchedAlarms.map((alarm, index) => (
                  <div key={index} className="flex items-center justify-between p-2 hover:bg-accent rounded-md">
                    <span className="text-sm font-medium">{alarm.name}</span>
                    <Badge variant="outline" className="text-xs">
                      ID: {alarm.id}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Activity className="h-12 w-12 mx-auto text-green-500 mb-2" />
                <p className="text-sm text-muted-foreground">All alarms are covered!</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
