import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { tap, catchError, map, switchMap } from 'rxjs/operators';
import { User } from '../models/user.model';
import { FocusSession } from '../models/focus-session.model';
import { CommunityGroup } from '../models/community-group.model';
import { Achievement } from '../models/achievement.model';
import { BusArrivalResponse, BusStopSearchResponse } from '../models/bus-arrival.model';
import { StorageService } from './storage.service';
import { AuthService } from './auth.service';

interface BasicResponse {
  success: boolean;
}

interface UpdateStatsResponse {
  success: boolean;
  stats: any;
}

type FailureResponse = { success: false; error: string };

interface LocalStorageData {
  userStats: any;
  focusSessions: FocusSession[];
  communityGroups: CommunityGroup[];
  achievements: Achievement[];
  lastUpdated: string;
}

@Injectable({
  providedIn: 'root'
})
export class DataService {
  private readonly API_URL = '/api';
  private readonly STORAGE_KEY = 'mindfulMoment_data';
  
  // Data subjects for reactive updates
  private userStatsSubject = new BehaviorSubject<any>(null);
  public userStats$ = this.userStatsSubject.asObservable();

  private focusSessionsSubject = new BehaviorSubject<FocusSession[]>([]);
  public focusSessions$ = this.focusSessionsSubject.asObservable();

  private communityGroupsSubject = new BehaviorSubject<CommunityGroup[]>([]);
  public communityGroups$ = this.communityGroupsSubject.asObservable();

  private achievementsSubject = new BehaviorSubject<Achievement[]>([]);
  public achievements$ = this.achievementsSubject.asObservable();

  constructor(
    private http: HttpClient,
    private storageService: StorageService,
    private authService: AuthService
  ) {
    this.loadDataFromStorage();
    this.loadInitialDataFromStorageJson();
  }

  /**
   * Load initial data from storage.json when app starts
   */
  private loadInitialDataFromStorageJson(): void {
    const currentUser = this.authService.getCurrentUser();
    if (!currentUser) return;

    const userId = parseInt(currentUser.id);
    if (isNaN(userId)) return;

    // Load user from storage.json
    this.storageService.getUserById(userId).subscribe(storageUser => {
      if (storageUser && storageUser.stats) {
        // Load focus sessions from storage.json
        if (storageUser.stats.focusSessions && Array.isArray(storageUser.stats.focusSessions)) {
          const storageSessions = storageUser.stats.focusSessions.map((s: any) => ({
            ...s,
            userId: s.userId.toString()
          })) as FocusSession[];
          
          // Merge with existing sessions (avoid duplicates)
          const existingSessions = this.focusSessionsSubject.value;
          const existingIds = new Set(existingSessions.map(s => s.id));
          const newSessions = storageSessions.filter(s => !existingIds.has(s.id));
          this.focusSessionsSubject.next([...existingSessions, ...newSessions]);
        }

        // Load user stats from storage.json
        if (storageUser.stats.todayStats) {
          const stats = this.convertStorageStatsToUserStats(storageUser.stats);
          this.userStatsSubject.next(stats);
        }
      }
    });
  }

  /**
   * Convert storage.json stats format to UserStats format
   */
  private convertStorageStatsToUserStats(storageStats: any): any {
    const todayStats = storageStats.todayStats || {};
    const focusSessions = storageStats.focusSessions || [];
    
    // Calculate totals from sessions
    const totalMinutes = focusSessions.reduce((sum: number, s: any) => sum + (s.duration || 0), 0);
    const totalSessions = focusSessions.length;
    const phoneUsageReduction = focusSessions.reduce((sum: number, s: any) => sum + (s.phoneUsageReduction || 0), 0);
    const socialInteractions = focusSessions.reduce((sum: number, s: any) => 
      sum + (s.socialInteractions?.length || 0), 0);

    return {
      totalSessions: todayStats.sessionsCompleted || totalSessions,
      totalMindfulMinutes: todayStats.totalMinutes || totalMinutes,
      totalSafetyAlerts: 0,
      totalSocialEngagements: socialInteractions,
      focusSessionStats: {
        totalPublicFocusTime: totalMinutes,
        totalSocialInteractions: socialInteractions,
        phoneUsageReduction: phoneUsageReduction,
        mindfulMoments: focusSessions.reduce((sum: number, s: any) => 
          sum + (s.mindfulMoments?.length || 0), 0)
      },
      publicAwarenessStats: {
        totalPublicTime: storageStats.publicAwarenessStats?.totalPublicTime || 0,
        safetyAlerts: storageStats.publicAwarenessStats?.safetyAlerts || 0,
        socialPrompts: storageStats.publicAwarenessStats?.socialPrompts || 0,
        mindfulScore: storageStats.publicAwarenessStats?.mindfulScore || 0,
        locationScores: storageStats.publicAwarenessStats?.locationScores || {
          publicSpaces: 0,
          mrtStations: 0,
          shoppingCenters: 0
        }
      }
    };
  }

