import { apiClient } from './axios.js';

export const authApi = {
  login: (username, password) =>
    apiClient.post('/auth/login', { username, password }).then((r) => r.data),
  me: () => apiClient.get('/auth/me').then((r) => r.data),
};

export const dashboardApi = {
  get: () => apiClient.get('/dashboard').then((r) => r.data),
  stats: () => apiClient.get('/stats').then((r) => r.data),
};

export const printsApi = {
  list: (params = {}) =>
    apiClient.get('/prints', { params }).then((r) => r.data),
  get: (id) => apiClient.get(`/prints/${id}`).then((r) => r.data),
  remove: (id) => apiClient.delete(`/prints/${id}`).then((r) => r.data),
};

export const printersApi = {
  list: () => apiClient.get('/printers').then((r) => r.data),
};

export const usersApi = {
  summary: () => apiClient.get('/users/summary').then((r) => r.data),
  update: (rawUsername, payload) =>
    apiClient.put(`/users/${encodeURIComponent(rawUsername)}`, payload).then((r) => r.data),
};

export const reportsApi = {
  meta: () => apiClient.get('/reports').then((r) => r.data),
  excelUrl: (params = {}) => buildUrl('/reports/excel', params),
  pdfUrl: (params = {}) => buildUrl('/reports/pdf', params),
  download: async (kind, params = {}) => {
    const path = kind === 'pdf' ? '/reports/pdf' : '/reports/excel';
    const response = await apiClient.get(path, {
      params,
      responseType: 'blob',
    });
    const filename =
      extractFilename(response.headers['content-disposition']) ||
      `print_logs.${kind === 'pdf' ? 'pdf' : 'xlsx'}`;
    return { blob: response.data, filename };
  },
};

function buildUrl(path, params) {
  const usp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') usp.append(k, v);
  });
  const qs = usp.toString();
  return `${path}${qs ? `?${qs}` : ''}`;
}

function extractFilename(contentDisposition) {
  if (!contentDisposition) return null;
  const match = /filename="?([^";]+)"?/i.exec(contentDisposition);
  return match ? match[1] : null;
}
