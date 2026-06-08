import AsyncStorage from '@react-native-async-storage/async-storage';

export interface Settings {
  theme: 'light' | 'dark' | 'system';
  notifications: {
    enabled: boolean;
    reminders: boolean;
    sound: boolean;
  };
  privacy: {
    tracking: boolean;
    shareUsageStats: boolean;
    anonymousMode: boolean;
  };
  focusSession: {
    defaultDurationMinutes: number;
    autoStartBreak: boolean;
    breakDurationMinutes: number;
  };
  insights: {
    showWeeklySummary: boolean;
    showMonthlySummary: boolean;
  };
  community: {
    showLeaderboard: boolean;
    showChallenges: boolean;
    anonymousParticipation: boolean;
  };
  language: string;
  accessibility: {
    fontSize: 'small' | 'medium' | 'large';
    highContrast: boolean;
  };
}

const DEFAULT_SETTINGS: Settings = {
  theme: 'light',
  notifications: {
    enabled: true,
    reminders: true,
    sound: true,
  },
  privacy: {
    tracking: false,
    shareUsageStats: false,
    anonymousMode: true,
  },
  focusSession: {
    defaultDurationMinutes: 25,
    autoStartBreak: true,
    breakDurationMinutes: 5,
  },
  insights: {
    showWeeklySummary: true,
    showMonthlySummary: true,
  },
  community: {
    showLeaderboard: true,
    showChallenges: true,
    anonymousParticipation: true,
  },
  language: 'en',
  accessibility: {
    fontSize: 'medium',
    highContrast: false,
  },
};

const SETTINGS_STORAGE_KEY = '@MindfulMoment:settings';

class SettingsManager {
  private settings: Settings = DEFAULT_SETTINGS;
  private listeners: Array<(settings: Settings) => void> = [];

  constructor() {
    this.loadSettings();
  }

  /**
   * Load settings from AsyncStorage
   */
  async loadSettings(): Promise<Settings> {
    try {
      const storedSettings = await AsyncStorage.getItem(SETTINGS_STORAGE_KEY);
      if (storedSettings) {
        const parsedSettings = JSON.parse(storedSettings);
        this.settings = { ...DEFAULT_SETTINGS, ...parsedSettings };
      } else {
        this.settings = { ...DEFAULT_SETTINGS };
        await this.saveSettings();
      }
      this.notifyListeners();
      return this.settings;
    } catch (error) {
      console.error('Error loading settings:', error);
      this.settings = { ...DEFAULT_SETTINGS };
      return this.settings;
    }
  }

  /**
   * Save settings to AsyncStorage
   */
  async saveSettings(): Promise<boolean> {
    try {
      await AsyncStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(this.settings));
      this.notifyListeners();
      return true;
    } catch (error) {
      console.error('Error saving settings:', error);
      return false;
    }
  }

  /**
   * Get a setting value using dot notation
   */
  get<K extends keyof Settings>(key: K): Settings[K];
  get<K extends keyof Settings, S extends Settings[K]>(key: K, defaultValue: S): S;
  get(key: string, defaultValue?: any): any {
    const keys = key.split('.');
    let value: any = this.settings;
    
    for (const k of keys) {
      if (value && typeof value === 'object' && k in value) {
        value = value[k];
      } else {
        return defaultValue;
      }
    }
    
    return value;
  }

  /**
   * Set a setting value using dot notation
   */
  async set<K extends keyof Settings>(key: K, value: Settings[K]): Promise<boolean>;
  async set(key: string, value: any): Promise<boolean> {
    const keys = key.split('.');
    let current: any = this.settings;
    
    for (let i = 0; i < keys.length - 1; i++) {
      if (!current[keys[i]]) {
        current[keys[i]] = {};
      }
      current = current[keys[i]];
    }
    
    current[keys[keys.length - 1]] = value;
    return await this.saveSettings();
  }

  /**
   * Update multiple settings at once
   */
  async updateMultiple(updates: Partial<Settings>): Promise<boolean> {
    this.settings = { ...this.settings, ...updates };
    return await this.saveSettings();
  }

  /**
   * Reset settings to defaults
   */
  async resetToDefaults(): Promise<boolean> {
    this.settings = { ...DEFAULT_SETTINGS };
    return await this.saveSettings();
  }

  /**
   * Get all settings
   */
  getAll(): Settings {
    return { ...this.settings };
  }

  /**
   * Add a listener for settings changes
   */
  addListener(listener: (settings: Settings) => void): () => void {
    this.listeners.push(listener);
    return () => {
      const index = this.listeners.indexOf(listener);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }

  /**
   * Notify all listeners of settings changes
   */
  private notifyListeners(): void {
    this.listeners.forEach(listener => listener(this.settings));
  }

  /**
   * Export settings as JSON string
   */
  exportSettings(): string {
    return JSON.stringify(this.settings, null, 2);
  }

  /**
   * Import settings from JSON string
   */
  async importSettings(jsonString: string): Promise<boolean> {
    try {
      const importedSettings = JSON.parse(jsonString);
      return await this.updateMultiple(importedSettings);
    } catch (error) {
      console.error('Error importing settings:', error);
      return false;
    }
  }

  // Convenience methods for common settings
  getTheme(): Settings['theme'] {
    return this.get('theme');
  }

  setTheme(theme: Settings['theme']): Promise<boolean> {
    return this.set('theme', theme);
  }

  areNotificationsEnabled(): boolean {
    return this.get('notifications.enabled');
  }

  getFocusSessionDuration(): number {
    return this.get('focusSession.defaultDurationMinutes');
  }

  getBreakDuration(): number {
    return this.get('focusSession.breakDurationMinutes');
  }

  isTrackingEnabled(): boolean {
    return this.get('privacy.tracking');
  }

  isAnonymousMode(): boolean {
    return this.get('privacy.anonymousMode');
  }

  getFontSize(): Settings['accessibility']['fontSize'] {
    return this.get('accessibility.fontSize');
  }

  isHighContrast(): boolean {
    return this.get('accessibility.highContrast');
  }

  getLanguage(): string {
    return this.get('language');
  }
}

// Create singleton instance
export const settingsManager = new SettingsManager();

// Export types
export type { Settings };
export { DEFAULT_SETTINGS }; 