  // User Statistics
  getUserStats(userId?: string): Observable<any> {
    const id = userId || this.getCurrentUserId();
    if (!id) return of(null);

    // Try to get from localStorage first
    const localData = this.loadDataFromStorage();
    if (localData?.userStats) {
      this.userStatsSubject.next(localData.userStats);
      return of(localData.userStats);
    }

    // Try to get from storage.json via StorageService
    const numericId = parseInt(id);
    if (!isNaN(numericId)) {
      return this.storageService.getUserById(numericId).pipe(
        switchMap(storageUser => {
          if (storageUser && storageUser.stats) {
            const stats = this.convertStorageStatsToUserStats(storageUser.stats);
            this.userStatsSubject.next(stats);
            this.saveDataToStorage();
            return of(stats);
          }
          
          // Fallback to empty stats
          return this.getEmptyStats();
        }),
        catchError(error => {
          console.error('Error fetching user stats from storage:', error);
          return this.getEmptyStats();
        })
      );
    }

    return this.getEmptyStats();
  }

  private getEmptyStats(): Observable<any> {
    const emptyStats = {
      totalSessions: 0,
      totalMindfulMinutes: 0,
      totalSafetyAlerts: 0,
      totalSocialEngagements: 0,
      focusSessionStats: {
        totalPublicFocusTime: 0,
        totalSocialInteractions: 0,
        phoneUsageReduction: 0,
        mindfulMoments: 0
      },
      publicAwarenessStats: {
        totalPublicTime: 0,
        safetyAlerts: 0,
        socialPrompts: 0,
        mindfulScore: 0
      }
    };
    this.userStatsSubject.next(emptyStats);
    return of(emptyStats);
  }

  updateUserStats(stats: any): Observable<UpdateStatsResponse | FailureResponse> {
    const userId = this.getCurrentUserId();
    if (!userId) return of<FailureResponse>({ success: false, error: 'No user logged in' });

    // Update local storage immediately
    this.userStatsSubject.next(stats);
    this.saveDataToStorage();

    // Try to sync with API (if backend is available)
    return this.http.put<UpdateStatsResponse>(`${this.API_URL}/user/${userId}/stats`, stats)
      .pipe(
        tap((response: UpdateStatsResponse) => {
          if (response.success) {
            this.userStatsSubject.next(response.stats);
            this.saveDataToStorage();
          }
        }),
        catchError(error => {
          console.error('Error updating user stats (saved locally):', error);
          // Return success even if API fails, since we saved locally
          return of<UpdateStatsResponse>({ success: true, stats });
        })
      );
  }

  // Focus Sessions
  getFocusSessions(userId?: string): Observable<FocusSession[]> {
    const id = userId || this.getCurrentUserId();
    if (!id) return of([]);

    // Try to get from localStorage first
    const localData = this.loadDataFromStorage();
    let localSessions: FocusSession[] = [];
    if (localData?.focusSessions) {
      localSessions = localData.focusSessions.filter(s => s.userId === id);
    }

    // Try to get from storage.json via StorageService
    const numericId = parseInt(id);
    if (!isNaN(numericId)) {
      return this.storageService.getUserById(numericId).pipe(
        switchMap(storageUser => {
          let storageSessions: FocusSession[] = [];
          
          if (storageUser && storageUser.stats && storageUser.stats.focusSessions) {
            storageSessions = storageUser.stats.focusSessions.map((s: any) => ({
              ...s,
              userId: id,
              location: s.location || {
                type: 'home' as any,
                name: 'Unknown',
                environment: 'quiet' as any
              }
            })) as FocusSession[];
          }

          // Merge sessions (localStorage takes priority, avoid duplicates)
          const localIds = new Set(localSessions.map(s => s.id));
          const uniqueStorageSessions = storageSessions.filter(s => !localIds.has(s.id));
          const mergedSessions = [...localSessions, ...uniqueStorageSessions];
          
          this.focusSessionsSubject.next(mergedSessions);
          this.saveDataToStorage();
          
          return of(mergedSessions);
        }),
        catchError(error => {
          console.error('Error fetching focus sessions from storage:', error);
          this.focusSessionsSubject.next(localSessions);
          return of(localSessions);
        })
      );
    }

    this.focusSessionsSubject.next(localSessions);
    return of(localSessions);
  }

