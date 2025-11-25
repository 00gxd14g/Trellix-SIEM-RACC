import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { Checkbox } from '@/components/ui/checkbox';
import { X, Save, AlertTriangle } from 'lucide-react';

export default function BulkEditModal({ 
  type = 'rule', // 'rule' or 'alarm'
  selectedItems, 
  onClose, 
  onSave 
}) {
  const [formData, setFormData] = useState({});
  const [enabledFields, setEnabledFields] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const ruleFields = [
    { key: 'name', label: 'Rule Name', type: 'text' },
    { key: 'rule_id', label: 'Rule ID', type: 'text' },
    { key: 'description', label: 'Description', type: 'textarea' },
    { key: 'severity', label: 'Severity', type: 'number', min: 0, max: 100 },
    { key: 'sig_id', label: 'Signature ID', type: 'text' },
    { key: 'rule_type', label: 'Rule Type', type: 'number' },
    { key: 'revision', label: 'Revision', type: 'number' },
    { key: 'origin', label: 'Origin', type: 'number' },
    { key: 'action', label: 'Action', type: 'number' }
  ];

  const alarmFields = [
    { key: 'name', label: 'Alarm Name', type: 'text' },
    { key: 'min_version', label: 'Min Version', type: 'text' },
    { key: 'severity', label: 'Severity', type: 'number', min: 0, max: 100 },
    { key: 'match_field', label: 'Match Field', type: 'text' },
    { key: 'match_value', label: 'Match Value', type: 'text' },
    { key: 'condition_type', label: 'Condition Type', type: 'number' },
    { key: 'assignee_id', label: 'Assignee ID', type: 'number' },
    { key: 'esc_assignee_id', label: 'Escalation Assignee ID', type: 'number' },
    { key: 'note', label: 'Note', type: 'textarea' }
  ];

  const fields = type === 'rule' ? ruleFields : alarmFields;

  const handleFieldToggle = (fieldKey, checked) => {
    const newEnabledFields = new Set(enabledFields);
    if (checked) {
      newEnabledFields.add(fieldKey);
    } else {
      newEnabledFields.delete(fieldKey);
      const newFormData = { ...formData };
      delete newFormData[fieldKey];
      setFormData(newFormData);
    }
    setEnabledFields(newEnabledFields);
  };

  const handleFieldChange = (fieldKey, value) => {
    setFormData(prev => ({ ...prev, [fieldKey]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (enabledFields.size === 0) {
      toast({ 
        title: "Warning", 
        description: "Please select at least one field to update.", 
        variant: "warning" 
      });
      return;
    }

    const updates = {};
    enabledFields.forEach(field => {
      updates[field] = formData[field];
    });

    setLoading(true);
    try {
      await onSave(Array.from(selectedItems), updates);
      toast({ 
        title: "Success", 
        description: `${selectedItems.size} ${type}(s) updated successfully.` 
      });
      onClose();
    } catch (error) {
      console.error('Bulk edit error:', error);
      toast({ 
        title: "Error", 
        description: `Failed to update ${type}s`, 
        variant: "destructive" 
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-auto">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div>
            <CardTitle className="text-xl font-bold">
              Bulk Edit {type === 'rule' ? 'Rules' : 'Alarms'}
            </CardTitle>
            <CardDescription>
              Update {selectedItems.size} selected {type}(s) at once
            </CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        
        <CardContent>
          <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-yellow-600" />
              <span className="text-sm font-medium text-yellow-800">Warning</span>
            </div>
            <p className="text-sm text-yellow-700 mt-1">
              This will update all selected {type}s. Only checked fields will be modified.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 gap-4">
              {fields.map((field) => (
                <div key={field.key} className="flex items-start gap-3 p-3 border rounded-md">
                  <Checkbox
                    id={`enable-${field.key}`}
                    checked={enabledFields.has(field.key)}
                    onCheckedChange={(checked) => handleFieldToggle(field.key, checked)}
                    className="mt-2"
                  />
                  <div className="flex-1 space-y-2">
                    <Label 
                      htmlFor={`field-${field.key}`}
                      className={enabledFields.has(field.key) ? 'text-foreground' : 'text-muted-foreground'}
                    >
                      {field.label}
                    </Label>
                    {field.type === 'textarea' ? (
                      <Textarea
                        id={`field-${field.key}`}
                        value={formData[field.key] || ''}
                        onChange={(e) => handleFieldChange(field.key, e.target.value)}
                        disabled={!enabledFields.has(field.key)}
                        placeholder={`New ${field.label.toLowerCase()}`}
                        rows={3}
                      />
                    ) : (
                      <Input
                        id={`field-${field.key}`}
                        type={field.type}
                        value={formData[field.key] || ''}
                        onChange={(e) => handleFieldChange(field.key, e.target.value)}
                        disabled={!enabledFields.has(field.key)}
                        placeholder={`New ${field.label.toLowerCase()}`}
                        min={field.min}
                        max={field.max}
                      />
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button type="button" variant="outline" onClick={onClose} disabled={loading}>
                Cancel
              </Button>
              <Button type="submit" disabled={loading || enabledFields.size === 0}>
                <Save className="h-4 w-4 mr-2" />
                {loading ? 'Updating...' : `Update ${selectedItems.size} ${type}(s)`}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
