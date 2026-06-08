import { Injectable } from '@angular/core';
import { Observable, BehaviorSubject, of } from 'rxjs';
import { map } from 'rxjs/operators';
import { DataService } from './data.service';
import { FocusSession } from '../models/focus-session.model';

export interface SessionStats {
  totalSessions: number;
  totalMinutes: number;
  averageSessionDuration: number;
  longestSession: number;
  shortestSession: number;
  currentStreak: number;
  longestStreak: number;
  sessionsByType: { [key: string]: number };
  sessionsByLocation: { [key: string]: number };
  totalSteps: number;
  totalDistance: number; // in meters
  totalBreathingCycles: number;
  totalDistractions: number;
  totalTasksCompleted: number;
  averageFocusIntensity: number;
  averageMeditationDepth: number;
  averageAwarenessLevel: number;
}

export interface LocationStats {
  location: string;
  type: string;
  sessionsCount: number;
  totalMinutes: number;
  averageDuration: number;
  averageScore: number;
  bestScore: number;
  lastSession?: string;
}

export interface DailyStats {
  date: string;
  sessionsCompleted: number;
  totalMinutes: number;
  averageSession: number;
  streak: number;
  sessionsByType: { [key: string]: number };
  metrics: {
    steps?: number;
    distance?: number;
    breathingCycles?: number;
    distractions?: number;
    tasksCompleted?: number;
  };
}

@Injectable({
  providedIn: 'root'
})
export class StatsService {
  private statsSubject = new BehaviorSubject<SessionStats | null>(null);
  public stats$ = this.statsSubject.asObservable();

  constructor(private dataService: DataService) {
    this.loadStats();
  }

  /**
   * Load and calculate all session statistics
   */
  loadStats(): void {
    this.dataService.getFocusSessions().subscribe(sessions => {
      const stats = this.calculateStats(sessions);
      this.statsSubject.next(stats);
    });
  }

  /**
   * Calculate comprehensive statistics from sessions
   */
  calculateStats(sessions: FocusSession[]): SessionStats {
    const completedSessions = sessions.filter(s => s.status === 'completed');
    
    if (completedSessions.length === 0) {
      return this.getEmptyStats();
    }

    const durations = completedSessions.map(s => s.duration);
    const totalMinutes = durations.reduce((sum, d) => sum + d, 0);
    const averageDuration = Math.round(totalMinutes / completedSessions.length);
    
    // Calculate streaks
    const streak = this.calculateStreak(completedSessions);
    const longestStreak = this.calculateLongestStreak(completedSessions);

    // Sessions by type
    const sessionsByType: { [key: string]: number } = {};
    completedSessions.forEach(session => {
      const type = session.type || 'focus';
      sessionsByType[type] = (sessionsByType[type] || 0) + 1;
    });

    // Sessions by location
    const sessionsByLocation: { [key: string]: number } = {};
    completedSessions.forEach(session => {
      const locationName = this.sanitizeLocationName(session.location?.name || 'Unknown');
      sessionsByLocation[locationName] = (sessionsByLocation[locationName] || 0) + 1;
    });

    // Aggregate type-specific metrics
    const totalSteps = completedSessions.reduce((sum, s) => 
      sum + (s.typeMetrics?.steps || 0), 0);
    const totalDistance = completedSessions.reduce((sum, s) => 
      sum + (s.typeMetrics?.distance || 0), 0);
    const totalBreathingCycles = completedSessions.reduce((sum, s) => 
      sum + (s.typeMetrics?.breathingCycles || 0), 0);
    const totalDistractions = completedSessions.reduce((sum, s) => 
      sum + (s.typeMetrics?.distractionCount || 0), 0);
    const totalTasksCompleted = completedSessions.reduce((sum, s) => 
      sum + (s.typeMetrics?.tasksCompleted || 0), 0);

    // Calculate averages
    const focusSessions = completedSessions.filter(s => s.type === 'focus');
    const meditationSessions = completedSessions.filter(s => s.type === 'meditation');
    const mindfulnessSessions = completedSessions.filter(s => s.type === 'mindfulness');

    const averageFocusIntensity = focusSessions.length > 0
      ? focusSessions.reduce((sum, s) => sum + (s.typeMetrics?.focusIntensity || 5), 0) / focusSessions.length
      : 0;

    const averageMeditationDepth = meditationSessions.length > 0
      ? meditationSessions.reduce((sum, s) => sum + (s.typeMetrics?.meditationDepth || 5), 0) / meditationSessions.length
      : 0;

    const averageAwarenessLevel = mindfulnessSessions.length > 0
      ? mindfulnessSessions.reduce((sum, s) => sum + (s.typeMetrics?.awarenessLevel || 5), 0) / mindfulnessSessions.length
      : 0;

    return {
      totalSessions: completedSessions.length,
      totalMinutes,
      averageSessionDuration: averageDuration,
      longestSession: Math.max(...durations),
      shortestSession: Math.min(...durations),
      currentStreak: streak,
      longestStreak: longestStreak,
      sessionsByType,
      sessionsByLocation,
      totalSteps,
      totalDistance,
      totalBreathingCycles,
      totalDistractions,
      totalTasksCompleted,
      averageFocusIntensity: Math.round(averageFocusIntensity * 10) / 10,
      averageMeditationDepth: Math.round(averageMeditationDepth * 10) / 10,
      averageAwarenessLevel: Math.round(averageAwarenessLevel * 10) / 10
    };
  }

