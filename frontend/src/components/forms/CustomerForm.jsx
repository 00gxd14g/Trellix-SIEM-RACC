import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { customerAPI } from '@/lib/api';

export default function CustomerForm({ customer, onClose, onSuccess }) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    contact_email: '',
    contact_phone: '',
  });
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    if (customer) {
      setFormData(customer);
    }
  }, [customer]);

  const handleChange = (e) => {
    const { id, value } = e.target;
    setFormData((prevData) => ({
      ...prevData,
      [id]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (customer) {
        await customerAPI.update(customer.id, formData);
        toast({ title: "Success", description: "Customer updated successfully." });
      } else {
        await customerAPI.create(formData);
        toast({ title: "Success", description: "Customer created successfully." });
      }
      onSuccess();
    } catch (error) {
      console.error('Failed to save customer:', error);
      toast({ title: "Error", description: `Failed to save customer: ${error.response?.data?.error || error.message}`, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>{customer ? 'Edit Customer' : 'Create New Customer'}</CardTitle>
        <CardDescription>{customer ? `Update details for ${customer.name}` : 'Fill in the details to create a new customer'}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Customer Name</Label>
            <Input id="name" value={formData.name} onChange={handleChange} required />
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea id="description" value={formData.description} onChange={handleChange} rows="3" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="contact_email">Contact Email</Label>
            <Input id="contact_email" type="email" value={formData.contact_email} onChange={handleChange} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="contact_phone">Contact Phone</Label>
            <Input id="contact_phone" value={formData.contact_phone} onChange={handleChange} />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? (customer ? 'Updating...' : 'Creating...') : (customer ? 'Update Customer' : 'Create Customer')}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
