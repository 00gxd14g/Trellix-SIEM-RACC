import { useState, useEffect, useCallback } from 'react';
import { ruleAPI } from '@/lib/api';

export const useRules = (customerId, filters = {}) => {
  const [rules, setRules] = useState([]);
  const [pagination, setPagination] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchRules = useCallback(async (params = {}) => {
    if (!customerId) return;
    
    try {
      setLoading(true);
      const response = await ruleAPI.getAll(customerId, { ...filters, ...params });
      setRules(response.data.rules || []);
      setPagination(response.data.pagination || {});
      setError(null);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to fetch rules');
    } finally {
      setLoading(false);
    }
  }, [customerId, filters]);

  const searchRules = async (searchParams = {}) => {
    if (!customerId) return;
    
    try {
      setLoading(true);
      const response = await ruleAPI.search(customerId, searchParams);
      setRules(response.data.rules || []);
      setPagination({});
      setError(null);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to search rules');
    } finally {
      setLoading(false);
    }
  };

  const generateAlarms = async (ruleIds) => {
    try {
      const response = await ruleAPI.generateAlarms(customerId, ruleIds);
      return response.data;
    } catch (err) {
      throw new Error(err.response?.data?.error || 'Failed to generate alarms');
    }
  };

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  return {
    rules,
    pagination,
    loading,
    error,
    fetchRules,
    searchRules,
    generateAlarms,
  };
};

export const useRule = (customerId, ruleId) => {
  const [rule, setRule] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchRule = useCallback(async () => {
    if (!customerId || !ruleId) return;
    
    try {
      setLoading(true);
      const response = await ruleAPI.getById(customerId, ruleId);
      setRule(response.data.rule);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to fetch rule');
    } finally {
      setLoading(false);
    }
  }, [customerId, ruleId]);

  useEffect(() => {
    fetchRule();
  }, [fetchRule]);

  return {
    rule,
    loading,
    error,
    fetchRule,
  };
};