  createFocusSession(session: Partial<FocusSession>): Observable<BasicResponse | FailureResponse> {
    const userId = this.getCurrentUserId();
    if (!userId) return of<FailureResponse>({ success: false, error: 'No user logged in' });

    // Create full session object
    const fullSession: FocusSession = {
      id: session.id || Date.now().toString(),
      userId: session.userId || userId,
      startTime: session.startTime || new Date().toISOString(),
      endTime: session.endTime,
      duration: session.duration || 0,
      location: session.location || {
        type: 'home' as any,
        name: 'Unknown',
        environment: 'quiet' as any
      },
      type: session.type || 'focus' as any,
      status: session.status || 'active' as any,
      goals: session.goals || [],
      achievements: session.achievements || [],
      accomplishments: session.accomplishments,
      distractions: session.distractions || [],
      socialInteractions: session.socialInteractions || [],
      phoneUsageReduction: session.phoneUsageReduction || 0,
      mindfulMoments: session.mindfulMoments || [],
      typeMetrics: session.typeMetrics || undefined,
      createdAt: session.createdAt || new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      notes: session.notes,
      moodBefore: session.moodBefore,
      moodAfter: session.moodAfter,
      llmEvaluation: session.llmEvaluation
    };

    // Add to local storage immediately
    const currentSessions = this.focusSessionsSubject.value;
    const updatedSessions = [...currentSessions, fullSession];
    this.focusSessionsSubject.next(updatedSessions);
    this.saveDataToStorage();

    // Also update storage.json user stats
    this.updateStorageJsonUserStats(userId, fullSession);

    // Try to sync with API (if backend is available)
    return this.http.post<BasicResponse>(`${this.API_URL}/focus-sessions`, session)
      .pipe(
        tap((response: BasicResponse) => {
          if (response.success) {
            this.saveDataToStorage();
          }
        }),
        catchError(error => {
          console.error('Error creating focus session (saved locally):', error);
          // Return success even if API fails, since we saved locally
          return of<BasicResponse>({ success: true });
        })
      );
  }

  /**
   * Update user stats in storage.json when a session is created
   */
  private updateStorageJsonUserStats(userId: string, session: FocusSession): void {
    const numericId = parseInt(userId);
    if (isNaN(numericId)) return;

    this.storageService.getUserById(numericId).subscribe(storageUser => {
      if (storageUser) {
        if (!storageUser.stats) {
          storageUser.stats = {
            todayStats: {
              sessionsCompleted: 0,
              totalMinutes: 0,
              averageSession: 0,
              streak: 0
            },
            focusSessions: []
          };
        }

        if (!storageUser.stats.focusSessions) {
          storageUser.stats.focusSessions = [];
        }

        // Add session to storage.json
        const sessionForStorage = {
          ...session,
          userId: numericId
        };
        storageUser.stats.focusSessions.push(sessionForStorage);

        // Update today stats
        const today = new Date().toISOString().split('T')[0];
        const sessionDate = new Date(session.startTime).toISOString().split('T')[0];
        
        if (sessionDate === today && session.status === 'completed') {
          const todayStats = storageUser.stats.todayStats || {
            sessionsCompleted: 0,
            totalMinutes: 0,
            averageSession: 0,
            streak: 0
          };
          
          todayStats.sessionsCompleted = (todayStats.sessionsCompleted || 0) + 1;
          todayStats.totalMinutes = (todayStats.totalMinutes || 0) + (session.duration || 0);
          todayStats.averageSession = Math.round(todayStats.totalMinutes / todayStats.sessionsCompleted);
          
          storageUser.stats.todayStats = todayStats;
        }

        // Update storage
        this.storageService.updateUser(numericId, { stats: storageUser.stats }).subscribe();
      }
    });
  }

