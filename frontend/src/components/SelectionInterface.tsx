import React, { useState } from 'react';
import { PlanningResponse, CandidateLodging, CandidateActivity, CandidateFood, CandidateIntercityTransport, ResumeSelections } from '../types/api';

interface SelectionInterfaceProps {
  response: PlanningResponse;
  onConfirm: (selections: ResumeSelections) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

const SelectionInterface: React.FC<SelectionInterfaceProps> = ({ 
  response, 
  onConfirm, 
  onCancel, 
  isLoading = false 
}) => {
  const [selections, setSelections] = useState<ResumeSelections>({
    lodging: undefined,
    intercity_transport: undefined,
    activities: [],
    food: []
  });

  const { lodging, activities, food, intercity_transport } = response;

  const handleLodgingSelect = (option: CandidateLodging) => {
    setSelections(prev => ({ ...prev, lodging: option }));
  };

  const handleTransportSelect = (option: CandidateIntercityTransport) => {
    setSelections(prev => ({ ...prev, intercity_transport: option }));
  };

  const handleActivityToggle = (activity: CandidateActivity) => {
    setSelections(prev => {
      const currentActivities = prev.activities || [];
      const isSelected = currentActivities.some(a => a.id === activity.id || a.name === activity.name);
      
      if (isSelected) {
        return {
          ...prev,
          activities: currentActivities.filter(a => a.id !== activity.id && a.name !== activity.name)
        };
      } else {
        return {
          ...prev,
          activities: [...currentActivities, activity]
        };
      }
    });
  };

  const handleFoodToggle = (foodOption: CandidateFood) => {
    setSelections(prev => {
      const currentFood = prev.food || [];
      const isSelected = currentFood.some(f => f.id === foodOption.id || f.name === foodOption.name);
      
      if (isSelected) {
        return {
          ...prev,
          food: currentFood.filter(f => f.id !== foodOption.id && f.name !== foodOption.name)
        };
      } else {
        return {
          ...prev,
          food: [...currentFood, foodOption]
        };
      }
    });
  };

  const isActivitySelected = (activity: CandidateActivity) => {
    return selections.activities?.some(a => a.id === activity.id || a.name === activity.name) || false;
  };

  const isFoodSelected = (foodOption: CandidateFood) => {
    return selections.food?.some(f => f.id === foodOption.id || f.name === foodOption.name) || false;
  };

  const canConfirm = () => {
    return selections.lodging && selections.intercity_transport;
  };

  const handleConfirm = () => {
    if (canConfirm()) {
      onConfirm(selections);
    }
  };

  const renderSelectableCard = (
    item: any, 
    type: 'lodging' | 'transport' | 'activity' | 'food',
    isSelected: boolean = false,
    onSelect: () => void
  ) => (
    <div 
      key={item.id || item.name} 
      className={`card cursor-pointer transition-all duration-200 ${
        isSelected 
          ? 'ring-2 ring-primary-500 bg-primary-50' 
          : 'hover:shadow-md hover:border-primary-300'
      }`}
      onClick={onSelect}
    >
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-lg font-semibold text-gray-900">{item.name}</h3>
        <div className="flex items-center space-x-2">
          {item.rating && (
            <span className="bg-yellow-100 text-yellow-800 text-xs font-medium px-2.5 py-0.5 rounded-full">
              ⭐ {item.rating}
            </span>
          )}
          {isSelected && (
            <span className="bg-primary-100 text-primary-800 text-xs font-medium px-2.5 py-0.5 rounded-full">
              ✓ Selected
            </span>
          )}
        </div>
      </div>
      
      {item.address && (
        <p className="text-sm text-gray-600 mb-2">📍 {item.address}</p>
      )}
      
      {item.price_level && (
        <p className="text-sm text-gray-600 mb-2">💰 {item.price_level}</p>
      )}

      {type === 'lodging' && item.price_night && (
        <p className="text-sm text-gray-600 mb-2">💵 ${item.price_night}/night</p>
      )}

      {type === 'transport' && item.price && (
        <p className="text-sm text-gray-600 mb-2">💵 ${item.price}</p>
      )}

      {type === 'activity' && item.duration_min && (
        <p className="text-sm text-gray-600 mb-2">⏱️ {Math.floor(item.duration_min / 60)}h {item.duration_min % 60}m</p>
      )}

      {type === 'activity' && item.tags && item.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {item.tags.map((tag: string, index: number) => (
            <span key={index} className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded">
              {tag}
            </span>
          ))}
        </div>
      )}

      {type === 'food' && item.tags && item.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {item.tags.map((tag: string, index: number) => (
            <span key={index} className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded">
              {tag}
            </span>
          ))}
        </div>
      )}
      
