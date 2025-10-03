import React, { useState } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { TripFormData, Traveller } from '../types/api';

interface TripFormProps {
  onSubmit: (data: TripFormData) => void;
  isLoading?: boolean;
}

const TripForm: React.FC<TripFormProps> = ({ onSubmit, isLoading = false }) => {
  const { register, control, handleSubmit, formState: { errors } } = useForm<TripFormData>({
    defaultValues: {
      destination: '',
      destination_country: '',
      date_from: '',
      date_to: '',
      budget: 1000,
      currency: 'USD',
      group_type: 'alone',
      trip_purpose: '',
      current_location: '',
      travellers: [
        {
          name: '',
          date_of_birth: '',
          spoken_languages: ['english'],
          interests: [],
          nationality: '',
        }
      ]
    }
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'travellers'
  });

  const [travellerLanguages, setTravellerLanguages] = useState<Record<number, string[]>>({});
  const [travellerInterests, setTravellerInterests] = useState<Record<number, string[]>>({});

  const addLanguage = (travellerIndex: number, language: string) => {
    if (!language.trim()) return;
    const current = travellerLanguages[travellerIndex] || [];
    if (!current.includes(language)) {
      setTravellerLanguages(prev => ({
        ...prev,
        [travellerIndex]: [...current, language]
      }));
    }
  };

  const removeLanguage = (travellerIndex: number, language: string) => {
    setTravellerLanguages(prev => ({
      ...prev,
      [travellerIndex]: (prev[travellerIndex] || []).filter(l => l !== language)
    }));
  };

  const addInterest = (travellerIndex: number, interest: string) => {
    if (!interest.trim()) return;
    const current = travellerInterests[travellerIndex] || [];
    if (!current.includes(interest)) {
      setTravellerInterests(prev => ({
        ...prev,
        [travellerIndex]: [...current, interest]
      }));
    }
  };

  const removeInterest = (travellerIndex: number, interest: string) => {
    setTravellerInterests(prev => ({
      ...prev,
      [travellerIndex]: (prev[travellerIndex] || []).filter(i => i !== interest)
    }));
  };

  const onFormSubmit = (data: TripFormData) => {
    // Add the dynamic languages and interests to the form data
    const enrichedData = {
      ...data,
      travellers: data.travellers.map((traveller, index) => ({
        ...traveller,
        spoken_languages: travellerLanguages[index] || ['english'],
        interests: travellerInterests[index] || []
      }))
    };
    onSubmit(enrichedData);
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="card">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Plan Your Trip</h2>
        
        <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-6">
          {/* Destination Section */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="form-label">Destination</label>
              <input
                {...register('destination', { required: 'Destination is required' })}
                className="form-input"
                placeholder="e.g., Tokyo"
              />
              {errors.destination && (
                <p className="mt-1 text-sm text-red-600">{errors.destination.message}</p>
              )}
            </div>
            
            <div>
              <label className="form-label">Country</label>
              <input
                {...register('destination_country', { required: 'Country is required' })}
                className="form-input"
                placeholder="e.g., Japan"
              />
              {errors.destination_country && (
                <p className="mt-1 text-sm text-red-600">{errors.destination_country.message}</p>
              )}
            </div>
          </div>

          {/* Dates Section */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="form-label">Start Date</label>
              <input
                {...register('date_from', { required: 'Start date is required' })}
                type="date"
                className="form-input"
              />
              {errors.date_from && (
                <p className="mt-1 text-sm text-red-600">{errors.date_from.message}</p>
              )}
            </div>
            
            <div>
              <label className="form-label">End Date</label>
              <input
                {...register('date_to', { required: 'End date is required' })}
                type="date"
                className="form-input"
              />
              {errors.date_to && (
                <p className="mt-1 text-sm text-red-600">{errors.date_to.message}</p>
              )}
            </div>
          </div>

          {/* Budget Section */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="form-label">Budget</label>
              <input
                {...register('budget', { 
                  required: 'Budget is required',
                  min: { value: 1, message: 'Budget must be at least 1' }
                })}
                type="number"
                className="form-input"
                placeholder="1000"
              />
              {errors.budget && (
                <p className="mt-1 text-sm text-red-600">{errors.budget.message}</p>
              )}
            </div>
            
            <div>
              <label className="form-label">Currency</label>
              <select {...register('currency')} className="form-input">
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
                <option value="GBP">GBP</option>
                <option value="JPY">JPY</option>
                <option value="CAD">CAD</option>
                <option value="AUD">AUD</option>
              </select>
            </div>
          </div>

          {/* Trip Details */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="form-label">Group Type</label>
              <select {...register('group_type')} className="form-input">
                <option value="alone">Solo Travel</option>
                <option value="couple">Couple</option>
                <option value="family">Family</option>
                <option value="friends">Friends</option>
                <option value="business">Business</option>
              </select>
            </div>
            
            <div>
              <label className="form-label">Current Location</label>
              <input
                {...register('current_location')}
                className="form-input"
                placeholder="e.g., New York"
              />
            </div>
          </div>

          <div>
            <label className="form-label">Trip Purpose</label>
            <input
              {...register('trip_purpose')}
              className="form-input"
              placeholder="e.g., cultural experience, relaxation, adventure"
            />
          </div>

          {/* Travellers Section */}
          <div>
            <div className="flex justify-between items-center mb-4">
              <label className="form-label mb-0">Travellers</label>
              <button
                type="button"
                onClick={() => append({
                  name: '',
                  date_of_birth: '',
                  spoken_languages: ['english'],
                  interests: [],
                  nationality: '',
                })}
                className="btn-secondary text-sm"
              >
                Add Traveller
              </button>
            </div>

            {fields.map((field, index) => (
              <div key={field.id} className="border border-gray-200 rounded-lg p-4 mb-4">
                <div className="flex justify-between items-center mb-4">
                  <h4 className="font-medium text-gray-900">Traveller {index + 1}</h4>
                  {fields.length > 1 && (
                    <button
                      type="button"
                      onClick={() => remove(index)}
                      className="text-red-600 hover:text-red-800 text-sm"
                    >
                      Remove
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="form-label">Name</label>
                    <input
                      {...register(`travellers.${index}.name`, { required: 'Name is required' })}
                      className="form-input"
                      placeholder="Full name"
                    />
                    {errors.travellers?.[index]?.name && (
                      <p className="mt-1 text-sm text-red-600">{errors.travellers[index]?.name?.message}</p>
                    )}
                  </div>

                  <div>
                    <label className="form-label">Date of Birth</label>
                    <input
                      {...register(`travellers.${index}.date_of_birth`, { required: 'Date of birth is required' })}
                      type="date"
                      className="form-input"
                    />
                    {errors.travellers?.[index]?.date_of_birth && (
                      <p className="mt-1 text-sm text-red-600">{errors.travellers[index]?.date_of_birth?.message}</p>
                    )}
                  </div>

                  <div>
                    <label className="form-label">Nationality</label>
                    <input
                      {...register(`travellers.${index}.nationality`)}
                      className="form-input"
                      placeholder="e.g., American"
                    />
                  </div>
                </div>

                {/* Languages */}
                <div className="mt-4">
                  <label className="form-label">Spoken Languages</label>
                  <div className="flex flex-wrap gap-2 mb-2">
                    {(travellerLanguages[index] || ['english']).map((lang, langIndex) => (
                      <span
                        key={langIndex}
                        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800"
                      >
                        {lang}
                        <button
                          type="button"
                          onClick={() => removeLanguage(index, lang)}
                          className="ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full text-primary-400 hover:bg-primary-200 hover:text-primary-500"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Add language"
                      className="form-input flex-1"
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          addLanguage(index, e.currentTarget.value);
                          e.currentTarget.value = '';
                        }
                      }}
                    />
                  </div>
                </div>

                {/* Interests */}
                <div className="mt-4">
                  <label className="form-label">Interests</label>
                  <div className="flex flex-wrap gap-2 mb-2">
                    {(travellerInterests[index] || []).map((interest, interestIndex) => (
                      <span
                        key={interestIndex}
                        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"
                      >
                        {interest}
                        <button
                          type="button"
                          onClick={() => removeInterest(index, interest)}
                          className="ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full text-green-400 hover:bg-green-200 hover:text-green-500"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Add interest"
                      className="form-input flex-1"
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          addInterest(index, e.currentTarget.value);
                          e.currentTarget.value = '';
                        }
                      }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Submit Button */}
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Planning...' : 'Start Planning'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default TripForm;

