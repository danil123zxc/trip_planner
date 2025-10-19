import React, { useEffect, useMemo, useState } from 'react';
import { CandidateResearch, ResearchPlan } from '../types/api';

type CandidateKey = keyof ResearchPlan;

interface CandidateSection {
  key: CandidateKey;
  label: string;
  helper: string;
}

interface CandidateFieldState {
  enabled: boolean;
  name: string;
  description: string;
  candidates_number: number | '';
}

type PlanFormState = Record<CandidateKey, CandidateFieldState>;

const candidateSections: CandidateSection[] = [
  {
    key: 'lodging_candidates',
    label: 'Lodging Research',
    helper: 'Describe the type of accommodation and specify how many alternatives you want to review.',
  },
  {
    key: 'activities_candidates',
    label: 'Activities Research',
    helper: 'List the experiences you want covered and the number of suggestions to collect.',
  },
  {
    key: 'food_candidates',
    label: 'Food & Dining Research',
    helper: 'Outline cuisine preferences or dietary needs and the number of venues to gather.',
  },
  {
    key: 'intercity_transport_candidates',
    label: 'Intercity Transport Research',
    helper: 'Specify transport modes, budget, timing needs, and how many routes to investigate.',
  },
];

const buildInitialState = (plan?: ResearchPlan | null): PlanFormState => {
  const state = {} as PlanFormState;

  candidateSections.forEach(({ key }) => {
    const details = plan?.[key];
    state[key] = {
      enabled: Boolean(details),
      name: details?.name ?? '',
      description: details?.description ?? '',
      candidates_number:
        typeof details?.candidates_number === 'number' && !Number.isNaN(details.candidates_number)
          ? details.candidates_number
          : '',
    };
  });

  return state;
};

const toCandidateResearch = (field: CandidateFieldState): CandidateResearch | undefined => {
  if (!field.enabled) {
    return undefined;
  }

  const payload: CandidateResearch = {};
  const trimmedName = field.name.trim();
  const trimmedDescription = field.description.trim();

  if (trimmedName) {
    payload.name = trimmedName;
  }
  if (trimmedDescription) {
    payload.description = trimmedDescription;
  }
  if (typeof field.candidates_number === 'number' && Number.isFinite(field.candidates_number)) {
    payload.candidates_number = field.candidates_number;
  }

  if (!Object.keys(payload).length) {
    return undefined;
  }

  return payload;
};

const hasEnabledCategory = (plan: PlanFormState): boolean =>
  candidateSections.some(({ key }) => plan[key].enabled);

interface ResearchPlanFormProps {
  initialPlan?: ResearchPlan | null;
  onSubmit: (plan: ResearchPlan) => Promise<void> | void;
  isSubmitting?: boolean;
}

const ResearchPlanForm: React.FC<ResearchPlanFormProps> = ({
  initialPlan,
  onSubmit,
  isSubmitting = false,
}) => {
  const [formState, setFormState] = useState<PlanFormState>(() => buildInitialState(initialPlan));

  useEffect(() => {
    setFormState(buildInitialState(initialPlan));
  }, [initialPlan]);

  const handleToggle = (key: CandidateKey) => {
    setFormState((prev) => ({
      ...prev,
      [key]: {
        ...prev[key],
        enabled: !prev[key].enabled,
      },
    }));
  };

  const handleFieldChange =
    (key: CandidateKey, field: keyof CandidateFieldState) =>
    (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const value = event.target.value;

      setFormState((prev) => ({
        ...prev,
        [key]: {
          ...prev[key],
          [field]:
            field === 'candidates_number'
              ? value === ''
                ? ''
                : Math.max(1, Number.parseInt(value, 10) || 1)
              : value,
        },
      }));
    };

  const resetToInitial = () => {
    setFormState(buildInitialState(initialPlan));
  };

  const submitDisabled = useMemo(
    () => !hasEnabledCategory(formState) || isSubmitting,
    [formState, isSubmitting],
  );

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submitDisabled) {
      return;
    }

    const payload: ResearchPlan = {};

    candidateSections.forEach(({ key }) => {
      const candidate = toCandidateResearch(formState[key]);
      if (candidate) {
        payload[key] = candidate;
      }
    });

    await onSubmit(payload);
  };

  return (
    <form onSubmit={handleSubmit} className="card space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">Tune Extra Research</h3>
        <p className="text-sm text-gray-600 mt-1">
          Select the categories that need deeper research and describe the focus for the next pass.
          Adjust candidate counts to control how many new options each agent should find.
        </p>
      </div>

      <div className="space-y-5">
        {candidateSections.map(({ key, label, helper }) => {
          const field = formState[key];
          return (
            <div key={key} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center space-x-3">
                    <label className="text-base font-medium text-gray-900" htmlFor={`${key}-toggle`}>
                      {label}
                    </label>
                    <input
                      id={`${key}-toggle`}
                      type="checkbox"
                      className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                      checked={field.enabled}
                      onChange={() => handleToggle(key)}
                    />
                    <span className="text-sm text-gray-600">
                      {field.enabled ? 'Included' : 'Skip this category'}
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 mt-1">{helper}</p>
                </div>
              </div>

              {field.enabled && (
                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700" htmlFor={`${key}-name`}>
                      Research Focus Title
                    </label>
                    <input
                      id={`${key}-name`}
                      type="text"
                      value={field.name}
                      onChange={handleFieldChange(key, 'name')}
                      placeholder="e.g. Boutique hotels near the river"
                      className="input"
                    />
                  </div>

                  <div className="space-y-2">
                    <label
                      className="block text-sm font-medium text-gray-700"
                      htmlFor={`${key}-candidates`}
                    >
                      Number of Candidates
                    </label>
                    <input
                      id={`${key}-candidates`}
                      type="number"
                      min={1}
                      value={field.candidates_number}
                      onChange={handleFieldChange(key, 'candidates_number')}
                      className="input"
                    />
                  </div>

                  <div className="md:col-span-2 space-y-2">
                    <label
                      className="block text-sm font-medium text-gray-700"
                      htmlFor={`${key}-description`}
                    >
                      Detailed Instructions
                    </label>
                    <textarea
                      id={`${key}-description`}
                      value={field.description}
                      onChange={handleFieldChange(key, 'description')}
                      placeholder="Key preferences, budget hints, locations, or constraints."
                      rows={3}
                      className="input resize-y"
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-3 md:space-y-0">
        <div className="text-sm text-gray-600">
          <p>
            Tip: enable only the areas that still feel under-researched. Leave disabled sections
            untouched to use the current recommendations.
          </p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            type="button"
            onClick={resetToInitial}
            className="btn-secondary"
            disabled={isSubmitting}
          >
            Reset
          </button>
          <button
            type="submit"
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={submitDisabled}
          >
            {isSubmitting ? 'Requesting…' : 'Request Extra Research'}
          </button>
        </div>
      </div>
    </form>
  );
};

export default ResearchPlanForm;
