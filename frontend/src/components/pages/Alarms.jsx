import { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { LoadingSpinner } from '@/components/ui/loading';
import { useToast } from '@/hooks/use-toast';
import { useAppContext } from '@/context/AppContext';
import { alarmAPI, customerAPI } from '@/lib/api';
import AlarmDetailModal from '@/components/modals/AlarmDetailModal';
import AlarmEditForm from '@/components/forms/AlarmEditForm';
import AlarmCreateForm from '@/components/forms/AlarmCreateForm';
import BulkEditModal from '@/components/modals/BulkEditModal';
import { InlineEdit } from '@/components/ui/inline-edit';
import { getSeverityMeta } from '@/utils/severity';
import XMLEditor from '@/components/XMLEditor';
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui';
import {
  AlertTriangle,
  Search,
  Plus,
  Edit,
  Trash2,
  Eye,
  FileDown,
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
  AlertCircle,
  Info,
  Bell,
  BellOff,
  Clock
} from 'lucide-react';

export default function Alarms() {
  const { selectedCustomerId } = useAppContext();
  const [alarms, setAlarms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAlarms, setSelectedAlarms] = useState(new Set());
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState({ min: 0, max: 100 });
  const [page, setPage] = useState(1);
  const [selectedAlarm, setSelectedAlarm] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showBulkEditModal, setShowBulkEditModal] = useState(false);
  const [editingAlarm, setEditingAlarm] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  const [sortField, setSortField] = useState('name');
  const [sortDirection, setSortDirection] = useState('asc');
  const [statusFilter, setStatusFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [importing, setImporting] = useState(false);
  const [showXMLEditor, setShowXMLEditor] = useState(false);
  const [xmlEditorContent, setXmlEditorContent] = useState('');
  const [xmlEditorTitle, setXmlEditorTitle] = useState('Alarm XML Editor');
  const fileInputRef = useRef(null);
  const { toast } = useToast();
  const PAGE_SIZE = 25;

  const fetchAlarms = useCallback(async () => {
    try {
      setLoading(true);
      const response = await alarmAPI.getAll(selectedCustomerId, {
        search: searchTerm,
        severity_min: severityFilter.min,
        severity_max: severityFilter.max,
      });
      setAlarms(response.data.alarms || []);
    } catch (error) {
      console.error('Failed to fetch alarms:', error);
      toast({ title: "Error", description: "Failed to fetch alarms", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }, [selectedCustomerId, searchTerm, severityFilter, toast]);

  useEffect(() => {
    if (selectedCustomerId) {
      fetchAlarms();
    }
  }, [selectedCustomerId, fetchAlarms]);

  useEffect(() => {
    setPage(1);
  }, [selectedCustomerId, searchTerm, severityFilter.min, severityFilter.max, statusFilter, typeFilter]);

  const handleSearch = (e) => {
    setSearchTerm(e.target.value);
  };

  const handleSeverityFilterChange = (type, value) => {
    setSeverityFilter((prev) => ({ ...prev, [type]: value }));
  };

  const handleAlarmSelection = (alarmId) => {
    setSelectedAlarms((prevSelected) => {
      const newSelected = new Set(prevSelected);
      if (newSelected.has(alarmId)) {
        newSelected.delete(alarmId);
      } else {
        newSelected.add(alarmId);
      }
      return newSelected;
    });
  };

  const handleSelectAll = () => {
    if (selectedAlarms.size === filteredAlarms.length) {
      setSelectedAlarms(new Set());
    } else {
      setSelectedAlarms(new Set(filteredAlarms.map(alarm => alarm.id)));
    }
  };

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const handleExport = async (format = 'xml') => {
    if (!selectedCustomerId) {
      toast({ title: "Select Customer", description: "Choose a customer before exporting alarms.", variant: "destructive" });
      return;
    }

    // Check if alarms are selected for HTML/PDF export
    if ((format === 'html' || format === 'pdf') && selectedAlarms.size === 0) {
      toast({ title: "No Selection", description: "Please select at least one alarm to export as HTML/PDF.", variant: "destructive" });
      return;
    }

    try {
      let response;
      let contentType;
      let fileExtension;

      if (format === 'html') {
        response = await alarmAPI.exportHtml(selectedCustomerId, Array.from(selectedAlarms));
        contentType = 'text/html';
        fileExtension = 'html';
      } else if (format === 'pdf') {
        response = await alarmAPI.exportPdf(selectedCustomerId, Array.from(selectedAlarms));
        contentType = 'application/pdf';
        fileExtension = 'pdf';
      } else {
        // XML export (existing functionality)
        response = await alarmAPI.exportAll(selectedCustomerId, Array.from(selectedAlarms));
        contentType = 'application/xml';
        fileExtension = 'xml';
      }

      const blob = response.data instanceof Blob ? response.data : new Blob([response.data], { type: contentType });
      const disposition = response.headers['content-disposition'];
      let filename = `alarms-${new Date().toISOString().split('T')[0]}.${fileExtension}`;

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
      toast({ title: "Export Complete", description: `Alarm ${format.toUpperCase()} downloaded successfully.` });
    } catch (error) {
      console.error('Failed to export alarms:', error);
      if (error.response?.status === 404 && format === 'xml') {
        const dataStr = JSON.stringify(filteredAlarms, null, 2);
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `alarms-${new Date().toISOString().split('T')[0]}.json`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
        toast({ title: "Exported as JSON", description: "No alarm XML found. Exported filtered alarms as JSON instead." });
      } else {
        toast({ title: "Export Failed", description: error.response?.data?.error || error.message, variant: "destructive" });
      }
    }
  };

  const handleBulkDelete = async () => {
    if (selectedAlarms.size === 0) {
      toast({ title: "Info", description: "Please select at least one alarm to delete.", variant: "info" });
      return;
    }

    if (!window.confirm(`Are you sure you want to delete ${selectedAlarms.size} alarm(s)?`)) {
      return;
    }

    try {
      const response = await alarmAPI.bulkDelete(selectedCustomerId, Array.from(selectedAlarms));
      toast({ title: "Success", description: `${response.data.deleted_count} alarm(s) deleted successfully.` });
      setSelectedAlarms(new Set());
      fetchAlarms();
    } catch (error) {
      console.error('Failed to delete alarms:', error);
      toast({ title: "Error", description: error.response?.data?.error || "Failed to delete alarms", variant: "destructive" });
    }
  };

  const handleImportClick = () => {
    if (!selectedCustomerId) {
      toast({ title: "Select Customer", description: "Choose a customer before importing alarms.", variant: "destructive" });
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
    formData.append('file_type', 'alarm');

    setImporting(true);
    try {
      const response = await customerAPI.uploadFile(selectedCustomerId, formData);
      const validation = response.data?.validation;

      if (validation?.success) {
        const importedCount = validation.items_processed ?? 0;
        toast({
          title: "Import Complete",
          description: `${file.name} processed successfully (${importedCount} alarms imported).`
        });
        if (validation.warnings?.length) {
          toast({
            title: "Import Warnings",
            description: validation.warnings.slice(0, 3).join('; '),
            variant: "default"
          });
        }
        fetchAlarms();
      } else if (validation) {
        const errorSummary = validation.errors?.slice(0, 3).join('; ') || 'Validation failed.';
        toast({
          title: "Validation Failed",
          description: `${file.name} imported with errors: ${errorSummary}${validation.errors?.length > 3 ? '...' : ''}`,
          variant: "destructive"
        });
        fetchAlarms();
      } else if (response.data?.success) {
        toast({ title: "Import Complete", description: `${file.name} processed successfully.` });
        fetchAlarms();
      } else {
        toast({ title: "Import Failed", description: response.data?.error || 'Unable to process alarm file.', variant: "destructive" });
      }
    } catch (error) {
      console.error('Failed to import alarms:', error);
      toast({ title: "Import Failed", description: error.response?.data?.error || error.message, variant: "destructive" });
    } finally {
      setImporting(false);
      event.target.value = '';
    }
  };

  const handleViewDetails = async (alarm) => {
    try {
      // Fetch full details including XML content
      const response = await alarmAPI.getById(selectedCustomerId, alarm.id);
      const fullAlarm = response.data.alarm;
      if (response.data.xml_content) {
        fullAlarm.xml_content = response.data.xml_content;
      }
      setSelectedAlarm(fullAlarm);
      setShowDetailModal(true);
    } catch (error) {
      console.error("Failed to fetch alarm details:", error);
      toast({ title: "Error", description: "Failed to fetch full alarm details", variant: "destructive" });
      // Fallback
      setSelectedAlarm(alarm);
      setShowDetailModal(true);
    }
  };

  const handleEditAlarm = (alarm) => {
    setEditingAlarm(alarm);
    setShowEditForm(true);
  };

  const handleInlineEdit = async (alarmId, field, value) => {
    try {
      await alarmAPI.update(selectedCustomerId, alarmId, { [field]: value });
      toast({ title: "Success", description: "Alarm updated successfully." });
      fetchAlarms();
    } catch (error) {
      console.error('Failed to update alarm:', error);
      toast({ title: "Error", description: "Failed to update alarm", variant: "destructive" });
      throw error;
    }
  };

  const handleUpdateAlarmXML = async (newXML) => {
    if (!selectedAlarm) return;
    try {
      await alarmAPI.update(selectedCustomerId, selectedAlarm.id, { xml_content: newXML });
      toast({ title: "Success", description: "Alarm XML updated successfully." });
      fetchAlarms();
      // Update the selected alarm in local state to reflect changes
      setSelectedAlarm(prev => ({ ...prev, xml_content: newXML }));
    } catch (error) {
      console.error('Failed to update alarm XML:', error);
      toast({ title: "Error", description: "Failed to update alarm XML", variant: "destructive" });
    }
  };

  const handleBulkEdit = async (alarmIds, updates) => {
    const updatePromises = alarmIds.map(alarmId =>
      alarmAPI.update(selectedCustomerId, alarmId, updates)
    );
    await Promise.all(updatePromises);
    fetchAlarms();
  };

  const handleDeleteAlarm = async (alarmId) => {
    if (!window.confirm("Are you sure you want to delete this alarm?")) {
      return;
    }
    try {
      await alarmAPI.delete(selectedCustomerId, alarmId);
      toast({ title: "Success", description: "Alarm deleted successfully." });
      fetchAlarms();
    } catch (error) {
      console.error('Failed to delete alarm:', error);
      toast({ title: "Error", description: "Failed to delete alarm", variant: "destructive" });
    }
  };

  const handleDownloadAlarm = async (alarmId, filename) => {
    try {
      const response = await alarmAPI.getById(selectedCustomerId, alarmId);
      const alarmXML = response.data.xml_content || response.data.alarm.xml_content;
      const blob = new Blob([alarmXML], { type: 'application/xml' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename || `alarm_${alarmId}.xml`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast({ title: "Success", description: "Alarm XML downloaded successfully." });
    } catch (error) {
      console.error('Failed to download alarm XML:', error);
      toast({ title: "Error", description: "Failed to download alarm XML", variant: "destructive" });
    }
  };

  const getStatusIcon = (alarm) => {
    // You can customize this based on your alarm data structure
    if (alarm.acknowledged) return <BellOff className="h-4 w-4" />;
    if (alarm.triggered_count > 5) return <AlertTriangle className="h-4 w-4" />;
    return <Bell className="h-4 w-4" />;
  };

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

  const filteredAlarms = useMemo(() => {
    let filtered = alarms.filter((alarm) => {
      const normalizedSearch = searchTerm.toLowerCase();
      const matchesSearch =
        alarm.name.toLowerCase().includes(normalizedSearch) ||
        (alarm.match_value && alarm.match_value.toLowerCase().includes(normalizedSearch)) ||
        (alarm.note && alarm.note.toLowerCase().includes(normalizedSearch)) ||
        (alarm.alarm_name && alarm.alarm_name.toLowerCase().includes(normalizedSearch)) ||
        (alarm.windows_event_ids && alarm.windows_event_ids.some(eventId => String(eventId).toLowerCase().includes(normalizedSearch)));

      const matchesSeverity =
        alarm.severity >= severityFilter.min && alarm.severity <= severityFilter.max;

      const matchesStatus = statusFilter === 'all' ||
        (statusFilter === 'active' && !alarm.acknowledged) ||
        (statusFilter === 'acknowledged' && alarm.acknowledged) ||
        (statusFilter === 'triggered' && alarm.triggered_count > 0);

      const matchesType = typeFilter === 'all' ||
        (typeFilter === 'correlation' && alarm.match_value.includes('correlation')) ||
        (typeFilter === 'direct' && !alarm.match_value.includes('correlation'));

      return matchesSearch && matchesSeverity && matchesStatus && matchesType;
    });

    // Sort the filtered results
    filtered.sort((a, b) => {
      let aValue = a[sortField];
      let bValue = b[sortField];

      if (sortField === 'severity' || sortField === 'triggered_count') {
        aValue = parseInt(aValue) || 0;
        bValue = parseInt(bValue) || 0;
      }

      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [alarms, searchTerm, severityFilter, statusFilter, typeFilter, sortField, sortDirection]);

  const totalPages = Math.max(1, Math.ceil(filteredAlarms.length / PAGE_SIZE));
  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  const currentPage = Math.min(page, totalPages);
  const paginatedAlarms = useMemo(() => (
    filteredAlarms.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)
  ), [filteredAlarms, currentPage]);

  if (!selectedCustomerId) {
    return (
      <div className="flex items-center justify-center h-full">
        <Card className="max-w-md">
          <CardContent className="pt-6">
            <div className="text-center space-y-4">
              <AlertCircle className="h-12 w-12 mx-auto text-yellow-500" />
              <p className="text-lg font-medium">No Customer Selected</p>
              <p className="text-sm text-muted-foreground">
                Please select a customer from the sidebar to view alarms.
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
          <h1 className="text-3xl font-bold">Alarms Management</h1>
          <p className="text-muted-foreground mt-1">
            Monitor and manage security alarms for your system
          </p>
        </div>
        <div className="flex items-center gap-2">
          {selectedAlarms.size > 0 && (
            <Button variant="outline" size="sm" onClick={async () => {
              try {
                // Fetch full alarm data with XML content
                const alarmIds = Array.from(selectedAlarms);
                const alarmPromises = alarmIds.map(id => alarmAPI.getById(selectedCustomerId, id));
                const alarmResponses = await Promise.all(alarmPromises);

                const alarmsWithXML = alarmResponses.map(res => res.data.alarm || res.data);
                const combinedXML = alarmsWithXML
                  .map(a => a.xml_content)
                  .filter(Boolean)
                  .join('\n\n<!-- ======================== -->\n\n');

                if (!combinedXML) {
                  toast({
                    title: "No XML Content",
                    description: "Selected alarms don't have XML content",
                    variant: "destructive"
                  });
                  return;
                }

                setXmlEditorContent(combinedXML);
                setXmlEditorTitle(`Bulk XML Editor (${selectedAlarms.size} alarms)`);
                setShowXMLEditor(true);
              } catch (error) {
                console.error('Failed to fetch alarm XML:', error);
                toast({
                  title: "Error",
                  description: "Failed to fetch alarm XML content",
                  variant: "destructive"
                });
              }
            }}>
              <FileDown className="h-4 w-4 mr-2" />
              View XML ({selectedAlarms.size})
            </Button>
          )}
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" size="sm">
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-48 space-y-2">
              <p className="text-xs text-muted-foreground">Export as:</p>
              {[
                { label: 'XML', value: 'xml' },
                { label: 'HTML', value: 'html' },
                { label: 'PDF', value: 'pdf' },
              ].map(option => (
                <Button
                  key={option.value}
                  variant="ghost"
                  className="w-full justify-start"
                  onClick={() => handleExport(option.value)}
                >
                  {option.label}
                </Button>
              ))}
            </PopoverContent>
          </Popover>
          <Button variant="outline" size="sm" onClick={handleImportClick} disabled={importing}>
            <Upload className="h-4 w-4 mr-2" />
            {importing ? 'Importing...' : 'Import'}
          </Button>
          <Button onClick={() => setShowCreateForm(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Alarm
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
              <CardTitle>Alarm List</CardTitle>
              <CardDescription>
                {filteredAlarms.length} of {alarms.length} alarms shown
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              {selectedAlarms.size > 0 && (
                <>
                  <Badge variant="outline" className="text-sm">
                    {selectedAlarms.size} selected
                  </Badge>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowBulkEditModal(true)}
                    className="gap-2"
                  >
                    <Edit className="h-4 w-4" />
                    Bulk Edit
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleBulkDelete}
                    className="text-destructive hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete Selected
                  </Button>
                </>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Search and Filter Bar */}
          <div className="space-y-4 mb-6">
            <div className="flex items-center gap-4">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by name, match value, or note..."
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
            </div>

            {/* Advanced Filters */}
            {showFilters && (
              <Card className="p-4">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
                        variant={statusFilter === 'acknowledged' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setStatusFilter('acknowledged')}
                      >
                        Ack
                      </Button>
                      <Button
                        variant={statusFilter === 'triggered' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setStatusFilter('triggered')}
                      >
                        Triggered
                      </Button>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Type</label>
                    <div className="flex gap-2">
                      <Button
                        variant={typeFilter === 'all' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setTypeFilter('all')}
                      >
                        All
                      </Button>
                      <Button
                        variant={typeFilter === 'correlation' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setTypeFilter('correlation')}
                      >
                        Correlation
                      </Button>
                      <Button
                        variant={typeFilter === 'direct' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setTypeFilter('direct')}
                      >
                        Direct
                      </Button>
                    </div>
                  </div>
                  <div className="flex items-end gap-2">
                    <Button onClick={fetchAlarms} variant="default" size="sm" className="gap-2">
                      <Search className="h-4 w-4" />
                      Apply Filters
                    </Button>
                    <Button
                      onClick={() => {
                        setSearchTerm('');
                        setSeverityFilter({ min: 0, max: 100 });
                        setStatusFilter('all');
                        setTypeFilter('all');
                        fetchAlarms();
                      }}
                      variant="outline"
                      size="sm"
                      className="gap-2"
                    >
                      Reset
                    </Button>
                  </div>
                </div>
              </Card>
            )}
          </div>

          {/* Alarms Table */}
          {filteredAlarms.length === 0 ? (
            <div className="text-center py-12">
              <Info className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-lg font-medium">No alarms found</p>
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
                      <th className="w-8 px-2 py-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0"
                          onClick={handleSelectAll}
                        >
                          {selectedAlarms.size === filteredAlarms.length && filteredAlarms.length > 0 ? (
                            <CheckSquare className="h-3 w-3" />
                          ) : (
                            <Square className="h-3 w-3" />
                          )}
                        </Button>
                      </th>
                      <th className="px-2 py-1 text-left">
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
                      <th className="px-2 py-1 text-left">
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
                      <th className="px-2 py-1 text-left font-medium text-muted-foreground uppercase tracking-wider">
                        Match Field
                      </th>
                      <th className="px-2 py-1 text-left font-medium text-muted-foreground uppercase tracking-wider">
                        Match Value
                      </th>
                      <th className="px-2 py-1 text-left font-medium text-muted-foreground uppercase tracking-wider">
                        Matched Rule
                      </th>
                      <th className="px-2 py-1 text-left font-medium text-muted-foreground uppercase tracking-wider">
                        Win Event IDs
                      </th>
                      <th className="px-2 py-1 text-left font-medium text-muted-foreground uppercase tracking-wider">
                        Min Ver
                      </th>
                      <th className="px-2 py-1 text-left font-medium text-muted-foreground uppercase tracking-wider">
                        Note
                      </th>
                      <th className="px-2 py-1 text-left">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleSort('triggered_count')}
                          className="font-medium text-xs uppercase tracking-wider hover:bg-transparent h-auto p-0"
                        >
                          Triggered
                          {sortField === 'triggered_count' && (
                            sortDirection === 'asc' ? <SortAsc className="ml-1 h-3 w-3" /> : <SortDesc className="ml-1 h-3 w-3" />
                          )}
                        </Button>
                      </th>
                      <th className="px-2 py-1 text-left font-medium text-muted-foreground uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-2 py-1 text-right font-medium text-muted-foreground uppercase tracking-wider w-24">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-background divide-y divide-border">
                    {paginatedAlarms.map((alarm) => (
                      <tr key={alarm.id} className="hover:bg-muted/50 transition-colors">
                        <td className="px-2 py-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0"
                            onClick={() => handleAlarmSelection(alarm.id)}
                          >
                            {selectedAlarms.has(alarm.id) ? (
                              <CheckSquare className="h-3 w-3" />
                            ) : (
                              <Square className="h-3 w-3" />
                            )}
                          </Button>
                        </td>
                        <td className="px-2 py-1">
                          <div className="flex items-center gap-2">
                            {getStatusIcon(alarm)}
                            <InlineEdit
                              value={alarm.name}
                              onSave={(value) => handleInlineEdit(alarm.id, 'name', value)}
                              placeholder="Alarm name"
                              className="flex-1 font-medium"
                            />
                          </div>
                        </td>
                        <td className="px-2 py-1">
                          <div className="flex items-center gap-2">
                            <InlineEdit
                              value={alarm.severity}
                              onSave={(value) => handleInlineEdit(alarm.id, 'severity', parseInt(value))}
                              type="number"
                              placeholder="Sev"
                              className="w-12 text-xs"
                            />
                            {renderSeverityIndicator(alarm.severity)}
                          </div>
                        </td>
                        <td className="px-2 py-1">
                          <InlineEdit
                            value={alarm.match_field}
                            onSave={(value) => handleInlineEdit(alarm.id, 'match_field', value)}
                            placeholder="Match field"
                            className="text-xs"
                          />
                        </td>
                        <td className="px-2 py-1">
                          <InlineEdit
                            value={alarm.match_value}
                            onSave={(value) => handleInlineEdit(alarm.id, 'match_value', value)}
                            placeholder="Match value"
                            className="text-xs font-mono"
                          />
                        </td>
                        <td className="px-2 py-1">
                          {alarm.matched_rules?.length > 0 ? (
                            <div className="flex flex-col gap-1">
                              {alarm.matched_rules.map(rule => (
                                <span key={rule.id} className="text-xs text-blue-600 truncate max-w-[150px]" title={`${rule.name} (${rule.rule_id})`}>
                                  {rule.name}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="text-muted-foreground text-xs italic">None</span>
                          )}
                        </td>
                        <td className="px-2 py-1">
                          {alarm.windows_event_ids?.length ? (
                            <div className="flex flex-wrap gap-1 max-w-[120px]">
                              {alarm.windows_event_ids.slice(0, 3).map((eventId) => (
                                <Badge key={eventId} variant="outline" className="text-[10px] px-1 py-0 font-mono h-4">
                                  {eventId}
                                </Badge>
                              ))}
                              {alarm.windows_event_ids.length > 3 && (
                                <span className="text-[10px] text-muted-foreground">+{alarm.windows_event_ids.length - 3}</span>
                              )}
                            </div>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </td>
                        <td className="px-2 py-1">
                          <InlineEdit
                            value={alarm.min_version}
                            onSave={(value) => handleInlineEdit(alarm.id, 'min_version', value)}
                            placeholder="Min ver"
                            className="text-xs w-16"
                          />
                        </td>
                        <td className="px-2 py-1">
                          <td className="px-2 py-1">
                            <InlineEdit
                              value={alarm.note}
                              onSave={(value) => handleInlineEdit(alarm.id, 'note', value)}
                              placeholder="Note"
                              className="text-xs max-w-[150px]"
                            />
                          </td>
                        </td>
                        <td className="px-2 py-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-medium">{alarm.triggered_count || 0}</span>
                            {alarm.triggered_count > 0 && (
                              <Clock className="h-3 w-3 text-muted-foreground" />
                            )}
                          </div>
                        </td>
                        <td className="px-2 py-1">
                          {alarm.acknowledged ? (
                            <Badge variant="secondary" className="gap-1 text-[10px] px-1 py-0 h-5">
                              <BellOff className="h-3 w-3" />
                              Ack
                            </Badge>
                          ) : (
                            <Badge variant="default" className="gap-1 text-[10px] px-1 py-0 h-5">
                              <Bell className="h-3 w-3" />
                              Active
                            </Badge>
                          )}
                        </td>
                        <td className="px-2 py-1 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleViewDetails(alarm)}
                              className="h-6 w-6 p-0"
                            >
                              <Eye className="h-3 w-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleEditAlarm(alarm)}
                              className="h-6 w-6 p-0"
                            >
                              <Edit className="h-3 w-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDownloadAlarm(alarm.id, `${alarm.name}.xml`)}
                              className="h-6 w-6 p-0"
                            >
                              <FileDown className="h-3 w-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteAlarm(alarm.id)}
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
          {filteredAlarms.length > 0 && (
            <div className="flex items-center justify-between border-t pt-4 mt-4 text-sm text-muted-foreground">
              <span>
                Showing {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, filteredAlarms.length)} of {filteredAlarms.length}
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
        <AlarmDetailModal
          alarm={selectedAlarm}
          onClose={() => setShowDetailModal(false)}
          onSave={handleUpdateAlarmXML}
        />
      )}

      {showEditForm && (
        <AlarmEditForm
          alarm={editingAlarm}
          onClose={() => setShowEditForm(false)}
          onSuccess={() => {
            setShowEditForm(false);
            fetchAlarms();
          }}
        />
      )}

      {showCreateForm && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <AlarmCreateForm
              customerId={selectedCustomerId}
              onClose={() => setShowCreateForm(false)}
              onSuccess={() => {
                setShowCreateForm(false);
                fetchAlarms();
              }}
            />
          </div>
        </div>
      )}

      {showBulkEditModal && (
        <BulkEditModal
          type="alarm"
          selectedItems={selectedAlarms}
          onClose={() => setShowBulkEditModal(false)}
          onSave={handleBulkEdit}
        />
      )}

      <XMLEditor
        open={showXMLEditor}
        onOpenChange={setShowXMLEditor}
        xmlContent={xmlEditorContent}
        title={xmlEditorTitle}
        readOnly={true}
      />
    </div>
  );
}
