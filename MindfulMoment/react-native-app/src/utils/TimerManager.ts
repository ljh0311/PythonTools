import { settingsManager, Settings } from './SettingsManager';

export interface Session {
  id: number;
  type: 'focus' | 'break' | 'longBreak';
  duration: number;
  startTime: Date;
  endTime?: Date;
  completed: boolean;
  paused: boolean;
  pauseTime: number;
  currentTime?: number;
}

export interface TimerData {
  currentTime: number;
  totalTime: number;
  remaining: number;
  elapsed: number;
  progress: number;
  sessionType: string;
  session: Session | null;
}

export interface SessionStats {
  totalSessions: number;
  focusSessions: number;
  breakSessions: number;
  totalFocusTime: number;
  totalBreakTime: number;
  averageFocusTime: number;
}

type TimerCallback = (data: TimerData) => void;
type SessionCallback = (session: Session) => void;

class TimerManager {
  private isRunning: boolean = false;
  private isPaused: boolean = false;
  private currentTime: number = 0;
  private totalTime: number = 0;
  private interval: NodeJS.Timeout | null = null;
  private sessionType: 'focus' | 'break' | 'longBreak' = 'focus';
  private sessions: Session[] = [];
  private currentSession: Session | null = null;
  private settings: typeof settingsManager;

  // Event callbacks
  private onTickCallback: TimerCallback | null = null;
  private onCompleteCallback: SessionCallback | null = null;
  private onPauseCallback: SessionCallback | null = null;
  private onResumeCallback: SessionCallback | null = null;
  private onStartCallback: SessionCallback | null = null;
  private onStopCallback: SessionCallback | null = null;

  constructor() {
    this.settings = settingsManager;
  }

  /**
   * Start a focus session
   */
  startFocusSession(duration?: number): Session {
    const sessionDuration = duration || this.settings.getFocusSessionDuration();
    this.startTimer(sessionDuration * 60, 'focus');
    
    // Create session record
    this.currentSession = {
      id: Date.now(),
      type: 'focus',
      duration: sessionDuration,
      startTime: new Date(),
      endTime: undefined,
      completed: false,
      paused: false,
      pauseTime: 0,
      currentTime: this.currentTime
    };
    
    this.sessions.push(this.currentSession);
    
    // Trigger start event
    if (this.onStartCallback) {
      this.onStartCallback(this.currentSession);
    }
    
    return this.currentSession;
  }

  /**
   * Start a break session
   */
  startBreakSession(duration?: number, type: 'break' | 'longBreak' = 'break'): Session {
    const breakDuration = duration || this.settings.getBreakDuration();
    this.startTimer(breakDuration * 60, type);
    
    // Create session record
    this.currentSession = {
      id: Date.now(),
      type: type,
      duration: breakDuration,
      startTime: new Date(),
      endTime: undefined,
      completed: false,
      paused: false,
      pauseTime: 0,
      currentTime: this.currentTime
    };
    
    this.sessions.push(this.currentSession);
    
    // Trigger start event
    if (this.onStartCallback) {
      this.onStartCallback(this.currentSession);
    }
    
    return this.currentSession;
  }

  /**
   * Start the timer
   */
  private startTimer(seconds: number, type: 'focus' | 'break' | 'longBreak' = 'focus'): void {
    if (this.isRunning) {
      this.stop();
    }
    
    this.sessionType = type;
    this.totalTime = seconds;
    this.currentTime = seconds;
    this.isRunning = true;
    this.isPaused = false;
    
    this.interval = setInterval(() => {
      this.tick();
    }, 1000);
    
    // Trigger first tick immediately
    this.tick();
  }

  /**
   * Timer tick function
   */
  private tick(): void {
    if (!this.isRunning || this.isPaused) return;
    
    this.currentTime--;
    
    // Update session record
    if (this.currentSession) {
      this.currentSession.currentTime = this.currentTime;
    }
    
    // Trigger tick event
    if (this.onTickCallback) {
      this.onTickCallback({
        currentTime: this.currentTime,
        totalTime: this.totalTime,
        remaining: this.currentTime,
        elapsed: this.totalTime - this.currentTime,
        progress: ((this.totalTime - this.currentTime) / this.totalTime) * 100,
        sessionType: this.sessionType,
        session: this.currentSession
      });
    }
    
    // Check if timer is complete
    if (this.currentTime <= 0) {
      this.complete();
    }
  }

