import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { DataService } from '../../services/data.service';
import { User } from '../../models/user.model';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss'],
  imports: [CommonModule, FormsModule, RouterLink],
  standalone: true
})
export class HomeComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  
  currentUser: User | null = null;
  userStats: any = null;
  performanceMetrics: any = null;
  selectedPeriod = 'week';
  selectedPerformanceTab = 'overview';
  isLoading = false;

  // Performance data
  focusSessions = 0;
  mindfulTime = 0;
  socialInteractions = 0;
  phoneReduction = 0;

  // Change indicators
  focusSessionsChange = 0;
  mindfulTimeChange = 0;
  socialInteractionsChange = 0;
  phoneReductionChange = 0;

  // Period-based performance data
  focusSessionsPeriod = 0;
  mindfulTimePeriod = 0;
  socialInteractionsPeriod = 0;
  phoneReductionPeriod = 0;

  // Period-based change indicators
  focusSessionsChangePeriod = 0;
  mindfulTimeChangePeriod = 0;
  socialInteractionsChangePeriod = 0;
  phoneReductionChangePeriod = 0;

  // Insights data
  focusTrendSummary = '';
  weeklyBreakdown: any = null;
  achievementProgress: any[] = [];
  goalsProgress: any[] = [];
  
  // Additional insights
  communitySessions = 0;
  publicPlacesCount = 0;
  insightsSharedCount = 0;
  longestPhoneFreeStreak = 0;
  socialImpactScore = 0;
  mostActiveDay = '';
  longestFocusSession = 0;
  bestStreakDays = 0;

  // Location scores
  locationScores = {
    publicSpaces: 0,
    mrtStations: 0,
    shoppingCenters: 0
  };

  // Flags to track static values
  hasStaticValues = {
    changeIndicators: true,
    locationScores: false,
    weeklyBreakdown: true
  };

  constructor(
    private authService: AuthService,
    private dataService: DataService
  ) {}

  ngOnInit() {
    this.loadUserData();
    this.loadPerformanceData();
    this.loadInsights();
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private loadUserData() {
    this.authService.currentUser$
      .pipe(takeUntil(this.destroy$))
      .subscribe(user => {
        this.currentUser = user;
        if (user) {
          this.loadUserStats();
          this.loadInsights();
        }
      });
  }

  private loadUserStats() {
    this.dataService.getUserStats()
      .pipe(takeUntil(this.destroy$))
      .subscribe(stats => {
        this.userStats = stats;
        this.updatePerformanceMetrics();
        this.loadAdditionalInsights();
      });
  }

  private loadPerformanceData() {
    this.dataService.getPerformanceInsights(this.selectedPeriod)
      .pipe(takeUntil(this.destroy$))
      .subscribe(insights => {
        this.performanceMetrics = insights;
        this.updatePerformanceMetrics();
      });
  }

  private loadInsights() {
    // Load focus trend summary
    this.updateFocusTrendSummary();
    
    // Load weekly breakdown
    this.loadWeeklyBreakdown();
    
    // Load achievement progress from storage.json
    this.loadAchievementProgress();
    
    // Load goals progress from storage.json
    this.loadGoalsProgress();
    
    // Load location scores from storage.json
    this.loadLocationScores();
    
    // Load additional insights
    this.loadAdditionalInsights();
  }

  private loadLocationScores() {
    if (!this.currentUser) return;

    const userId = this.currentUser.id;
    this.dataService.getUserStats(userId)
      .pipe(takeUntil(this.destroy$))
      .subscribe(stats => {
        if (stats?.publicAwarenessStats?.locationScores) {
          this.locationScores = {
            publicSpaces: stats.publicAwarenessStats.locationScores.publicSpaces || 0,
            mrtStations: stats.publicAwarenessStats.locationScores.mrtStations || 0,
            shoppingCenters: stats.publicAwarenessStats.locationScores.shoppingCenters || 0
          };
          this.hasStaticValues.locationScores = false;
        } else {
          // Use static values temporarily
          this.locationScores = {
            publicSpaces: 75,
            mrtStations: 85,
            shoppingCenters: 72
          };
          this.hasStaticValues.locationScores = true;
        }
      });
  }

  private loadAdditionalInsights() {
    if (!this.userStats) return;

    const stats = this.userStats;
    const focusStats = stats.focusSessionStats || {};
    
    // Calculate community sessions (sessions with social interactions)
    this.communitySessions = Math.floor((focusStats.totalSocialInteractions || 0) / 2);
    
    // Calculate public places count (based on sessions)
    this.publicPlacesCount = Math.floor((stats.totalSessions || 0) * 0.3);
    
    // Calculate insights shared count
    this.insightsSharedCount = Math.floor((stats.totalSocialEngagements || 0) * 0.5);
    
    // Calculate longest phone-free streak (in days)
    this.longestPhoneFreeStreak = Math.floor((focusStats.phoneUsageReduction || 0) / 2);
    
    // Calculate social impact score (0-100 based on social engagements and interactions)
    const socialEngagements = stats.totalSocialEngagements || 0;
    const socialInteractions = focusStats.totalSocialInteractions || 0;
    this.socialImpactScore = Math.min(100, Math.floor((socialEngagements + socialInteractions) * 2));
    
    // Get most active day from weekly breakdown
    this.mostActiveDay = this.weeklyBreakdown?.bestDay || 'Monday';
    
    // Calculate longest focus session (estimate based on average)
    const avgSession = stats.totalSessions > 0 ? Math.round((stats.totalMindfulMinutes || 0) / stats.totalSessions) : 0;
    this.longestFocusSession = Math.round(avgSession * 1.5);
    
    // Calculate best streak days (estimate based on total sessions)
    // Assuming a streak is consecutive days with at least one session
    this.bestStreakDays = Math.max(1, Math.floor((stats.totalSessions || 0) / 7));
  }

  private updatePerformanceMetrics() {
    if (!this.userStats) return;

    const stats = this.userStats;
    const focusStats = stats.focusSessionStats || {};
    const publicStats = stats.publicAwarenessStats || {};

    // Calculate metrics based on selected period
    const multiplier = this.getPeriodMultiplier();
    
    this.focusSessions = Math.floor((stats.totalSessions || 0) * multiplier);
    this.mindfulTime = Math.round(((stats.totalMindfulMinutes || 0) / 60) * multiplier * 10) / 10;
    this.socialInteractions = Math.floor((stats.totalSocialEngagements || 0) * multiplier);
    this.phoneReduction = Math.round((focusStats.phoneUsageReduction || 0) * multiplier * 10) / 10;

    // Period-based metrics (same as above, but stored separately for the "By Period" tab)
    this.focusSessionsPeriod = this.focusSessions;
    this.mindfulTimePeriod = this.mindfulTime;
    this.socialInteractionsPeriod = this.socialInteractions;
    this.phoneReductionPeriod = this.phoneReduction;

    // Calculate change indicators based on previous period comparison
    // TODO: Implement proper period comparison when historical data is available
    // For now, using static values temporarily
    this.focusSessionsChange = Math.floor(Math.random() * 20) + 5;
    this.mindfulTimeChange = Math.floor(Math.random() * 15) + 3;
    this.socialInteractionsChange = Math.floor(Math.random() * 25) + 8;
    this.phoneReductionChange = Math.floor(Math.random() * 18) + 2;
    this.hasStaticValues.changeIndicators = true;

    // Period-based change indicators
    this.focusSessionsChangePeriod = this.focusSessionsChange;
    this.mindfulTimeChangePeriod = this.mindfulTimeChange;
    this.socialInteractionsChangePeriod = this.socialInteractionsChange;
    this.phoneReductionChangePeriod = this.phoneReductionChange;
  }

  private getPeriodMultiplier(): number {
    switch (this.selectedPeriod) {
      case 'month': return 4;
      case 'all': return 12;
      default: return 1;
    }
  }

  private updateFocusTrendSummary() {
    if (!this.userStats) {
      this.focusTrendSummary = "Start your first focus session to see trends here.";
      return;
    }

    const totalSessions = this.userStats.totalSessions || 0;
    const totalMinutes = this.userStats.totalMindfulMinutes || 0;
    const avgSession = totalSessions > 0 ? Math.round(totalMinutes / totalSessions) : 0;

    if (totalSessions === 0) {
      this.focusTrendSummary = "Start your first focus session to see trends here.";
    } else if (totalSessions < 5) {
      this.focusTrendSummary = "You're just getting started! Keep building your focus habit.";
    } else if (avgSession < 15) {
      this.focusTrendSummary = "Your sessions are short but consistent. Try extending them gradually.";
    } else if (avgSession > 30) {
      this.focusTrendSummary = "Excellent! You're maintaining long, focused sessions.";
    } else {
      this.focusTrendSummary = "Great progress! Your focus sessions are well-balanced.";
    }
  }

  private loadWeeklyBreakdown() {
    // TODO: Calculate from actual session data when historical data is available
    // For now, using static/random values temporarily
    this.weeklyBreakdown = {
      bestDay: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][Math.floor(Math.random() * 7)],
      mostActiveTime: ['Morning', 'Afternoon', 'Evening'][Math.floor(Math.random() * 3)],
      avgSession: this.userStats ? Math.round((this.userStats.totalMindfulMinutes || 0) / Math.max(1, this.userStats.totalSessions || 1)) : 25
    };
    this.hasStaticValues.weeklyBreakdown = true;
  }

  private loadAchievementProgress() {
    if (!this.currentUser) return;

    const userId = this.currentUser.id;
    this.dataService.getAchievements(userId)
      .pipe(takeUntil(this.destroy$))
      .subscribe(achievements => {
        if (achievements && achievements.length > 0) {
          this.achievementProgress = achievements.map(ach => ({
            name: ach.name,
            progress: ach.progress || 0,
            icon: ach.icon || 'fas fa-trophy'
          }));
        } else {
          // Fallback: calculate from stats if no achievements in storage
          if (this.userStats) {
            this.achievementProgress = [
              {
                name: 'Mindful Explorer',
                progress: Math.min(100, Math.floor((this.userStats.totalSessions || 0) * 5)),
                icon: 'fas fa-medal'
              },
              {
                name: 'Social Connector',
                progress: Math.min(100, Math.floor((this.userStats.totalSocialEngagements || 0) * 8)),
                icon: 'fas fa-star'
              }
            ];
          }
        }
      });
  }

  private loadGoalsProgress() {
    if (!this.currentUser) return;

    const userId = this.currentUser.id;
    this.dataService.getUserGoals(userId)
      .pipe(takeUntil(this.destroy$))
      .subscribe(goals => {
        if (goals && goals.length > 0) {
          this.goalsProgress = goals.map(goal => ({
            name: goal.name,
            target: goal.target,
            progress: goal.progress || 0,
            current: goal.current || '0',
            targetValue: goal.targetValue || goal.target
          }));
        } else {
          // Fallback: calculate from stats if no goals in storage
          if (this.userStats) {
            const stats = this.userStats;
            const focusStats = stats.focusSessionStats || {};

            this.goalsProgress = [
              {
                name: 'Daily Focus Goal',
                target: '30 min',
                progress: Math.min(100, Math.floor(((stats.totalMindfulMinutes || 0) / 30) * 100)),
                current: `${Math.round((stats.totalMindfulMinutes || 0) / 60 * 10) / 10}h`,
                targetValue: '30 min'
              },
              {
                name: 'Weekly Social Goal',
                target: '10 interactions',
                progress: Math.min(100, Math.floor(((stats.totalSocialEngagements || 0) / 10) * 100)),
                current: `${stats.totalSocialEngagements || 0}`,
                targetValue: '10'
              },
              {
                name: 'Phone Reduction Goal',
                target: '2h daily',
                progress: Math.min(100, Math.floor(((focusStats.phoneUsageReduction || 0) / 2) * 100)),
                current: `${Math.round((focusStats.phoneUsageReduction || 0) * 10) / 10}h`,
                targetValue: '2h'
              }
            ];
          }
        }
      });
  }

  onPeriodChange(period: string) {
    this.selectedPeriod = period;
    this.loadPerformanceData();
  }

  refreshData() {
    this.isLoading = true;
    this.dataService.refreshAllData();
    
    // Simulate loading time
    setTimeout(() => {
      this.isLoading = false;
    }, 1000);
  }

  getGreeting(): string {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  }

  getUserDisplayName(): string {
    if (!this.currentUser) return '';
    return this.currentUser.firstName || this.currentUser.username || 'User';
  }
}
