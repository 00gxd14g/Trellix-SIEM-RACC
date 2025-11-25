import React, { useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/Switch';
import { useTheme } from '@/components/theme-provider';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { LoadingSpinner } from '@/components/ui/loading';
import { useToast } from '@/hooks/use-toast';
import { settingsAPI } from '@/lib/api';
import { useAppContext } from '@/context/AppContext';
import {
  Settings as SettingsIcon,
  Save,
  RotateCcw,
  Database,
  Shield,
  FileText,
  Bell,
  Globe2,
  Wifi,
  Plug,
  Info,
  Users,
  Download,
  Upload,
  CheckCircle2,
  XCircle,
  AlertCircle,
} from 'lucide-react';

const INITIAL_SYSTEM_SETTINGS = {
  general: {
    appName: 'RACC',
    maxFileSize: 16,
    defaultPageSize: 50,
    enableNotifications: true,
    notificationEmail: '',
    backupEnabled: true,
    backupFrequency: 'daily',
    enableAuditLog: true,
    sessionTimeout: 60,
    theme: 'system',
  },
  api: {
    apiBaseUrl: 'http://localhost:5000/api',
    healthEndpoint: '/health',
    apiKey: '',
    authHeader: 'Authorization',
    timeout: 15,
    verifySsl: false,
    pollInterval: 60,
  },
  customer_defaults: {
    maxAlarmNameLength: 128,
    defaultSeverity: 50,
    defaultConditionType: 14,
    matchField: 'DSIDSigID',
    summaryTemplate: `Destination IP: [$Destination IP]\nSource IP: [$Source IP]\nSource Port: [$Source Port]\nDestination Port: [$Destination Port]\nAlarm Name: [$Alarm Name]\nCondition Type: [$Condition Type]\nAlarm Note: [$Alarm Note]\nTrigger Date: [$Trigger Date]\nAlarm Severity: [$Alarm Severity]\nTraffic Type: L2L / R2L`,
    defaultAssignee: 8199,
    defaultEscAssignee: 57355,
    defaultMinVersion: '11.6.14',
  },
};

const CUSTOMER_NUMERIC_FIELDS = new Set([
  'maxAlarmNameLength',
  'defaultSeverity',
  'defaultConditionType',
  'defaultAssignee',
  'defaultEscAssignee',
]);

const GENERAL_NUMERIC_FIELDS = new Set(['maxFileSize', 'defaultPageSize', 'sessionTimeout']);
const API_NUMERIC_FIELDS = new Set(['timeout', 'pollInterval']);

export default function Settings() {
  const { theme, setTheme } = useTheme();
  const { toast } = useToast();
  const { customers, selectedCustomerId } = useAppContext();

  const [systemSettings, setSystemSettings] = useState(INITIAL_SYSTEM_SETTINGS);
  const [systemDefaults, setSystemDefaults] = useState(INITIAL_SYSTEM_SETTINGS);
  const [systemLoading, setSystemLoading] = useState(true);
  const [systemDirty, setSystemDirty] = useState(false);
  const [systemSaving, setSystemSaving] = useState(false);
  const [apiTestResult, setApiTestResult] = useState(null);

  const [activeCustomerId, setActiveCustomerId] = useState(null);
  const [customerSettings, setCustomerSettings] = useState({
    defaults: INITIAL_SYSTEM_SETTINGS.customer_defaults,
    overrides: {},
    effective: INITIAL_SYSTEM_SETTINGS.customer_defaults,
  });
  const [customerDirty, setCustomerDirty] = useState(false);
  const [customerLoading, setCustomerLoading] = useState(false);

  const [exportLoading, setExportLoading] = useState(false);
  const [importLoading, setImportLoading] = useState(false);

  useEffect(() => {
    const loadSystemSettings = async () => {
      setSystemLoading(true);
      try {
        const response = await settingsAPI.getSystem();
        const data = response.data;
        setSystemSettings(data.settings);
        setSystemDefaults(data.defaults);
        setSystemDirty(false);

        const preferredTheme = data.settings.general.theme || 'system';
        if (preferredTheme !== theme) {
          setTheme(preferredTheme);
        }
      } catch (error) {
        console.error('Failed to load system settings:', error);
        toast({ title: 'Error', description: 'Failed to load system settings.', variant: 'destructive' });
      } finally {
        setSystemLoading(false);
      }
    };

    loadSystemSettings();
  }, [setTheme, toast]);

  useEffect(() => {
    const initialCustomer = selectedCustomerId || customers[0]?.id || null;
    setActiveCustomerId(initialCustomer);
  }, [customers, selectedCustomerId]);

  useEffect(() => {
    if (!activeCustomerId) {
      return;
    }

    const loadCustomerSettings = async () => {
      setCustomerLoading(true);
      try {
        const response = await settingsAPI.getCustomer(activeCustomerId);
        const data = response.data;
        setCustomerSettings({
          defaults: data.defaults,
          overrides: data.overrides,
          effective: data.effective,
        });
        setCustomerDirty(false);
      } catch (error) {
        console.error('Failed to load customer settings:', error);
        toast({ title: 'Error', description: 'Failed to load customer settings.', variant: 'destructive' });
      } finally {
        setCustomerLoading(false);
      }
    };

    loadCustomerSettings();
  }, [activeCustomerId, toast]);

  const updateSystemSetting = (section, field, rawValue) => {
    const numericFields = section === 'general' ? GENERAL_NUMERIC_FIELDS
      : section === 'api' ? API_NUMERIC_FIELDS
        : new Set();

    let value = rawValue;

    // Handle numeric fields
    if (numericFields.has(field)) {
      if (rawValue === '') {
        value = '';
      } else {
        const num = Number.parseInt(rawValue, 10);
        if (isNaN(num)) {
          // Don't update if invalid number
          return;
        }
        value = num;
      }
    }

    setSystemSettings(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value,
      },
    }));
    setSystemDirty(true);

    // Apply theme immediately for live preview
    if (section === 'general' && field === 'theme' && typeof value === 'string') {
      setTheme(value);
    }
  };

  const handleResetSystem = () => {
    setSystemSettings(systemDefaults);
    setSystemDirty(true);
    toast({ title: 'Settings Reset', description: 'System settings have been reset to defaults.' });
  };

  const handleSaveSystem = async () => {
    setSystemSaving(true);
    try {
      const response = await settingsAPI.updateSystem(systemSettings);

      // Update with server-validated settings
      if (response.data?.updated) {
        const merged = {
          general: response.data.updated.general || systemSettings.general,
          api: response.data.updated.api || systemSettings.api,
          customer_defaults: response.data.updated.customer_defaults || systemSettings.customer_defaults,
        };
        setSystemSettings(merged);
      }

      toast({
        title: 'Success',
        description: 'System settings saved successfully.',
      });
      setSystemDirty(false);
    } catch (error) {
      console.error('Failed to save system settings:', error);
      const message = error.response?.data?.error || 'Failed to save system settings.';
      toast({
        title: 'Error',
        description: message,
        variant: 'destructive'
      });
    } finally {
      setSystemSaving(false);
    }
  };

  const handleTestConnection = async () => {
    setApiTestResult({ status: 'pending' });
    try {
      const response = await settingsAPI.testConnection(systemSettings.api);
      const payload = response.data;
      if (payload.success) {
        setApiTestResult({
          status: 'success',
          message: `Connection successful (HTTP ${payload.status_code})`,
        });
        toast({ title: 'API Connection', description: 'Successfully reached the configured API.' });
      } else {
        setApiTestResult({
          status: 'error',
          message: payload.error || 'Connection test failed.',
        });
        toast({ title: 'API Connection Failed', description: payload.error || 'Unable to reach API.', variant: 'destructive' });
      }
    } catch (error) {
      const message = error.response?.data?.error || error.message;
      setApiTestResult({ status: 'error', message });
      toast({ title: 'API Connection Failed', description: message, variant: 'destructive' });
    }
  };

  const handleCustomerOverrideChange = (field, rawValue) => {
    const value = CUSTOMER_NUMERIC_FIELDS.has(field)
      ? rawValue === ''
        ? ''
        : Number.parseInt(rawValue, 10)
      : rawValue;

    setCustomerSettings(prev => ({
      ...prev,
      overrides: {
        ...prev.overrides,
        [field]: value,
      },
      effective: {
        ...prev.effective,
        [field]: value === '' || value === null ? prev.defaults[field] : value,
      },
    }));
    setCustomerDirty(true);
  };

  const handleResetCustomerOverrides = () => {
    setCustomerSettings(prev => ({
      defaults: prev.defaults,
      overrides: {},
      effective: { ...prev.defaults },
    }));
    setCustomerDirty(true);
  };

  const handleSaveCustomerOverrides = async () => {
    if (!activeCustomerId) return;
    try {
      const response = await settingsAPI.updateCustomer(activeCustomerId, customerSettings.overrides);
      const data = response.data;
      setCustomerSettings({
        defaults: data.defaults,
        overrides: data.overrides,
        effective: data.effective,
      });
      setCustomerDirty(false);
      toast({ title: 'Success', description: 'Customer settings saved successfully.' });
    } catch (error) {
      console.error('Failed to save customer settings:', error);
      toast({ title: 'Error', description: 'Failed to save customer settings.', variant: 'destructive' });
    }
  };

  const handleExportSettings = async () => {
    setExportLoading(true);
    try {
      const settingsToExport = {
        version: '1.0',
        timestamp: new Date().toISOString(),
        settings: systemSettings,
      };

      const blob = new Blob([JSON.stringify(settingsToExport, null, 2)], {
        type: 'application/json',
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `settings-export-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast({
        title: 'Export Successful',
        description: 'Settings have been exported successfully.',
      });
    } catch (error) {
      console.error('Failed to export settings:', error);
      toast({
        title: 'Export Failed',
        description: 'Failed to export settings.',
        variant: 'destructive',
      });
    } finally {
      setExportLoading(false);
    }
  };

  const handleImportSettings = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setImportLoading(true);
    try {
      const text = await file.text();
      const imported = JSON.parse(text);

      // Validate import structure
      if (!imported.settings) {
        throw new Error('Invalid settings file format');
      }

      // Merge with existing settings to preserve any new fields
      const merged = {
        general: { ...systemSettings.general, ...(imported.settings.general || {}) },
        api: { ...systemSettings.api, ...(imported.settings.api || {}) },
        customer_defaults: {
          ...systemSettings.customer_defaults,
          ...(imported.settings.customer_defaults || {}),
        },
      };

      setSystemSettings(merged);
      setSystemDirty(true);

      toast({
        title: 'Import Successful',
        description: 'Settings imported. Click Save to apply changes.',
      });
    } catch (error) {
      console.error('Failed to import settings:', error);
      toast({
        title: 'Import Failed',
        description: error.message || 'Failed to parse settings file.',
        variant: 'destructive',
      });
    } finally {
      setImportLoading(false);
      // Reset file input
      event.target.value = '';
    }
  };

  const customerOptions = useMemo(() => (
    customers.map(customer => ({ value: customer.id, label: customer.name || `Customer ${customer.id}` }))
  ), [customers]);

  if (systemLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoadingSpinner className="h-10 w-10" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-3xl font-bold">Settings</h1>
            <p className="text-muted-foreground mt-1">Configure system, API, and customer-specific settings.</p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Button
              variant="outline"
              onClick={handleExportSettings}
              disabled={exportLoading || systemSaving}
            >
              {exportLoading ? (
                <LoadingSpinner className="mr-2 h-4 w-4" />
              ) : (
                <Download className="h-4 w-4 mr-2" />
              )}
              Export
            </Button>
            <Button
              variant="outline"
              onClick={() => document.getElementById('import-settings-input')?.click()}
              disabled={importLoading || systemSaving}
            >
              {importLoading ? (
                <LoadingSpinner className="mr-2 h-4 w-4" />
              ) : (
                <Upload className="h-4 w-4 mr-2" />
              )}
              Import
            </Button>
            <input
              id="import-settings-input"
              type="file"
              accept=".json"
              className="hidden"
              onChange={handleImportSettings}
            />
            <Button variant="outline" onClick={handleResetSystem} disabled={!systemDirty || systemSaving}>
              <RotateCcw className="h-4 w-4 mr-2" />
              Reset
            </Button>
            <Button onClick={handleSaveSystem} disabled={!systemDirty || systemSaving}>
              {systemSaving ? (
                <>
                  <LoadingSpinner className="mr-2 h-4 w-4" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save Changes
                </>
              )}
            </Button>
          </div>
        </div>

        {systemDirty && (
          <div className="flex items-center gap-2 rounded-md border border-amber-500/50 bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-400">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <span>You have unsaved changes. Click Save to apply them.</span>
          </div>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <SettingsIcon className="h-5 w-5" />
            General Settings
          </CardTitle>
          <CardDescription>Basic application configuration settings</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="appName">Application Name</Label>
              <Input
                id="appName"
                value={systemSettings.general.appName}
                onChange={(e) => updateSystemSetting('general', 'appName', e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="maxFileSize">Max File Size (MB)</Label>
              <Input
                id="maxFileSize"
                type="number"
                value={systemSettings.general.maxFileSize}
                onChange={(e) => updateSystemSetting('general', 'maxFileSize', e.target.value)}
                min={1}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="defaultPageSize">Default Page Size</Label>
              <Input
                id="defaultPageSize"
                type="number"
                value={systemSettings.general.defaultPageSize}
                onChange={(e) => updateSystemSetting('general', 'defaultPageSize', e.target.value)}
                min={5}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="sessionTimeout">Session Timeout (minutes)</Label>
              <Input
                id="sessionTimeout"
                type="number"
                value={systemSettings.general.sessionTimeout}
                onChange={(e) => updateSystemSetting('general', 'sessionTimeout', e.target.value)}
                min={5}
              />
            </div>
          </div>
          <div className="flex items-center justify-between border rounded-md p-4">
            <div>
              <p className="font-medium">Enable Notifications</p>
              <p className="text-sm text-muted-foreground">Toggle email notifications for system alerts.</p>
            </div>
            <Switch
              id="enableNotifications"
              checked={systemSettings.general.enableNotifications}
              onCheckedChange={(checked) => updateSystemSetting('general', 'enableNotifications', checked)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="notificationEmail">Notification Email</Label>
            <Input
              id="notificationEmail"
              type="email"
              value={systemSettings.general.notificationEmail}
              onChange={(e) => updateSystemSetting('general', 'notificationEmail', e.target.value)}
              placeholder="admin@company.com"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe2 className="h-5 w-5" />
            API Connection Settings
          </CardTitle>
          <CardDescription>Configure how the frontend communicates with the backend API.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="space-y-2">
            <Label htmlFor="apiBaseUrl">API Base URL</Label>
            <Input
              id="apiBaseUrl"
              value={systemSettings.api.apiBaseUrl}
              onChange={(e) => updateSystemSetting('api', 'apiBaseUrl', e.target.value)}
              placeholder="http://localhost:5000/api"
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="healthEndpoint">Health Endpoint</Label>
              <Input
                id="healthEndpoint"
                value={systemSettings.api.healthEndpoint}
                onChange={(e) => updateSystemSetting('api', 'healthEndpoint', e.target.value)}
                placeholder="/health"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="pollInterval">Status Poll Interval (seconds)</Label>
              <Input
                id="pollInterval"
                type="number"
                min={15}
                value={systemSettings.api.pollInterval}
                onChange={(e) => updateSystemSetting('api', 'pollInterval', e.target.value)}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="apiKey">API Key / Token</Label>
              <Input
                id="apiKey"
                type="password"
                value={systemSettings.api.apiKey}
                onChange={(e) => updateSystemSetting('api', 'apiKey', e.target.value)}
                placeholder="Bearer token or API key"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="authHeader">Auth Header Name</Label>
              <Input
                id="authHeader"
                value={systemSettings.api.authHeader}
                onChange={(e) => updateSystemSetting('api', 'authHeader', e.target.value)}
                placeholder="Authorization"
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="timeout">Request Timeout (seconds)</Label>
              <Input
                id="timeout"
                type="number"
                min={5}
                value={systemSettings.api.timeout}
                onChange={(e) => updateSystemSetting('api', 'timeout', e.target.value)}
              />
            </div>
            <div className="flex items-center justify-between border rounded-md p-4">
              <div>
                <p className="font-medium">Verify SSL Certificates</p>
                <p className="text-sm text-muted-foreground">Disable only for local development.</p>
              </div>
              <Switch
                id="verifySsl"
                checked={systemSettings.api.verifySsl}
                onCheckedChange={(checked) => updateSystemSetting('api', 'verifySsl', checked)}
              />
            </div>
          </div>
          <div className="flex flex-col gap-3">
            {apiTestResult?.status === 'pending' && (
              <div className="flex items-center gap-2 rounded-md border border-blue-500/50 bg-blue-500/10 p-3 text-sm text-blue-700 dark:text-blue-400">
                <LoadingSpinner className="h-4 w-4 flex-shrink-0" />
                <span>Testing connection...</span>
              </div>
            )}
            {apiTestResult?.status === 'success' && (
              <div className="flex items-center gap-2 rounded-md border border-green-500/50 bg-green-500/10 p-3 text-sm text-green-700 dark:text-green-400">
                <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
                <span>{apiTestResult.message}</span>
              </div>
            )}
            {apiTestResult?.status === 'error' && (
              <div className="flex items-center gap-2 rounded-md border border-red-500/50 bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">
                <XCircle className="h-4 w-4 flex-shrink-0" />
                <div className="flex-1">
                  <div className="font-medium">Connection failed</div>
                  <div className="text-xs mt-1 opacity-90">{apiTestResult.message}</div>
                </div>
              </div>
            )}
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Wifi className="h-4 w-4" />
                <span>Ensure the API is reachable from this frontend.</span>
              </div>
              <Button
                type="button"
                variant="outline"
                onClick={handleTestConnection}
                disabled={apiTestResult?.status === 'pending'}
              >
                <Plug className="h-4 w-4 mr-2" />
                Test Connection
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Rule-to-Alarm Defaults
          </CardTitle>
          <CardDescription>Configuration applied when generating alarms from rules.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="maxAlarmNameLength">Max Alarm Name Length</Label>
              <Input
                id="maxAlarmNameLength"
                type="number"
                value={systemSettings.customer_defaults.maxAlarmNameLength}
                onChange={(e) => updateSystemSetting('customer_defaults', 'maxAlarmNameLength', e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="defaultSeverity">Default Severity</Label>
              <Input
                id="defaultSeverity"
                type="number"
                min={0}
                max={100}
                value={systemSettings.customer_defaults.defaultSeverity}
                onChange={(e) => updateSystemSetting('customer_defaults', 'defaultSeverity', e.target.value)}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="defaultConditionType">Default Condition Type</Label>
              <Input
                id="defaultConditionType"
                type="number"
                value={systemSettings.customer_defaults.defaultConditionType}
                onChange={(e) => updateSystemSetting('customer_defaults', 'defaultConditionType', e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="matchField">Match Field</Label>
              <Input
                id="matchField"
                value={systemSettings.customer_defaults.matchField}
                onChange={(e) => updateSystemSetting('customer_defaults', 'matchField', e.target.value)}
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="summaryTemplate">Summary Template</Label>
            <Textarea
              id="summaryTemplate"
              rows={8}
              value={systemSettings.customer_defaults.summaryTemplate}
              onChange={(e) => updateSystemSetting('customer_defaults', 'summaryTemplate', e.target.value)}
              className="font-mono text-sm"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Alarm Template Settings
          </CardTitle>
          <CardDescription>Default assignment and metadata for generated alarms.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="defaultAssignee">Default Assignee ID</Label>
              <Input
                id="defaultAssignee"
                value={systemSettings.customer_defaults.defaultAssignee}
                onChange={(e) => updateSystemSetting('customer_defaults', 'defaultAssignee', e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="defaultEscAssignee">Default Escalation Assignee ID</Label>
              <Input
                id="defaultEscAssignee"
                value={systemSettings.customer_defaults.defaultEscAssignee}
                onChange={(e) => updateSystemSetting('customer_defaults', 'defaultEscAssignee', e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="defaultMinVersion">Default Minimum Version</Label>
              <Input
                id="defaultMinVersion"
                value={systemSettings.customer_defaults.defaultMinVersion}
                onChange={(e) => updateSystemSetting('customer_defaults', 'defaultMinVersion', e.target.value)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Database & Backup Settings
          </CardTitle>
          <CardDescription>Database maintenance and backup configuration</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="flex items-center justify-between border rounded-md p-4">
            <div>
              <p className="font-medium">Enable Automatic Backups</p>
              <p className="text-sm text-muted-foreground">Recommended for production environments.</p>
            </div>
            <Switch
              id="backupEnabled"
              checked={systemSettings.general.backupEnabled}
              onCheckedChange={(checked) => updateSystemSetting('general', 'backupEnabled', checked)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="backupFrequency">Backup Frequency</Label>
            <select
              id="backupFrequency"
              value={systemSettings.general.backupFrequency}
              onChange={(e) => updateSystemSetting('general', 'backupFrequency', e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              <option value="hourly">Hourly</option>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Security Settings
          </CardTitle>
          <CardDescription>Audit logging and access management.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="flex items-center justify-between border rounded-md p-4">
            <div>
              <p className="font-medium">Enable Audit Logging</p>
              <p className="text-sm text-muted-foreground">Captures important system events.</p>
            </div>
            <Switch
              id="enableAuditLog"
              checked={systemSettings.general.enableAuditLog}
              onCheckedChange={(checked) => updateSystemSetting('general', 'enableAuditLog', checked)}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
          <CardDescription>Customize the look and feel of the application.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="theme-select">Theme Preference</Label>
            <select
              id="theme-select"
              value={systemSettings.general.theme}
              onChange={(e) => updateSystemSetting('general', 'theme', e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              <option value="system">System</option>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Customer Overrides
          </CardTitle>
          <CardDescription>Configure customer-specific overrides for alarm generation defaults.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="customer-select">Customer</Label>
            <select
              id="customer-select"
              value={activeCustomerId || ''}
              onChange={(e) => setActiveCustomerId(e.target.value ? Number.parseInt(e.target.value, 10) : null)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              <option value="">Select a customer</option>
              {customerOptions.map(option => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>

          {activeCustomerId ? (
            customerLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <LoadingSpinner className="h-4 w-4" />
                Loading customer settings...
              </div>
            ) : (
              <div className="space-y-4">
                <div className="rounded-md border bg-muted/30 p-4 text-sm text-muted-foreground">
                  <div className="flex items-center gap-2 font-medium text-foreground">
                    <Info className="h-4 w-4" />
                    Effective values are defaults merged with overrides.
                  </div>
                  <p className="mt-2">Clear a field to revert to the default value shown in the placeholder.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="customer-defaultSeverity">Default Severity</Label>
                    <Input
                      id="customer-defaultSeverity"
                      type="number"
                      value={customerSettings.overrides.defaultSeverity ?? ''}
                      onChange={(e) => handleCustomerOverrideChange('defaultSeverity', e.target.value)}
                      placeholder={`Default: ${customerSettings.defaults.defaultSeverity}`}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="customer-defaultConditionType">Default Condition Type</Label>
                    <Input
                      id="customer-defaultConditionType"
                      type="number"
                      value={customerSettings.overrides.defaultConditionType ?? ''}
                      onChange={(e) => handleCustomerOverrideChange('defaultConditionType', e.target.value)}
                      placeholder={`Default: ${customerSettings.defaults.defaultConditionType}`}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="customer-matchField">Match Field</Label>
                    <Input
                      id="customer-matchField"
                      value={customerSettings.overrides.matchField ?? ''}
                      onChange={(e) => handleCustomerOverrideChange('matchField', e.target.value)}
                      placeholder={`Default: ${customerSettings.defaults.matchField}`}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="customer-maxAlarmNameLength">Max Alarm Name Length</Label>
                    <Input
                      id="customer-maxAlarmNameLength"
                      type="number"
                      value={customerSettings.overrides.maxAlarmNameLength ?? ''}
                      onChange={(e) => handleCustomerOverrideChange('maxAlarmNameLength', e.target.value)}
                      placeholder={`Default: ${customerSettings.defaults.maxAlarmNameLength}`}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="customer-defaultAssignee">Default Assignee ID</Label>
                    <Input
                      id="customer-defaultAssignee"
                      value={customerSettings.overrides.defaultAssignee ?? ''}
                      onChange={(e) => handleCustomerOverrideChange('defaultAssignee', e.target.value)}
                      placeholder={`Default: ${customerSettings.defaults.defaultAssignee}`}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="customer-defaultEscAssignee">Default Escalation ID</Label>
                    <Input
                      id="customer-defaultEscAssignee"
                      value={customerSettings.overrides.defaultEscAssignee ?? ''}
                      onChange={(e) => handleCustomerOverrideChange('defaultEscAssignee', e.target.value)}
                      placeholder={`Default: ${customerSettings.defaults.defaultEscAssignee}`}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="customer-defaultMinVersion">Default Min Version</Label>
                    <Input
                      id="customer-defaultMinVersion"
                      value={customerSettings.overrides.defaultMinVersion ?? ''}
                      onChange={(e) => handleCustomerOverrideChange('defaultMinVersion', e.target.value)}
                      placeholder={`Default: ${customerSettings.defaults.defaultMinVersion}`}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="customer-summaryTemplate">Summary Template Override</Label>
                  <Textarea
                    id="customer-summaryTemplate"
                    rows={6}
                    value={customerSettings.overrides.summaryTemplate ?? ''}
                    onChange={(e) => handleCustomerOverrideChange('summaryTemplate', e.target.value)}
                    placeholder="Leave blank to use system default"
                    className="font-mono text-sm"
                  />
                </div>

                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-sm text-muted-foreground">
                    Effective Severity: <span className="font-medium text-foreground">{customerSettings.effective.defaultSeverity}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button type="button" variant="outline" onClick={() => handleResetCustomerOverrides()} disabled={!customerDirty}>
                      Reset Overrides
                    </Button>
                    <Button type="button" onClick={handleSaveCustomerOverrides} disabled={!customerDirty}>
                      Save Customer Overrides
                    </Button>
                  </div>
                </div>
              </div>
            )
          ) : (
            <div className="rounded-md border bg-muted/30 p-4 text-sm text-muted-foreground">
              Select a customer to manage overrides.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
