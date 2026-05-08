import axios from 'axios';

const baseURL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, '') ||
  'http://localhost:8000/api';

const STORAGE_TOKEN_KEY = 'pt_access_token';
const STORAGE_ADMIN_KEY = 'pt_admin';

export const apiClient = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(STORAGE_TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem(STORAGE_TOKEN_KEY);
      localStorage.removeItem(STORAGE_ADMIN_KEY);
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.replace('/login');
      }
    }
    return Promise.reject(error);
  },
);

export const tokenStorage = {
  get: () => localStorage.getItem(STORAGE_TOKEN_KEY),
  set: (token) => localStorage.setItem(STORAGE_TOKEN_KEY, token),
  clear: () => {
    localStorage.removeItem(STORAGE_TOKEN_KEY);
    localStorage.removeItem(STORAGE_ADMIN_KEY);
  },
};

export const adminStorage = {
  get: () => {
    try {
      const raw = localStorage.getItem(STORAGE_ADMIN_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (_e) {
      return null;
    }
  },
  set: (admin) => localStorage.setItem(STORAGE_ADMIN_KEY, JSON.stringify(admin)),
};

export const API_BASE_URL = baseURL;
