export interface Achievement {
  id: string;
  name: string;
  description: string;
  category: AchievementCategory;
  icon: string;
  color: string;
  points: number;
  requirements: AchievementRequirement[];
  progress: number; // 0-100
  isCompleted: boolean;
  completedDate?: string;
  rarity: AchievementRarity;
  tags: string[];
  prerequisites?: string[]; // IDs of required achievements
}

export interface AchievementRequirement {
  id: string;
  type: RequirementType;
  description: string;
  target: number;
  current: number;
  unit: string;
  isCompleted: boolean;
}

export enum AchievementCategory {
  FOCUS = 'focus',
  MINDFULNESS = 'mindfulness',
  SOCIAL = 'social',
  SAFETY = 'safety',
  WELLNESS = 'wellness',
  COMMUNITY = 'community',
  LEARNING = 'learning',
  MILESTONE = 'milestone'
}

export enum RequirementType {
  SESSIONS = 'sessions',
  DURATION = 'duration',
  INTERACTIONS = 'interactions',
  POINTS = 'points',
  STREAK = 'streak',
  LOCATIONS = 'locations',
  EVENTS = 'events',
  CHALLENGES = 'challenges'
}

export enum AchievementRarity {
  COMMON = 'common',
  UNCOMMON = 'uncommon',
  RARE = 'rare',
  EPIC = 'epic',
  LEGENDARY = 'legendary'
}
