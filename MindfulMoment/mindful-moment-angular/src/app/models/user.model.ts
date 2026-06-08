export type UserRole = 'developer' | 'admin' | 'user';

export interface User {
  id: string;
  email: string;
  username: string;
  firstName: string;
  lastName: string;
  dateOfBirth?: string;
  phone?: string;
  community: string;
  preferences: UserPreferences;
  stats: UserStats;
  achievements: string[];
  badges: Badge[];
  points: number;
  level: number;
  homeSettings: HomeSettings;
  publicAwarenessSettings: PublicAwarenessSettings;
  permissions?: string[];
  role?: UserRole;
  joinDate: string;
  lastActive: string;
}

export interface UserPreferences {
  language: string;
  alertFrequency: number;
  primaryGoal: string;
  notifications: boolean;
  location: boolean;
  screenTime: boolean;
  focusMode: boolean;
  theme: string;
  accessibility: AccessibilitySettings;
  // Detailed notification settings
  notificationSettings?: {
    enabled: boolean;
    mindfulNudges: boolean;
    safetyReminders: boolean;
    focusSessionAlerts: boolean;
    communityUpdates: boolean;
    quietHours: {
      enabled: boolean;
      start: string;
      end: string;
    };
  };
  // Privacy settings
  privacySettings?: {
    tracking: boolean;
    shareUsageStats: boolean;
    anonymousMode: boolean;
    dataRetention: string;
  };
}

export interface AccessibilitySettings {
  highContrast: boolean;
  largeText: boolean;
  screenReader: boolean;
}

export interface UserStats {
  totalSessions: number;
  totalMindfulMinutes: number;
  totalSafetyAlerts: number;
  totalSocialEngagements: number;
  joinDate: string;
  lastActive: string;
  focusSessionStats: FocusSessionStats;
  publicAwarenessStats: PublicAwarenessStats;
}

export interface FocusSessionStats {
  totalPublicFocusTime: number;
  totalSocialInteractions: number;
  phoneUsageReduction: number;
  mindfulMoments: number;
}

export interface PublicAwarenessStats {
  totalPublicTime: number;
  safetyAlerts: number;
  socialPrompts: number;
  mindfulScore: number;
}

export interface Badge {
  id: string;
  name: string;
  description: string;
  icon: string;
  earnedDate: string;
  category: string;
}

export interface HomeSettings {
  wifiNetworks: string[];
  location: LocationData | null;
  isConfigured: boolean;
}

export interface PublicAwarenessSettings {
  isEnabled: boolean;
  alertFrequency: number;
  socialPrompts: boolean;
  safetyAlerts: boolean;
}

export interface LocationData {
  latitude: number;
  longitude: number;
  address: string;
  city: string;
  country: string;
}
