import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { ruleAPI } from '@/lib/api';

export default function RuleCreateForm({ customerId, onClose, onSuccess }) {
  const [formData, setFormData] = useState({
    name: '',
    rule_id: '',
    sig_id: '',
    severity: 50,
    description: '',
    rule_type: 0, // Default to 0 for now, adjust as needed
    revision: '1',
    protocol: '',
    source_port: '',
    dest_port: '',
    classification_id: '',
    classification_text: '',
    reference: ''
  });
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const handleChange = (e) => {
    const { id, value } = e.target;
    setFormData((prevData) => ({
      ...prevData,
      [id]: id === 'severity' || id === 'rule_type' ? parseInt(value) : value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await ruleAPI.create(customerId, formData);
      toast({ title: "Success", description: "Rule created successfully." });
      onSuccess();
    } catch (error) {
      console.error('Failed to create rule:', error);
      toast({ title: "Error", description: `Failed to create rule: ${error.response?.data?.error || error.message}`, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>Create New Rule</CardTitle>
        <CardDescription>Fill in the details to create a new rule for customer ID: {customerId}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">Rule Name</Label>
              <Input id="name" value={formData.name} onChange={handleChange} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="rule_id">Rule ID</Label>
              <Input id="rule_id" value={formData.rule_id} onChange={handleChange} required />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="sig_id">Sig ID</Label>
              <Input id="sig_id" value={formData.sig_id} onChange={handleChange} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="severity">Severity</Label>
              <Input id="severity" type="number" value={formData.severity} onChange={handleChange} min="0" max="100" required />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea id="description" value={formData.description} onChange={handleChange} rows="3" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="rule_type">Rule Type</Label>
              <Input id="rule_type" type="number" value={formData.rule_type} onChange={handleChange} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="revision">Revision</Label>
              <Input id="revision" value={formData.revision} onChange={handleChange} />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="protocol">Protocol</Label>
              <Input id="protocol" value={formData.protocol} onChange={handleChange} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="source_port">Source Port</Label>
              <Input id="source_port" value={formData.source_port} onChange={handleChange} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="dest_port">Destination Port</Label>
              <Input id="dest_port" value={formData.dest_port} onChange={handleChange} />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="classification_id">Classification ID</Label>
              <Input id="classification_id" value={formData.classification_id} onChange={handleChange} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="classification_text">Classification Text</Label>
              <Input id="classification_text" value={formData.classification_text} onChange={handleChange} />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="reference">Reference</Label>
            <Input id="reference" value={formData.reference} onChange={handleChange} />
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'Creating...' : 'Create Rule'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
