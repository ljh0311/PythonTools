import AsyncStorage from '@react-native-async-storage/async-storage';
import { notificationService } from './NotificationService';
import { locationService } from './LocationService';

export interface FocusSession {
  id: string;
  duration: number; // minutes
  startTime: Date;
  endTime?: Date;
  isActive: boolean;
  category: 'commute' | 'social' | 'work' | 'exercise' | 'custom';
  blockedApps: string[];
  location?: {
    zoneId: string;
    zoneName: string;
  };
  mindfulMinutes: number;
  completed: boolean;
  interrupted: boolean;
  interruptionReason?: string;
}

export interface FocusSessionSettings {
  defaultDuration: number;
  defaultCategory: string;
  blockedAppCategories: {
    social: string[];
    entertainment: string[];
    games: string[];
    news: string[];
  };
  autoStartInPublic: boolean;
  reminderFrequency: number; // minutes
  soundEnabled: boolean;
  vibrationEnabled: boolean;
}

export interface FocusSessionStats {
  totalSessions: number;
  totalMindfulMinutes: number;
  averageSessionLength: number;
  completionRate: number;
  longestStreak: number;
  currentStreak: number;
  sessionsByCategory: Record<string, number>;
  sessionsByLocation: Record<string, number>;
}

class FocusSessionService {
  private sessions: FocusSession[] = [];
  private currentSession: FocusSession | null = null;
  private settings: FocusSessionSettings;
  private sessionTimer: NodeJS.Timeout | null = null;
  private reminderTimer: NodeJS.Timeout | null = null;

  constructor() {
    this.settings = {
      defaultDuration: 15,
      defaultCategory: 'commute',
      blockedAppCategories: {
        social: ['facebook', 'instagram', 'twitter', 'tiktok', 'snapchat'],
        entertainment: ['youtube', 'netflix', 'spotify', 'twitch'],
        games: ['candycrush', 'pokemongo', 'clashofclans', 'minecraft'],
        news: ['reddit', 'news', 'buzzfeed', 'vice'],
      },
      autoStartInPublic: false,
      reminderFrequency: 30,
      soundEnabled: true,
      vibrationEnabled: true,
    };
  }

  async initialize(): Promise<void> {
    await this.loadSessions();
    await this.loadSettings();
  }

  async startSession(
    duration: number,
    category: string,
    blockedApps: string[] = []
  ): Promise<FocusSession> {
    // End any existing session
    if (this.currentSession) {
      await this.endSession();
    }

    const session: FocusSession = {
      id: `session_${Date.now()}`,
      duration,
      startTime: new Date(),
      isActive: true,
      category: category as any,
      blockedApps: blockedApps.length > 0 ? blockedApps : this.getDefaultBlockedApps(category),
      mindfulMinutes: 0,
      completed: false,
      interrupted: false,
    };

    // Add location context if available
    const currentZone = locationService.getCurrentZone();
    if (currentZone) {
      session.location = {
        zoneId: currentZone.id,
        zoneName: currentZone.name,
      };
    }

    this.currentSession = session;
    this.sessions.push(session);

    // Start session timer
    this.startSessionTimer(session);

    // Send start notification
    await notificationService.sendFocusSessionStart(duration);

    // Save session
    await this.saveSessions();

    console.log(`Focus session started: ${duration} minutes, ${category}`);
    return session;
  }

  async endSession(interruptionReason?: string): Promise<FocusSession | null> {
    if (!this.currentSession) return null;

    const session = { ...this.currentSession };
    session.endTime = new Date();
    session.isActive = false;
    session.interrupted = !!interruptionReason;
    session.interruptionReason = interruptionReason;

    // Calculate mindful minutes
    const durationMs = session.endTime.getTime() - session.startTime.getTime();
    const durationMinutes = Math.floor(durationMs / (1000 * 60));
    session.mindfulMinutes = Math.min(durationMinutes, session.duration);
    session.completed = durationMinutes >= session.duration * 0.8; // 80% completion threshold

    // Stop timers
    this.stopSessionTimer();
    this.stopReminderTimer();

    // Update session in array
    const sessionIndex = this.sessions.findIndex(s => s.id === session.id);
    if (sessionIndex !== -1) {
      this.sessions[sessionIndex] = session;
    }

    this.currentSession = null;

    // Send completion notification
    if (session.completed) {
      await notificationService.sendFocusSessionEnd(session.mindfulMinutes);
    }

    // Save sessions
    await this.saveSessions();

    console.log(`Focus session ended: ${session.mindfulMinutes} mindful minutes`);
    return session;
  }