  /**
   * Pause the timer
   */
  pause(): void {
    if (!this.isRunning || this.isPaused) return;
    
    this.isPaused = true;
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }
    
    // Update session record
    if (this.currentSession) {
      this.currentSession.paused = true;
      this.currentSession.pauseTime = Date.now();
    }
    
    // Trigger pause event
    if (this.onPauseCallback) {
      this.onPauseCallback(this.currentSession!);
    }
  }

  /**
   * Resume the timer
   */
  resume(): void {
    if (!this.isRunning || !this.isPaused) return;
    
    this.isPaused = false;
    
    // Update session record
    if (this.currentSession) {
      this.currentSession.paused = false;
      this.currentSession.pauseTime = 0;
    }
    
    this.interval = setInterval(() => {
      this.tick();
    }, 1000);
    
    // Trigger resume event
    if (this.onResumeCallback) {
      this.onResumeCallback(this.currentSession!);
    }
  }

  /**
   * Stop the timer
   */
  stop(): void {
    if (!this.isRunning) return;
    
    this.isRunning = false;
    this.isPaused = false;
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }
    
    // Update session record
    if (this.currentSession) {
      this.currentSession.endTime = new Date();
      this.currentSession.completed = false;
    }
    
    // Trigger stop event
    if (this.onStopCallback) {
      this.onStopCallback(this.currentSession!);
    }
  }

  /**
   * Complete the timer
   */
  private complete(): void {
    this.isRunning = false;
    this.isPaused = false;
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }
    this.currentTime = 0;
    
    // Update session record
    if (this.currentSession) {
      this.currentSession.endTime = new Date();
      this.currentSession.completed = true;
      this.currentSession.currentTime = 0;
    }
    
    // Trigger complete event
    if (this.onCompleteCallback) {
      this.onCompleteCallback(this.currentSession!);
    }
    
    // Auto-start break if enabled
    if (this.sessionType === 'focus' && this.settings.get('focusSession.autoStartBreak', true)) {
      setTimeout(() => {
        this.startBreakSession();
      }, 1000);
    }
  }

  /**
   * Reset the timer
   */
  reset(): void {
    this.stop();
    this.currentTime = this.totalTime;
    
    // Trigger tick event to update UI
    if (this.onTickCallback) {
      this.onTickCallback({
        currentTime: this.currentTime,
        totalTime: this.totalTime,
        remaining: this.currentTime,
        elapsed: 0,
        progress: 0,
        sessionType: this.sessionType,
        session: this.currentSession
      });
    }
  }

  /**
   * Set timer duration
   */
  setDuration(seconds: number): void {
    this.totalTime = seconds;
    this.currentTime = seconds;
    
    // Trigger tick event to update UI
    if (this.onTickCallback) {
      this.onTickCallback({
        currentTime: this.currentTime,
        totalTime: this.totalTime,
        remaining: this.currentTime,
        elapsed: 0,
        progress: 0,
        sessionType: this.sessionType,
        session: this.currentSession
      });
    }
  }

  /**
   * Get formatted time string
   */
  getFormattedTime(seconds?: number): string {
    const time = seconds !== undefined ? seconds : this.currentTime;
    const minutes = Math.floor(time / 60);
    const remainingSeconds = time % 60;
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  }

  /**
   * Get progress percentage
   */
  getProgress(): number {
    if (this.totalTime === 0) return 0;
    return ((this.totalTime - this.currentTime) / this.totalTime) * 100;
  }

  /**
   * Get session statistics
   */
  getSessionStats(): SessionStats {
    const completedSessions = this.sessions.filter(s => s.completed);
    const focusSessions = completedSessions.filter(s => s.type === 'focus');
    const breakSessions = completedSessions.filter(s => s.type === 'break' || s.type === 'longBreak');
    
    const totalFocusTime = focusSessions.reduce((total, session) => {
      if (session.endTime) {
        return total + (session.endTime.getTime() - session.startTime.getTime());
      }
      return total;
    }, 0);
    
    const totalBreakTime = breakSessions.reduce((total, session) => {
      if (session.endTime) {
        return total + (session.endTime.getTime() - session.startTime.getTime());
      }
      return total;
    }, 0);
    
    return {
      totalSessions: completedSessions.length,
      focusSessions: focusSessions.length,
      breakSessions: breakSessions.length,
      totalFocusTime: Math.round(totalFocusTime / 1000 / 60), // minutes
      totalBreakTime: Math.round(totalBreakTime / 1000 / 60), // minutes
      averageFocusTime: focusSessions.length > 0 ? 
        Math.round(totalFocusTime / 1000 / 60 / focusSessions.length) : 0
    };
  }

  /**
   * Get today's sessions
   */
  getTodaySessions(): Session[] {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    return this.sessions.filter(session => {
      const sessionDate = new Date(session.startTime);
      sessionDate.setHours(0, 0, 0, 0);
      return sessionDate.getTime() === today.getTime();
    });
  }

  /**
   * Get weekly sessions
   */
  getWeeklySessions(): Session[] {
    const now = new Date();
    const weekStart = new Date(now);
    weekStart.setDate(now.getDate() - now.getDay());
    weekStart.setHours(0, 0, 0, 0);
    
    return this.sessions.filter(session => {
      return new Date(session.startTime) >= weekStart;
    });
  }

  /**
   * Export session data
   */
  exportSessions(): string {
    return JSON.stringify(this.sessions, null, 2);
  }

  /**
   * Import session data
   */
  importSessions(jsonString: string): boolean {
    try {
      const importedSessions = JSON.parse(jsonString);
      this.sessions = importedSessions;
      return true;
    } catch (error) {
      console.error('Error importing sessions:', error);
      return false;
    }
  }

  /**
   * Clear all sessions
   */
  clearSessions(): void {
    this.sessions = [];
  }

  /**
   * Get current session
   */
  getCurrentSession(): Session | null {
    return this.currentSession;
  }

  /**
   * Check if timer is running
   */
  isActive(): boolean {
    return this.isRunning;
  }

  /**
   * Check if timer is paused
   */
  isPausedState(): boolean {
    return this.isPaused;
  }

  /**
   * Get remaining time in seconds
   */
  getRemainingTime(): number {
    return this.currentTime;
  }

  /**
   * Get elapsed time in seconds
   */
  getElapsedTime(): number {
    return this.totalTime - this.currentTime;
  }

  // Event handlers
  onTick(callback: TimerCallback): void {
    this.onTickCallback = callback;
  }

  onComplete(callback: SessionCallback): void {
    this.onCompleteCallback = callback;
  }

  onPause(callback: SessionCallback): void {
    this.onPauseCallback = callback;
  }

  onResume(callback: SessionCallback): void {
    this.onResumeCallback = callback;
  }

  onStart(callback: SessionCallback): void {
    this.onStartCallback = callback;
  }

  onStop(callback: SessionCallback): void {
    this.onStopCallback = callback;
  }

  // Remove event handlers
  removeOnTick(): void {
    this.onTickCallback = null;
  }

  removeOnComplete(): void {
    this.onCompleteCallback = null;
  }

  removeOnPause(): void {
    this.onPauseCallback = null;
  }

  removeOnResume(): void {
    this.onResumeCallback = null;
  }

  removeOnStart(): void {
    this.onStartCallback = null;
  }

  removeOnStop(): void {
    this.onStopCallback = null;
  }

  // Remove all event handlers
  removeAllHandlers(): void {
    this.onTickCallback = null;
    this.onCompleteCallback = null;
    this.onPauseCallback = null;
    this.onResumeCallback = null;
    this.onStartCallback = null;
    this.onStopCallback = null;
  }
}

// Create singleton instance
export const timerManager = new TimerManager();

// Export types
export type { Session, TimerData, SessionStats }; 