  /**
   * Get location-based statistics
   */
  getLocationStats(): Observable<LocationStats[]> {
    return this.dataService.getFocusSessions().pipe(
      map(sessions => {
        const completedSessions = sessions.filter(s => s.status === 'completed');
        const locationMap = new Map<string, {
          sessions: FocusSession[];
          type: string;
        }>();

        completedSessions.forEach(session => {
          const locationName = this.sanitizeLocationName(session.location?.name || 'Unknown');
          const locationType = session.location?.type || 'public';
          
          if (!locationMap.has(locationName)) {
            locationMap.set(locationName, {
              sessions: [],
              type: locationType
            });
          }
          locationMap.get(locationName)!.sessions.push(session);
        });

        const locationStats: LocationStats[] = [];
        locationMap.forEach((data, locationName) => {
          const sessions = data.sessions;
          const durations = sessions.map(s => s.duration);
          const totalMinutes = durations.reduce((sum, d) => sum + d, 0);
          const averageDuration = totalMinutes / sessions.length;

          // Calculate average score (simplified - could be more sophisticated)
          const averageScore = this.calculateLocationScore(sessions);
          const bestScore = Math.max(...sessions.map(s => this.calculateSessionScore(s)));

          const lastSession = sessions
            .sort((a, b) => new Date(b.startTime).getTime() - new Date(a.startTime).getTime())[0]
            ?.startTime;

          locationStats.push({
            location: locationName,
            type: data.type,
            sessionsCount: sessions.length,
            totalMinutes,
            averageDuration: Math.round(averageDuration),
            averageScore: Math.round(averageScore),
            bestScore: Math.round(bestScore),
            lastSession
          });
        });

        return locationStats.sort((a, b) => b.sessionsCount - a.sessionsCount);
      })
    );
  }

