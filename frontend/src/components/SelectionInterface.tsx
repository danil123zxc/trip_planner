import React, { useEffect, useMemo, useState } from 'react';
import {
  PlanningResponse,
  CandidateLodging,
  CandidateActivity,
  CandidateFood,
  CandidateIntercityTransport,
  ResumeSelections,
  ResearchPlan,
} from '../types/api';
import ResearchPlanForm from './ResearchPlanForm';

interface SelectionInterfaceProps {
  response: PlanningResponse;
  onConfirm: (selections: ResumeSelections) => void;
  onCancel: () => void;
  onExtraResearch?: (researchPlan: ResearchPlan) => Promise<void> | void;
  isLoading?: boolean;
}

type CandidateType = 'lodging' | 'transport' | 'activity' | 'food';

type CandidateIdentity = {
  id?: string | null;
  name?: string | null;
};

const makeCandidateKey = (item: CandidateIdentity | undefined): string => {
  if (!item) {
    return '';
  }

  if (item.id && typeof item.id === 'string' && item.id.trim().length > 0) {
    return `id:${item.id.trim()}`;
  }

  if (item.name && typeof item.name === 'string' && item.name.trim().length > 0) {
    return `name:${item.name.trim()}`;
  }

  try {
    return `hash:${JSON.stringify(item)}`;
  } catch {
    return 'hash:unknown';
  }
};

