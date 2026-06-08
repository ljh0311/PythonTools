import { Component, OnInit, OnDestroy, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { Chart, ChartConfiguration, ChartType, registerables } from 'chart.js';
import { AuthService } from '../../services/auth.service';
import { DataService } from '../../services/data.service';
import { StatsService } from '../../services/stats.service';
import { User } from '../../models/user.model';
import { FocusSession } from '../../models/focus-session.model';

// Register Chart.js components
Chart.register(...registerables);

@Component({
  selector: 'app-insights',
  templateUrl: './insights.component.html',
  styleUrls: ['./insights.component.scss'],
  imports: [CommonModule, DecimalPipe],
  standalone: true
})
export class InsightsComponent implements OnInit, OnDestroy, AfterViewInit {
  private destroy$ = new Subject<void>();
  
  @ViewChild('weeklyChartCanvas', { static: false }) weeklyChartCanvas!: ElementRef<HTMLCanvasElement>;
  @ViewChild('sessionsChartCanvas', { static: false }) sessionsChartCanvas!: ElementRef<HTMLCanvasElement>;
  
  // Make Math available in template
  Math = Math;
  
  currentUser: User | null = null;
  selectedPeriod = 'week';
  isLoading = false;
  
  // Chart instances
  private weeklyChart: Chart | null = null;
  private sessionsChart: Chart | null = null;

  // Period options for filtering
  periodOptions = [
    { id: 'week', label: 'Week' },
    { id: 'month', label: 'Month' },
    { id: 'all', label: 'All Time' }
  ];
  
  // Performance metrics
  performanceMetrics = {
    focusSessions: 0,
    mindfulTime: 0,
    socialInteractions: 0,
    phoneReduction: 0,
    focusSessionsChange: 0,
    mindfulTimeChange: 0,
    socialInteractionsChange: 0,
    phoneReductionChange: 0
  };
  
  // Weekly breakdown data
  weeklyData: any[] = [];
  
  // Achievement progress
  achievements: any[] = [];
  
  // Location performance
  locationPerformance: any[] = [];

  // Session stats
  sessionStats: any = null;

  // Recent sessions for accomplishments/distractions and LLM
  recentSessions: FocusSession[] = [];
  llmEvaluation: any = null;
  llmLoading = false;
  llmError: string | null = null;

  constructor(
    private authService: AuthService,
    private dataService: DataService,
    private statsService: StatsService,
    private router: Router
  ) {}

  ngOnInit() {
    this.loadUserData();
    this.loadInsightsData();
    this.loadSessionStats();
    this.loadWeeklyBreakdown();
    this.loadAchievements();
    this.loadLocationPerformance();
    this.loadRecentSessions();
  }

  ngAfterViewInit() {
    // Wait a bit for view to be fully initialized
    setTimeout(() => {
      this.initializeCharts();
    }, 100);
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
    
    // Destroy charts
    if (this.weeklyChart) {
      this.weeklyChart.destroy();
    }
    if (this.sessionsChart) {
      this.sessionsChart.destroy();
    }
  }

  private loadUserData() {
    this.authService.currentUser$
      .pipe(takeUntil(this.destroy$))
      .subscribe(user => {
        this.currentUser = user;
      });
  }

  private loadInsightsData() {
    this.isLoading = true;
    
    // Load performance insights from DataService
    this.dataService.getPerformanceInsights(this.selectedPeriod)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data) => {
          this.performanceMetrics = data;
          this.isLoading = false;
        },
        error: (error) => {
          console.error('Error loading insights:', error);
          // Calculate from session stats if API fails
          this.calculatePerformanceMetrics();
          this.isLoading = false;
        }
      });
  }

  /**
   * Load session statistics from StatsService
   */
  private loadSessionStats() {
    this.statsService.stats$
      .pipe(takeUntil(this.destroy$))
      .subscribe(stats => {
        if (stats) {
          this.sessionStats = stats;
          this.calculatePerformanceMetrics();
        }
      });
  }

  /**
   * Calculate performance metrics from session stats and sessions
   */
  private calculatePerformanceMetrics() {
    if (!this.sessionStats) {
      // Load from sessions directly if stats not available
      this.dataService.getFocusSessions()
        .pipe(takeUntil(this.destroy$))
        .subscribe(sessions => {
          this.calculateMetricsFromSessions(sessions);
        });
      return;
    }

    // Calculate from sessions for accurate data
    this.dataService.getFocusSessions()
      .pipe(takeUntil(this.destroy$))
      .subscribe(sessions => {
        this.calculateMetricsFromSessions(sessions);
      });
  }

  /**
   * Calculate metrics directly from sessions
   */
  private calculateMetricsFromSessions(sessions: FocusSession[]) {
    const completedSessions = sessions.filter(s => s.status === 'completed');
    
    // Filter by period if needed
    let filteredSessions = completedSessions;
    const now = new Date();
    if (this.selectedPeriod === 'week') {
      const weekAgo = new Date(now);
      weekAgo.setDate(weekAgo.getDate() - 7);
      filteredSessions = completedSessions.filter(s => new Date(s.startTime) >= weekAgo);
    } else if (this.selectedPeriod === 'month') {
      const monthAgo = new Date(now);
      monthAgo.setMonth(monthAgo.getMonth() - 1);
      filteredSessions = completedSessions.filter(s => new Date(s.startTime) >= monthAgo);
    }

    const totalSessions = filteredSessions.length;
    const totalMinutes = filteredSessions.reduce((sum, s) => sum + (s.duration || 0), 0);
    const totalSocialInteractions = filteredSessions.reduce((sum, s) => 
      sum + (s.socialInteractions?.length || 0), 0);
    const totalPhoneReduction = filteredSessions.reduce((sum, s) => 
      sum + (s.phoneUsageReduction || 0), 0);

    // Calculate previous period for comparison (if possible)
    const previousPeriodSessions = this.getPreviousPeriodSessions(completedSessions);
    const previousTotalSessions = previousPeriodSessions.length;
    const previousTotalMinutes = previousPeriodSessions.reduce((sum, s) => sum + (s.duration || 0), 0);
    const previousSocialInteractions = previousPeriodSessions.reduce((sum, s) => 
      sum + (s.socialInteractions?.length || 0), 0);
    const previousPhoneReduction = previousPeriodSessions.reduce((sum, s) => 
      sum + (s.phoneUsageReduction || 0), 0);

    // Calculate percentage changes
    const sessionsChange = previousTotalSessions > 0 
      ? Math.round(((totalSessions - previousTotalSessions) / previousTotalSessions) * 100)
      : 0;
    const timeChange = previousTotalMinutes > 0
      ? Math.round(((totalMinutes - previousTotalMinutes) / previousTotalMinutes) * 100)
      : 0;
    const socialChange = previousSocialInteractions > 0
      ? Math.round(((totalSocialInteractions - previousSocialInteractions) / previousSocialInteractions) * 100)
      : 0;
    const phoneChange = previousPhoneReduction > 0
      ? Math.round(((totalPhoneReduction - previousPhoneReduction) / previousPhoneReduction) * 100)
      : 0;

    this.performanceMetrics = {
      focusSessions: totalSessions,
      mindfulTime: Math.round((totalMinutes / 60) * 10) / 10,
      socialInteractions: totalSocialInteractions,
      phoneReduction: Math.round((totalPhoneReduction / 60) * 10) / 10,
      focusSessionsChange: sessionsChange,
      mindfulTimeChange: timeChange,
      socialInteractionsChange: socialChange,
      phoneReductionChange: phoneChange
    };
  }

  /**
   * Get sessions from previous period for comparison
   */
  private getPreviousPeriodSessions(sessions: FocusSession[]): FocusSession[] {
    const now = new Date();
    let startDate: Date;
    let endDate: Date;

    if (this.selectedPeriod === 'week') {
      // Previous week (7-14 days ago)
      endDate = new Date(now);
      endDate.setDate(endDate.getDate() - 7);
      startDate = new Date(endDate);
      startDate.setDate(startDate.getDate() - 7);
    } else if (this.selectedPeriod === 'month') {
      // Previous month (1-2 months ago)
      endDate = new Date(now);
      endDate.setMonth(endDate.getMonth() - 1);
      startDate = new Date(endDate);
      startDate.setMonth(startDate.getMonth() - 1);
    } else {
      // For 'all', compare to first half vs second half
      return [];
    }

    return sessions.filter(s => {
      const sessionDate = new Date(s.startTime);
      return sessionDate >= startDate && sessionDate < endDate;
    });
  }

  /**
   * Load weekly breakdown from sessions
   */
  private loadWeeklyBreakdown() {
    this.dataService.getFocusSessions()
      .pipe(takeUntil(this.destroy$))
      .subscribe(sessions => {
        this.calculateWeeklyBreakdown(sessions);
      });
  }

  /**
   * Calculate weekly breakdown from sessions
   */
  private calculateWeeklyBreakdown(sessions: FocusSession[]) {
    const completedSessions = sessions.filter(s => s.status === 'completed');
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    
    // Get last 7 days
    const weeklyDataMap = new Map<string, { sessions: number; time: number; interactions: number }>();
    
    days.forEach(day => {
      weeklyDataMap.set(day, { sessions: 0, time: 0, interactions: 0 });
    });

    // Get sessions from last 7 days
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);

    completedSessions
      .filter(s => new Date(s.startTime) >= weekAgo)
      .forEach(session => {
        const date = new Date(session.startTime);
        const dayName = days[date.getDay()];
        const dayData = weeklyDataMap.get(dayName)!;
        
        dayData.sessions++;
        dayData.time += session.duration || 0;
        dayData.interactions += session.socialInteractions?.length || 0;
      });

    // Convert to array in correct order (Monday to Sunday)
    const dayOrder = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    this.weeklyData = dayOrder.map(day => ({
      day,
      sessions: weeklyDataMap.get(day)?.sessions || 0,
      time: weeklyDataMap.get(day)?.time || 0,
      interactions: weeklyDataMap.get(day)?.interactions || 0
    }));
    
    // Update charts if they exist
    if (this.weeklyChart || this.sessionsChart) {
      setTimeout(() => this.updateCharts(), 100);
    }
  }

  /**
   * Load achievements from DataService
   */
  private loadAchievements() {
    this.dataService.getAchievements()
      .pipe(takeUntil(this.destroy$))
      .subscribe(achievements => {
        this.achievements = achievements.map(a => ({
          name: a.name,
          progress: a.progress || 0,
          target: a.requirements?.reduce((sum, r) => sum + (r.current || 0), 0) || 100,
          icon: a.icon || 'fas fa-trophy'
        }));
      });
  }

  /**
   * Load location performance from StatsService
   */
  private loadLocationPerformance() {
    this.statsService.getLocationStats()
      .pipe(takeUntil(this.destroy$))
      .subscribe(locationStats => {
        this.locationPerformance = locationStats.map(stat => ({
          location: this.sanitizeLocationName(stat.location),
          score: stat.averageScore,
          sessions: stat.sessionsCount
        }));
      });
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

  onPeriodChange(period: string) {
    this.selectedPeriod = period;
    this.loadInsightsData();
    this.loadWeeklyBreakdown();
    this.loadLocationPerformance();
    this.loadRecentSessions();
    // Update charts after data loads
    setTimeout(() => {
      this.updateCharts();
    }, 300);
  }

  /**
   * Load recent completed sessions for accomplishments/distractions and AI evaluation
   */
  private loadRecentSessions() {
    this.dataService.getFocusSessions()
      .pipe(takeUntil(this.destroy$))
      .subscribe(sessions => {
        const completed = sessions.filter(s => s.status === 'completed');
        const now = new Date();
        let cutoff: Date;
        if (this.selectedPeriod === 'month') {
          cutoff = new Date(now);
          cutoff.setMonth(cutoff.getMonth() - 1);
        } else if (this.selectedPeriod === 'all') {
          cutoff = new Date(0);
        } else {
          cutoff = new Date(now);
          cutoff.setDate(cutoff.getDate() - 7);
        }
        this.recentSessions = completed
          .filter(s => new Date(s.startTime) >= cutoff)
          .sort((a, b) => new Date(b.startTime).getTime() - new Date(a.startTime).getTime())
          .slice(0, 20);
      });
  }

  /** Generate AI evaluation for recent sessions */
  generateAIInsights() {
    if (this.recentSessions.length === 0 || !this.currentUser) return;
    this.llmLoading = true;
    this.llmError = null;
    const sessionsToSend = this.recentSessions.slice(0, 5);
    this.dataService.evaluateSessions(sessionsToSend).subscribe({
      next: (res) => {
        this.llmLoading = false;
        if (res.success && res.evaluation) {
          this.llmEvaluation = res.evaluation;
        } else {
          this.llmError = res.error || 'Evaluation failed';
        }
      },
      error: () => {
        this.llmLoading = false;
        this.llmError = 'Request failed';
      }
    });
  }
  
  /**
   * Initialize Chart.js charts
   */
  private initializeCharts(): void {
    if (this.weeklyChartCanvas) {
      this.createWeeklyChart();
    }
    if (this.sessionsChartCanvas) {
      this.createSessionsChart();
    }
  }
  
  /**
   * Create weekly breakdown chart
   */
  private createWeeklyChart(): void {
    if (!this.weeklyChartCanvas) return;
    
    const ctx = this.weeklyChartCanvas.nativeElement.getContext('2d');
    if (!ctx) return;
    
    const maxSessions = Math.max(...this.weeklyData.map(d => d.sessions), 1);
    
    const config: ChartConfiguration = {
      type: 'bar',
      data: {
        labels: this.weeklyData.map(d => d.day),
        datasets: [
          {
            label: 'Sessions',
            data: this.weeklyData.map(d => d.sessions),
            backgroundColor: 'rgba(74, 144, 226, 0.8)',
            borderColor: 'rgba(74, 144, 226, 1)',
            borderWidth: 1
          },
          {
            label: 'Time (min)',
            data: this.weeklyData.map(d => d.time),
            backgroundColor: 'rgba(40, 167, 69, 0.8)',
            borderColor: 'rgba(40, 167, 69, 1)',
            borderWidth: 1,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: 'top'
          },
          tooltip: {
            mode: 'index',
            intersect: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: 'Sessions'
            }
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            beginAtZero: true,
            title: {
              display: true,
              text: 'Minutes'
            },
            grid: {
              drawOnChartArea: false
            }
          }
        }
      }
    };
    
    this.weeklyChart = new Chart(ctx, config);
  }
  
  /**
   * Create sessions trend chart
   */
  private createSessionsChart(): void {
    if (!this.sessionsChartCanvas) return;
    
    const ctx = this.sessionsChartCanvas.nativeElement.getContext('2d');
    if (!ctx) return;
    
    // Prepare data for line chart (last 7 days)
    const last7Days = this.getLast7DaysData();
    
    const config: ChartConfiguration = {
      type: 'line',
      data: {
        labels: last7Days.map(d => d.label),
        datasets: [
          {
            label: 'Focus Sessions',
            data: last7Days.map(d => d.sessions),
            borderColor: 'rgba(74, 144, 226, 1)',
            backgroundColor: 'rgba(74, 144, 226, 0.1)',
            tension: 0.4,
            fill: true
          },
          {
            label: 'Mindful Time (hours)',
            data: last7Days.map(d => d.time / 60),
            borderColor: 'rgba(40, 167, 69, 1)',
            backgroundColor: 'rgba(40, 167, 69, 0.1)',
            tension: 0.4,
            fill: true,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: 'top'
          },
          tooltip: {
            mode: 'index',
            intersect: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: 'Sessions'
            }
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            beginAtZero: true,
            title: {
              display: true,
              text: 'Hours'
            },
            grid: {
              drawOnChartArea: false
            }
          }
        }
      }
    };
    
    this.sessionsChart = new Chart(ctx, config);
  }
  
  /**
   * Get last 7 days data for trend chart
   */
  private getLast7DaysData(): Array<{ label: string; sessions: number; time: number }> {
    const days: Array<{ label: string; sessions: number; time: number }> = [];
    const today = new Date();
    
    for (let i = 6; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      const dayName = date.toLocaleDateString('en-US', { weekday: 'short' });
      const dateStr = date.toDateString();
      
      // This would ideally come from actual session data
      // For now, using weeklyData if available
      const dayData = this.weeklyData.find(d => {
        const dayIndex = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].indexOf(d.day);
        const checkDate = new Date(today);
        checkDate.setDate(checkDate.getDate() - (6 - i));
        return checkDate.getDay() === dayIndex;
      });
      
      days.push({
        label: dayName,
        sessions: dayData?.sessions || 0,
        time: dayData?.time || 0
      });
    }
    
    return days;
  }
  
  /**
   * Update charts with new data
   */
  private updateCharts(): void {
    if (this.weeklyChart) {
      this.weeklyChart.data.labels = this.weeklyData.map(d => d.day);
      this.weeklyChart.data.datasets[0].data = this.weeklyData.map(d => d.sessions);
      this.weeklyChart.data.datasets[1].data = this.weeklyData.map(d => d.time);
      this.weeklyChart.update();
    }
    
    if (this.sessionsChart) {
      const last7Days = this.getLast7DaysData();
      this.sessionsChart.data.labels = last7Days.map(d => d.label);
      this.sessionsChart.data.datasets[0].data = last7Days.map(d => d.sessions);
      this.sessionsChart.data.datasets[1].data = last7Days.map(d => d.time / 60);
      this.sessionsChart.update();
    }
  }

  getProgressPercentage(current: number, target: number): number {
    return Math.min((current / target) * 100, 100);
  }

  getScoreColor(score: number): string {
    if (score >= 80) return '#28A745';
    if (score >= 60) return '#FF9800';
    return '#DC3545';
  }

  getChangeColor(change: number): string {
    return change >= 0 ? '#28A745' : '#DC3545';
  }

  getChangeIcon(change: number): string {
    return change >= 0 ? 'fas fa-arrow-up' : 'fas fa-arrow-down';
  }

  navigateToHome() {
    this.router.navigate(['/home']);
  }

  formatReflectionDate(startTime: string): string {
    const d = new Date(startTime);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const sessionDate = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    const diffDays = Math.floor((today.getTime() - sessionDate.getTime()) / (1000 * 60 * 60 * 24));
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return d.toLocaleDateString('en-US', { weekday: 'short' });
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  getSessionTypeLabel(type: string): string {
    const labels: Record<string, string> = {
      study: 'Study',
      'travel-safety': 'Travel safety',
      focus: 'Focus',
      meditation: 'Meditation',
      walking: 'Walking',
      mindfulness: 'Mindfulness',
      breathing: 'Breathing'
    };
    return labels[type] || type || 'Session';
  }

  navigateToFocus() {
    this.router.navigate(['/focus']);
  }
}