  /**
   * Get daily statistics
   */
  getDailyStats(days: number = 30): Observable<DailyStats[]> {
    return this.dataService.getFocusSessions().pipe(
      map(sessions => {
        const completedSessions = sessions.filter(s => s.status === 'completed');
        const dailyMap = new Map<string, FocusSession[]>();

        completedSessions.forEach(session => {
          const date = new Date(session.startTime).toISOString().split('T')[0];
          if (!dailyMap.has(date)) {
            dailyMap.set(date, []);
          }
          dailyMap.get(date)!.push(session);
        });

        const dailyStats: DailyStats[] = [];
        const today = new Date();
        for (let i = 0; i < days; i++) {
          const date = new Date(today);
          date.setDate(date.getDate() - i);
          const dateStr = date.toISOString().split('T')[0];
          const daySessions = dailyMap.get(dateStr) || [];

          if (daySessions.length > 0) {
            const durations = daySessions.map(s => s.duration);
            const totalMinutes = durations.reduce((sum, d) => sum + d, 0);
            const averageSession = Math.round(totalMinutes / daySessions.length);

            const sessionsByType: { [key: string]: number } = {};
            daySessions.forEach(s => {
              const type = s.type || 'focus';
              sessionsByType[type] = (sessionsByType[type] || 0) + 1;
            });

            dailyStats.push({
              date: dateStr,
              sessionsCompleted: daySessions.length,
              totalMinutes,
              averageSession,
              streak: 0, // Will be calculated separately
              sessionsByType,
              metrics: {
                steps: daySessions.reduce((sum, s) => sum + (s.typeMetrics?.steps || 0), 0),
                distance: daySessions.reduce((sum, s) => sum + (s.typeMetrics?.distance || 0), 0),
                breathingCycles: daySessions.reduce((sum, s) => sum + (s.typeMetrics?.breathingCycles || 0), 0),
                distractions: daySessions.reduce((sum, s) => sum + (s.typeMetrics?.distractionCount || 0), 0),
                tasksCompleted: daySessions.reduce((sum, s) => sum + (s.typeMetrics?.tasksCompleted || 0), 0)
              }
            });
          }
        }

        return dailyStats.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
      })
    );
  }

  /**
   * Calculate session score (0-100)
   */
  private calculateSessionScore(session: FocusSession): number {
    let score = 50; // Base score

    // Duration bonus
    if (session.duration >= 30) score += 20;
    else if (session.duration >= 15) score += 10;

    // Type-specific metrics
    if (session.typeMetrics) {
      if (session.type === 'focus' || session.type === 'study') {
        const intensity = session.typeMetrics.focusIntensity || 5;
        const tasks = session.typeMetrics.tasksCompleted || 0;
        const distractions = session.typeMetrics.distractionCount || 0;
        score += (intensity - 5) * 2;
        score += tasks * 5;
        score -= distractions * 3;
      } else if (session.type === 'travel-safety') {
        const safeMin = session.typeMetrics.safeZoneMinutes || 0;
        const alerts = session.typeMetrics.alertsAcknowledged || 0;
        score += Math.min(safeMin * 2, 30);
        score += alerts * 5;
      } else if (session.type === 'meditation') {
        const depth = session.typeMetrics.meditationDepth || 5;
        score += (depth - 5) * 3;
      } else if (session.type === 'mindfulness') {
        const awareness = session.typeMetrics.awarenessLevel || 5;
        score += (awareness - 5) * 3;
      }
    }

    // Achievement bonus
    score += session.achievements.length * 5;

    return Math.min(100, Math.max(0, score));
  }

  /**
   * Calculate average score for a location
   */
  private calculateLocationScore(sessions: FocusSession[]): number {
    if (sessions.length === 0) return 0;
    const totalScore = sessions.reduce((sum, s) => sum + this.calculateSessionScore(s), 0);
    return totalScore / sessions.length;
  }

  /**
   * Calculate current streak
   */
  private calculateStreak(sessions: FocusSession[]): number {
    if (sessions.length === 0) return 0;

    const dates = sessions
      .map(s => new Date(s.startTime).toDateString())
      .filter((date, index, self) => self.indexOf(date) === index)
      .sort((a, b) => new Date(b).getTime() - new Date(a).getTime());

    let streak = 0;
    const today = new Date().toDateString();
    let expectedDate = new Date(today);

    for (const dateStr of dates) {
      if (new Date(dateStr).toDateString() === expectedDate.toDateString()) {
        streak++;
        expectedDate.setDate(expectedDate.getDate() - 1);
      } else if (streak === 0 && dateStr === today) {
        streak = 1;
        expectedDate.setDate(expectedDate.getDate() - 1);
      } else {
        break;
      }
    }

    return streak;
  }

