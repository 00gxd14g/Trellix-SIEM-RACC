import axios from 'axios';
import logger from './logger';

// Resolve API base URL so frontend and backend stay in sync across environments
const resolveBaseUrl = () => {
  const envUrl = import.meta.env.VITE_API_URL?.trim();
  if (envUrl) {
    return envUrl.replace(/\/$/, '');
  }

  if (import.meta.env.DEV) {
    return '/api';
  }

  if (typeof window !== 'undefined' && window.location) {
    const inferred = new URL('/api', window.location.origin);
    return inferred.origin + inferred.pathname;
  }

  return '/api';
};

const API_BASE_URL = resolveBaseUrl();

export const extractCustomerIdFromUrl = (url) => {
  if (!url) return null;
  const match = url.match(/\/customers\/(\d+)/);
  return match ? match[1] : null;
};

const getCustomerIdFromConfig = (config) => {
  if (!config || !config.url) return null;
  return extractCustomerIdFromUrl(config.url);
};

export { api };

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging and tenant header injection
api.interceptors.request.use(
  config => {
    config.metadata = { startTime: new Date() };

    // Extract customer ID from URL and add as X-Customer-ID header
    const customerId = getCustomerIdFromConfig(config);
    if (customerId) {
      config.headers['X-Customer-ID'] = customerId;
    }

    if (config.data instanceof FormData) {
      delete config.headers['Content-Type'];
      delete config.headers['content-type'];
    }

    logger.debug(`API Request: ${config.method?.toUpperCase()} ${config.url}`, {
      params: config.params,
      data: config.data,
      headers: config.headers
    });
    return config;
  },
  error => {
    logger.error('API Request Error', error);
    return Promise.reject(error);
  }
);

// Response interceptor for logging and error handling
api.interceptors.response.use(
  response => {
    const duration = new Date() - response.config.metadata.startTime;
    logger.logApiCall(
      response.config.method?.toUpperCase(),
      response.config.url,
      response.config.data,
      response,
      duration
    );
    return response;
  },
  error => {
    const duration = error.config?.metadata ? new Date() - error.config.metadata.startTime : 0;

    if (error.response?.status === 404) {
      logger.error('API endpoint not found', {
        url: error.config?.url,
        method: error.config?.method,
        status: 404
      });
    } else if (error.response?.status === 500) {
      logger.error('Server error', {
        url: error.config?.url,
        method: error.config?.method,
        status: 500,
        error: error.response.data
      });
    } else if (error.code === 'ERR_NETWORK') {
      logger.error('Network error', {
        url: error.config?.url,
        method: error.config?.method,
        message: 'Unable to connect to server'
      });
    } else {
      logger.error('API Error', {
        url: error.config?.url,
        method: error.config?.method,
        status: error.response?.status,
        error: error.response?.data || error.message
      });
    }

    if (error.config?.metadata) {
      logger.logApiCall(
        error.config.method?.toUpperCase(),
        error.config.url,
        error.config.data,
        error.response,
        duration
      );
    }

    return Promise.reject(error);
  }
);

// Customer API
export const customerAPI = {
  getAll: () => api.get('/customers'),
  getById: (id) => api.get(`/customers/${id}`),
  create: (data) => api.post('/customers', data),
  update: (id, data) => api.put(`/customers/${id}`, data),
  delete: (id) => api.delete(`/customers/${id}`),
  getFiles: (id) => api.get(`/customers/${id}/files`),
  uploadFile: (id, formData, config = {}) => api.post(`/customers/${id}/files/upload`, formData, {
    ...config,
  }),
  downloadFile: (id, type) => api.get(`/customers/${id}/files/${type}`, {
    responseType: 'blob',
  }),
  deleteFile: (id, type) => api.delete(`/customers/${id}/files/${type}`),
};

// Rule API
export const ruleAPI = {
  getAll: (customerId, params = {}) => api.get(`/customers/${customerId}/rules`, { params }),
  getById: (customerId, ruleId) => api.get(`/customers/${customerId}/rules/${ruleId}`),
  create: (customerId, data) => api.post(`/customers/${customerId}/rules`, data),
  update: (customerId, ruleId, data) => api.put(`/customers/${customerId}/rules/${ruleId}`, data),
  delete: (customerId, ruleId) => api.delete(`/customers/${customerId}/rules/${ruleId}`),
  search: (customerId, params = {}) => api.get(`/customers/${customerId}/rules/search`, { params }),
  generateAlarms: (customerId, ruleIds) => api.post(`/customers/${customerId}/rules/generate-alarms`, { rule_ids: ruleIds }),
  transformBulk: (customerId, data) => api.post(`/customers/${customerId}/rules/transform-bulk`, data),
  getStats: (customerId) => api.get(`/customers/${customerId}/rules/stats`),
  exportAll: (customerId, ids = []) => {
    const params = {};
    if (ids && ids.length > 0) {
      params.rule_ids = ids.join(',');
    }
    return api.get(`/customers/${customerId}/rules/export`, {
      params,
      responseType: 'blob',
    });
  },
};

// Alarm API
export const alarmAPI = {
  getAll: (customerId, params = {}) => api.get(`/customers/${customerId}/alarms`, { params }),
  getById: (customerId, alarmId) => api.get(`/customers/${customerId}/alarms/${alarmId}`),
  create: (customerId, data) => api.post(`/customers/${customerId}/alarms`, data),
  update: (customerId, alarmId, data) => api.put(`/customers/${customerId}/alarms/${alarmId}`, data),
  delete: (customerId, alarmId) => api.delete(`/customers/${customerId}/alarms/${alarmId}`),
  bulkDelete: (customerId, alarmIds) => api.post(`/customers/${customerId}/alarms/bulk-delete`, { alarm_ids: alarmIds }),
  getStats: (customerId) => api.get(`/customers/${customerId}/alarms/stats`),
  exportAll: (customerId, ids = []) => {
    const params = {};
    if (ids && ids.length > 0) {
      params.alarm_ids = ids.join(',');
    }
    return api.get(`/customers/${customerId}/alarms/export`, {
      params,
      responseType: 'blob',
    });
  },
};

// Analysis API
export const analysisAPI = {
  getCoverage: (customerId) => api.get(`/customers/${customerId}/analysis/coverage`),
  getRelationships: (customerId) => api.get(`/customers/${customerId}/analysis/relationships`),
  getUnmatchedRules: (customerId) => api.get(`/customers/${customerId}/analysis/unmatched-rules`),
  getUnmatchedAlarms: (customerId) => api.get(`/customers/${customerId}/analysis/unmatched-alarms`),
  generateMissingAlarms: (customerId, data = {}) => api.post(`/customers/${customerId}/analysis/generate-missing`, data),
  detectRelationships: (customerId) => api.post(`/customers/${customerId}/analysis/detect-relationships`),
  getEventUsage: (customerId, params = {}) => api.get(`/customers/${customerId}/analysis/event-usage`, { params }),
  getReport: (customerId) => api.get(`/customers/${customerId}/analysis/report`, { responseType: 'blob' }),
};

// Settings API
export const settingsAPI = {
  getSystem: () => api.get('/settings'),
  updateSystem: (data) => api.put('/settings', data),
  getCustomer: (customerId) => api.get(`/customers/${customerId}/settings`),
  updateCustomer: (customerId, overrides) => api.put(`/customers/${customerId}/settings`, { overrides }),
  testConnection: (config) => api.post('/settings/api/test', { config }),
};

// System utilities
export const systemAPI = {
  getHealth: () => api.get('/health'),
};