      {item.notes && (
        <p className="text-sm text-gray-700 mb-3">{item.notes}</p>
      )}
      
      {item.url && (
        <a 
          href={item.url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-primary-600 hover:text-primary-800 text-sm font-medium"
          onClick={(e) => e.stopPropagation()}
        >
          View Details →
        </a>
      )}
    </div>
  );

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="card">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Make Your Selections</h2>
        <p className="text-gray-600">
          Please select your preferred options to continue with your trip planning. 
          You must select at least one lodging option and one transport option.
        </p>
      </div>

      {/* Lodging Selection */}
      {lodging && lodging.length > 0 && (
        <div>
          <h3 className="text-xl font-semibold text-gray-900 mb-4">🏨 Select Lodging (Required)</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {lodging.map((option) => 
              renderSelectableCard(
                option, 
                'lodging', 
                selections.lodging?.id === option.id || selections.lodging?.name === option.name,
                () => handleLodgingSelect(option)
              )
            )}
          </div>
        </div>
      )}

      {/* Transport Selection */}
      {intercity_transport && intercity_transport.length > 0 && (
        <div>
          <h3 className="text-xl font-semibold text-gray-900 mb-4">🚌 Select Transport (Required)</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {intercity_transport.map((option) => 
              renderSelectableCard(
                option, 
                'transport', 
                selections.intercity_transport?.name === option.name,
                () => handleTransportSelect(option)
              )
            )}
          </div>
        </div>
      )}

      {/* Activities Selection */}
      {activities && activities.length > 0 && (
        <div>
          <h3 className="text-xl font-semibold text-gray-900 mb-4">
            🎯 Select Activities (Optional)
            {selections.activities && selections.activities.length > 0 && (
              <span className="text-sm font-normal text-gray-600 ml-2">
                ({selections.activities.length} selected)
              </span>
            )}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {activities.map((activity) => 
              renderSelectableCard(
                activity, 
                'activity', 
                isActivitySelected(activity),
                () => handleActivityToggle(activity)
              )
            )}
          </div>
        </div>
      )}

      {/* Food Selection */}
      {food && food.length > 0 && (
        <div>
          <h3 className="text-xl font-semibold text-gray-900 mb-4">
            🍽️ Select Food & Dining (Optional)
            {selections.food && selections.food.length > 0 && (
              <span className="text-sm font-normal text-gray-600 ml-2">
                ({selections.food.length} selected)
              </span>
            )}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {food.map((foodOption) => 
              renderSelectableCard(
                foodOption, 
                'food', 
                isFoodSelected(foodOption),
                () => handleFoodToggle(foodOption)
              )
            )}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex justify-between items-center pt-6 border-t border-gray-200">
        <button
          onClick={onCancel}
          className="btn-secondary"
          disabled={isLoading}
        >
          Cancel
        </button>
        
        <button
          onClick={handleConfirm}
          disabled={!canConfirm() || isLoading}
          className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Processing...' : 'Continue Planning'}
        </button>
      </div>

      {/* Selection Summary */}
      {(selections.lodging || selections.intercity_transport || 
        (selections.activities && selections.activities.length > 0) || 
        (selections.food && selections.food.length > 0)) && (
        <div className="card bg-blue-50 border-blue-200">
          <h4 className="font-medium text-blue-900 mb-2">Selection Summary</h4>
          <div className="text-sm text-blue-800 space-y-1">
            {selections.lodging && (
              <p>🏨 Lodging: {selections.lodging.name}</p>
            )}
            {selections.intercity_transport && (
              <p>🚌 Transport: {selections.intercity_transport.name}</p>
            )}
            {selections.activities && selections.activities.length > 0 && (
              <p>🎯 Activities: {selections.activities.length} selected</p>
            )}
            {selections.food && selections.food.length > 0 && (
              <p>🍽️ Food: {selections.food.length} selected</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default SelectionInterface;

