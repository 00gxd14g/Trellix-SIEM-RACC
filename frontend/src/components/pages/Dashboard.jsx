import React, { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAppContext } from '@/context/AppContext';
import { customerAPI, ruleAPI, alarmAPI, analysisAPI, systemAPI } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { 
  Users, 
  FileText, 
  Bell, 
  RefreshCw, 
  ArrowRight, 
  AlertTriangle,
  Server,
  Wifi,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, PieChart, Pie, Cell } from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#AF19FF', '#FF19A6'];

export default function Dashboard() {
  const { selectedCustomerId, customers } = useAppContext();
  const { toast } = useToast();
  const [stats, setStats] = useState({
    totalCustomers: 0,
    totalRules: 0,
    totalAlarms: 0,
    ruleStats: {},
    alarmStats: {},
    analysisCoverage: null,
    eventUsage: [],
    totalEventIds: 0,
  });
  const [loading, setLoading] = useState(true);
  const [apiStatus, setApiStatus] = useState({
    ok: true,
    status: 'unknown',
    message: '',
    version: '',
    lastChecked: null,
  });

  const fetchDashboardData = useCallback(async () => {
    setLoading(true);
    try {
      const [customersRes, rulesRes, alarmsRes] = await Promise.all([
        customerAPI.getAll(),
        selectedCustomerId ? ruleAPI.getStats(selectedCustomerId) : Promise.resolve({ data: { stats: {} } }),
        selectedCustomerId ? alarmAPI.getStats(selectedCustomerId) : Promise.resolve({ data: { stats: {} } }),
      ]);

      try {
        const healthRes = await systemAPI.getHealth();
        setApiStatus({
          ok: true,
          status: healthRes.data.status || 'healthy',
          message: healthRes.data.message || 'API reachable',
          version: healthRes.data.version || 'unknown',
          lastChecked: new Date().toISOString(),
        });
      } catch (healthError) {
        console.warn('API health check failed:', healthError);
        const message = healthError.response?.data?.error || healthError.message || 'Unable to reach API.';
        setApiStatus({
          ok: false,
          status: 'unreachable',
          message,
          version: '',
          lastChecked: new Date().toISOString(),
        });
      }

      let analysisCoverage = null;
      let eventUsage = [];
      let totalEventIds = 0;
      if (selectedCustomerId) {
        try {
          const coverageRes = await analysisAPI.getCoverage(selectedCustomerId);
          analysisCoverage = coverageRes.data.coverage;
        } catch (error) {
          console.warn("Could not fetch analysis coverage for selected customer:", error);
          toast({ title: "Warning", description: "Could not load full analysis data for the selected customer.", variant: "warning" });
        }

        try {
          const usageRes = await analysisAPI.getEventUsage(selectedCustomerId, { limit: 20 });
          const usagePayload = usageRes.data.event_usage || {};
          eventUsage = usagePayload.events || [];
          totalEventIds = usagePayload.total_unique_events || 0;
        } catch (error) {
          console.warn("Could not fetch event usage for selected customer:", error);
        }
      }

      setStats({
        totalCustomers: customersRes.data.customers.length,
        totalRules: rulesRes.data.stats?.total_rules || 0,
        totalAlarms: alarmsRes.data.stats?.total_alarms || 0,
        ruleStats: rulesRes.data.stats || {},
        alarmStats: alarmsRes.data.stats || {},
        analysisCoverage: analysisCoverage,
        eventUsage,
        totalEventIds,
      });
    } catch (error) {
      console.error("Failed to fetch dashboard data:", error);
      toast({ title: "Error", description: "Failed to load dashboard data.", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }, [selectedCustomerId, toast]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const ruleSeverityData = stats.ruleStats.severity_distribution?.map(item => ({
    name: `Severity ${item.severity}`,
    value: item.count
  })) || [];

  const alarmSeverityData = stats.alarmStats.severity_distribution?.map(item => ({
    name: `Severity ${item.severity}`,
    value: item.count
  })) || [];

  const ruleTypeData = stats.ruleStats.type_distribution?.map(item => ({
    name: `Type ${item.type}`,
    value: item.count
  })) || [];

  const alarmConditionTypeData = stats.alarmStats.condition_type_distribution?.map(item => ({
    name: `Type ${item.type}`,
    value: item.count
  })) || [];

  const eventUsageData = stats.eventUsage.slice(0, 10).map(item => ({
    event: item.event_id,
    rules: item.rule_count,
    alarms: item.alarm_count,
    total: item.total_references,
    description: item.description,
  }));

  const currentCustomerName = selectedCustomerId 
    ? (customers.find(c => c.id === selectedCustomerId)?.name || 'Unknown Customer') 
    : 'No Customer Selected';

  const apiCardBorder = apiStatus.ok ? 'border-muted' : 'border-destructive/40';
  const apiStatusLabel = apiStatus.ok ? 'Operational' : 'Unavailable';
  const apiStatusColor = apiStatus.ok ? 'text-green-600' : 'text-destructive';

  return (
    <div className="space-y-8 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground mt-2">Overview of your SIEM Alarm Management System</p>
        </div>
        <Button onClick={fetchDashboardData} disabled={loading} variant="outline">
          <RefreshCw className="mr-2 h-4 w-4" />
          {loading ? 'Refreshing...' : 'Refresh Data'}
        </Button>
      </div>

      <Card className="bg-gradient-to-r from-primary to-primary/80 text-primary-foreground shadow-lg">
        <CardHeader>
          <CardTitle className="text-2xl">Welcome to RACC</CardTitle>
          <CardDescription className="text-primary-foreground/80">
            RACC: MSSP'ler ve Kurumlar İçin Trellix SIEM Yönetiminde Multi-Tenant Devrimi
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-lg font-semibold">Current Customer: {currentCustomerName}</p>
          {!selectedCustomerId && (
            <p className="text-sm mt-2">
              Please select a customer from the sidebar to view customer-specific data.
            </p>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className={`border ${apiCardBorder}`}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">API Status</CardTitle>
            <Server className={`h-4 w-4 ${apiStatus.ok ? 'text-green-600' : 'text-destructive'}`} />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${apiStatusColor}`}>{apiStatusLabel}</div>
            <p className="text-xs text-muted-foreground">{apiStatus.message || 'Status unknown'}</p>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <Wifi className="h-3 w-3" />
              <span>Version: {apiStatus.version || 'n/a'}</span>
            </div>
            {apiStatus.lastChecked && (
              <p className="text-xs text-muted-foreground mt-1">
                Last checked: {new Date(apiStatus.lastChecked).toLocaleTimeString()}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Customers</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalCustomers}</div>
            <p className="text-xs text-muted-foreground">Registered in the system</p>
            <Link to="/customers" className="text-sm text-primary hover:underline flex items-center mt-2">
              View Customers <ArrowRight className="ml-1 h-3 w-3" />
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Rules</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalRules}</div>
            <p className="text-xs text-muted-foreground">For the selected customer</p>
            {selectedCustomerId && (
              <Link to="/rules" className="text-sm text-primary hover:underline flex items-center mt-2">
                Manage Rules <ArrowRight className="ml-1 h-3 w-3" />
              </Link>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Alarms</CardTitle>
            <Bell className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalAlarms}</div>
            <p className="text-xs text-muted-foreground">For the selected customer</p>
            {selectedCustomerId && (
              <Link to="/alarms" className="text-sm text-primary hover:underline flex items-center mt-2">
                Manage Alarms <ArrowRight className="ml-1 h-3 w-3" />
              </Link>
            )}
          </CardContent>
        </Card>
      </div>

      {selectedCustomerId && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Rule Severity Distribution</CardTitle>
              <CardDescription>Breakdown of rules by severity level</CardDescription>
            </CardHeader>
            <CardContent>
              {ruleSeverityData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={ruleSeverityData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="value" fill="#8884d8" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-center py-10 text-muted-foreground">
                  No rule severity data available.
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Alarm Severity Distribution</CardTitle>
              <CardDescription>Breakdown of alarms by severity level</CardDescription>
            </CardHeader>
            <CardContent>
              {alarmSeverityData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={alarmSeverityData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {alarmSeverityData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-center py-10 text-muted-foreground">
                  No alarm severity data available.
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Rule Type Distribution</CardTitle>
              <CardDescription>Breakdown of rules by type</CardDescription>
            </CardHeader>
            <CardContent>
              {ruleTypeData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={ruleTypeData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="value" fill="#82ca9d" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-center py-10 text-muted-foreground">
                  No rule type data available.
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Alarm Condition Type Distribution</CardTitle>
              <CardDescription>Breakdown of alarms by condition type</CardDescription>
            </CardHeader>
            <CardContent>
              {alarmConditionTypeData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={alarmConditionTypeData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      outerRadius={80}
                      fill="#82ca9d"
                      dataKey="value"
                    >
                      {alarmConditionTypeData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-center py-10 text-muted-foreground">
                  No alarm condition type data available.
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Windows Event Usage</CardTitle>
              <CardDescription>Most frequently referenced Windows event IDs across rules and alarms</CardDescription>
            </CardHeader>
            <CardContent>
              {eventUsageData.length > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height={320}>
                    <BarChart data={eventUsageData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="event" tick={{ fontSize: 12 }} />
                      <YAxis allowDecimals={false} />
                      <Tooltip
                        formatter={(value, name) => [value, name === 'rules' ? 'Rules' : 'Alarms']}
                        labelFormatter={(label, payload) => {
                          const meta = payload && payload[0] ? payload[0].payload : {};
                          return meta.description ? `${label} — ${meta.description}` : label;
                        }}
                      />
                      <Legend />
                      <Bar dataKey="rules" stackId="usage" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="alarms" stackId="usage" fill="#f97316" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                  <p className="text-xs text-muted-foreground mt-3">
                    Showing top {eventUsageData.length} of {stats.totalEventIds} referenced Windows event IDs.
                  </p>
                </>
              ) : (
                <div className="text-center py-10 text-muted-foreground">
                  No Windows event usage data available for the selected customer.
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Analysis Coverage</CardTitle>
              <CardDescription>Overview of rule-alarm matching coverage</CardDescription>
            </CardHeader>
            <CardContent>
              {stats.analysisCoverage ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-center">
                  <div className="space-y-2">
                    <p className="text-muted-foreground">Total Rules</p>
                    <p className="text-3xl font-bold">{stats.analysisCoverage.total_rules}</p>
                  </div>
                  <div className="space-y-2">
                    <p className="text-muted-foreground">Matched Rules</p>
                    <p className="text-3xl font-bold text-green-500">{stats.analysisCoverage.matched_rules}</p>
                  </div>
                  <div className="space-y-2">
                    <p className="text-muted-foreground">Total Alarms</p>
                    <p className="text-3xl font-bold">{stats.analysisCoverage.total_alarms}</p>
                  </div>
                  <div className="space-y-2">
                    <p className="text-muted-foreground">Matched Alarms</p>
                    <p className="text-3xl font-bold text-green-500">{stats.analysisCoverage.matched_alarms}</p>
                  </div>
                  <div className="space-y-2 md:col-span-2">
                    <p className="text-muted-foreground">Overall Coverage</p>
                    <p className="text-4xl font-bold text-primary">{stats.analysisCoverage.coverage_percentage?.toFixed(2)}%</p>
                  </div>
                </div>
              ) : (
                <div className="text-center py-10 text-muted-foreground">
                  No analysis coverage data available for the selected customer.
                  <Link to="/analysis" className="block text-primary hover:underline mt-2">
                    Go to Analysis Page <ArrowRight className="ml-1 h-3 w-3 inline-block" />
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {!selectedCustomerId && (
        <div className="text-center py-10">
          <AlertTriangle className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
          <h3 className="text-xl font-semibold">No Customer Selected</h3>
          <p className="text-muted-foreground mt-2">
            Please select a customer from the sidebar to view detailed dashboard metrics.
          </p>
          <Link to="/customers" className="mt-4 inline-flex items-center text-primary hover:underline">
            Go to Customers Page <ArrowRight className="ml-1 h-3 w-3" />
          </Link>
        </div>
      )}
    </div>
  );
}
