import { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { LoadingSpinner } from '@/components/ui/loading';
import { useToast } from '@/hooks/use-toast';
import { useAppContext } from '@/context/AppContext';
import RuleEditForm from '@/components/forms/RuleEditForm';
import RuleCreateForm from '@/components/forms/RuleCreateForm';
import RuleDetailModal from '@/components/modals/RuleDetailModal';
import BulkEditModal from '@/components/modals/BulkEditModal';
import { InlineEdit } from '@/components/ui/inline-edit';
import { getSeverityMeta } from '@/utils/severity';
import { ruleAPI, customerAPI } from '@/lib/api';
import {
  FileText,
  Search,
  Zap,
  Edit,
  Plus,
  Trash2,
  Filter,
  Download,
  Upload,
  ChevronDown,
  ChevronUp,
  SortAsc,
  SortDesc,
  CheckSquare,
  Square,
  X,
  Eye,
  FileDown,
  AlertCircle,
  Info
} from 'lucide-react';

export default function Rules() {
  const { selectedCustomerId } = useAppContext();
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [selectedRules, setSelectedRules] = useState(new Set());
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState({ min: 0, max: 100 });
  const [page, setPage] = useState(1);
  const [showEditForm, setShowEditForm] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showBulkEditModal, setShowBulkEditModal] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [selectedRule, setSelectedRule] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  const [sortField, setSortField] = useState('name');
  const [sortDirection, setSortDirection] = useState('asc');
  const [statusFilter, setStatusFilter] = useState('all');
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef(null);
  const { toast } = useToast();
  const PAGE_SIZE = 25;

  const fetchRules = useCallback(async () => {
    try {
      setLoading(true);
      const response = await ruleAPI.getAll(selectedCustomerId, {
        search: searchTerm,
        severity_min: severityFilter.min,
        severity_max: severityFilter.max,
      });
      setRules(response.data.rules || []);
    } catch (error) {
      console.error('Failed to fetch rules:', error);
      toast({ title: "Error", description: "Failed to fetch rules", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }, [selectedCustomerId, searchTerm, severityFilter.min, severityFilter.max, toast]);

  useEffect(() => {
    if (selectedCustomerId) {
      fetchRules();
    }
  }, [selectedCustomerId, fetchRules]);

  useEffect(() => {
    setPage(1);
  }, [selectedCustomerId, searchTerm, severityFilter.min, severityFilter.max, statusFilter]);

  const handleSearch = (e) => {
    setSearchTerm(e.target.value);
  };

  const handleSeverityFilterChange = (type, value) => {
    setSeverityFilter((prev) => ({ ...prev, [type]: value }));
  };

  const handleRuleSelection = (ruleId) => {
    setSelectedRules((prevSelected) => {
      const newSelected = new Set(prevSelected);
      if (newSelected.has(ruleId)) {
        newSelected.delete(ruleId);
      } else {
        newSelected.add(ruleId);
      }
      return newSelected;
    });
  };

  const handleSelectAll = () => {
    if (selectedRules.size === filteredRules.length) {
      setSelectedRules(new Set());
    } else {
      setSelectedRules(new Set(filteredRules.map(rule => rule.id)));
    }
  };

  const handleGenerateAlarms = async () => {
    if (selectedRules.size === 0) {
      toast({ title: "Info", description: "Please select at least one rule to generate alarms.", variant: "info" });
      return;
    }
    setGenerating(true);
    try {
      const response = await ruleAPI.generateAlarms(selectedCustomerId, Array.from(selectedRules));
      toast({ title: "Success", description: `${response.data.generated_count} alarms generated successfully.`, variant: "success" });
      setSelectedRules(new Set());
      fetchRules();
    } catch (error) {
      console.error('Failed to generate alarms:', error);
      toast({ title: "Error", description: "Failed to generate alarms", variant: "destructive" });
    } finally {
      setGenerating(false);
    }
  };

  const handleViewDetails = (rule) => {
    setSelectedRule(rule);
    setShowDetailModal(true);
  };

  const handleUpdateRuleXML = async (newXML) => {
    if (!selectedRule) return;
    try {
      await ruleAPI.update(selectedCustomerId, selectedRule.id, { xml_content: newXML });
      toast({ title: "Success", description: "Rule XML updated successfully." });
      fetchRules();
      setSelectedRule(prev => ({ ...prev, xml_content: newXML }));
    } catch (error) {
      console.error('Failed to update rule XML:', error);
      toast({ title: "Error", description: "Failed to update rule XML", variant: "destructive" });
    }
  };

  const handleEditRule = (rule) => {
    setEditingRule(rule);
    setShowEditForm(true);
  };

  const handleDeleteRule = async (ruleId) => {
    if (!window.confirm("Are you sure you want to delete this rule?")) {
      return;
    }
    try {
      await ruleAPI.delete(selectedCustomerId, ruleId);
      toast({ title: "Success", description: "Rule deleted successfully." });
      fetchRules();
    } catch (error) {
      console.error('Failed to delete rule:', error);
      toast({ title: "Error", description: "Failed to delete rule", variant: "destructive" });
    }
  };

  const handleInlineEdit = async (ruleId, field, value) => {
    try {
      await ruleAPI.update(selectedCustomerId, ruleId, { [field]: value });
      toast({ title: "Success", description: "Rule updated successfully." });
      fetchRules();
    } catch (error) {
      console.error('Failed to update rule:', error);
      toast({ title: "Error", description: "Failed to update rule", variant: "destructive" });
      throw error;
    }
  };

  const handleBulkEdit = async (ruleIds, updates) => {
    const updatePromises = ruleIds.map(ruleId =>
      ruleAPI.update(selectedCustomerId, ruleId, updates)
    );
    await Promise.all(updatePromises);
    fetchRules();
  };

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const handleExport = async () => {
    if (!selectedCustomerId) {
      toast({ title: "Select Customer", description: "Choose a customer before exporting rules.", variant: "destructive" });
      return;
    }

    try {
      const response = await ruleAPI.exportAll(selectedCustomerId, Array.from(selectedRules));
      const contentType = response.headers['content-type'] || 'application/xml';
      const blob = response.data instanceof Blob ? response.data : new Blob([response.data], { type: contentType });
      const disposition = response.headers['content-disposition'];
      let filename = `rules-${new Date().toISOString().split('T')[0]}.xml`;

      if (disposition) {
        const match = disposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
        if (match) {
          filename = decodeURIComponent(match[1] || match[2]);
        }
      }

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast({ title: "Export Complete", description: "Rule XML downloaded successfully." });
    } catch (error) {
      console.error('Failed to export rules:', error);
      toast({ title: "Export Failed", description: error.response?.data?.error || error.message, variant: "destructive" });
    }
  };

  const handleImportClick = () => {
    if (!selectedCustomerId) {
      toast({ title: "Select Customer", description: "Choose a customer before importing rules.", variant: "destructive" });
      return;
    }
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0];
    if (!file || !selectedCustomerId) {
      event.target.value = '';
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('file_type', 'rule');

    setImporting(true);
    try {
      const response = await customerAPI.uploadFile(selectedCustomerId, formData);
      const validation = response.data?.validation;

      if (validation?.success) {
        const importedCount = validation.items_processed ?? 0;
        toast({
          title: "Import Complete",
          description: `${file.name} processed successfully (${importedCount} rules imported).`
        });
        if (validation.warnings?.length) {
          toast({
            title: "Import Warnings",
            description: validation.warnings.slice(0, 3).join('; '),
            variant: "default"
          });
        }
        fetchRules();
      } else if (validation) {
        const errorSummary = validation.errors?.slice(0, 3).join('; ') || 'Validation failed.';
        toast({
          title: "Validation Failed",
          description: `${file.name} imported with errors: ${errorSummary}${validation.errors?.length > 3 ? '...' : ''}`,
          variant: "destructive"
        });
        fetchRules();
      } else if (response.data?.success) {
        toast({ title: "Import Complete", description: `${file.name} processed successfully.` });
        fetchRules();
      } else {
        toast({ title: "Import Failed", description: response.data?.error || 'Unable to process rule file.', variant: "destructive" });
      }
    } catch (error) {
      console.error('Failed to import rules:', error);
      toast({ title: "Import Failed", description: error.response?.data?.error || error.message, variant: "destructive" });
    } finally {
      setImporting(false);
      event.target.value = '';
    }
  };

  const filteredRules = useMemo(() => {
    let filtered = rules.filter((rule) => {
      const normalizedSearch = searchTerm.toLowerCase();
      const matchesSearch =
        rule.name.toLowerCase().includes(normalizedSearch) ||
        rule.rule_id.toLowerCase().includes(normalizedSearch) ||
        (rule.description && rule.description.toLowerCase().includes(normalizedSearch)) ||
        (rule.sig_id && rule.sig_id.toLowerCase().includes(normalizedSearch)) ||
        (rule.windows_event_ids && rule.windows_event_ids.some(eventId => String(eventId).toLowerCase().includes(normalizedSearch)));

      const matchesSeverity =
        rule.severity >= severityFilter.min && rule.severity <= severityFilter.max;

      const matchesStatus = statusFilter === 'all' ||
        (statusFilter === 'active' && rule.sig_id) ||
        (statusFilter === 'inactive' && !rule.sig_id);

      return matchesSearch && matchesSeverity && matchesStatus;
    });

    // Sort the filtered results
    filtered.sort((a, b) => {
      let aValue = a[sortField];
      let bValue = b[sortField];

      if (sortField === 'severity') {
        aValue = parseInt(aValue) || 0;
        bValue = parseInt(bValue) || 0;
      }

      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [rules, searchTerm, severityFilter, statusFilter, sortField, sortDirection]);

  const totalPages = Math.max(1, Math.ceil(filteredRules.length / PAGE_SIZE));
  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  const currentPage = Math.min(page, totalPages);
  const paginatedRules = useMemo(() => (
    filteredRules.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)
  ), [filteredRules, currentPage]);

  const renderSeverityIndicator = (value) => {
    const { variant, label, barClass, value: normalized } = getSeverityMeta(value);

    return (
      <div className="flex items-center gap-2">
        <Badge variant={variant} className="text-xs font-medium px-2 py-1 min-w-[72px] justify-center">
          {label}
        </Badge>
        <div className="h-2 w-16 bg-muted rounded-full overflow-hidden">
          <div
            className={`h-full transition-all ${barClass}`}
            style={{ width: `${normalized}%` }}
            aria-hidden="true"
          />
        </div>
      </div>
    );
  };

  const handleDownloadRule = async (ruleId, filename) => {
    try {
      const response = await ruleAPI.getById(selectedCustomerId, ruleId);
      const xmlContent = response.data.xml_content || response.data.rule?.xml_content;
      if (!xmlContent) {
        toast({ title: "Unavailable", description: "Rule XML is not available for download.", variant: "destructive" });
        return;
      }

      const blob = new Blob([xmlContent], { type: 'application/xml' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename || `rule_${ruleId}.xml`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast({ title: "Rule Downloaded", description: "Rule XML downloaded successfully." });
    } catch (error) {
      console.error('Failed to download rule XML:', error);
      toast({ title: "Download Failed", description: error.response?.data?.error || error.message, variant: "destructive" });
    }
  };

  if (!selectedCustomerId) {
    return (
      <div className="flex items-center justify-center h-full">
        <Card className="max-w-md">
          <CardContent className="pt-6">
            <div className="text-center space-y-4">
              <AlertCircle className="h-12 w-12 mx-auto text-yellow-500" />
              <p className="text-lg font-medium">No Customer Selected</p>
              <p className="text-sm text-muted-foreground">
                Please select a customer from the sidebar to view rules.
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

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Rules Management</h1>
          <p className="text-muted-foreground mt-1">
            Manage and analyze security rules for your SIEM system
          </p>
          {rules.length > 0 && (
            <div className="flex items-center gap-4 mt-2 text-sm">
              <span className="text-muted-foreground">
                Total: <span className="font-semibold text-foreground">{rules.length}</span> rules
              </span>
              <span className="text-muted-foreground">
                With SigID: <span className="font-semibold text-foreground">{rules.filter(r => r.sig_id).length}</span>
              </span>
              <span className="text-muted-foreground">
                Filtered: <span className="font-semibold text-foreground">{filteredRules.length}</span>
              </span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
          <Button variant="outline" size="sm" onClick={handleImportClick} disabled={importing}>
            <Upload className="h-4 w-4 mr-2" />
            {importing ? 'Importing...' : 'Import'}
          </Button>
          <Button onClick={() => setShowCreateForm(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Rule
          </Button>
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept=".xml"
        className="hidden"
        onChange={handleFileChange}
      />

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Rule List</CardTitle>
              <CardDescription>
                {filteredRules.length} of {rules.length} rules shown
              </CardDescription>
            </div>
            <Badge variant="outline" className="text-sm">
              {selectedRules.size} selected
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          {/* Search and Filter Bar */}
          <div className="space-y-4 mb-6">
            <div className="flex items-center gap-4">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by name, ID, SigID, or description..."
                  value={searchTerm}
                  onChange={handleSearch}
                  className="pl-10"
                />
                {searchTerm && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setSearchTerm('')}
                    className="absolute right-2 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
              <Button
                variant="outline"
                onClick={() => setShowFilters(!showFilters)}
                className="gap-2"
              >
                <Filter className="h-4 w-4" />
                Filters
                {showFilters ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
              <Button
                onClick={handleGenerateAlarms}
                disabled={selectedRules.size === 0 || generating}
                className="gap-2"
              >
                <Zap className="h-4 w-4" />
                {generating ? 'Generating...' : `Generate Alarms (${selectedRules.size})`}
              </Button>
              <Button
                variant="outline"
                onClick={() => setShowBulkEditModal(true)}
                disabled={selectedRules.size === 0}
                className="gap-2"
              >
                <Edit className="h-4 w-4" />
                Bulk Edit ({selectedRules.size})
              </Button>
            </div>

            {/* Advanced Filters */}
            {showFilters && (
              <Card className="p-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Severity Range</label>
                    <div className="flex items-center gap-2">
                      <Input
                        type="number"
                        placeholder="Min"
                        value={severityFilter.min}
                        onChange={(e) => handleSeverityFilterChange('min', parseInt(e.target.value) || 0)}
                        className="w-24"
                        min="0"
                        max="100"
                      />
                      <span className="text-sm text-muted-foreground">to</span>
                      <Input
                        type="number"
                        placeholder="Max"
                        value={severityFilter.max}
                        onChange={(e) => handleSeverityFilterChange('max', parseInt(e.target.value) || 100)}
                        className="w-24"
                        min="0"
                        max="100"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Status</label>
                    <div className="flex gap-2">
                      <Button
                        variant={statusFilter === 'all' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setStatusFilter('all')}
                      >
                        All
                      </Button>
                      <Button
                        variant={statusFilter === 'active' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setStatusFilter('active')}
                      >
                        Active
                      </Button>
                      <Button
                        variant={statusFilter === 'inactive' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setStatusFilter('inactive')}
                      >
                        Inactive
                      </Button>
                    </div>
                  </div>
                  <div className="flex items-end gap-2">
                    <Button onClick={fetchRules} variant="default" size="sm" className="gap-2">
                      <Search className="h-4 w-4" />
                      Apply Filters
                    </Button>
                    <Button
                      onClick={() => {
                        setSearchTerm('');
                        setSeverityFilter({ min: 0, max: 100 });
                        setStatusFilter('all');
                        fetchRules();
                      }}
                      variant="outline"
                      size="sm"
                    >
                      Reset
                    </Button>
                  </div>
                </div>
              </Card>
            )}
          </div>

          {/* Rules Table */}
          {filteredRules.length === 0 ? (
            <div className="text-center py-12">
              <Info className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-lg font-medium">No rules found</p>
              <p className="text-sm text-muted-foreground mt-1">
                Try adjusting your search or filters
              </p>
            </div>
          ) : (
            <div className="rounded-lg border">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-border text-xs">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="w-8 px-2 py-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0"
                          onClick={handleSelectAll}
                        >
                          {selectedRules.size === filteredRules.length && filteredRules.length > 0 ? (
                            <CheckSquare className="h-3 w-3" />
                          ) : (
                            <Square className="h-3 w-3" />
                          )}
                        </Button>
                      </th>
                      <th className="px-3 py-2 text-left">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleSort('name')}
                          className="font-medium text-xs uppercase tracking-wider hover:bg-transparent h-auto p-0"
                        >
                          Name
                          {sortField === 'name' && (
                            sortDirection === 'asc' ? <SortAsc className="ml-1 h-3 w-3" /> : <SortDesc className="ml-1 h-3 w-3" />
                          )}
                        </Button>
                      </th>
                      <th className="px-3 py-2 text-left">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleSort('rule_id')}
                          className="font-medium text-xs uppercase tracking-wider hover:bg-transparent h-auto p-0"
                        >
                          Rule ID
                          {sortField === 'rule_id' && (
                            sortDirection === 'asc' ? <SortAsc className="ml-1 h-3 w-3" /> : <SortDesc className="ml-1 h-3 w-3" />
                          )}
                        </Button>
                      </th>
                      <th className="px-3 py-2 text-left">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleSort('severity')}
                          className="font-medium text-xs uppercase tracking-wider hover:bg-transparent h-auto p-0"
                        >
                          Severity
                          {sortField === 'severity' && (
                            sortDirection === 'asc' ? <SortAsc className="ml-1 h-3 w-3" /> : <SortDesc className="ml-1 h-3 w-3" />
                          )}
                        </Button>
                      </th>
                      <th className="px-3 py-2 text-left font-medium text-muted-foreground uppercase tracking-wider">
                        Sig ID
                      </th>
                      <th className="px-3 py-2 text-left font-medium text-muted-foreground uppercase tracking-wider">
                        Win Event IDs
                      </th>
                      <th className="px-3 py-2 text-left font-medium text-muted-foreground uppercase tracking-wider">
                        Type
                      </th>
                      <th className="px-3 py-2 text-left font-medium text-muted-foreground uppercase tracking-wider">
                        Description
                      </th>
                      <th className="px-3 py-2 text-right font-medium text-muted-foreground uppercase tracking-wider w-24">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-background divide-y divide-border">
                    {paginatedRules.map((rule) => (
                      <tr key={rule.id} className="hover:bg-muted/50 transition-colors">
                        <td className="px-2 py-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0"
                            onClick={() => handleRuleSelection(rule.id)}
                          >
                            {selectedRules.has(rule.id) ? (
                              <CheckSquare className="h-3 w-3" />
                            ) : (
                              <Square className="h-3 w-3" />
                            )}
                          </Button>
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex items-center gap-2">
                            <FileText className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                            <InlineEdit
                              value={rule.name}
                              onSave={(value) => handleInlineEdit(rule.id, 'name', value)}
                              placeholder="Rule name"
                              className="flex-1 font-medium"
                            />
                          </div>
                        </td>
                        <td className="px-3 py-2">
                          <InlineEdit
                            value={rule.rule_id}
                            onSave={(value) => handleInlineEdit(rule.id, 'rule_id', value)}
                            placeholder="Rule ID"
                            className="font-mono text-xs"
                          />
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex items-center gap-2">
                            <InlineEdit
                              value={rule.severity}
                              onSave={(value) => handleInlineEdit(rule.id, 'severity', parseInt(value))}
                              type="number"
                              placeholder="Sev"
                              className="w-12 text-xs"
                            />
                            {renderSeverityIndicator(rule.severity)}
                          </div>
                        </td>
                        <td className="px-3 py-2">
                          <InlineEdit
                            value={rule.sig_id}
                            onSave={(value) => handleInlineEdit(rule.id, 'sig_id', value)}
                            placeholder="Sig ID"
                            className="font-mono text-xs"
                          />
                        </td>
                        <td className="px-3 py-2">
                          {rule.windows_event_ids?.length ? (
                            <div className="flex flex-wrap gap-1 max-w-[120px]">
                              {rule.windows_event_ids.slice(0, 3).map((eventId) => (
                                <Badge key={eventId} variant="outline" className="text-[10px] px-1 py-0 font-mono h-4">
                                  {eventId}
                                </Badge>
                              ))}
                              {rule.windows_event_ids.length > 3 && (
                                <span className="text-[10px] text-muted-foreground">+{rule.windows_event_ids.length - 3}</span>
                              )}
                            </div>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          <InlineEdit
                            value={rule.rule_type}
                            onSave={(value) => handleInlineEdit(rule.id, 'rule_type', parseInt(value) || null)}
                            type="number"
                            placeholder="Type"
                            className="w-12 text-xs"
                          />
                        </td>
                        <td className="px-3 py-2">
                          <InlineEdit
                            value={rule.description}
                            onSave={(value) => handleInlineEdit(rule.id, 'description', value)}
                            placeholder="Description"
                            multiline
                            className="max-w-[200px] truncate block"
                          />
                        </td>
                        <td className="px-3 py-2 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleViewDetails(rule)}
                              className="h-6 w-6 p-0"
                            >
                              <Eye className="h-3 w-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleEditRule(rule)}
                              className="h-6 w-6 p-0"
                            >
                              <Edit className="h-3 w-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDownloadRule(rule.id, `${rule.name}.xml`)}
                              className="h-6 w-6 p-0"
                            >
                              <FileDown className="h-3 w-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteRule(rule.id)}
                              className="h-6 w-6 p-0 hover:text-destructive"
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          {filteredRules.length > 0 && (
            <div className="flex items-center justify-between border-t pt-4 mt-4 text-sm text-muted-foreground">
              <span>
                Showing {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, filteredRules.length)} of {filteredRules.length}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={currentPage === 1}
                  onClick={() => setPage(prev => Math.max(1, prev - 1))}
                >
                  Prev
                </Button>
                <span>Page {currentPage} / {totalPages}</span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={currentPage === totalPages}
                  onClick={() => setPage(prev => Math.min(totalPages, prev + 1))}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {showDetailModal && (
        <RuleDetailModal
          rule={selectedRule}
          onClose={() => setShowDetailModal(false)}
          onSave={handleUpdateRuleXML}
        />
      )}

      {showEditForm && (
        <RuleEditForm
          rule={editingRule}
          onClose={() => setShowEditForm(false)}
          onSuccess={() => {
            setShowEditForm(false);
            fetchRules();
          }}
        />
      )}

      {showCreateForm && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <RuleCreateForm
              customerId={selectedCustomerId}
              onClose={() => setShowCreateForm(false)}
              onSuccess={() => {
                setShowCreateForm(false);
                fetchRules();
              }}
            />
          </div>
        </div>
      )}

      {showBulkEditModal && (
        <BulkEditModal
          type="rule"
          selectedItems={selectedRules}
          onClose={() => setShowBulkEditModal(false)}
          onSave={handleBulkEdit}
        />
      )}
    </div>
  );
}
