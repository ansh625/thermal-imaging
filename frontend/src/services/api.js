import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  signup: (data) => api.post('/auth/signup', null, { params: data }),
  login: (data) => api.post('/auth/login', new URLSearchParams(data), {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  }),
  getMe: () => api.get('/auth/me'),
  forgotPassword: (email) => api.post('/auth/forgot-password', null, { params: { email } }),
  resetPassword: (token, newPassword) => api.post('/auth/reset-password', null, {
    params: { token, new_password: newPassword }
  }),
};

// Camera API
export const cameraAPI = {
  connect: (data) => api.post('/camera/connect', null, { params: data }),
  disconnect: (data) => api.post('/camera/disconnect', null, { params: data }),
  list: () => api.get('/camera/list'),
  delete: (cameraId) => api.delete(`/camera/${cameraId}`),
};

// Recording API
export const recordingAPI = {
  start: (sessionId) => api.post('/recording/start', null, { params: { session_id: sessionId } }),
  stop: (sessionId) => api.post('/recording/stop', null, { params: { session_id: sessionId } }),
  list: () => api.get('/recording/list'),
  download: (recordingId) => `${API_URL}/recording/download/${recordingId}`,
  delete: (recordingId) => api.delete(`/recording/${recordingId}`),
};

// Detection API
export const detectionAPI = {
  list: (limit = 100) => api.get('/detection/list', { params: { limit } }),
};

// Schedule API
export const scheduleAPI = {
  create: (data) => api.post('/schedule/create', null, { params: data }),
  list: () => api.get('/schedule/list'),
  toggle: (scheduleId) => api.put(`/schedule/${scheduleId}/toggle`),
  delete: (scheduleId) => api.delete(`/schedule/${scheduleId}`),
};

// Dashboard API
export const dashboardAPI = {
  getStats: () => api.get('/dashboard/stats'),
};

export default api;