const SelectionInterface: React.FC<SelectionInterfaceProps> = ({
  response,
  onConfirm,
  onCancel,
  onExtraResearch,
  isLoading = false,
}) => {
  const [selectedLodging, setSelectedLodging] = useState<CandidateLodging | undefined>(undefined);
  const [selectedTransport, setSelectedTransport] =
    useState<CandidateIntercityTransport | undefined>(undefined);
  const [selectedActivityMap, setSelectedActivityMap] = useState<
    Map<string, CandidateActivity>
  >(new Map());
  const [selectedFoodMap, setSelectedFoodMap] = useState<Map<string, CandidateFood>>(new Map());
  const [extraResearchLoading, setExtraResearchLoading] = useState(false);

  const { lodging, activities, food, intercity_transport, research_plan } = response;

  const handleLodgingSelect = (option: CandidateLodging) => {
    setSelectedLodging(option);
  };

  const handleTransportSelect = (option: CandidateIntercityTransport) => {
    setSelectedTransport(option);
  };

  const handleActivityToggle = (activity: CandidateActivity) => {
    const key = makeCandidateKey(activity);
    setSelectedActivityMap((prev) => {
      const next = new Map(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.set(key, activity);
      }
      return next;
    });
  };

  const handleFoodToggle = (foodOption: CandidateFood) => {
    const key = makeCandidateKey(foodOption);
    setSelectedFoodMap((prev) => {
      const next = new Map(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.set(key, foodOption);
      }
      return next;
    });
  };

  const selectedActivities = useMemo(
    () => Array.from(selectedActivityMap.values()),
    [selectedActivityMap],
  );

  const selectedFood = useMemo(() => Array.from(selectedFoodMap.values()), [selectedFoodMap]);

  const isActivitySelected = (activity: CandidateActivity): boolean => {
    return selectedActivityMap.has(makeCandidateKey(activity));
  };

  const isFoodSelected = (foodOption: CandidateFood): boolean => {
    return selectedFoodMap.has(makeCandidateKey(foodOption));
  };

  const canConfirm = useMemo(() => {
    return Boolean(selectedLodging && selectedTransport);
  }, [selectedLodging, selectedTransport]);

  const handleConfirm = () => {
    if (canConfirm) {
      if (!selectedLodging || !selectedTransport) {
        return;
      }

      const payload: ResumeSelections = {
        lodging: selectedLodging,
        intercity_transport: selectedTransport,
        activities: selectedActivities.length > 0 ? selectedActivities : [],
        food: selectedFood.length > 0 ? selectedFood : [],
      };

      onConfirm(payload);
    }
  };

  const handleExtraResearchSubmit = async (plan: ResearchPlan) => {
    if (!onExtraResearch) {
      return;
    }

    setExtraResearchLoading(true);
    try {
      await onExtraResearch(plan);
    } finally {
      setExtraResearchLoading(false);
    }
  };

  useEffect(() => {
    // Reset selections whenever a new response payload arrives
    setSelectedLodging(undefined);
    setSelectedTransport(undefined);
    setSelectedActivityMap(new Map());
    setSelectedFoodMap(new Map());
  }, [response]);

  const renderSelectableCard = (
    item: any,
    type: CandidateType,
    isSelected: boolean,
    onSelect: () => void,
  ) => {
    const chipClass = isSelected
      ? 'ring-2 ring-primary-500 bg-primary-50'
      : 'hover:shadow-md hover:border-primary-300';

    return (
      <div
        key={item.id || item.name}
        className={`card cursor-pointer transition-all duration-200 ${chipClass}`}
        onClick={onSelect}
      >
        <div className="flex justify-between items-start mb-2">
          <h3 className="text-lg font-semibold text-gray-900">{item.name}</h3>
          <div className="flex items-center space-x-2">
            {item.rating && (
              <span className="bg-yellow-100 text-yellow-800 text-xs font-medium px-2.5 py-0.5 rounded-full">
                Rating {item.rating}
              </span>
            )}
            {isSelected && (
              <span className="bg-primary-100 text-primary-800 text-xs font-medium px-2.5 py-0.5 rounded-full">
                Selected
              </span>
            )}
          </div>
        </div>

        {item.address && (
          <p className="text-sm text-gray-600 mb-2">Address: {item.address}</p>
        )}

        {item.price_level && (
          <p className="text-sm text-gray-600 mb-2">Price Level: {item.price_level}</p>
        )}

        {type === 'lodging' && item.price_night && (
          <p className="text-sm text-gray-600 mb-2">Approx. {item.price_night} per night</p>
        )}

        {type === 'transport' && item.price && (
          <p className="text-sm text-gray-600 mb-2">Fare Estimate: {item.price}</p>
        )}

        {type === 'activity' && item.duration_min && (
          <p className="text-sm text-gray-600 mb-2">Duration: {Math.floor(item.duration_min / 60)}h {item.duration_min % 60}m</p>
        )}

        {(type === 'activity' || type === 'food') && item.tags && item.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {item.tags.map((tag: string, index: number) => (
              <span key={index} className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded">
                {tag}
              </span>
            ))}
          </div>
        )}

        {item.notes && <p className="text-sm text-gray-700 mb-3">{item.notes}</p>}

        {item.url && (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary-600 hover:text-primary-800 text-sm font-medium"
            onClick={(event) => event.stopPropagation()}
          >
            View Details
          </a>
        )}
      </div>
    );
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="card">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Review and Choose Options</h2>
        <p className="text-gray-600">
          Pick the lodging and transport that suit your trip. You can also add activities and dining
          picks. When finished, continue to build the final itinerary.
        </p>
      </div>

      {research_plan && onExtraResearch && (
        <ResearchPlanForm
          initialPlan={research_plan}
          onSubmit={handleExtraResearchSubmit}
          isSubmitting={extraResearchLoading || isLoading}
        />
      )}

      {lodging && lodging.length > 0 && (
        <section>
          <h3 className="text-xl font-semibold text-gray-900 mb-4">Select Lodging (required)</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {lodging.map((option) =>
              renderSelectableCard(
                option,
                'lodging',
                selectedLodging
                  ? makeCandidateKey(selectedLodging) === makeCandidateKey(option)
                  : false,
                () => handleLodgingSelect(option),
              ),
            )}
          </div>
        </section>
      )}

      {intercity_transport && intercity_transport.length > 0 && (
        <section>
          <h3 className="text-xl font-semibold text-gray-900 mb-4">Select Transport (required)</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {intercity_transport.map((option) =>
              renderSelectableCard(
                option,
                'transport',
                selectedTransport
                  ? makeCandidateKey(selectedTransport) === makeCandidateKey(option)
                  : false,
                () => handleTransportSelect(option),
              ),
            )}
          </div>
        </section>
      )}

      {activities && activities.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-semibold text-gray-900">Select Activities (optional)</h3>
            {selectedActivities.length > 0 && (
              <span className="text-sm text-gray-600">{selectedActivities.length} chosen</span>
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {activities.map((activity) =>
              renderSelectableCard(
                activity,
                'activity',
                isActivitySelected(activity),
                () => handleActivityToggle(activity),
              ),
            )}
          </div>
        </section>
      )}

      {food && food.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-semibold text-gray-900">Select Food and Dining (optional)</h3>
            {selectedFood.length > 0 && (
              <span className="text-sm text-gray-600">{selectedFood.length} chosen</span>
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {food.map((foodOption) =>
              renderSelectableCard(
                foodOption,
                'food',
                isFoodSelected(foodOption),
                () => handleFoodToggle(foodOption),
              ),
            )}
          </div>
        </section>
      )}

      <div className="flex justify-between items-center pt-6 border-t border-gray-200">
        <button onClick={onCancel} className="btn-secondary" disabled={isLoading}>
          Cancel
        </button>
        <button
          onClick={handleConfirm}
          disabled={!canConfirm || isLoading}
          className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Processing...' : 'Continue Planning'}
        </button>
      </div>

      {(selectedLodging || selectedTransport || selectedActivities.length > 0 || selectedFood.length > 0) && (
        <div className="card bg-blue-50 border border-blue-200">
          <h4 className="font-medium text-blue-900 mb-2">Current selections</h4>
          <div className="text-sm text-blue-800 space-y-1">
            {selectedLodging && <p>Lodging: {selectedLodging.name}</p>}
            {selectedTransport && <p>Transport: {selectedTransport.name}</p>}
            {selectedActivities.length > 0 && <p>Activities: {selectedActivities.length} chosen</p>}
            {selectedFood.length > 0 && <p>Food: {selectedFood.length} chosen</p>}
          </div>
        </div>
      )}
    </div>
  );
};

export default SelectionInterface;
