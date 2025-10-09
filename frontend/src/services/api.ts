import axios from 'axios';
import { PlanRequest, PlanningResponse, ResumeRequest } from '../types/api';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds timeout for long-running requests
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`Making ${config.method?.toUpperCase()} request to ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const tripPlanningApi = {
  // Start a new trip planning session
  startPlanning: async (request: PlanRequest): Promise<PlanningResponse> => {
    const response = await api.post<PlanningResponse>('/plan/start', request);
    return response.data;
  },

  // Resume a trip planning session after user selections
  resumePlanning: async (request: ResumeRequest): Promise<PlanningResponse> => {
    const response = await api.post<PlanningResponse>('/plan/resume', request);
    return response.data;
  },

  // Health check endpoint
  healthCheck: async (): Promise<{ status: string; service: string }> => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;

