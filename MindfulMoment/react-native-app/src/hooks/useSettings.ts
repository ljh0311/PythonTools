import { useState, useEffect } from 'react';
import { settingsManager, Settings } from '../utils/SettingsManager';

/**
 * Hook to use settings in React components
 * Automatically updates when settings change
 */
export function useSettings(): Settings {
  const [settings, setSettings] = useState<Settings>(settingsManager.getAll());

  useEffect(() => {
    const unsubscribe = settingsManager.addListener(setSettings);
    return unsubscribe;
  }, []);

  return settings;
}

/**
 * Hook to get a specific setting value
 * @param key - The setting key (supports dot notation)
 * @param defaultValue - Default value if setting doesn't exist
 */
export function useSetting<T>(key: string, defaultValue?: T): T {
  const [value, setValue] = useState<T>(() => {
    return settingsManager.get(key, defaultValue);
  });

  useEffect(() => {
    const unsubscribe = settingsManager.addListener(() => {
      const newValue = settingsManager.get(key, defaultValue);
      setValue(newValue);
    });
    return unsubscribe;
  }, [key, defaultValue]);

  return value;
}

/**
 * Hook to get theme setting
 */
export function useTheme(): Settings['theme'] {
  return useSetting<Settings['theme']>('theme', 'light');
}

/**
 * Hook to get notification settings
 */
export function useNotifications() {
  return useSetting('notifications', {
    enabled: true,
    reminders: true,
    sound: true,
  });
}

/**
 * Hook to get privacy settings
 */
export function usePrivacy() {
  return useSetting('privacy', {
    tracking: false,
    shareUsageStats: false,
    anonymousMode: true,
  });
}

/**
 * Hook to get focus session settings
 */
export function useFocusSession() {
  return useSetting('focusSession', {
    defaultDurationMinutes: 25,
    autoStartBreak: true,
    breakDurationMinutes: 5,
  });
}

/**
 * Hook to get accessibility settings
 */
export function useAccessibility() {
  return useSetting('accessibility', {
    fontSize: 'medium' as const,
    highContrast: false,
  });
}

/**
 * Hook to get community settings
 */
export function useCommunity() {
  return useSetting('community', {
    showLeaderboard: true,
    showChallenges: true,
    anonymousParticipation: true,
  });
}

/**
 * Hook to get insights settings
 */
export function useInsights() {
  return useSetting('insights', {
    showWeeklySummary: true,
    showMonthlySummary: true,
  });
}

/**
 * Hook to get language setting
 */
export function useLanguage(): string {
  return useSetting<string>('language', 'en');
}

/**
 * Hook to check if notifications are enabled
 */
export function useNotificationsEnabled(): boolean {
  return useSetting<boolean>('notifications.enabled', true);
}

/**
 * Hook to get focus session duration
 */
export function useFocusSessionDuration(): number {
  return useSetting<number>('focusSession.defaultDurationMinutes', 25);
}

/**
 * Hook to get break duration
 */
export function useBreakDuration(): number {
  return useSetting<number>('focusSession.breakDurationMinutes', 5);
}

/**
 * Hook to check if tracking is enabled
 */
export function useTrackingEnabled(): boolean {
  return useSetting<boolean>('privacy.tracking', false);
}

/**
 * Hook to check if anonymous mode is enabled
 */
export function useAnonymousMode(): boolean {
  return useSetting<boolean>('privacy.anonymousMode', true);
}

/**
 * Hook to get font size setting
 */
export function useFontSize(): Settings['accessibility']['fontSize'] {
  return useSetting<Settings['accessibility']['fontSize']>('accessibility.fontSize', 'medium');
}

/**
 * Hook to check if high contrast is enabled
 */
export function useHighContrast(): boolean {
  return useSetting<boolean>('accessibility.highContrast', false);
} 