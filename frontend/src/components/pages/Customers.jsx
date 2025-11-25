import React, { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useToast } from '@/hooks/use-toast';
import { customerAPI } from '@/lib/api';
import { Link } from 'react-router-dom';
import { Plus, Search, Edit, Trash2, Eye, Mail, Phone, Info, X } from 'lucide-react';
import CustomerForm from '@/components/forms/CustomerForm';
import { LoadingSpinner } from '@/components/ui/loading';

export default function Customers() {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState(null);
  const { toast } = useToast();

  const fetchCustomers = useCallback(async () => {
    setLoading(true);
    try {
      const response = await customerAPI.getAll();
      setCustomers(response.data.customers || []);
    } catch (error) {
      console.error('Failed to fetch customers:', error);
      toast({ title: "Error", description: "Failed to fetch customers", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  const handleSearch = (e) => {
    setSearchTerm(e.target.value);
  };

  const handleCreateCustomer = () => {
    setEditingCustomer(null);
    setShowCreateForm(true);
  };

  const handleEditCustomer = (customer) => {
    setEditingCustomer(customer);
    setShowEditForm(true);
  };

  const handleDeleteCustomer = async (customerId) => {
    if (!window.confirm("Are you sure you want to delete this customer and all associated data?")) {
      return;
    }
    try {
      await customerAPI.delete(customerId);
      toast({ title: "Success", description: "Customer deleted successfully." });
      fetchCustomers();
    } catch (error) {
      console.error('Failed to delete customer:', error);
      toast({ title: "Error", description: `Failed to delete customer: ${error.response?.data?.error || error.message}`, variant: "destructive" });
    }
  };

  const filteredCustomers = customers.filter((customer) =>
    customer.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (customer.contact_email && customer.contact_email.toLowerCase().includes(searchTerm.toLowerCase()))
  );

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
          <h1 className="text-3xl font-bold">Customers</h1>
          <p className="text-muted-foreground mt-1">Manage your customer accounts</p>
        </div>
        <Button onClick={handleCreateCustomer}>
          <Plus className="h-4 w-4 mr-2" />
          New Customer
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Customer List</CardTitle>
          <CardDescription>{filteredCustomers.length} customers found</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search customers..."
              value={searchTerm}
              onChange={handleSearch}
              className="pl-10 pr-3"
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

          {filteredCustomers.length === 0 ? (
            <div className="text-center py-12">
              <Info className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-lg font-medium">No customers found</p>
              <p className="text-sm text-muted-foreground mt-1">
                Try adjusting your search or create a new customer.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredCustomers.map((customer) => (
                <Card key={customer.id} className="shadow-sm hover:shadow-md transition-shadow">
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span>{customer.name}</span>
                      <div className="flex space-x-1">
                        <Button variant="ghost" size="sm" onClick={() => handleEditCustomer(customer)} className="h-8 w-8 p-0">
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleDeleteCustomer(customer.id)} className="h-8 w-8 p-0 text-destructive hover:text-destructive">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardTitle>
                    {customer.description && (
                      <CardDescription className="truncate">{customer.description}</CardDescription>
                    )}
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {customer.contact_email && (
                      <div className="flex items-center text-sm text-muted-foreground">
                        <Mail className="h-4 w-4 mr-2" />
                        <span>{customer.contact_email}</span>
                      </div>
                    )}
                    {customer.contact_phone && (
                      <div className="flex items-center text-sm text-muted-foreground">
                        <Phone className="h-4 w-4 mr-2" />
                        <span>{customer.contact_phone}</span>
                      </div>
                    )}
                    <Link to={`/customers/${customer.id}`} className="inline-flex items-center text-sm text-primary hover:underline mt-2">
                      View Details <Eye className="h-4 w-4 ml-1" />
                    </Link>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {(showCreateForm || showEditForm) && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <CustomerForm
            customer={editingCustomer}
            onClose={() => { setShowCreateForm(false); setShowEditForm(false); setEditingCustomer(null); }}
            onSuccess={() => { setShowCreateForm(false); setShowEditForm(false); setEditingCustomer(null); fetchCustomers(); }}
          />
        </div>
      )}
    </div>
  );
}

