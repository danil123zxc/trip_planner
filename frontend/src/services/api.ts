import axios from 'axios';
import { PlanRequest, PlanningResponse, ResumeRequest, ResumeSelections } from '../types/api';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const getTimeout = () => {
  const raw =
    process.env.REACT_APP_API_TIMEOUT_MS ??
    process.env.REACT_APP_API_TIMEOUT;

  if (!raw) {
    return 120000; // default to 2 minutes to allow for slower planning runs
  }

  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 120000;
};

const API_TIMEOUT = getTimeout();

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: API_TIMEOUT,
});

type WithIdOrName = { id?: string | null; name?: string | null };

const coerceArray = <T>(value?: T | T[] | null): T[] => {
  if (!value) {
    return [];
  }
  return Array.isArray(value) ? value.filter(Boolean) as T[] : [value];
};

const dedupeByIdOrName = <T extends WithIdOrName>(items: T[]): T[] => {
  const seen = new Set<string>();
  const result: T[] = [];

  for (const item of items) {
    if (!item) {
      continue;
    }
    const key = item.id ?? item.name;
    if (key && seen.has(key)) {
      continue;
    }
    if (key) {
      seen.add(key);
    }
    result.push(item);
  }

  return result;
};

const normalizeSingleSelection = <T extends WithIdOrName>(value?: T | T[] | null): T[] => {
  const normalized = dedupeByIdOrName(coerceArray(value));
  return normalized.length > 0 ? [normalized[0]] : [];
};

const normalizeMultiSelection = <T extends WithIdOrName>(value?: T[] | null): T[] => {
  return dedupeByIdOrName(coerceArray(value));
};

const formatSelections = (selections?: ResumeSelections) => {
  if (!selections) {
    return {
      lodging: [],
      intercity_transport: [],
      activities: [],
      food: [],
    };
  }

  return {
    lodging: normalizeSingleSelection(selections.lodging),
    intercity_transport: normalizeSingleSelection(selections.intercity_transport),
    activities: normalizeMultiSelection(selections.activities),
    food: normalizeMultiSelection(selections.food),
  };
};

const buildFinalPlanPayload = (request: ResumeRequest) => {
  if (!request.config) {
    throw new Error('Missing workflow config required to resume planning.');
  }
  if (!request.selections) {
    throw new Error('Selections are required to generate the final plan.');
  }

  return {
    config: request.config,
    selections: formatSelections(request.selections),
  };
};

const buildExtraResearchPayload = (request: ResumeRequest) => {
  if (!request.config) {
    throw new Error('Missing workflow config required to resume planning.');
  }
  if (!request.research_plan) {
    throw new Error('Research plan overrides are required for extra research.');
  }

  return {
    config: request.config,
    research_plan: request.research_plan,
  };
};

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`Making ${config.method?.toUpperCase()} request to ${config.url}`);
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
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

  // Resume the workflow by either finalizing the plan or requesting extra research
  resumePlanning: async (request: ResumeRequest): Promise<PlanningResponse> => {
    const targetEndpoint = request.research_plan ? '/plan/extra_research' : '/plan/final_plan';
    const payload = request.research_plan
      ? buildExtraResearchPayload(request)
      : buildFinalPlanPayload(request);

    const response = await api.post<PlanningResponse>(targetEndpoint, payload);
    return response.data;
  },

  // Health check endpoint
  healthCheck: async (): Promise<{ status: string; service: string }> => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;
