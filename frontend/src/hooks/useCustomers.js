import { useState, useEffect, useCallback } from 'react';
import { customerAPI } from '@/lib/api';

export const useCustomers = () => {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchCustomers = async () => {
    try {
      setLoading(true);
      const response = await customerAPI.getAll();
      setCustomers(response.data.customers || []);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to fetch customers');
    } finally {
      setLoading(false);
    }
  };

  const createCustomer = async (customerData) => {
    try {
      const response = await customerAPI.create(customerData);
      setCustomers(prev => [...prev, response.data.customer]);
      return response.data.customer;
    } catch (err) {
      throw new Error(err.response?.data?.error || 'Failed to create customer');
    }
  };

  const updateCustomer = async (id, customerData) => {
    try {
      const response = await customerAPI.update(id, customerData);
      setCustomers(prev => prev.map(c => c.id === id ? response.data.customer : c));
      return response.data.customer;
    } catch (err) {
      throw new Error(err.response?.data?.error || 'Failed to update customer');
    }
  };

  const deleteCustomer = async (id) => {
    try {
      await customerAPI.delete(id);
      setCustomers(prev => prev.filter(c => c.id !== id));
    } catch (err) {
      throw new Error(err.response?.data?.error || 'Failed to delete customer');
    }
  };

  useEffect(() => {
    fetchCustomers();
  }, []);

  return {
    customers,
    loading,
    error,
    fetchCustomers,
    createCustomer,
    updateCustomer,
    deleteCustomer,
  };
};

export const useCustomer = (customerId) => {
  const [customer, setCustomer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchCustomer = useCallback(async () => {
    if (!customerId) return;
    
    try {
      setLoading(true);
      const response = await customerAPI.getById(customerId);
      setCustomer(response.data.customer);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to fetch customer');
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    fetchCustomer();
  }, [fetchCustomer]);

  return {
    customer,
    loading,
    error,
    fetchCustomer,
  };
};
