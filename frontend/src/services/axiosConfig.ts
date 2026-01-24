/**
 * Axios configuration with automatic API key handling
 */

import axios from 'axios';

function getDefaultApiBaseUrl(): string {
  // IMPORTANT:
  // - This axios instance is used in the browser, not inside Docker network.
  // - Therefore we should NOT use docker-compose service names like "api".
  // - Use the current hostname and the exposed API port instead.
  if (typeof window === 'undefined') return '';

  const envBase = process.env.REACT_APP_API_BASE_URL || process.env.REACT_APP_API_URL;
  if (envBase) return envBase;

  const host = window.location.hostname || 'localhost';
  return `${window.location.protocol}//${host}:8000`;
}

// Create axios instance with default configuration
const api = axios.create({
  baseURL: getDefaultApiBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to include API key
api.interceptors.request.use(
  (config) => {
    // In development mode, use dev_admin_key automatically
    if (process.env.NODE_ENV === 'development') {
      config.headers['X-API-Key'] = 'dev_admin_key';
    } else {
      // In production, try to get key from localStorage
      const apiKey = localStorage.getItem('apiKey');
      if (apiKey) {
        config.headers['X-API-Key'] = apiKey;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.error('API Key authentication failed');
    }
    return Promise.reject(error);
  }
);

export default api;
