import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import { api } from '@/lib/api';
import { useAppContext } from '@/context/AppContext';
import { Loader2, RefreshCw, Filter, X, BarChart3, Users, FileText, Bell, Settings, Shield, Code, Download, Eye, FileDown, Bug, Server } from 'lucide-react';
import { format } from 'date-fns';

// Category icons mapping
const categoryIcons = {
  customer: Users,
  rule: FileText,
  alarm: Bell,
  file: FileText,
  analysis: BarChart3,
  settings: Settings,
  security: Shield,
  frontend: Code,
  debug: Bug,
  system: Server,
  other: FileText,
};

// Category colors
const categoryColors = {
  customer: 'bg-blue-500',
  rule: 'bg-purple-500',
  alarm: 'bg-red-500',
  file: 'bg-green-500',
  analysis: 'bg-yellow-500',
  settings: 'bg-gray-500',
  security: 'bg-orange-500',
  frontend: 'bg-cyan-500',
  debug: 'bg-indigo-500',
  system: 'bg-slate-600',
  other: 'bg-slate-500',
};

export default function Logs() {
  const { selectedCustomerId } = useAppContext();
  const { toast } = useToast();
  const [logs, setLogs] = useState([]);
  const [categories, setCategories] = useState({});
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [activeTab, setActiveTab] = useState('all');
  const [selectedLog, setSelectedLog] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [filters, setFilters] = useState({
    action: 'all',
    resource_type: 'all',
    status: 'all',
    category: '',
    customer_id: selectedCustomerId ? selectedCustomerId.toString() : ''
  });

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        page,
        per_page: 20
      };

      if (filters.action !== 'all') params.action = filters.action;
      if (filters.resource_type !== 'all') params.resource_type = filters.resource_type;
      if (filters.status !== 'all') params.status = filters.status;
      if (filters.category) params.category = filters.category;
      if (selectedCustomerId) params.customer_id = selectedCustomerId;

      const response = await api.get('/logs/audit', { params });
      if (response.data.success) {
        setLogs(response.data.logs);
        setTotalPages(Math.ceil(response.data.total / 20));
      }
    } catch (error) {
      toast({
        title: "Error fetching logs",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  }, [page, filters, selectedCustomerId, toast]);

  const fetchCategories = useCallback(async () => {
    try {
      const params = {};
      if (selectedCustomerId) params.customer_id = selectedCustomerId;

      const response = await api.get('/logs/categories', { params });
      if (response.data.success) {
        setCategories(response.data.categories);
      }
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  }, [selectedCustomerId]);

  const fetchStats = useCallback(async () => {
    try {
      const params = {};
      if (selectedCustomerId) params.customer_id = selectedCustomerId;

      const response = await api.get('/logs/stats', { params });
      if (response.data.success) {
        setStats(response.data.stats);
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  }, [selectedCustomerId]);

  const handleExportLogs = async () => {
    setExporting(true);
    try {
      const params = {};
      if (filters.action !== 'all') params.action = filters.action;
      if (filters.resource_type !== 'all') params.resource_type = filters.resource_type;
      if (filters.status !== 'all') params.status = filters.status;
      if (filters.category) params.category = filters.category;
      if (selectedCustomerId) params.customer_id = selectedCustomerId;

      // Fetch all logs (without pagination)
      params.per_page = 10000;

      const response = await api.get('/logs/audit', { params });
      if (response.data.success) {
        const logsToExport = response.data.logs;

        // Create CSV content
        const headers = ['Timestamp', 'Action', 'Resource Type', 'Resource ID', 'Status', 'User ID', 'IP Address', 'Method', 'Endpoint', 'Error Message'];
        const csvRows = [headers.join(',')];

        logsToExport.forEach(log => {
          const row = [
            log.timestamp || '',
            log.action || '',
            log.resource_type || '',
            log.resource_id || '',
            log.status || '',
            log.user_id || '',
            log.ip_address || '',
            log.method || '',
            log.endpoint || '',
            (log.error_message || '').replace(/,/g, ';')
          ];
          csvRows.push(row.join(','));
        });

        const csvContent = csvRows.join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `logs_${new Date().toISOString()}.csv`;
        link.click();
        URL.revokeObjectURL(url);

        toast({
          title: "Export Successful",
          description: `Exported ${logsToExport.length} logs to CSV`,
        });
      }
    } catch (error) {
      toast({
        title: "Export Failed",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setExporting(false);
    }
  };

  const handleExportJSON = async () => {
    setExporting(true);
    try {
      const params = {};
      if (filters.action !== 'all') params.action = filters.action;
      if (filters.resource_type !== 'all') params.resource_type = filters.resource_type;
      if (filters.status !== 'all') params.status = filters.status;
      if (filters.category) params.category = filters.category;
      if (selectedCustomerId) params.customer_id = selectedCustomerId;

      params.per_page = 10000;

      const response = await api.get('/logs/audit', { params });
      if (response.data.success) {
        const logsToExport = response.data.logs;

        const blob = new Blob([JSON.stringify(logsToExport, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `logs_${new Date().toISOString()}.json`;
        link.click();
        URL.revokeObjectURL(url);

        toast({
          title: "Export Successful",
          description: `Exported ${logsToExport.length} logs to JSON`,
        });
      }
    } catch (error) {
      toast({
        title: "Export Failed",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setExporting(false);
    }
  };

  const handleViewDetails = (log) => {
    setSelectedLog(log);
    setShowDetailsModal(true);
  };

  useEffect(() => {
    if (selectedCustomerId) {
      setFilters(prev => ({ ...prev, customer_id: selectedCustomerId.toString() }));
    }
  }, [selectedCustomerId]);

  useEffect(() => {
    fetchLogs();
    fetchCategories();
    fetchStats();
  }, [fetchLogs, fetchCategories, fetchStats]);

  const handleApplyFilters = () => {
    setPage(1);
    fetchLogs();
  };

  const clearFilters = () => {
    setFilters({
      action: 'all',
      resource_type: 'all',
      status: 'all',
      category: '',
      customer_id: selectedCustomerId ? selectedCustomerId.toString() : ''
    });
    setPage(1);
    setTimeout(fetchLogs, 0);
  };

  const handleCategoryClick = (category) => {
    setFilters(prev => ({ ...prev, category }));
    setActiveTab(category);
    setPage(1);
  };

  const renderLogTable = (logsToShow) => (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Timestamp</TableHead>
          <TableHead>Action</TableHead>
          <TableHead>Resource</TableHead>
          <TableHead>User / IP</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Details</TableHead>
          <TableHead>Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {loading ? (
          <TableRow>
            <TableCell colSpan={7} className="h-24 text-center">
              <Loader2 className="h-6 w-6 animate-spin mx-auto text-muted-foreground" />
            </TableCell>
          </TableRow>
        ) : logsToShow.length === 0 ? (
          <TableRow>
            <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
              No logs found matching criteria
            </TableCell>
          </TableRow>
        ) : (
          logsToShow.map((log) => (
            <TableRow key={log.id}>
              <TableCell className="font-mono text-xs">
                {log.timestamp ? format(new Date(log.timestamp), 'yyyy-MM-dd HH:mm:ss') : '-'}
              </TableCell>
              <TableCell>
                <Badge variant="outline" className="font-mono text-xs">{log.action}</Badge>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  {categoryIcons[log.resource_type] &&
                    React.createElement(categoryIcons[log.resource_type], {
                      className: "h-4 w-4"
                    })
                  }
                  <div className="flex flex-col">
                    <span className="font-medium capitalize text-sm">{log.resource_type}</span>
                    <span className="text-xs text-muted-foreground">ID: {log.resource_id || '-'}</span>
                  </div>
                </div>
              </TableCell>
              <TableCell>
                <div className="flex flex-col text-xs">
                  <span>{log.user_id || 'System'}</span>
                  <span className="text-muted-foreground">{log.ip_address}</span>
                </div>
              </TableCell>
              <TableCell>
                <Badge
                  variant={log.status === 'success' ? 'default' : 'destructive'}
                  className={log.status === 'success' ? 'bg-green-600 hover:bg-green-700' : ''}
                >
                  {log.status}
                </Badge>
              </TableCell>
              <TableCell className="max-w-[200px] truncate text-xs text-muted-foreground">
                {log.error_message || (log.metadata ? JSON.stringify(log.metadata).substring(0, 50) + '...' : '-')}
              </TableCell>
              <TableCell>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleViewDetails(log)}
                >
                  <Eye className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Audit Logs</h1>
          <p className="text-muted-foreground mt-2">
            View system activity and audit records
            {selectedCustomerId && ` for customer ID ${selectedCustomerId}`}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleExportLogs} disabled={exporting}>
            {exporting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <FileDown className="h-4 w-4 mr-2" />}
            Export CSV
          </Button>
          <Button variant="outline" onClick={handleExportJSON} disabled={exporting}>
            {exporting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Download className="h-4 w-4 mr-2" />}
            Export JSON
          </Button>
          <Button variant="outline" onClick={() => { fetchLogs(); fetchCategories(); fetchStats(); }}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="cursor-pointer hover:bg-muted/50 transition-colors" onClick={clearFilters}>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">{stats.total}</div>
              <p className="text-xs text-muted-foreground">Total Logs</p>
            </CardContent>
          </Card>
          <Card className="cursor-pointer hover:bg-muted/50 transition-colors" onClick={() => setFilters(prev => ({ ...prev, status: 'success' }))}>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-green-600">
                {stats.by_status?.success || 0}
              </div>
              <p className="text-xs text-muted-foreground">Successful</p>
            </CardContent>
          </Card>
          <Card className="cursor-pointer hover:bg-muted/50 transition-colors" onClick={() => setFilters(prev => ({ ...prev, status: 'failure' }))}>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-red-600">
                {(stats.by_status?.failure || 0) + (stats.by_status?.error || 0)}
              </div>
              <p className="text-xs text-muted-foreground">Errors</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">
                {Object.keys(stats.by_resource_type || {}).length}
              </div>
              <p className="text-xs text-muted-foreground">Categories</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Category Pills */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Categories</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            <Button
              variant={activeTab === 'all' ? 'default' : 'outline'}
              size="sm"
              onClick={() => {
                setActiveTab('all');
                setFilters(prev => ({ ...prev, category: '' }));
                setPage(1);
              }}
            >
              All Logs
              {stats && <Badge variant="secondary" className="ml-2">{stats.total}</Badge>}
            </Button>
            {Object.entries(categories).map(([category, count]) => {
              const Icon = categoryIcons[category] || FileText;
              const colorClass = categoryColors[category] || 'bg-gray-500';
              return (
                <Button
                  key={category}
                  variant={activeTab === category ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => handleCategoryClick(category)}
                  className={activeTab === category ? colorClass : ''}
                >
                  <Icon className="h-4 w-4 mr-2" />
                  {category.charAt(0).toUpperCase() + category.slice(1)}
                  <Badge variant="secondary" className="ml-2">{count}</Badge>
                </Button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Filters */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Filters</CardTitle>
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" onClick={clearFilters}>
                <X className="h-4 w-4 mr-2" />
                Clear
              </Button>
              <Button size="sm" onClick={handleApplyFilters}>
                <Filter className="h-4 w-4 mr-2" />
                Apply
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Status</label>
              <Select
                value={filters.status}
                onValueChange={(v) => setFilters(prev => ({ ...prev, status: v }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All Statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="success">Success</SelectItem>
                  <SelectItem value="failure">Failure</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Resource Type</label>
              <Select
                value={filters.resource_type}
                onValueChange={(v) => setFilters(prev => ({ ...prev, resource_type: v }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All Resources" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Resources</SelectItem>
                  <SelectItem value="customer">Customer</SelectItem>
                  <SelectItem value="rule">Rule</SelectItem>
                  <SelectItem value="alarm">Alarm</SelectItem>
                  <SelectItem value="file">File</SelectItem>
                  <SelectItem value="analysis">Analysis</SelectItem>
                  <SelectItem value="settings">Settings</SelectItem>
                  <SelectItem value="security">Security</SelectItem>
                  <SelectItem value="frontend">Frontend</SelectItem>
                  <SelectItem value="debug">Debug</SelectItem>
                  <SelectItem value="system">System</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Action</label>
              <Input
                placeholder="Filter by action..."
                value={filters.action === 'all' ? '' : filters.action}
                onChange={(e) => setFilters(prev => ({ ...prev, action: e.target.value || 'all' }))}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Logs Table */}
      <div className="border rounded-md">
        {renderLogTable(logs)}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Page {page} of {totalPages}
        </p>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
          >
            Next
          </Button>
        </div>
      </div>

      {/* Details Modal */}
      <Dialog open={showDetailsModal} onOpenChange={setShowDetailsModal}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Log Details</DialogTitle>
            <DialogDescription>
              Detailed information about this log entry
            </DialogDescription>
          </DialogHeader>

          {selectedLog && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-semibold text-muted-foreground">Timestamp</label>
                  <p className="font-mono text-sm">
                    {selectedLog.timestamp ? format(new Date(selectedLog.timestamp), 'yyyy-MM-dd HH:mm:ss.SSS') : '-'}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-semibold text-muted-foreground">Status</label>
                  <div className="mt-1">
                    <Badge
                      variant={selectedLog.status === 'success' ? 'default' : 'destructive'}
                      className={selectedLog.status === 'success' ? 'bg-green-600' : ''}
                    >
                      {selectedLog.status}
                    </Badge>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-semibold text-muted-foreground">Action</label>
                  <p className="font-mono text-sm">{selectedLog.action || '-'}</p>
                </div>
                <div>
                  <label className="text-sm font-semibold text-muted-foreground">Resource Type</label>
                  <p className="text-sm capitalize">{selectedLog.resource_type || '-'}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-semibold text-muted-foreground">Resource ID</label>
                  <p className="font-mono text-sm">{selectedLog.resource_id || '-'}</p>
                </div>
                <div>
                  <label className="text-sm font-semibold text-muted-foreground">Customer ID</label>
                  <p className="font-mono text-sm">{selectedLog.customer_id || '-'}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-semibold text-muted-foreground">User ID</label>
                  <p className="text-sm">{selectedLog.user_id || 'System'}</p>
                </div>
                <div>
                  <label className="text-sm font-semibold text-muted-foreground">IP Address</label>
                  <p className="font-mono text-sm">{selectedLog.ip_address || '-'}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-semibold text-muted-foreground">Method</label>
                  <Badge variant="outline" className="mt-1">{selectedLog.method || '-'}</Badge>
                </div>
                <div>
                  <label className="text-sm font-semibold text-muted-foreground">Status Code</label>
                  <Badge variant="outline" className="mt-1">{selectedLog.status_code || '-'}</Badge>
                </div>
              </div>

              <div>
                <label className="text-sm font-semibold text-muted-foreground">Endpoint</label>
                <p className="font-mono text-sm bg-muted p-2 rounded mt-1">{selectedLog.endpoint || '-'}</p>
              </div>

              <div>
                <label className="text-sm font-semibold text-muted-foreground">User Agent</label>
                <p className="text-xs bg-muted p-2 rounded mt-1 break-all">{selectedLog.user_agent || '-'}</p>
              </div>

              {selectedLog.error_message && (
                <div>
                  <label className={`text-sm font-semibold ${['failure', 'error'].includes(selectedLog.status) ? 'text-red-600' : 'text-muted-foreground'}`}>
                    {['failure', 'error'].includes(selectedLog.status) ? 'Error Message' : 'Message'}
                  </label>
                  <p className={`text-sm p-3 rounded mt-1 ${['failure', 'error'].includes(selectedLog.status)
                    ? 'bg-red-50 border border-red-200 text-red-800'
                    : 'bg-muted font-mono'
                    }`}>
                    {selectedLog.error_message}
                  </p>
                </div>
              )}

              {/* Request Details */}
              {selectedLog.metadata?.request && (
                <div>
                  <label className="text-sm font-semibold text-muted-foreground">Request Details</label>
                  <pre className="text-xs bg-muted p-3 rounded mt-1 overflow-x-auto">
                    {typeof selectedLog.metadata.request === 'string'
                      ? selectedLog.metadata.request
                      : JSON.stringify(selectedLog.metadata.request, null, 2)}
                  </pre>
                </div>
              )}

              {/* Response Details */}
              {selectedLog.metadata?.response && (
                <div>
                  <label className="text-sm font-semibold text-muted-foreground">Response Details</label>
                  <pre className="text-xs bg-muted p-3 rounded mt-1 overflow-x-auto">
                    {typeof selectedLog.metadata.response === 'string'
                      ? selectedLog.metadata.response
                      : JSON.stringify(selectedLog.metadata.response, null, 2)}
                  </pre>
                </div>
              )}

              {selectedLog.metadata && Object.keys(selectedLog.metadata).length > 0 && (
                <div>
                  <label className="text-sm font-semibold text-muted-foreground">Metadata</label>
                  <pre className="text-xs bg-muted p-3 rounded mt-1 overflow-x-auto">
                    {JSON.stringify(selectedLog.metadata, null, 2)}
                  </pre>
                </div>
              )}

              {selectedLog.changes && Object.keys(selectedLog.changes).length > 0 && (
                <div>
                  <label className="text-sm font-semibold text-muted-foreground">Changes</label>
                  <pre className="text-xs bg-muted p-3 rounded mt-1 overflow-x-auto">
                    {JSON.stringify(selectedLog.changes, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
