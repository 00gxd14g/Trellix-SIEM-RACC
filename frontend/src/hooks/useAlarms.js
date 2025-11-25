import { useState, useEffect, useCallback } from 'react';
import { alarmAPI } from '@/lib/api';

export const useAlarms = (customerId, filters = {}) => {
  const [alarms, setAlarms] = useState([]);
  const [pagination, setPagination] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchAlarms = useCallback(async (params = {}) => {
    if (!customerId) return;
    
    try {
      setLoading(true);
      const response = await alarmAPI.getAll(customerId, { ...filters, ...params });
      setAlarms(response.data.alarms || []);
      setPagination(response.data.pagination || {});
      setError(null);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to fetch alarms');
    } finally {
      setLoading(false);
    }
  }, [customerId, filters]);

  const createAlarm = async (alarmData) => {
    try {
      const response = await alarmAPI.create(customerId, alarmData);
      setAlarms(prev => [...prev, response.data.alarm]);
      return response.data.alarm;
    } catch (err) {
      throw new Error(err.response?.data?.error || 'Failed to create alarm');
    }
  };

  const updateAlarm = async (alarmId, alarmData) => {
    try {
      const response = await alarmAPI.update(customerId, alarmId, alarmData);
      setAlarms(prev => prev.map(a => a.id === alarmId ? response.data.alarm : a));
      return response.data.alarm;
    } catch (err) {
      throw new Error(err.response?.data?.error || 'Failed to update alarm');
    }
  };

  const deleteAlarm = async (alarmId) => {
    try {
      await alarmAPI.delete(customerId, alarmId);
      setAlarms(prev => prev.filter(a => a.id !== alarmId));
    } catch (err) {
      throw new Error(err.response?.data?.error || 'Failed to delete alarm');
    }
  };

  useEffect(() => {
    fetchAlarms();
  }, [fetchAlarms]);

  return {
    alarms,
    pagination,
    loading,
    error,
    fetchAlarms,
    createAlarm,
    updateAlarm,
    deleteAlarm,
  };
};

export const useAlarm = (customerId, alarmId) => {
  const [alarm, setAlarm] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchAlarm = useCallback(async () => {
    if (!customerId || !alarmId) return;
    
    try {
      setLoading(true);
      const response = await alarmAPI.getById(customerId, alarmId);
      setAlarm(response.data.alarm);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to fetch alarm');
    } finally {
      setLoading(false);
    }
  }, [customerId, alarmId]);

  useEffect(() => {
    fetchAlarm();
  }, [fetchAlarm]);

  return {
    alarm,
    loading,
    error,
    fetchAlarm,
  };
};