  async pauseSession(): Promise<void> {
    if (!this.currentSession) return;

    // Pause the session (keep it active but stop timers)
    this.stopSessionTimer();
    this.stopReminderTimer();
    
    console.log('Focus session paused');
  }

  async resumeSession(): Promise<void> {
    if (!this.currentSession) return;

    // Resume the session
    this.startSessionTimer(this.currentSession);
    
    console.log('Focus session resumed');
  }

  getCurrentSession(): FocusSession | null {
    return this.currentSession;
  }

  getSessions(): FocusSession[] {
    return this.sessions;
  }

  getTodaySessions(): FocusSession[] {
    const today = new Date().toISOString().split('T')[0];
    return this.sessions.filter(session => 
      session.startTime.toISOString().startsWith(today)
    );
  }

  getSessionStats(): FocusSessionStats {
    const completedSessions = this.sessions.filter(s => s.completed);
    const totalSessions = this.sessions.length;
    const totalMindfulMinutes = this.sessions.reduce((sum, s) => sum + s.mindfulMinutes, 0);
    
    // Calculate average session length
    const totalDuration = this.sessions.reduce((sum, s) => sum + s.duration, 0);
    const averageSessionLength = totalSessions > 0 ? totalDuration / totalSessions : 0;
    
    // Calculate completion rate
    const completionRate = totalSessions > 0 ? (completedSessions.length / totalSessions) * 100 : 0;
    
    // Calculate streaks
    const { longestStreak, currentStreak } = this.calculateStreaks();
    
    // Group by category
    const sessionsByCategory: Record<string, number> = {};
    this.sessions.forEach(session => {
      sessionsByCategory[session.category] = (sessionsByCategory[session.category] || 0) + 1;
    });
    
    // Group by location
    const sessionsByLocation: Record<string, number> = {};
    this.sessions.forEach(session => {
      if (session.location) {
        sessionsByLocation[session.location.zoneName] = (sessionsByLocation[session.location.zoneName] || 0) + 1;
      }
    });

    return {
      totalSessions,
      totalMindfulMinutes,
      averageSessionLength,
      completionRate,
      longestStreak,
      currentStreak,
      sessionsByCategory,
      sessionsByLocation,
    };
  }

  async updateSettings(newSettings: Partial<FocusSessionSettings>): Promise<void> {
    this.settings = { ...this.settings, ...newSettings };
    await this.saveSettings();
  }

  getSettings(): FocusSessionSettings {
    return this.settings;
  }

  getDefaultBlockedApps(category: string): string[] {
    switch (category) {
      case 'social':
        return this.settings.blockedAppCategories.social;
      case 'entertainment':
        return this.settings.blockedAppCategories.entertainment;
      case 'work':
        return [
          ...this.settings.blockedAppCategories.social,
          ...this.settings.blockedAppCategories.entertainment,
          ...this.settings.blockedAppCategories.games,
        ];
      case 'exercise':
        return [
          ...this.settings.blockedAppCategories.social,
          ...this.settings.blockedAppCategories.entertainment,
        ];
      default:
        return this.settings.blockedAppCategories.social;
    }
  }

  async suggestFocusSession(): Promise<boolean> {
    // Check if we should suggest a focus session based on location and usage patterns
    const currentZone = locationService.getCurrentZone();
    const screenTimeInZone = locationService.getScreenTimeInCurrentZone();
    
    if (!currentZone || !this.settings.autoStartInPublic) {
      return false;
    }

    // Suggest session if user has been on phone for more than 3 minutes in public space
    if (screenTimeInZone > 3 && !this.currentSession) {
      await notificationService.sendFocusSessionReminder();
      return true;
    }

    return false;
  }