  updateFocusSession(sessionId: string, updates: Partial<FocusSession>): Observable<BasicResponse | FailureResponse> {
    // Update local storage immediately
    const currentSessions = this.focusSessionsSubject.value;
    const sessionIndex = currentSessions.findIndex(s => s.id === sessionId);
    
    if (sessionIndex !== -1) {
      const updatedSession = {
        ...currentSessions[sessionIndex],
        ...updates,
        updatedAt: new Date().toISOString()
      };
      const updatedSessions = [...currentSessions];
      updatedSessions[sessionIndex] = updatedSession;
      this.focusSessionsSubject.next(updatedSessions);
      this.saveDataToStorage();
    }

    // Try to sync with API (if backend is available)
    return this.http.put<BasicResponse>(`${this.API_URL}/focus-sessions/${sessionId}`, updates)
      .pipe(
        tap((response: BasicResponse) => {
          if (response.success) {
            this.saveDataToStorage();
          }
        }),
        catchError(error => {
          console.error('Error updating focus session (saved locally):', error);
          // Return success even if API fails, since we saved locally
          return of<BasicResponse>({ success: true });
        })
      );
  }

  // Community Groups
  getCommunityGroups(): Observable<CommunityGroup[]> {
    // Always check storage.json first to get latest data, then update localStorage
    return this.storageService.loadStorage().pipe(
      switchMap(storageData => {
        if (storageData?.communityGroups && storageData.communityGroups.length > 0) {
          const groups = storageData.communityGroups as CommunityGroup[];
          this.communityGroupsSubject.next(groups);
          this.saveDataToStorage();
          return of(groups);
        }

        // If storage.json doesn't have groups, check localStorage
        const localData = this.loadDataFromStorage();
        if (localData?.communityGroups && localData.communityGroups.length > 0) {
          this.communityGroupsSubject.next(localData.communityGroups);
          return of(localData.communityGroups);
        }

        // Fallback to API (if backend is available)
        return this.http.get<CommunityGroup[]>(`${this.API_URL}/community/groups`)
          .pipe(
            tap(groups => {
              this.communityGroupsSubject.next(groups);
              this.saveDataToStorage();
            }),
            catchError(error => {
              console.error('Error fetching community groups:', error);
              this.communityGroupsSubject.next([]);
              return of([]);
            })
          );
      })
    );
  }

  getGroupById(id: string): Observable<CommunityGroup | null> {
    return this.getCommunityGroups().pipe(
      map(groups => groups.find(g => g.id === id) ?? null)
    );
  }

  getBusArrivals(busStopCode: string, serviceNo?: string): Observable<BusArrivalResponse> {
    let url = `${this.API_URL}/bus/arrivals?BusStopCode=${encodeURIComponent(busStopCode)}`;
    if (serviceNo != null && String(serviceNo).trim() !== '') {
      url += `&ServiceNo=${encodeURIComponent(String(serviceNo).trim())}`;
    }
    return this.http.get<BusArrivalResponse>(url);
  }

  /** Search stops by description, road name, or stop code (backend caches LTA BusStops). */
  searchBusStops(query: string): Observable<BusStopSearchResponse> {
    const params = new HttpParams().set('q', query.trim());
    return this.http.get<BusStopSearchResponse>(`${this.API_URL}/bus/stops/search`, { params });
  }

  joinCommunityGroup(groupId: string): Observable<BasicResponse | FailureResponse> {
    const userId = this.getCurrentUserId();
    if (!userId) return of<FailureResponse>({ success: false, error: 'No user logged in' });

    return this.http.post<BasicResponse>(`${this.API_URL}/community/groups/${groupId}/join`, { userId })
      .pipe(
        tap((response: BasicResponse) => {
          if (response.success) {
            this.refreshCommunityGroups();
          }
        }),
        catchError(error => {
          console.error('Error joining community group:', error);
          return of<FailureResponse>({ success: false, error: 'Join failed' });
        })
      );
  }

