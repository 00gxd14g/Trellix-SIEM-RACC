/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { customerAPI } from '@/lib/api';

const AppContext = createContext();

export function AppProvider({ children }) {
  const [customers, setCustomers] = useState([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCustomers = async () => {
      try {
        const response = await customerAPI.getAll();
        setCustomers(response.data.customers || []);
      } catch (error) {
        console.error('Failed to fetch customers:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchCustomers();
  }, []);

  const selectedCustomer = useMemo(() => {
    if (!selectedCustomerId) return null;
    return customers.find(c => c.id === selectedCustomerId);
  }, [selectedCustomerId, customers]);

  const value = {
    customers,
    loading,
    selectedCustomerId,
    setSelectedCustomerId,
    selectedCustomer,
    refreshCustomers: async () => {
      const response = await customerAPI.getAll();
      setCustomers(response.data.customers || []);
    },
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
}
