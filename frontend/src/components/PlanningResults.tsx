import React from 'react';
import { PlanningResponse, CandidateLodging, CandidateActivity, CandidateFood, CandidateIntercityTransport } from '../types/api';

interface PlanningResultsProps {
  response: PlanningResponse;
  onSelection?: (selections: any) => void;
}

const PlanningResults: React.FC<PlanningResultsProps> = ({ response, onSelection }) => {
  const { 
    status, 
    estimated_budget, 
    lodging, 
    activities, 
    food, 
    intercity_transport, 
    recommendations, 
    final_plan,
    messages 
  } = response;

  const renderCandidateCard = (candidate: any, type: string) => (
    <div key={candidate.id || candidate.name} className="card">
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-lg font-semibold text-gray-900">{candidate.name}</h3>
        {candidate.rating && (
          <span className="bg-yellow-100 text-yellow-800 text-xs font-medium px-2.5 py-0.5 rounded-full">
            ⭐ {candidate.rating}
          </span>
        )}
      </div>
      
      {candidate.address && (
        <p className="text-sm text-gray-600 mb-2">📍 {candidate.address}</p>
      )}
      
      {candidate.price_level && (
        <p className="text-sm text-gray-600 mb-2">💰 {candidate.price_level}</p>
      )}
      
      {candidate.notes && (
        <p className="text-sm text-gray-700 mb-3">{candidate.notes}</p>
      )}
      
      {candidate.url && (
        <a 
          href={candidate.url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-primary-600 hover:text-primary-800 text-sm font-medium"
        >
          View Details →
        </a>
      )}
    </div>
  );

  const renderBudgetEstimate = (budget: any) => (
    <div className="card">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Budget Estimate</h3>
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">Intercity Transport:</span>
          <span className="font-medium">{budget.currency} {budget.intercity_transport}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Local Transport:</span>
          <span className="font-medium">{budget.currency} {budget.local_transport}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Food:</span>
          <span className="font-medium">{budget.currency} {budget.food}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Activities:</span>
          <span className="font-medium">{budget.currency} {budget.activities}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Lodging:</span>
          <span className="font-medium">{budget.currency} {budget.lodging}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Other:</span>
          <span className="font-medium">{budget.currency} {budget.other}</span>
        </div>
        <div className="flex justify-between col-span-2 pt-2 border-t border-gray-200">
          <span className="text-gray-900 font-semibold">Total:</span>
          <span className="font-bold text-lg">{budget.currency} {budget.total}</span>
        </div>
        <div className="flex justify-between col-span-2">
          <span className="text-gray-600">Per Day:</span>
          <span className="font-medium">{budget.currency} {budget.budget_per_day}</span>
        </div>
      </div>
      {budget.notes && (
        <div className="mt-4 p-3 bg-blue-50 rounded-lg">
          <p className="text-sm text-blue-800">{budget.notes}</p>
        </div>
      )}
    </div>
  );

  const renderRecommendations = (recs: any) => (
    <div className="card">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Travel Recommendations</h3>
      
      <div className="mb-4">
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
          recs.safety_level === 'very_safe' ? 'bg-green-100 text-green-800' :
          recs.safety_level === 'safe' ? 'bg-blue-100 text-blue-800' :
          recs.safety_level === 'moderate' ? 'bg-yellow-100 text-yellow-800' :
          recs.safety_level === 'risky' ? 'bg-orange-100 text-orange-800' :
          'bg-red-100 text-red-800'
        }`}>
          Safety Level: {recs.safety_level.replace('_', ' ').toUpperCase()}
        </span>
      </div>

      {recs.safety_notes && recs.safety_notes.length > 0 && (
        <div className="mb-4">
          <h4 className="font-medium text-gray-900 mb-2">Safety Notes</h4>
          <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
            {recs.safety_notes.map((note: string, index: number) => (
              <li key={index}>{note}</li>
            ))}
          </ul>
        </div>
      )}

      {recs.cultural_considerations && recs.cultural_considerations.length > 0 && (
        <div className="mb-4">
          <h4 className="font-medium text-gray-900 mb-2">Cultural Considerations</h4>
          <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
            {recs.cultural_considerations.map((consideration: string, index: number) => (
              <li key={index}>{consideration}</li>
            ))}
          </ul>
        </div>
      )}

      {recs.weather_conditions && (
        <div className="mb-4">
          <h4 className="font-medium text-gray-900 mb-2">Weather</h4>
          <p className="text-sm text-gray-700">{recs.weather_conditions}</p>
        </div>
      )}

      {recs.currency_info && (
        <div className="mb-4">
          <h4 className="font-medium text-gray-900 mb-2">Currency Info</h4>
          <p className="text-sm text-gray-700">{recs.currency_info}</p>
        </div>
      )}
    </div>
  );

  const renderFinalPlan = (plan: any) => (
    <div className="card">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Your Trip Itinerary</h3>
      
      {plan.total_budget && (
        <div className="mb-6 p-4 bg-green-50 rounded-lg">
          <div className="flex justify-between items-center">
            <span className="text-green-800 font-medium">Total Budget:</span>
            <span className="text-green-900 font-bold text-xl">{plan.currency} {plan.total_budget}</span>
          </div>
        </div>
      )}

      {plan.days && plan.days.length > 0 && (
        <div className="space-y-6">
          {plan.days.map((day: any, index: number) => (
            <div key={index} className="border border-gray-200 rounded-lg p-4">
              <h4 className="font-semibold text-gray-900 mb-3">
                Day {day.day_number} - {new Date(day.day_date).toLocaleDateString()}
              </h4>
              
              {day.activities && day.activities.length > 0 && (
                <div className="mb-4">
                  <h5 className="font-medium text-gray-800 mb-2">Activities</h5>
                  <div className="space-y-2">
                    {day.activities.map((activity: any, actIndex: number) => (
                      <div key={actIndex} className="text-sm text-gray-700 bg-gray-50 p-2 rounded">
                        <span className="font-medium">{activity.name}</span>
                        {activity.duration_min && (
                          <span className="text-gray-500 ml-2">({Math.floor(activity.duration_min / 60)}h {activity.duration_min % 60}m)</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {day.food && day.food.length > 0 && (
                <div className="mb-4">
                  <h5 className="font-medium text-gray-800 mb-2">Food & Dining</h5>
                  <div className="space-y-2">
                    {day.food.map((food: any, foodIndex: number) => (
                      <div key={foodIndex} className="text-sm text-gray-700 bg-gray-50 p-2 rounded">
                        <span className="font-medium">{food.name}</span>
                        {food.tags && food.tags.length > 0 && (
                          <span className="text-gray-500 ml-2">({food.tags.join(', ')})</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {day.day_budget && (
                <div className="text-sm text-gray-600">
                  <span className="font-medium">Day Budget:</span> {plan.currency} {day.day_budget}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Status Banner */}
      <div className={`p-4 rounded-lg ${
        status === 'complete' ? 'bg-green-50 border border-green-200' :
        status === 'interrupt' ? 'bg-yellow-50 border border-yellow-200' :
        status === 'needs_follow_up' ? 'bg-blue-50 border border-blue-200' :
        'bg-gray-50 border border-gray-200'
      }`}>
        <div className="flex items-center">
          <div className={`w-3 h-3 rounded-full mr-3 ${
            status === 'complete' ? 'bg-green-500' :
            status === 'interrupt' ? 'bg-yellow-500' :
            status === 'needs_follow_up' ? 'bg-blue-500' :
            'bg-gray-500'
          }`}></div>
          <h2 className="text-lg font-semibold text-gray-900">
            {status === 'complete' ? 'Trip Planning Complete!' :
             status === 'interrupt' ? 'Please Make Selections' :
             status === 'needs_follow_up' ? 'Additional Research Needed' :
             'Planning in Progress'}
          </h2>
        </div>
        {status === 'interrupt' && (
          <p className="mt-2 text-sm text-gray-600">
            Please review and select your preferred options to continue planning.
          </p>
        )}
      </div>

      {/* Budget Estimate */}
      {estimated_budget && renderBudgetEstimate(estimated_budget)}

      {/* Recommendations */}
      {recommendations && renderRecommendations(recommendations)}

      {/* Final Plan */}
      {final_plan && renderFinalPlan(final_plan)}

      {/* Lodging Options */}
      {lodging && lodging.length > 0 && (
        <div>
          <h3 className="text-xl font-semibold text-gray-900 mb-4">🏨 Lodging Options</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {lodging.map((option) => renderCandidateCard(option, 'lodging'))}
          </div>
        </div>
      )}

      {/* Activities */}
      {activities && activities.length > 0 && (
        <div>
          <h3 className="text-xl font-semibold text-gray-900 mb-4">🎯 Activities</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {activities.map((activity) => renderCandidateCard(activity, 'activity'))}
          </div>
        </div>
      )}

      {/* Food Options */}
      {food && food.length > 0 && (
        <div>
          <h3 className="text-xl font-semibold text-gray-900 mb-4">🍽️ Food & Dining</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {food.map((option) => renderCandidateCard(option, 'food'))}
          </div>
        </div>
      )}

      {/* Transport Options */}
      {intercity_transport && intercity_transport.length > 0 && (
        <div>
          <h3 className="text-xl font-semibold text-gray-900 mb-4">🚌 Transport Options</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {intercity_transport.map((option) => renderCandidateCard(option, 'transport'))}
          </div>
        </div>
      )}

      {/* Messages */}
      {messages && messages.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Planning Log</h3>
          <div className="space-y-2">
            {messages.map((message, index) => (
              <div key={index} className="text-sm text-gray-700 bg-gray-50 p-2 rounded">
                {message}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default PlanningResults;