  createCommunityGroup(group: CommunityGroup): Observable<BasicResponse | FailureResponse> {
    return this.http.post<BasicResponse>(`${this.API_URL}/community/groups`, group)
      .pipe(
        tap((response: BasicResponse) => {
          if (response.success) {
            this.refreshCommunityGroups();
          }
        }),
        catchError(error => {
          console.error('Error creating community group:', error);
          // For now, simulate success and add to local storage
          const localGroups = [...(this.communityGroupsSubject.value || [])];
          localGroups.push(group);
          this.communityGroupsSubject.next(localGroups);
          this.saveDataToStorage();
          this.refreshCommunityGroups();
          return of<BasicResponse>({ success: true });
        })
      );
  }

  updateCommunityGroup(group: CommunityGroup): Observable<BasicResponse | FailureResponse> {
    return this.http.put<BasicResponse>(`${this.API_URL}/community/groups/${group.id}`, group)
      .pipe(
        tap((response: BasicResponse) => {
          if (response.success) {
            this.refreshCommunityGroups();
          }
        }),
        catchError(error => {
          console.error('Error updating community group:', error);
          // For now, simulate success and update local storage
          const localGroups = [...(this.communityGroupsSubject.value || [])];
          const index = localGroups.findIndex((g: CommunityGroup) => g.id === group.id);
          if (index !== -1) {
            localGroups[index] = group;
            this.communityGroupsSubject.next(localGroups);
            this.saveDataToStorage();
            this.storageService.updateCommunityGroups(localGroups);
            this.refreshCommunityGroups();
          }
          return of<BasicResponse>({ success: true });
        })
      );
  }

  deleteCommunityGroup(groupId: string): Observable<BasicResponse | FailureResponse> {
    return this.http.delete<BasicResponse>(`${this.API_URL}/community/groups/${groupId}`)
      .pipe(
        tap((response: BasicResponse) => {
          if (response.success) {
            this.refreshCommunityGroups();
          }
        }),
        catchError(error => {
          console.error('Error deleting community group:', error);
          // For now, simulate success and remove from local storage
          const localGroups = (this.communityGroupsSubject.value || []).filter((g: CommunityGroup) => g.id !== groupId);
          this.communityGroupsSubject.next(localGroups);
          this.saveDataToStorage();
          this.refreshCommunityGroups();
          return of<BasicResponse>({ success: true });
        })
      );
  }

  approveJoinRequest(groupId: string, requestId: string): Observable<BasicResponse | FailureResponse> {
    return this.http.post<BasicResponse>(`${this.API_URL}/community/groups/${groupId}/join-requests/${requestId}/approve`, {})
      .pipe(
        tap((response: BasicResponse) => {
          if (response.success) {
            this.refreshCommunityGroups();
          }
        }),
        catchError(error => {
          console.error('Error approving join request:', error);
          return of<FailureResponse>({ success: false, error: 'Approval failed' });
        })
      );
  }

  rejectJoinRequest(groupId: string, requestId: string): Observable<BasicResponse | FailureResponse> {
    return this.http.post<BasicResponse>(`${this.API_URL}/community/groups/${groupId}/join-requests/${requestId}/reject`, {})
      .pipe(
        tap((response: BasicResponse) => {
          if (response.success) {
            this.refreshCommunityGroups();
          }
        }),
        catchError(error => {
          console.error('Error rejecting join request:', error);
          return of<FailureResponse>({ success: false, error: 'Rejection failed' });
        })
      );
  }

  // Achievements
  getAchievements(userId?: string): Observable<Achievement[]> {
    const id = userId || this.getCurrentUserId();
    if (!id) return of([]);

    // Try to get from localStorage first
    const localData = this.loadDataFromStorage();
    if (localData?.achievements && Array.isArray(localData.achievements)) {
      this.achievementsSubject.next(localData.achievements);
      return of(localData.achievements);
    }

    // Try to get from storage.json via StorageService
    const numericId = parseInt(id);
    if (!isNaN(numericId)) {
      return this.storageService.getUserById(numericId).pipe(
        switchMap(storageUser => {
          if (storageUser && storageUser.achievements && Array.isArray(storageUser.achievements)) {
            const achievements = storageUser.achievements as Achievement[];
            this.achievementsSubject.next(achievements);
            this.saveDataToStorage();
            return of(achievements);
          }

          // Fallback to API (if backend is available)
          return this.http.get<Achievement[]>(`${this.API_URL}/achievements/${id}`)
            .pipe(
              tap(achievements => {
                this.achievementsSubject.next(achievements);
                this.saveDataToStorage();
              }),
              catchError(error => {
                console.error('Error fetching achievements:', error);
                this.achievementsSubject.next([]);
                return of([]);
              })
            );
        })
      );
    }

    return of([]);
  }

