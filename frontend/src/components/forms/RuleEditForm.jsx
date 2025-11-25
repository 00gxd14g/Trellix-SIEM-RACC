import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { ruleAPI } from '@/lib/api';
import { X } from 'lucide-react';

export default function RuleEditForm({ rule, onClose, onSuccess }) {
  const [formData, setFormData] = useState({
    name: '',
    rule_id: '',
    sig_id: '',
    description: '',
    severity: 50,
    rule_type: '',
    revision: '',
    protocol: '',
    source_port: '',
    dest_port: '',
    classification_id: '',
    classification_text: '',
    reference: ''
  });
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    if (rule) {
      setFormData({
        name: rule.name || '',
        rule_id: rule.rule_id || '',
        sig_id: rule.sig_id || '',
        description: rule.description || '',
        severity: rule.severity || 50,
        rule_type: rule.rule_type || '',
        revision: rule.revision || '',
        protocol: rule.protocol || '',
        source_port: rule.source_port || '',
        dest_port: rule.dest_port || '',
        classification_id: rule.classification_id || '',
        classification_text: rule.classification_text || '',
        reference: rule.reference || ''
      });
    }
  }, [rule]);

  const handleChange = (e) => {
    const { id, value } = e.target;
    const numericFields = new Set(['severity', 'rule_type']);
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
      await ruleAPI.update(rule.customer_id, rule.id, formData);
      toast({ title: "Success", description: "Rule updated successfully." });
      onSuccess();
    } catch (error) {
      console.error('Failed to update rule:', error);
      toast({ title: "Error", description: `Failed to update rule: ${error.response?.data?.error || error.message}`, variant: "destructive" });
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
                <CardTitle>Edit Rule</CardTitle>
                <CardDescription>Update the details for rule: {rule.name}</CardDescription>
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
            <Button type="button" variant="outline" onClick={handleOverlayClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'Updating...' : 'Update Rule'}
            </Button>
          </div>
        </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