  /**
   * Calculate longest streak
   */
  private calculateLongestStreak(sessions: FocusSession[]): number {
    if (sessions.length === 0) return 0;

    const dates = sessions
      .map(s => new Date(s.startTime).toDateString())
      .filter((date, index, self) => self.indexOf(date) === index)
      .sort((a, b) => new Date(a).getTime() - new Date(b).getTime());

    let longestStreak = 0;
    let currentStreak = 1;

    for (let i = 1; i < dates.length; i++) {
      const prevDate = new Date(dates[i - 1]);
      const currDate = new Date(dates[i]);
      const diffDays = (currDate.getTime() - prevDate.getTime()) / (1000 * 60 * 60 * 24);

      if (diffDays === 1) {
        currentStreak++;
      } else {
        longestStreak = Math.max(longestStreak, currentStreak);
        currentStreak = 1;
      }
    }

    return Math.max(longestStreak, currentStreak);
  }

  /**
   * Sanitize location name to remove coordinate strings
   */
  private sanitizeLocationName(locationName: string): string {
    if (!locationName) return 'Unknown Location';
    
    // Check if it's a coordinate string (e.g., "Location at 1.3360, 103.9384")
    if (locationName.startsWith('Location at')) {
      // Extract coordinates and try to get a better name
      const coordMatch = locationName.match(/Location at ([\d.]+),\s*([\d.]+)/);
      if (coordMatch) {
        const lat = parseFloat(coordMatch[1]);
        const lng = parseFloat(coordMatch[2]);
        return this.getLocationNameFromCoordinates(lat, lng);
      }
      return 'Current Location';
    }
    
    // Check if it's just coordinates without "Location at" prefix
    const coordPattern = /^[\d.]+,\s*[\d.]+$/;
    if (coordPattern.test(locationName.trim())) {
      const coords = locationName.split(',').map(c => parseFloat(c.trim()));
      if (coords.length === 2) {
        return this.getLocationNameFromCoordinates(coords[0], coords[1]);
      }
      return 'Current Location';
    }
    
    return locationName;
  }

  /**
   * Get a user-friendly location name from coordinates
   */
  private getLocationNameFromCoordinates(lat: number, lng: number): string {
    // Singapore coordinates roughly: 1.3521, 103.8198
    // Check if in Singapore
    if (lat >= 1.15 && lat <= 1.5 && lng >= 103.6 && lng <= 104.0) {
      // Check for known Singapore areas (simplified)
      if (lat >= 1.28 && lat <= 1.35 && lng >= 103.8 && lng <= 103.9) {
        return 'Central Singapore';
      } else if (lat >= 1.35 && lat <= 1.45) {
        return 'Northern Singapore';
      } else if (lat >= 1.25 && lat <= 1.35 && lng >= 103.9) {
        return 'Eastern Singapore';
      } else if (lat >= 1.25 && lat <= 1.35 && lng <= 103.8) {
        return 'Western Singapore';
      } else {
        return 'Singapore';
      }
    }
    
    // Default to generic location name
    return 'Current Location';
  }

  /**
   * Get empty stats
   */
  private getEmptyStats(): SessionStats {
    return {
      totalSessions: 0,
      totalMinutes: 0,
      averageSessionDuration: 0,
      longestSession: 0,
      shortestSession: 0,
      currentStreak: 0,
      longestStreak: 0,
      sessionsByType: {},
      sessionsByLocation: {},
      totalSteps: 0,
      totalDistance: 0,
      totalBreathingCycles: 0,
      totalDistractions: 0,
      totalTasksCompleted: 0,
      averageFocusIntensity: 0,
      averageMeditationDepth: 0,
      averageAwarenessLevel: 0
    };
  }

  /**
   * Refresh statistics
   */
  refreshStats(): void {
    this.loadStats();
  }
}

