import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { alarmAPI } from '@/lib/api';

export default function AlarmCreateForm({ customerId, onClose, onSuccess }) {
  const [formData, setFormData] = useState({
    name: '',
    severity: 50,
    match_value: '',
    min_version: '11.6.14',
    match_field: 'DSIDSigID',
    condition_type: 14,
    assignee_id: 655372,
    esc_assignee_id: 90118,
    note: '',
  });
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const handleChange = (e) => {
    const { id, value } = e.target;
    setFormData((prevData) => ({
      ...prevData,
      [id]: id === 'severity' || id === 'condition_type' || id === 'assignee_id' || id === 'esc_assignee_id' ? parseInt(value) : value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await alarmAPI.create(customerId, formData);
      toast({ title: "Success", description: "Alarm created successfully." });
      onSuccess();
    } catch (error) {
      console.error('Failed to create alarm:', error);
      toast({ title: "Error", description: `Failed to create alarm: ${error.response?.data?.error || error.message}`, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>Create New Alarm</CardTitle>
        <CardDescription>Fill in the details to create a new alarm for customer ID: {customerId}</CardDescription>
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
            <Button type="button" variant="outline" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'Creating...' : 'Create Alarm'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
