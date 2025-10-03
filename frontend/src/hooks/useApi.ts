import { useState, useEffect } from 'react';
import { tripPlanningApi } from '../services/api';

export const useApiHealth = () => {
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await tripPlanningApi.healthCheck();
        setIsHealthy(true);
      } catch (error) {
        setIsHealthy(false);
      } finally {
        setIsLoading(false);
      }
    };

    checkHealth();
  }, []);

  return { isHealthy, isLoading };
};