  // Get user goals
  getUserGoals(userId?: string): Observable<any[]> {
    const id = userId || this.getCurrentUserId();
    if (!id) return of([]);

    const numericId = parseInt(id);
    if (!isNaN(numericId)) {
      return this.storageService.getUserById(numericId).pipe(
        map(storageUser => {
          return storageUser?.goals || [];
        }),
        catchError(error => {
          console.error('Error fetching user goals:', error);
          return of([]);
        })
      );
    }

    return of([]);
  }

  // Get safety tips
  getSafetyTips(): Observable<any[]> {
    return this.storageService.loadStorage().pipe(
      map(storageData => {
        return storageData?.safetyTips || [];
      }),
      catchError(error => {
        console.error('Error fetching safety tips:', error);
        return of([]);
      })
    );
  }

  // Get emergency contacts
  getEmergencyContacts(): Observable<any[]> {
    return this.storageService.loadStorage().pipe(
      map(storageData => {
        return storageData?.emergencyContacts || [];
      }),
      catchError(error => {
        console.error('Error fetching emergency contacts:', error);
        return of([]);
      })
    );
  }

  // Public Awareness
  getPublicAwarenessData(): Observable<any> {
    return this.http.get(`${this.API_URL}/public-awareness`)
      .pipe(
        catchError(error => {
          console.error('Error fetching public awareness data:', error);
          return of(null);
        })
      );
  }

  // Insights and Analytics
  getPerformanceInsights(period: string = 'week'): Observable<any> {
    const userId = this.getCurrentUserId();
    if (!userId) return of(null);

    return this.http.get(`${this.API_URL}/insights/${userId}?period=${period}`)
      .pipe(
        catchError(error => {
          console.error('Error fetching performance insights:', error);
          return of(null);
        })
      );
  }

  /**
   * Evaluate session(s) via LLM: analysis of what happened, impact, what to improve, what improved.
   * Optionally saves evaluation to the first session (backend and local).
   */
  evaluateSessions(
    sessions: FocusSession[],
    options?: { saveToFirstSession?: boolean }
  ): Observable<{ success: boolean; evaluation?: any; error?: string }> {
    const userId = this.getCurrentUserId();
    if (!userId || !sessions.length) {
      return of({ success: false, error: 'No user or sessions' });
    }
    const saveToFirstSession = options?.saveToFirstSession === true;
    return this.http.post<{ success: boolean; evaluation?: any; error?: string }>(
      `${this.API_URL}/sessions/evaluate`,
      {
        userId,
        sessions: sessions.map(s => ({
          id: s.id,
          type: s.type,
          duration: s.duration,
          accomplishments: s.accomplishments,
          notes: s.notes,
          distractions: s.distractions,
          goals: s.goals,
          typeMetrics: s.typeMetrics,
          moodBefore: s.moodBefore,
          moodAfter: s.moodAfter,
          startTime: s.startTime,
          endTime: s.endTime
        })),
        saveToSessions: saveToFirstSession && sessions.length === 1
      }
    ).pipe(
      tap(res => {
        if (res.success && res.evaluation && saveToFirstSession && sessions.length === 1) {
          this.updateFocusSession(sessions[0].id, { llmEvaluation: res.evaluation }).subscribe();
        }
      }),
      catchError(err => {
        console.error('Evaluate sessions error:', err);
        return of({ success: false, error: err?.message || 'Evaluation failed' });
      })
    );
  }

  // Location Services
  getLocationData(): Observable<any> {
    return this.http.get(`${this.API_URL}/location`)
      .pipe(
        catchError(error => {
          console.error('Error fetching location data:', error);
          return of(null);
        })
      );
  }

