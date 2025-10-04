import { useState, useEffect } from 'react';
import api from '../services/api';

export interface ApiHealthState {
  isHealthy: boolean | null;
  isLoading: boolean;
  error: string | null;
}

export const useApiHealth = () => {
  const [state, setState] = useState<ApiHealthState>({
    isHealthy: null,
    isLoading: true,
    error: null,
  });

  useEffect(() => {
    const checkHealth = async () => {
      try {
        setState(prev => ({ ...prev, isLoading: true, error: null }));
        await api.get('/health');
        setState({
          isHealthy: true,
          isLoading: false,
          error: null,
        });
      } catch (error) {
        setState({
          isHealthy: false,
          isLoading: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    };

    checkHealth();
  }, []);

  return state;
};

