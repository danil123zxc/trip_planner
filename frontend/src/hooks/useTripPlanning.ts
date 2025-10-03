import { useState, useCallback } from 'react';
import { tripPlanningApi } from '../services/api';
import { PlanRequest, PlanningResponse, ResumeRequest, PlanningState } from '../types/api';

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
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to start planning';
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
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to resume planning';
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

