import { useState, useEffect, useCallback } from 'react';
import { timerManager, TimerData, Session, SessionStats } from '../utils/TimerManager';

/**
 * Hook to use timer functionality
 * Provides timer state and controls
 */
export function useTimer() {
  const [timerData, setTimerData] = useState<TimerData>({
    currentTime: 0,
    totalTime: 0,
    remaining: 0,
    elapsed: 0,
    progress: 0,
    sessionType: 'focus',
    session: null
  });

  const [isRunning, setIsRunning] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [currentSession, setCurrentSession] = useState<Session | null>(null);

  useEffect(() => {
    // Set up timer event handlers
    timerManager.onTick((data) => {
      setTimerData(data);
    });

    timerManager.onStart((session) => {
      setIsRunning(true);
      setIsPaused(false);
      setCurrentSession(session);
    });

    timerManager.onPause((session) => {
      setIsPaused(true);
      setCurrentSession(session);
    });

    timerManager.onResume((session) => {
      setIsPaused(false);
      setCurrentSession(session);
    });

    timerManager.onStop((session) => {
      setIsRunning(false);
      setIsPaused(false);
      setCurrentSession(session);
    });

    timerManager.onComplete((session) => {
      setIsRunning(false);
      setIsPaused(false);
      setCurrentSession(session);
    });

    // Cleanup
    return () => {
      timerManager.removeAllHandlers();
    };
  }, []);

  const startFocusSession = useCallback((duration?: number) => {
    return timerManager.startFocusSession(duration);
  }, []);

  const startBreakSession = useCallback((duration?: number, type: 'break' | 'longBreak' = 'break') => {
    return timerManager.startBreakSession(duration, type);
  }, []);

  const pause = useCallback(() => {
    timerManager.pause();
  }, []);

  const resume = useCallback(() => {
    timerManager.resume();
  }, []);

  const stop = useCallback(() => {
    timerManager.stop();
  }, []);

  const reset = useCallback(() => {
    timerManager.reset();
  }, []);

  const setDuration = useCallback((seconds: number) => {
    timerManager.setDuration(seconds);
  }, []);

  return {
    // Timer state
    timerData,
    isRunning,
    isPaused,
    currentSession,
    
    // Timer controls
    startFocusSession,
    startBreakSession,
    pause,
    resume,
    stop,
    reset,
    setDuration,
    
    // Utility methods
    getFormattedTime: timerManager.getFormattedTime.bind(timerManager),
    getProgress: timerManager.getProgress.bind(timerManager),
    getRemainingTime: timerManager.getRemainingTime.bind(timerManager),
    getElapsedTime: timerManager.getElapsedTime.bind(timerManager)
  };
}

/**
 * Hook to get session statistics
 */
export function useSessionStats(): SessionStats {
  const [stats, setStats] = useState<SessionStats>(timerManager.getSessionStats());

  useEffect(() => {
    const updateStats = () => {
      setStats(timerManager.getSessionStats());
    };

    // Update stats when sessions change
    timerManager.onComplete(() => {
      updateStats();
    });

    timerManager.onStop(() => {
      updateStats();
    });

    return () => {
      timerManager.removeOnComplete();
      timerManager.removeOnStop();
    };
  }, []);

  return stats;
}

/**
 * Hook to get today's sessions
 */
export function useTodaySessions(): Session[] {
  const [sessions, setSessions] = useState<Session[]>(timerManager.getTodaySessions());

  useEffect(() => {
    const updateSessions = () => {
      setSessions(timerManager.getTodaySessions());
    };

    timerManager.onComplete(updateSessions);
    timerManager.onStop(updateSessions);

    return () => {
      timerManager.removeOnComplete();
      timerManager.removeOnStop();
    };
  }, []);

  return sessions;
}

/**
 * Hook to get weekly sessions
 */
export function useWeeklySessions(): Session[] {
  const [sessions, setSessions] = useState<Session[]>(timerManager.getWeeklySessions());

  useEffect(() => {
    const updateSessions = () => {
      setSessions(timerManager.getWeeklySessions());
    };

    timerManager.onComplete(updateSessions);
    timerManager.onStop(updateSessions);

    return () => {
      timerManager.removeOnComplete();
      timerManager.removeOnStop();
    };
  }, []);

  return sessions;
}

/**
 * Hook to get current session
 */
