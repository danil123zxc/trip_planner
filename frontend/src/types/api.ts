// API Types matching the backend models

export interface Traveller {
  name: string;
  date_of_birth: string; // ISO date string
  spoken_languages?: string[];
  interests?: string[];
  nationality?: string;
  notes?: string;
}

export interface Context {
  travellers: Traveller[];
  budget: number;
  currency: string;
  destination: string;
  destination_country: string;
  date_from: string; // ISO date string
  date_to: string; // ISO date string
  group_type: 'family' | 'couple' | 'alone' | 'friends' | 'business';
  trip_purpose?: string;
  current_location?: string;
  notes?: string;
}

export interface PlanRequest {
  context: Context;
}

export interface CandidateBase {
  id?: string;
  name: string;
  address?: string;
  price_level?: '$' | '$$' | '$$$' | '$$$$';
  rating?: number;
  reviews?: string[];
  photos?: string[];
  url?: string;
  lat?: number;
  lon?: number;
  evidence_score?: number;
  source_id?: string;
  notes?: string;
}

export interface CandidateLodging extends CandidateBase {
  area?: string;
  price_night?: number;
  cancel_policy?: string;
}

export interface CandidateActivity extends CandidateBase {
  open_time?: string;
  close_time?: string;
  duration_min?: number;
  price?: number;
  tags?: string[];
}

export interface CandidateFood extends CandidateBase {
  open_time?: string;
  close_time?: string;
  tags?: string[];
}

export interface Transfer {
  name: string;
  place: string;
  departure_time?: string;
  arrival_time?: string;
  duration_min?: number;
}

export interface CandidateIntercityTransport {
  name: string;
  fare_class?: string;
  refundable?: boolean;
  url?: string;
  price?: number;
  transfer?: Transfer[];
  total_duration_min?: number;
  note?: string;
}

export interface BudgetEstimate {
  budget_level?: '$' | '$$' | '$$$' | '$$$$';
  currency: string;
  intercity_transport: number;
  local_transport: number;
  food: number;
  activities: number;
  lodging: number;
  other: number;
  budget_per_day: number;
  notes?: string;
  total: number;
}

export interface CandidateResearch {
  name?: string;
  description?: string;
  candidates_number?: number;
}

export interface ResearchPlan {
  lodging_candidates?: CandidateResearch;
  activities_candidates?: CandidateResearch;
  food_candidates?: CandidateResearch;
  intercity_transport_candidates?: CandidateResearch;
  local_transport_candidates?: CandidateResearch;
}

export interface RecommendationsOutput {
  safety_level: 'very_safe' | 'safe' | 'moderate' | 'risky' | 'dangerous';
  safety_notes?: string[];
  travel_advisories?: string[];
  visa_requirements?: Record<string, string>;
  cultural_considerations?: string[];
  dress_code_recommendations?: string[];
  local_customs?: string[];
  language_barriers?: string[];
  child_friendly_rating: number;
  infant_considerations?: string[];
  elderly_accessibility?: string[];
  weather_conditions?: string;
  seasonal_considerations?: string[];
  best_time_to_visit?: string;
  currency_info?: string;
  payment_methods?: string[];
  religious_restrictions?: string[];
  dietary_restrictions_support?: Record<string, boolean>;
}

export interface PlanForDay {
  day_number: number;
  day_date: string;
  activities: CandidateActivity[];
  food: CandidateFood[];
  intracity_moves: any[];
  day_budget: number;
  start_time?: string;
  end_time?: string;
  notes?: string;
}

export interface FinalPlan {
  days?: PlanForDay[];
  total_budget?: number;
  lodging?: CandidateLodging;
  intercity_transport?: CandidateIntercityTransport;
  currency?: string;
  research_plan?: ResearchPlan;
}

export interface PlanningResponse {
  status: 'interrupt' | 'complete' | 'needs_follow_up' | 'no_plan';
  config?: Record<string, any>;
  estimated_budget?: BudgetEstimate;
  research_plan?: ResearchPlan;
  lodging?: CandidateLodging[];
  activities?: CandidateActivity[];
  food?: CandidateFood[];
  intercity_transport?: CandidateIntercityTransport[];
  recommendations?: RecommendationsOutput;
  final_plan?: FinalPlan;
  interrupt?: Record<string, any>;
  messages: string[];
}

export interface ResumeSelections {
  lodging?: CandidateLodging;
  intercity_transport?: CandidateIntercityTransport;
  activities?: CandidateActivity[];
  food?: CandidateFood[];
}

export interface ResumeRequest {
  config?: Record<string, any>;
  selections: ResumeSelections;
  research_plan?: Record<string, CandidateResearch>;
}

// Form types for the frontend
export interface TripFormData {
  destination: string;
  destination_country: string;
  date_from: string;
  date_to: string;
  budget: number;
  currency: string;
  group_type: 'family' | 'couple' | 'alone' | 'friends' | 'business';
  trip_purpose?: string;
  current_location?: string;
  travellers: Traveller[];
}

export interface PlanningState {
  status: 'idle' | 'loading' | 'success' | 'error';
  data?: PlanningResponse;
  error?: string;
}

