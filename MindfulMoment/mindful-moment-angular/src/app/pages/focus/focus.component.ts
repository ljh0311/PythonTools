import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { AuthService } from '../../services/auth.service';
import { DataService } from '../../services/data.service';
import { LocationService, GPSStatus } from '../../services/location.service';
import { StatsService } from '../../services/stats.service';
import { DeviceMetricsService } from '../../services/device-metrics.service';
import { FocusSimulationService } from '../../services/focus-simulation.service';
import { GpsStatusComponent } from '../../components/gps-status/gps-status.component';
import { User } from '../../models/user.model';
import { FocusSession, Distraction, DistractionType } from '../../models/focus-session.model';
import { BusArrivalResponse, BusArrivalNextBus } from '../../models/bus-arrival.model';

@Component({
  selector: 'app-focus',
  templateUrl: './focus.component.html',
  styleUrls: ['./focus.component.scss'],
  imports: [CommonModule, FormsModule, GpsStatusComponent, RouterLink],
  standalone: true
})
export class FocusComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  
  // Make Math available in template
  Math = Math;
  
  currentUser: User | null = null;
  isSessionActive = false;
  currentSession: FocusSession | null = null;
  sessionDuration = 25; // minutes
  timeRemaining = 0; // seconds
  sessionProgress = 0; // percentage
  sessionTimer: any = null;
  
  // Session types: Study sessions and Travel safety (device usage near road/MRT etc.)
  sessionTypes = [
    {
      id: 'study',
      name: 'Study Session',
      icon: 'fas fa-book',
      description: 'Focused study time with minimal device use',
      color: '#4A90E2',
      guidance: [
        'Choose a quiet space and put your phone away or on silent',
        'Set a clear goal for what you want to learn or complete',
        'Use the timer to stay in focused blocks (e.g. 25–30 min)',
        'Note distractions and return to the material without checking your device',
        'After the session, briefly note what you covered for later review'
      ],
      sound: 'focus'
    },
    {
      id: 'travel-safety',
      name: 'Travel Safety',
      icon: 'fas fa-shield-alt',
      description: 'Keep device away near roads, MRT platforms, and crossings',
      color: '#DC3545',
      guidance: [
        'Put your phone away when approaching roads, MRT platforms, or crossings',
        'Stay aware of your surroundings and other people',
                'Use this session to track time spent device-free in risk zones',
        'Acknowledge safety reminders so the app can support your habits',
        'When you reach your destination, end the session to log your safe travel'
      ],
      sound: 'safety'
    }
  ];

  selectedSessionType = 'study';
  selectedDuration = 25;
  durationOptions = [5, 10, 15, 25, 30, 45, 60];
  
  // Type-specific goals
  typeSpecificGoals: { [key: string]: any[] } = {
    study: [
      { id: 'concentration', name: 'Improve Concentration', icon: 'fas fa-bullseye' },
      { id: 'deep-work', name: 'Deep Work Block', icon: 'fas fa-laptop-code' },
      { id: 'task-completion', name: 'Complete Tasks', icon: 'fas fa-check-circle' },
      { id: 'revision', name: 'Revision / Review', icon: 'fas fa-book-open' }
    ],
    'travel-safety': [
      { id: 'road-crossing', name: 'Device away at crossings', icon: 'fas fa-traffic-light' },
      { id: 'mrt-platform', name: 'Device away on MRT platform', icon: 'fas fa-train' },
      { id: 'walking', name: 'Device away while walking', icon: 'fas fa-walking' },
      { id: 'general', name: 'General travel awareness', icon: 'fas fa-shield-alt' }
    ]
  };

  // Current session goals based on type
  get sessionGoals() {
    return this.typeSpecificGoals[this.selectedSessionType] || this.typeSpecificGoals['study'];
  }
  
  selectedGoals: string[] = [];
  
  // Type-specific metrics
  currentMetrics: any = {
    steps: 0,
    distance: 0,
    breathingRate: 0,
    breathingCycles: 0,
    meditationDepth: 5,
    focusClarity: 5,
    awarenessLevel: 5,
    presentMomentScore: 5,
    distractionCount: 0,
    focusIntensity: 5,
    tasksCompleted: 0,
    studyMinutes: 0,
    topicsCovered: 0,
    safeZoneMinutes: 0,
    alertsAcknowledged: 0,
    noiseLevel: null
  };
  
  // Guidance display
  currentGuidance: string[] = [];
  guidanceIndex = 0;
  showGuidance = true;
  
  // Session statistics
  todayStats = {
    sessionsCompleted: 0,
    totalMinutes: 0,
    averageSession: 0,
    streak: 0
  };

  // Location tracking
  currentLocation: any = null;
  locationHistory: any[] = [];
  isLocationTracking = false;
  gpsStatus: GPSStatus | null = null;
  /** Throttle Nominatim reverse-geocode during continuous GPS (every tick would violate usage policy). */
  private lastReverseGeocodeAt = 0;
  private static readonly REVERSE_GEOCODE_MIN_MS = 15000;

  // Device metrics subscription
  private deviceMetricsSubscription: any = null;

  // Post-session reflection modal
  showPostSessionModal = false;
  postSessionAccomplishments = '';
  postSessionWasDistracted = false;
  postSessionDistractions: { type: string; description: string }[] = [];

  // Bus arrivals (Travel Safety integration)
  busStopCode = '';
  busArrivalsResult: BusArrivalResponse | null = null;
  busArrivalsLoading = false;
  busArrivalsError: string | null = null;
  showCheckBusTimesCta = false;

  distractionTypeOptions: { value: DistractionType; label: string }[] = [
    { value: 'phone' as DistractionType, label: 'Phone' },
    { value: 'noise' as DistractionType, label: 'Noise' },
    { value: 'people' as DistractionType, label: 'People' },
    { value: 'thoughts' as DistractionType, label: 'Thoughts' },
    { value: 'environment' as DistractionType, label: 'Environment' }
  ];

  /** Session ID for which we're loading AI evaluation */
  evaluatingSessionId: string | null = null;

  // Past sessions
  pastSessions: FocusSession[] = [];
  filteredSessions: FocusSession[] = [];
  showPastSessions = false;
  sessionFilter = {
    type: 'all',
    dateRange: 'all',
    sortBy: 'date-desc' // date-desc, date-asc, duration-desc, duration-asc
  };

  constructor(
    private authService: AuthService,
    private dataService: DataService,
    private locationService: LocationService,
    private statsService: StatsService,
    private deviceMetricsService: DeviceMetricsService,
    private focusSimulationService: FocusSimulationService,
    private router: Router
  ) {}

  ngOnInit() {
    this.loadUserData();
    this.loadTodayStats();
    this.loadPastSessions();

    this.focusSimulationService.simulationEvents$
      .pipe(takeUntil(this.destroy$))
      .subscribe(event => {
        if (!this.isSessionActive || !this.currentSession) return;
        if (event.type === 'distraction') {
          this.recordDistraction();
          const type = event.distractionType ?? DistractionType.PHONE;
          const description = event.description ?? `Simulated ${type} distraction`;
          const distraction: Distraction = {
            id: `sim-dist-${Date.now()}`,
            type,
            description,
            duration: 0,
            timestamp: new Date().toISOString(),
            handled: false
          };
          this.currentSession.distractions = this.currentSession.distractions ?? [];
          this.currentSession.distractions.push(distraction);
        }
      });
    
    // Subscribe to GPS status
    this.locationService.gpsStatus$
      .pipe(takeUntil(this.destroy$))
      .subscribe((status: GPSStatus) => {
        this.gpsStatus = status;
      });
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
    if (this.sessionTimer) {
      clearInterval(this.sessionTimer);
    }
    this.deviceMetricsService.stopAllMetrics();
    this.stopLocationTracking();
  }

  private loadUserData() {
    this.authService.currentUser$
      .pipe(takeUntil(this.destroy$))
      .subscribe(user => {
        this.currentUser = user;
      });
  }

  private loadTodayStats() {
    // Calculate today's stats from saved sessions
    this.dataService.getFocusSessions()
      .pipe(takeUntil(this.destroy$))
      .subscribe(sessions => {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        // Filter sessions from today
        const todaySessions = sessions.filter(session => {
          const sessionDate = new Date(session.startTime);
          sessionDate.setHours(0, 0, 0, 0);
          return sessionDate.getTime() === today.getTime() && session.status === 'completed';
        });
        
        // Calculate stats
        const sessionsCompleted = todaySessions.length;
        const totalMinutes = todaySessions.reduce((sum, session) => sum + (session.duration || 0), 0);
        const averageSession = sessionsCompleted > 0 ? Math.round(totalMinutes / sessionsCompleted) : 0;
        
        // Calculate streak (consecutive days with at least one session)
        const streak = this.calculateStreak(sessions);
        
        this.todayStats = {
          sessionsCompleted,
          totalMinutes,
          averageSession,
          streak
        };
      });
  }

  /**
   * Load past sessions
   */
  private loadPastSessions() {
    this.dataService.getFocusSessions()
      .pipe(takeUntil(this.destroy$))
      .subscribe(sessions => {
        // Filter only completed sessions
        this.pastSessions = sessions.filter(s => s.status === 'completed');
        this.applyFilters();
      });
  }

  /**
   * Apply filters to past sessions
   */
  applyFilters() {
    let filtered = [...this.pastSessions];

    // Filter by type
    if (this.sessionFilter.type !== 'all') {
      filtered = filtered.filter(s => s.type === this.sessionFilter.type);
    }

    // Filter by date range
    const now = new Date();
    switch (this.sessionFilter.dateRange) {
      case 'today':
        const today = new Date(now);
        today.setHours(0, 0, 0, 0);
        filtered = filtered.filter(s => {
          const sessionDate = new Date(s.startTime);
          sessionDate.setHours(0, 0, 0, 0);
          return sessionDate.getTime() === today.getTime();
        });
        break;
      case 'week':
        const weekAgo = new Date(now);
        weekAgo.setDate(weekAgo.getDate() - 7);
        filtered = filtered.filter(s => new Date(s.startTime) >= weekAgo);
        break;
      case 'month':
        const monthAgo = new Date(now);
        monthAgo.setMonth(monthAgo.getMonth() - 1);
        filtered = filtered.filter(s => new Date(s.startTime) >= monthAgo);
        break;
    }

    // Sort sessions
    filtered.sort((a, b) => {
      switch (this.sessionFilter.sortBy) {
        case 'date-asc':
          return new Date(a.startTime).getTime() - new Date(b.startTime).getTime();
        case 'date-desc':
          return new Date(b.startTime).getTime() - new Date(a.startTime).getTime();
        case 'duration-desc':
          return (b.duration || 0) - (a.duration || 0);
        case 'duration-asc':
          return (a.duration || 0) - (b.duration || 0);
        default:
          return new Date(b.startTime).getTime() - new Date(a.startTime).getTime();
      }
    });

    this.filteredSessions = filtered;
  }

  /**
   * Toggle past sessions view
   */
  togglePastSessions() {
    this.showPastSessions = !this.showPastSessions;
    if (this.showPastSessions) {
      this.loadPastSessions();
    }
  }

  /**
   * Format date for display
   */
  formatDate(dateString: string): string {
    const date = new Date(dateString);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const sessionDate = new Date(date);
    sessionDate.setHours(0, 0, 0, 0);

    if (sessionDate.getTime() === today.getTime()) {
      return 'Today';
    }

    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    if (sessionDate.getTime() === yesterday.getTime()) {
      return 'Yesterday';
    }

    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined 
    });
  }

  /**
   * Format time for display
   */
  formatTimeDisplay(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit' 
    });
  }

  /**
   * Get session metrics summary
   */
  getSessionMetricsSummary(session: FocusSession): string {
    if (!session.typeMetrics) return '';

    const metrics = session.typeMetrics;
    const type = session.type;

    switch (type) {
      case 'study':
        return `${metrics.tasksCompleted || 0} tasks • ${metrics.distractionCount || 0} distractions • ${metrics.studyMinutes || session.duration || 0} min`;
      case 'travel-safety':
        return `${metrics.safeZoneMinutes || 0} safe min • ${metrics.alertsAcknowledged || 0} alerts • ${((metrics.distance || 0) / 1000).toFixed(2)} km`;
      case 'walking':
        return `${metrics.steps || 0} steps • ${((metrics.distance || 0) / 1000).toFixed(2)} km`;
      case 'focus':
        return `${metrics.tasksCompleted || 0} tasks • ${metrics.distractionCount || 0} distractions`;
      default:
        return '';
    }
  }

  private calculateStreak(sessions: FocusSession[]): number {
    if (sessions.length === 0) return 0;
    
    const completedSessions = sessions
      .filter(s => s.status === 'completed')
      .map(s => new Date(s.startTime).toDateString())
      .filter((date, index, self) => self.indexOf(date) === index) // unique dates
      .sort((a, b) => new Date(b).getTime() - new Date(a).getTime()); // sort descending
    
    if (completedSessions.length === 0) return 0;
    
    let streak = 0;
    const today = new Date().toDateString();
    let expectedDate = new Date(today);
    
    for (const sessionDate of completedSessions) {
      const sessionDateStr = new Date(sessionDate).toDateString();
      const expectedDateStr = expectedDate.toDateString();
      
      if (sessionDateStr === expectedDateStr) {
        streak++;
        expectedDate.setDate(expectedDate.getDate() - 1);
      } else if (streak === 0 && sessionDateStr === today) {
        // If today has a session, start streak
        streak = 1;
        expectedDate.setDate(expectedDate.getDate() - 1);
      } else {
        break;
      }
    }
    
    return streak;
  }

  startSession() {
    if (!this.currentUser) {
      this.router.navigate(['/login']);
      return;
    }
    this.showCheckBusTimesCta = false;
    this.lastReverseGeocodeAt = 0;

    this.isSessionActive = true;
    this.timeRemaining = this.selectedDuration * 60; // Convert to seconds
    this.sessionProgress = 0;

    // Get current session type config
    const sessionTypeConfig = this.sessionTypes.find(t => t.id === this.selectedSessionType);
    this.currentGuidance = sessionTypeConfig?.guidance || [];
    this.guidanceIndex = 0;

    // Initialize type-specific metrics
    this.initializeTypeMetrics(this.selectedSessionType);

    // Start location tracking if enabled
    this.startLocationTracking();

    // Create new session
    this.currentSession = {
      id: Date.now().toString(),
      userId: this.currentUser.id,
      startTime: new Date().toISOString(),
      duration: this.selectedDuration,
      type: this.selectedSessionType as any,
      status: 'active' as any,
      goals: this.selectedGoals.map(goalId => ({
        id: goalId,
        description: this.sessionGoals.find(g => g.id === goalId)?.name || '',
        completed: false,
        category: this.selectedSessionType as any
      })),
      achievements: [],
      distractions: [],
      socialInteractions: [],
      phoneUsageReduction: 0,
      mindfulMoments: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      location: {
        type: 'home' as any,
        name: 'Unknown',
        environment: 'quiet' as any
      },
      typeMetrics: this.getTypeMetrics()
    };

    // Start timer and metrics tracking
    this.startTimer();
    this.startMetricsTracking();
  }

  /**
   * Start location tracking (now handled by DeviceMetricsService for walking sessions)
   */
  private startLocationTracking(): void {
    if (!this.locationService.isLocationEnabled()) {
      console.log('Location tracking is disabled in settings');
      return;
    }

    this.isLocationTracking = true;
    this.locationHistory = [];

    // For travel-safety and walking, continuous location is handled by DeviceMetricsService
    // For other sessions, get initial location only
    if (this.selectedSessionType !== 'walking' && this.selectedSessionType !== 'travel-safety') {
      this.locationService.getCurrentLocation().subscribe({
        next: (location) => {
          this.currentLocation = location;
          this.locationHistory.push(location);
          this.updateSessionLocation(location);
        },
        error: (error) => {
          console.error('Error getting location:', error);
          // Use default location
          this.updateSessionLocation(null);
        }
      });
    }
  }

  /**
   * Update session location with current or detected location
   */
  private updateSessionLocation(location: any): void {
    if (!this.currentSession) return;

    if (location) {
      const coords = {
        latitude: location.latitude,
        longitude: location.longitude
      };
      this.currentSession.location = {
        ...this.currentSession.location,
        coordinates: coords
      } as any;
      this.currentSession.updatedAt = new Date().toISOString();

      const now = Date.now();
      if (
        this.lastReverseGeocodeAt > 0 &&
        now - this.lastReverseGeocodeAt < FocusComponent.REVERSE_GEOCODE_MIN_MS
      ) {
        return;
      }
      this.lastReverseGeocodeAt = now;

      this.locationService.getLocationInfo(location).subscribe({
        next: (info) => {
          if (this.currentSession) {
            // Ensure we don't save coordinate strings as location names
            let locationName = info.name;
            if (locationName && locationName.startsWith('Location at')) {
              // If we got a coordinate string, use the type-based name instead
              locationName = this.getLocationNameFromType(info.type);
            }

            this.currentSession.location = {
              type: info.type as any,
              name: locationName,
              address: info.address,
              environment: info.environment as any,
              coordinates: coords
            };
            this.currentSession.updatedAt = new Date().toISOString();
          }
        },
        error: () => {
          // Fallback to basic location
          if (this.currentSession) {
            this.currentSession.location = {
              type: 'public' as any,
              name: 'Current Location',
              environment: 'quiet' as any,
              coordinates: coords
            };
          }
        }
      });
    } else {
      // Default location if tracking fails
      if (this.currentSession) {
        this.currentSession.location = {
          type: 'home' as any,
          name: 'Unknown Location',
          environment: 'quiet' as any
        };
      }
    }
  }

  /**
   * Get a user-friendly location name from type
   */
  private getLocationNameFromType(type: string): string {
    switch (type) {
      case 'home':
        return 'Home';
      case 'work':
        return 'Work';
      case 'transport':
        return 'In Transit';
      case 'public':
        return 'Public Space';
      case 'outdoor':
        return 'Outdoor';
      default:
        return 'Current Location';
    }
  }

  private initializeTypeMetrics(type: string) {
    // Reset metrics based on type
    switch (type) {
      case 'study':
        this.currentMetrics.distractionCount = 0;
        this.currentMetrics.focusIntensity = 5;
        this.currentMetrics.tasksCompleted = 0;
        this.currentMetrics.studyMinutes = 0;
        this.currentMetrics.topicsCovered = 0;
        break;
      case 'travel-safety':
        this.currentMetrics.safeZoneMinutes = 0;
        this.currentMetrics.alertsAcknowledged = 0;
        this.currentMetrics.steps = 0;
        this.currentMetrics.distance = 0;
        break;
    }
  }

  private getTypeMetrics(): any {
    const type = this.selectedSessionType;
    const metrics: any = {};

    switch (type) {
      case 'study':
        metrics.distractionCount = this.currentMetrics.distractionCount;
        metrics.focusIntensity = this.currentMetrics.focusIntensity;
        metrics.tasksCompleted = this.currentMetrics.tasksCompleted;
        metrics.studyMinutes = this.currentMetrics.studyMinutes;
        metrics.topicsCovered = this.currentMetrics.topicsCovered;
        break;
      case 'travel-safety':
        metrics.safeZoneMinutes = this.currentMetrics.safeZoneMinutes;
        metrics.alertsAcknowledged = this.currentMetrics.alertsAcknowledged;
        metrics.steps = this.currentMetrics.steps;
        metrics.distance = this.currentMetrics.distance;
        break;
    }

    return metrics;
  }

  /**
   * Starts metrics tracking for the active session.
   * Device-based metrics (microphone, GPS, sensors) are handled by DeviceMetricsService.
   * Non-device metrics (simulated values) are tracked locally.
   */
  private metricsIntervals: { [key: string]: any } = {};

  private startMetricsTracking() {
    // Start device-based metrics tracking via service
    this.deviceMetricsService.startSessionMetrics(this.selectedSessionType)
      .pipe(takeUntil(this.destroy$))
      .subscribe(metrics => {
        // Update currentMetrics with device data
        if (metrics.noiseLevel) {
          this.currentMetrics.noiseLevel = metrics.noiseLevel; // Store full NoiseLevelData object
        }
        if (metrics.steps) {
          this.currentMetrics.steps = metrics.steps.steps;
          this.currentMetrics.distance = metrics.steps.distance;
        }
        if (metrics.location) {
          this.currentLocation = metrics.location;
          this.locationHistory.push(metrics.location);
          this.updateSessionLocation(metrics.location);
        }
      });

    // Study: track study minutes (increment every minute)
    if (this.selectedSessionType === 'study') {
      this.metricsIntervals['study'] = setInterval(() => {
        if (this.isSessionActive) {
          this.currentMetrics.studyMinutes = (this.currentMetrics.studyMinutes || 0) + 1;
        }
      }, 60000);
    }

    // Travel safety: track safe-zone minutes (device away in risk zones)
    if (this.selectedSessionType === 'travel-safety') {
      this.metricsIntervals['travel-safety'] = setInterval(() => {
        if (this.isSessionActive) {
          this.currentMetrics.safeZoneMinutes = (this.currentMetrics.safeZoneMinutes || 0) + 1;
        }
      }, 60000);
    }
  }

  /**
   * Call this function to clear all metrics intervals on pause/end.
   */
  private stopMetricsTracking() {
    // Stop device metrics tracking
    this.deviceMetricsService.stopAllMetrics();
    
    // Clear local intervals
    Object.values(this.metricsIntervals).forEach(interval => clearInterval(interval));
    this.metricsIntervals = {};
  }

  pauseSession() {
    if (this.sessionTimer) {
      clearInterval(this.sessionTimer);
      this.sessionTimer = null;
    }
  }

  resumeSession() {
    this.startTimer();
  }

  /** Opens the post-session reflection modal instead of ending immediately */
  requestEndSession() {
    this.showPostSessionModal = true;
    this.postSessionAccomplishments = '';
    this.postSessionWasDistracted = false;
    this.postSessionDistractions = [];
  }

  cancelPostSessionModal() {
    this.showPostSessionModal = false;
    this.postSessionAccomplishments = '';
    this.postSessionWasDistracted = false;
    this.postSessionDistractions = [];
  }

  addPostSessionDistraction() {
    this.postSessionDistractions.push({ type: 'phone', description: '' });
  }

  onDistractedCheckChange(checked: boolean) {
    if (checked && this.postSessionDistractions.length === 0) {
      this.addPostSessionDistraction();
    }
  }

  removePostSessionDistraction(index: number) {
    this.postSessionDistractions.splice(index, 1);
  }

  loadBusArrivals(): void {
    const code = this.busStopCode?.trim();
    if (!code) {
      this.busArrivalsError = 'Please enter a bus stop code';
      return;
    }
    this.busArrivalsError = null;
    this.busArrivalsResult = null;
    this.busArrivalsLoading = true;
    this.dataService
      .getBusArrivals(code)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data) => {
          this.busArrivalsResult = data;
          this.busArrivalsLoading = false;
        },
        error: (err) => {
          this.busArrivalsLoading = false;
          const status = err?.status;
          const body = err?.error;
          if (status === 503 || (body && body.error === 'Bus arrivals not configured')) {
            this.busArrivalsError = 'Bus arrivals not configured';
          } else {
            this.busArrivalsError = body?.error || err?.message || 'Unable to load bus arrivals';
          }
        }
      });
  }

  formatBusEta(eta: BusArrivalNextBus | undefined): string {
    if (!eta?.EstimatedArrival) return '--';
    try {
      const date = new Date(eta.EstimatedArrival);
      const now = new Date();
      const diffMs = date.getTime() - now.getTime();
      const diffMin = Math.round(diffMs / 60000);
      if (diffMin < 0) return 'Arriving';
      if (diffMin < 1) return '1 min';
      return `${diffMin} min`;
    } catch {
      return eta.EstimatedArrival;
    }
  }

  /** Apply reflection data to session and end session */
  confirmEndSession() {
    if (this.currentSession) {
      this.currentSession.accomplishments = this.postSessionAccomplishments.trim() || undefined;
      const now = new Date().toISOString();
      this.currentSession.distractions = this.postSessionDistractions
        .filter(d => d.description.trim())
        .map((d, i) => ({
          id: `dist-${Date.now()}-${i}`,
          type: (d.type || 'thoughts') as DistractionType,
          description: d.description.trim(),
          duration: 0,
          timestamp: now,
          handled: false
        }));
    }
    this.showPostSessionModal = false;
    this.postSessionAccomplishments = '';
    this.postSessionWasDistracted = false;
    this.postSessionDistractions = [];
    this.showCheckBusTimesCta = this.currentSession?.type === 'travel-safety';
    this.endSession();
  }

  endSession() {
    if (this.sessionTimer) {
      clearInterval(this.sessionTimer);
      this.sessionTimer = null;
    }

    // Stop device metrics first (owns GPS watch subscription for travel-safety / walking)
    this.deviceMetricsService.stopAllMetrics();

    this.stopLocationTracking();

    this.isSessionActive = false;
    this.timeRemaining = 0;
    this.sessionProgress = 100;

    if (this.currentSession) {
      // Calculate actual duration
      const startTime = new Date(this.currentSession.startTime);
      const endTime = new Date();
      const durationMinutes = Math.floor((endTime.getTime() - startTime.getTime()) / 1000 / 60);
      
      // Update final location
      if (this.currentLocation && this.currentSession.location) {
        this.currentSession.location.coordinates = {
          latitude: this.currentLocation.latitude,
          longitude: this.currentLocation.longitude
        };
      }
      
      this.currentSession.endTime = endTime.toISOString();
      this.currentSession.status = 'completed' as any;
      this.currentSession.duration = durationMinutes;
      this.currentSession.updatedAt = endTime.toISOString();
      this.currentSession.typeMetrics = this.getTypeMetrics();
      
      // Check for type-specific achievements
      this.checkTypeSpecificAchievements();
      
      // Save session
      this.dataService.createFocusSession(this.currentSession).subscribe({
        next: () => {
          console.log('Session saved successfully');
          // Refresh stats
          this.statsService.refreshStats();
          this.loadTodayStats();
          this.loadPastSessions();
        },
        error: (error) => {
          console.error('Error saving session:', error);
        }
      });
    }

    this.currentSession = null;
    this.currentLocation = null;
    this.locationHistory = [];
    this.showGuidance = true;
  }

  /**
   * Stop location tracking
   */
  private stopLocationTracking(): void {
    if (this.isLocationTracking) {
      this.locationService.stopTracking();
      this.isLocationTracking = false;
    }
  }


  private checkTypeSpecificAchievements() {
    if (!this.currentSession) return;

    const achievements: string[] = [];
    const type = this.selectedSessionType;
    const metrics = this.currentMetrics;

    switch (type) {
      case 'study':
        if (metrics.distractionCount === 0 && this.selectedDuration >= 25) achievements.push('undistracted-study');
        if (metrics.tasksCompleted >= 3) achievements.push('productive-study');
        if ((metrics.studyMinutes || this.currentSession.duration) >= 30) achievements.push('study-30min');
        break;
      case 'travel-safety':
        if ((metrics.safeZoneMinutes || this.currentSession.duration) >= 10) achievements.push('safe-travel-10min');
        if (metrics.alertsAcknowledged >= 1) achievements.push('safety-alert-acknowledged');
        break;
    }

    this.currentSession.achievements = [...(this.currentSession.achievements || []), ...achievements];
  }

  // Navigation through guidance
  nextGuidance() {
    if (this.guidanceIndex < this.currentGuidance.length - 1) {
      this.guidanceIndex++;
    }
  }

  previousGuidance() {
    if (this.guidanceIndex > 0) {
      this.guidanceIndex--;
    }
  }

  toggleGuidance() {
    this.showGuidance = !this.showGuidance;
  }

  // Type-specific metric updates
  updateBreathingRate(rate: number) {
    this.currentMetrics.breathingRate = rate;
  }

  recordBreathingCycle() {
    this.currentMetrics.breathingCycles++;
  }

  recordDistraction() {
    this.currentMetrics.distractionCount++;
  }

  completeTask() {
    this.currentMetrics.tasksCompleted++;
  }

  acknowledgeSafetyAlert() {
    this.currentMetrics.alertsAcknowledged = (this.currentMetrics.alertsAcknowledged || 0) + 1;
  }

  updateMeditationDepth(level: number) {
    this.currentMetrics.meditationDepth = level;
  }

  updateAwarenessLevel(level: number) {
    this.currentMetrics.awarenessLevel = level;
  }

  private startTimer() {
    this.sessionTimer = setInterval(() => {
      if (this.timeRemaining > 0) {
        this.timeRemaining--;
        this.sessionProgress = ((this.selectedDuration * 60 - this.timeRemaining) / (this.selectedDuration * 60)) * 100;
      } else {
        this.endSession();
      }
    }, 1000);
  }

  formatTime(seconds: number): string {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  }

  toggleGoal(goalId: string) {
    const index = this.selectedGoals.indexOf(goalId);
    if (index > -1) {
      this.selectedGoals.splice(index, 1);
    } else {
      this.selectedGoals.push(goalId);
    }
  }

  private legacyTypeNames: Record<string, string> = {
    focus: 'Focus',
    walking: 'Walking',
    meditation: 'Meditation',
    mindfulness: 'Mindfulness',
    breathing: 'Breathing'
  };

  private legacyTypeIcons: Record<string, string> = {
    focus: 'fas fa-bolt',
    walking: 'fas fa-walking',
    meditation: 'fas fa-om',
    mindfulness: 'fas fa-leaf',
    breathing: 'fas fa-wind'
  };

  getSessionTypeIcon(type: string): string {
    const sessionType = this.sessionTypes.find(t => t.id === type);
    return sessionType?.icon || this.legacyTypeIcons[type] || 'fas fa-bolt';
  }

  getSessionTypeName(type: string): string {
    const sessionType = this.sessionTypes.find(t => t.id === type);
    return sessionType?.name || this.legacyTypeNames[type] || 'Focus Session';
  }

  getSelectedSessionTypeColor(): string {
    const sessionType = this.sessionTypes.find(t => t.id === this.selectedSessionType);
    return sessionType?.color || '#4A90E2';
  }

  getSelectedSessionTypeName(): string {
    const sessionType = this.sessionTypes.find(t => t.id === this.selectedSessionType);
    return sessionType?.name || 'Focus Session';
  }

  getSelectedSessionTypeGuidance(): string[] {
    const sessionType = this.sessionTypes.find(t => t.id === this.selectedSessionType);
    return sessionType?.guidance || [];
  }

  getSessionTypeColor(type: string): string {
    const sessionType = this.sessionTypes.find(t => t.id === type);
    return sessionType?.color || '#4A90E2';
  }

  getGoalsDescription(session: FocusSession): string {
    if (!session.goals || session.goals.length === 0) return '';
    return session.goals.map(g => g.description).join(', ');
  }

  /**
   * Get a sanitized location name for display
   */
  getLocationDisplayName(session: FocusSession): string {
    if (!session.location || !session.location.name) return 'Unknown Location';
    
    const name = session.location.name;
    
    // Check if it's a coordinate string and sanitize it
    if (name.startsWith('Location at')) {
      return this.getLocationNameFromType(session.location.type);
    }
    
    // Check if it's just coordinates
    const coordPattern = /^[\d.]+,\s*[\d.]+$/;
    if (coordPattern.test(name.trim())) {
      return this.getLocationNameFromType(session.location.type);
    }
    
    return name;
  }

  navigateToHome() {
    this.router.navigate(['/home']);
  }

  navigateToInsights() {
    this.router.navigate(['/insights']);
  }

  /** Request AI evaluation for a single session; saves to session and refreshes list */
  getAIReflection(session: FocusSession) {
    if (this.evaluatingSessionId === session.id) return;
    this.evaluatingSessionId = session.id;
    this.dataService.evaluateSessions([session], { saveToFirstSession: true }).subscribe({
      next: (res) => {
        this.evaluatingSessionId = null;
        if (res.success) {
          this.loadPastSessions();
        }
      },
      error: () => {
        this.evaluatingSessionId = null;
      }
    });
  }
}