  private startSessionTimer(session: FocusSession): void {
    // Clear any existing timer
    this.stopSessionTimer();

    // Set session end timer
    this.sessionTimer = setTimeout(async () => {
      await this.endSession();
    }, session.duration * 60 * 1000);

    // Set reminder timer
    this.startReminderTimer();
  }

  private stopSessionTimer(): void {
    if (this.sessionTimer) {
      clearTimeout(this.sessionTimer);
      this.sessionTimer = null;
    }
  }

  private startReminderTimer(): void {
    // Clear any existing reminder timer
    this.stopReminderTimer();

    // Set reminder timer
    this.reminderTimer = setTimeout(async () => {
      if (this.currentSession) {
        await notificationService.sendFocusSessionReminder();
        this.startReminderTimer(); // Set next reminder
      }
    }, this.settings.reminderFrequency * 60 * 1000);
  }

  private stopReminderTimer(): void {
    if (this.reminderTimer) {
      clearTimeout(this.reminderTimer);
      this.reminderTimer = null;
    }
  }

  private calculateStreaks(): { longestStreak: number; currentStreak: number } {
    const sortedSessions = [...this.sessions]
      .filter(s => s.completed)
      .sort((a, b) => a.startTime.getTime() - b.startTime.getTime());

    let currentStreak = 0;
    let longestStreak = 0;
    let tempStreak = 0;

    for (let i = 0; i < sortedSessions.length; i++) {
      const session = sortedSessions[i];
      const sessionDate = session.startTime.toISOString().split('T')[0];
      
      if (i === 0) {
        tempStreak = 1;
      } else {
        const prevSession = sortedSessions[i - 1];
        const prevDate = prevSession.startTime.toISOString().split('T')[0];
        
        // Check if sessions are on consecutive days
        const currentDate = new Date(sessionDate);
        const previousDate = new Date(prevDate);
        const dayDiff = (currentDate.getTime() - previousDate.getTime()) / (1000 * 60 * 60 * 24);
        
        if (dayDiff === 1) {
          tempStreak++;
        } else {
          tempStreak = 1;
        }
      }
      
      longestStreak = Math.max(longestStreak, tempStreak);
    }

    // Calculate current streak (from most recent session)
    if (sortedSessions.length > 0) {
      const today = new Date().toISOString().split('T')[0];
      const lastSessionDate = sortedSessions[sortedSessions.length - 1].startTime.toISOString().split('T')[0];
      
      if (lastSessionDate === today) {
        currentStreak = tempStreak;
      } else {
        const dayDiff = (new Date(today).getTime() - new Date(lastSessionDate).getTime()) / (1000 * 60 * 60 * 24);
        currentStreak = dayDiff === 1 ? tempStreak : 0;
      }
    }

    return { longestStreak, currentStreak };
  }

  private async loadSessions(): Promise<void> {
    try {
      const sessionsData = await AsyncStorage.getItem('focusSessions');
      if (sessionsData) {
        this.sessions = JSON.parse(sessionsData).map((session: any) => ({
          ...session,
          startTime: new Date(session.startTime),
          endTime: session.endTime ? new Date(session.endTime) : undefined,
        }));
      }
    } catch (error) {
      console.error('Error loading focus sessions:', error);
    }
  }

  private async saveSessions(): Promise<void> {
    try {
      await AsyncStorage.setItem('focusSessions', JSON.stringify(this.sessions));
    } catch (error) {
      console.error('Error saving focus sessions:', error);
    }
  }

  private async loadSettings(): Promise<void> {
    try {
      const settingsData = await AsyncStorage.getItem('focusSessionSettings');
      if (settingsData) {
        this.settings = { ...this.settings, ...JSON.parse(settingsData) };
      }
    } catch (error) {
      console.error('Error loading focus session settings:', error);
    }
  }

  private async saveSettings(): Promise<void> {
    try {
      await AsyncStorage.setItem('focusSessionSettings', JSON.stringify(this.settings));
    } catch (error) {
      console.error('Error saving focus session settings:', error);
    }
  }

  async clearSessionData(): Promise<void> {
    this.sessions = [];
    this.currentSession = null;
    this.stopSessionTimer();
    this.stopReminderTimer();
    await AsyncStorage.removeItem('focusSessions');
  }
}

export const focusSessionService = new FocusSessionService(); 