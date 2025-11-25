import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { alarmAPI } from '@/lib/api';
import { X } from 'lucide-react';

const mapAlarmToForm = (alarm) => ({
  name: alarm?.name || '',
  severity: alarm?.severity ?? 50,
  match_value: alarm?.match_value || '',
  min_version: alarm?.min_version || '',
  match_field: alarm?.match_field || '',
  condition_type: alarm?.condition_type ?? '',
  assignee_id: alarm?.assignee_id ?? '',
  esc_assignee_id: alarm?.esc_assignee_id ?? '',
  note: alarm?.note || '',
});

export default function AlarmEditForm({ alarm, onClose, onSuccess }) {
  const [formData, setFormData] = useState(() => mapAlarmToForm(alarm));
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    setFormData(mapAlarmToForm(alarm));
  }, [alarm]);

  const handleChange = (e) => {
    const { id, value } = e.target;
    const numericFields = new Set(['severity', 'condition_type', 'assignee_id', 'esc_assignee_id']);
    const nextValue = numericFields.has(id)
      ? value === ''
        ? ''
        : Number.parseInt(value, 10)
      : value;

    setFormData((prevData) => ({
      ...prevData,
      [id]: nextValue,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await alarmAPI.update(alarm.customer_id, alarm.id, formData);
      toast({ title: "Success", description: "Alarm updated successfully." });
      onSuccess();
    } catch (error) {
      console.error('Failed to update alarm:', error);
      toast({ title: "Error", description: `Failed to update alarm: ${error.response?.data?.error || error.message}`, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const handleOverlayClose = useCallback(() => {
    if (!loading) {
      onClose();
    }
  }, [loading, onClose]);

  useEffect(() => {
    const listener = (event) => {
      if (event.key === 'Escape') {
        handleOverlayClose();
      }
    };
    document.addEventListener('keydown', listener);
    return () => document.removeEventListener('keydown', listener);
  }, [handleOverlayClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
      role="dialog"
      aria-modal="true"
      onClick={handleOverlayClose}
    >
      <div
        className="relative w-full max-w-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <Card className="shadow-xl border-border/80">
          <CardHeader className="space-y-1 pb-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <CardTitle>Edit Alarm</CardTitle>
                <CardDescription>Update the details for alarm: {alarm.name}</CardDescription>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="shrink-0"
                onClick={handleOverlayClose}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">Alarm Name</Label>
              <Input id="name" value={formData.name} onChange={handleChange} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="severity">Severity</Label>
              <Input id="severity" type="number" value={formData.severity} onChange={handleChange} min="0" max="100" required />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="match_value">Match Value</Label>
            <Input id="match_value" value={formData.match_value} onChange={handleChange} required />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="min_version">Min Version</Label>
              <Input id="min_version" value={formData.min_version} onChange={handleChange} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="match_field">Match Field</Label>
              <Input id="match_field" value={formData.match_field} onChange={handleChange} />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="condition_type">Condition Type</Label>
              <Input id="condition_type" type="number" value={formData.condition_type} onChange={handleChange} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="assignee_id">Assignee ID</Label>
              <Input id="assignee_id" type="number" value={formData.assignee_id} onChange={handleChange} />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="esc_assignee_id">Escalation Assignee ID</Label>
            <Input id="esc_assignee_id" type="number" value={formData.esc_assignee_id} onChange={handleChange} />
          </div>

          <div className="space-y-2">
            <Label htmlFor="note">Note</Label>
            <Textarea id="note" value={formData.note} onChange={handleChange} rows="3" />
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={handleOverlayClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'Updating...' : 'Update Alarm'}
            </Button>
          </div>
        </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