  // Helper methods
  private getCurrentUserId(): string | null {
    const user = localStorage.getItem('currentUser');
    if (user) {
      try {
        return JSON.parse(user).id;
      } catch (error) {
        console.error('Error parsing current user:', error);
        return null;
      }
    }
    return null;
  }

  private refreshFocusSessions(): void {
    this.getFocusSessions().subscribe();
  }

  private refreshCommunityGroups(): void {
    this.getCommunityGroups().subscribe();
  }

  // Refresh all data
  refreshAllData(): void {
    this.getUserStats().subscribe();
    this.getFocusSessions().subscribe();
    this.getCommunityGroups().subscribe();
    this.getAchievements().subscribe();
  }

  // ==================== LOCAL STORAGE METHODS ====================

  private loadDataFromStorage(): LocalStorageData | null {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      if (stored) {
        const data: LocalStorageData = JSON.parse(stored);
        // Load data into subjects
        if (data.userStats) this.userStatsSubject.next(data.userStats);
        if (data.focusSessions) this.focusSessionsSubject.next(data.focusSessions);
        if (data.communityGroups) this.communityGroupsSubject.next(data.communityGroups);
        if (data.achievements) this.achievementsSubject.next(data.achievements);
        return data;
      }
    } catch (error) {
      console.error('Error loading data from storage:', error);
      localStorage.removeItem(this.STORAGE_KEY);
    }
    return null;
  }

  private saveDataToStorage(): void {
    try {
      const data: LocalStorageData = {
        userStats: this.userStatsSubject.value,
        focusSessions: this.focusSessionsSubject.value,
        communityGroups: this.communityGroupsSubject.value,
        achievements: this.achievementsSubject.value,
        lastUpdated: new Date().toISOString()
      };
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(data));
    } catch (error) {
      console.error('Error saving data to storage:', error);
      // Handle quota exceeded error
      if (error instanceof Error && error.name === 'QuotaExceededError') {
        console.warn('LocalStorage quota exceeded. Consider clearing old data.');
      }
    }
  }

  // ==================== EXPORT/IMPORT JSON FILE METHODS ====================

  /**
   * Export all user data to a JSON file
   */
  exportDataToFile(): void {
    const userId = this.getCurrentUserId();
    if (!userId) {
      console.error('No user logged in');
      return;
    }

    const data = {
      userId,
      exportDate: new Date().toISOString(),
      version: '1.0',
      userStats: this.userStatsSubject.value,
      focusSessions: this.focusSessionsSubject.value,
      communityGroups: this.communityGroupsSubject.value,
      achievements: this.achievementsSubject.value
    };

    const jsonString = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `mindful-moment-data-${userId}-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  /**
   * Import data from a JSON file
   */
  importDataFromFile(file: File): Promise<{ success: boolean; error?: string }> {
    return new Promise((resolve) => {
      const reader = new FileReader();
      
      reader.onload = (e: any) => {
        try {
          const importedData = JSON.parse(e.target.result);
          
          // Validate data structure
          if (!importedData.userId || importedData.userId !== this.getCurrentUserId()) {
            resolve({ success: false, error: 'Data does not belong to current user' });
            return;
          }

          // Import data
          if (importedData.userStats) {
            this.userStatsSubject.next(importedData.userStats);
          }
          if (importedData.focusSessions) {
            this.focusSessionsSubject.next(importedData.focusSessions);
          }
          if (importedData.communityGroups) {
            this.communityGroupsSubject.next(importedData.communityGroups);
          }
          if (importedData.achievements) {
            this.achievementsSubject.next(importedData.achievements);
          }

          // Save to localStorage
          this.saveDataToStorage();
          
          resolve({ success: true });
        } catch (error) {
          console.error('Error importing data:', error);
          resolve({ success: false, error: 'Invalid JSON file' });
        }
      };

      reader.onerror = () => {
        resolve({ success: false, error: 'Error reading file' });
      };

      reader.readAsText(file);
    });
  }

  /**
   * Clear all local data
   */
  clearAllData(): void {
    localStorage.removeItem(this.STORAGE_KEY);
    this.userStatsSubject.next(null);
    this.focusSessionsSubject.next([]);
    this.communityGroupsSubject.next([]);
    this.achievementsSubject.next([]);
  }
}
