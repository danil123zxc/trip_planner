import { useState, useCallback } from 'react';
import { tripPlanningApi } from '../services/api';
import { PlanRequest, ResumeRequest, PlanningState } from '../types/api';

const formatErrorMessage = (error: any, fallback: string) => {
  if (error?.code === 'ECONNABORTED' || /timeout/i.test(error?.message ?? '')) {
    return 'The planning request is taking longer than expected. Please wait a bit and try again, or refresh once the backend finishes.';
  }

  const detail = error?.response?.data?.detail;

  if (Array.isArray(detail)) {
    return detail
      .map((entry: any) => {
        if (!entry) {
          return null;
        }

        if (typeof entry === 'string') {
          return entry;
        }

        if (entry.msg) {
          const location = Array.isArray(entry.loc) ? entry.loc.join('.') : entry.loc;
          return location ? `${location}: ${entry.msg}` : entry.msg;
        }

        return typeof entry === 'object' ? JSON.stringify(entry) : String(entry);
      })
      .filter(Boolean)
      .join('; ');
  }

  if (detail && typeof detail === 'object') {
    if ('message' in detail && typeof detail.message === 'string') {
      return detail.message;
    }

    return JSON.stringify(detail);
  }

  if (typeof detail === 'string') {
    return detail;
  }

  return error?.message || fallback;
};

export const useTripPlanning = () => {
  const [state, setState] = useState<PlanningState>({
    status: 'idle',
  });

  const startPlanning = useCallback(async (request: PlanRequest) => {
    setState({ status: 'loading' });
    
    try {
      const response = await tripPlanningApi.startPlanning(request);
      setState({ status: 'success', data: response });
      return response;
    } catch (error: any) {
      const errorMessage = formatErrorMessage(error, 'Failed to start planning');
      setState({ status: 'error', error: errorMessage });
      throw error;
    }
  }, []);

  const resumePlanning = useCallback(async (request: ResumeRequest) => {
    setState({ status: 'loading' });
    
    try {
      const response = await tripPlanningApi.resumePlanning(request);
      setState({ status: 'success', data: response });
      return response;
    } catch (error: any) {
      const errorMessage = formatErrorMessage(error, 'Failed to resume planning');
      setState({ status: 'error', error: errorMessage });
      throw error;
    }
  }, []);

  const reset = useCallback(() => {
    setState({ status: 'idle' });
  }, []);

  return {
    state,
    startPlanning,
    resumePlanning,
    reset,
  };
};