export function useCurrentSession(): Session | null {
  const [session, setSession] = useState<Session | null>(timerManager.getCurrentSession());

  useEffect(() => {
    const updateSession = (newSession: Session) => {
      setSession(newSession);
    };

    timerManager.onStart(updateSession);
    timerManager.onPause(updateSession);
    timerManager.onResume(updateSession);
    timerManager.onStop(updateSession);
    timerManager.onComplete(updateSession);

    return () => {
      timerManager.removeOnStart();
      timerManager.removeOnPause();
      timerManager.removeOnResume();
      timerManager.removeOnStop();
      timerManager.removeOnComplete();
    };
  }, []);

  return session;
}

/**
 * Hook to check if timer is active
 */
export function useTimerActive(): boolean {
  const [isActive, setIsActive] = useState(timerManager.isActive());

  useEffect(() => {
    const updateActive = () => {
      setIsActive(timerManager.isActive());
    };

    timerManager.onStart(updateActive);
    timerManager.onStop(updateActive);
    timerManager.onComplete(updateActive);

    return () => {
      timerManager.removeOnStart();
      timerManager.removeOnStop();
      timerManager.removeOnComplete();
    };
  }, []);

  return isActive;
}

/**
 * Hook to check if timer is paused
 */
export function useTimerPaused(): boolean {
  const [isPaused, setIsPaused] = useState(timerManager.isPausedState());

  useEffect(() => {
    const updatePaused = () => {
      setIsPaused(timerManager.isPausedState());
    };

    timerManager.onPause(updatePaused);
    timerManager.onResume(updatePaused);
    timerManager.onStop(updatePaused);
    timerManager.onComplete(updatePaused);

    return () => {
      timerManager.removeOnPause();
      timerManager.removeOnResume();
      timerManager.removeOnStop();
      timerManager.removeOnComplete();
    };
  }, []);

  return isPaused;
}

/**
 * Hook to get formatted time
 */
export function useFormattedTime(): string {
  const [formattedTime, setFormattedTime] = useState(timerManager.getFormattedTime());

  useEffect(() => {
    const updateTime = () => {
      setFormattedTime(timerManager.getFormattedTime());
    };

    timerManager.onTick(updateTime);

    return () => {
      timerManager.removeOnTick();
    };
  }, []);

  return formattedTime;
}

/**
 * Hook to get timer progress
 */
export function useTimerProgress(): number {
  const [progress, setProgress] = useState(timerManager.getProgress());

  useEffect(() => {
    const updateProgress = () => {
      setProgress(timerManager.getProgress());
    };

    timerManager.onTick(updateProgress);

    return () => {
      timerManager.removeOnTick();
    };
  }, []);

  return progress;
}

/**
 * Hook to get remaining time in seconds
 */
export function useRemainingTime(): number {
  const [remaining, setRemaining] = useState(timerManager.getRemainingTime());

  useEffect(() => {
    const updateRemaining = () => {
      setRemaining(timerManager.getRemainingTime());
    };

    timerManager.onTick(updateRemaining);

    return () => {
      timerManager.removeOnTick();
    };
  }, []);

  return remaining;
}

/**
 * Hook to get elapsed time in seconds
 */
export function useElapsedTime(): number {
  const [elapsed, setElapsed] = useState(timerManager.getElapsedTime());

  useEffect(() => {
    const updateElapsed = () => {
      setElapsed(timerManager.getElapsedTime());
    };

    timerManager.onTick(updateElapsed);

    return () => {
      timerManager.removeOnTick();
    };
  }, []);

  return elapsed;
}

/**
 * Hook to get session type
 */
export function useSessionType(): string {
  const [sessionType, setSessionType] = useState('focus');

  useEffect(() => {
    const updateSessionType = (data: TimerData) => {
      setSessionType(data.sessionType);
    };

    timerManager.onTick(updateSessionType);

    return () => {
      timerManager.removeOnTick();
    };
  }, []);

  return sessionType;
}

/**
 * Hook to export sessions
 */
export function useExportSessions(): () => string {
  return useCallback(() => {
    return timerManager.exportSessions();
  }, []);
}

/**
 * Hook to import sessions
 */
export function useImportSessions(): (jsonString: string) => boolean {
  return useCallback((jsonString: string) => {
    return timerManager.importSessions(jsonString);
  }, []);
}

/**
 * Hook to clear sessions
 */
export function useClearSessions(): () => void {
  return useCallback(() => {
    timerManager.clearSessions();
  }, []);
} 