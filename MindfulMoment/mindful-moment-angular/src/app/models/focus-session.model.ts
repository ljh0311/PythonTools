export interface FocusSession {
  id: string;
  userId: string;
  startTime: string;
  endTime?: string;
  duration: number; // in minutes
  location: SessionLocation;
  type: SessionType;
  status: SessionStatus;
  goals: SessionGoal[];
  achievements: string[];
  /** User-written summary of what they accomplished in this session */
  accomplishments?: string;
  notes?: string;
  moodBefore?: number; // 1-10 scale
  moodAfter?: number; // 1-10 scale
  distractions: Distraction[];
  /** AI-generated evaluation of the session (what happened, impact, improvements) */
  llmEvaluation?: SessionLLMEvaluation;
  socialInteractions: SocialInteraction[];
  phoneUsageReduction: number; // in minutes
  mindfulMoments: MindfulMoment[];
  createdAt: string;
  updatedAt: string;
  // Type-specific metrics
  typeMetrics?: TypeSpecificMetrics;
}

export interface TypeSpecificMetrics {
  // Walking metrics
  steps?: number;
  distance?: number; // in meters
  
  // Breathing metrics
  breathingRate?: number; // breaths per minute
  breathingPattern?: string; // e.g., "4-7-8", "box breathing"
  breathingCycles?: number;
  
  // Meditation metrics
  meditationDepth?: number; // 1-10 scale
  focusClarity?: number; // 1-10 scale
  
  // Mindfulness metrics
  awarenessLevel?: number; // 1-10 scale
  presentMomentScore?: number; // 1-10 scale
  
  // Focus metrics
  distractionCount?: number;
  focusIntensity?: number; // 1-10 scale
  tasksCompleted?: number;

  // Study metrics
  studyMinutes?: number;
  topicsCovered?: number;

  // Travel safety metrics (device usage near road/MRT platform etc.)
  safeZoneMinutes?: number; // minutes with device put away in risk zones
  alertsAcknowledged?: number;
}

export interface SessionLocation {
  type: LocationType;
  name: string;
  address?: string;
  coordinates?: {
    latitude: number;
    longitude: number;
  };
  environment: EnvironmentType;
}

export interface SessionGoal {
  id: string;
  description: string;
  completed: boolean;
  category: GoalCategory;
}

export interface Distraction {
  id: string;
  type: DistractionType;
  /** What distracted the user (e.g. "Phone notification", "Noise from hallway") */
  description: string;
  duration: number; // in minutes
  timestamp: string;
  handled: boolean;
}

export interface SessionLLMEvaluation {
  summary?: string;
  whatHappened?: string;
  impactOnUser?: string;
  whatCanBeImproved?: string;
  whatWasImproved?: string;
  generatedAt?: string;
}

export interface SocialInteraction {
  id: string;
  type: InteractionType;
  description: string;
  duration: number; // in minutes
  timestamp: string;
  positive: boolean;
}

export interface MindfulMoment {
  id: string;
  type: MindfulMomentType;
  description: string;
  timestamp: string;
  duration: number; // in minutes
  impact: number; // 1-10 scale
}

export enum SessionType {
  FOCUS = 'focus',
  MINDFULNESS = 'mindfulness',
  MEDITATION = 'meditation',
  BREATHING = 'breathing',
  WALKING = 'walking',
  STUDY = 'study',
  TRAVEL_SAFETY = 'travel-safety'
}

export enum SessionStatus {
  ACTIVE = 'active',
  COMPLETED = 'completed',
  PAUSED = 'paused',
  CANCELLED = 'cancelled'
}

export enum LocationType {
  HOME = 'home',
  PUBLIC = 'public',
  WORK = 'work',
  TRANSPORT = 'transport',
  OUTDOOR = 'outdoor'
}

export enum EnvironmentType {
  QUIET = 'quiet',
  NOISY = 'noisy',
  CROWDED = 'crowded',
  NATURAL = 'natural',
  URBAN = 'urban'
}

export enum GoalCategory {
  FOCUS = 'focus',
  MINDFULNESS = 'mindfulness',
  SOCIAL = 'social',
  WELLNESS = 'wellness',
  PRODUCTIVITY = 'productivity'
}

export enum DistractionType {
  PHONE = 'phone',
  NOISE = 'noise',
  PEOPLE = 'people',
  THOUGHTS = 'thoughts',
  ENVIRONMENT = 'environment'
}

export enum InteractionType {
  CONVERSATION = 'conversation',
  HELP = 'help',
  SHARING = 'sharing',
  LEARNING = 'learning',
  SUPPORT = 'support'
}

export enum MindfulMomentType {
  BREATHING = 'breathing',
  OBSERVATION = 'observation',
  GRATITUDE = 'gratitude',
  AWARENESS = 'awareness',
  CONNECTION = 'connection'
}
