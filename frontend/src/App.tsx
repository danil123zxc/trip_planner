import React, { useState } from 'react';
import { useTripPlanning } from './hooks/useTripPlanning';
import { useApiHealth } from './hooks/useApiHealth';
import TripForm from './components/TripForm';
import PlanningResults from './components/PlanningResults';
import SelectionInterface from './components/SelectionInterface';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorMessage from './components/ErrorMessage';
import { TripFormData, ResumeSelections } from './types/api';

function App() {
  const { state, startPlanning, resumePlanning, reset } = useTripPlanning();
  const { isHealthy, isLoading: healthLoading } = useApiHealth();
  const [currentConfig, setCurrentConfig] = useState<any>(null);

  const handleFormSubmit = async (formData: TripFormData) => {
    try {
      const response = await startPlanning({ context: formData });
      if (response.config) {
        setCurrentConfig(response.config);
      }
    } catch (error) {
      console.error('Failed to start planning:', error);
    }
  };

  const handleSelectionConfirm = async (selections: ResumeSelections) => {
    if (!currentConfig) return;
    
    try {
      const response = await resumePlanning({
        config: currentConfig,
        selections,
        research_plan: undefined
      });
      if (response.config) {
        setCurrentConfig(response.config);
      }
    } catch (error) {
      console.error('Failed to resume planning:', error);
    }
  };

  const handleStartOver = () => {
    reset();
    setCurrentConfig(null);
  };

  // Show loading while checking API health
  if (healthLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <LoadingSpinner size="lg" message="Checking API connection..." />
      </div>
    );
  }

  // Show error if API is not healthy
  if (isHealthy === false) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full">
          <ErrorMessage 
            message="Unable to connect to the trip planning API. Please make sure the backend server is running on http://localhost:8000"
            onRetry={() => window.location.reload()}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">🌍 Trip Planner</h1>
            </div>
            <div className="flex items-center space-x-4">
              {state.status === 'success' && state.data && (
                <button
                  onClick={handleStartOver}
                  className="btn-secondary text-sm"
                >
                  Start Over
                </button>
              )}
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span className="text-sm text-gray-600">API Connected</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {state.status === 'idle' && (
          <TripForm onSubmit={handleFormSubmit} isLoading={false} />
        )}

        {state.status === 'loading' && (
          <div className="flex justify-center items-center py-12">
            <LoadingSpinner size="lg" message="Planning your trip..." />
          </div>
        )}

        {state.status === 'error' && (
          <div className="max-w-2xl mx-auto">
            <ErrorMessage 
              message={state.error || 'An unexpected error occurred'}
              onRetry={handleStartOver}
            />
          </div>
        )}

        {state.status === 'success' && state.data && (
          <>
            {state.data.status === 'interrupt' ? (
              <SelectionInterface
                response={state.data}
                onConfirm={handleSelectionConfirm}
                onCancel={handleStartOver}
                isLoading={state.status === 'loading'}
              />
            ) : (
              <PlanningResults response={state.data} />
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-sm text-gray-500">
            <p>Powered by AI • Built with React & TypeScript</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;

