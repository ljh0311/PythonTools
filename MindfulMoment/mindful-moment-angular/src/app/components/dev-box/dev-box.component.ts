import { Component, OnInit, OnDestroy, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subject } from 'rxjs';
import { takeUntil, take } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../services/auth.service';
import { DataService } from '../../services/data.service';
import { FocusSimulationService } from '../../services/focus-simulation.service';
import { CommunityGroup, JoinRequest, JoinRequestStatus } from '../../models/community-group.model';
import { LocationType, EnvironmentType, SessionType, SessionStatus, DistractionType } from '../../models/focus-session.model';

@Component({
  selector: 'app-dev-box',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dev-box.component.html',
  styleUrl: './dev-box.component.scss'
})
export class DevBoxComponent implements OnInit, OnDestroy {
  @Output() closeRequested = new EventEmitter<void>();
  private destroy$ = new Subject<void>();

  environment = environment;
  currentUser: { id?: string; email?: string } | null = null;
  appVersion = '1.0.0';
  buildDate = new Date().toISOString().split('T')[0];
  simMessage: string | null = null;
  DistractionType = DistractionType;

  constructor(
    private authService: AuthService,
    private dataService: DataService,
    private focusSimulationService: FocusSimulationService
  ) {}

  ngOnInit() {
    this.authService.currentUser$
      .pipe(takeUntil(this.destroy$))
      .subscribe(user => this.currentUser = user);
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  clearLocalStorage() {
    localStorage.removeItem('mindfulMoment_data');
    localStorage.removeItem('mindfulMoment_storage');
    window.location.reload();
  }

  reloadApp() {
    window.location.reload();
  }

  private showSimMessage(msg: string) {
    this.simMessage = msg;
    setTimeout(() => (this.simMessage = null), 3000);
  }

  /** Simulate a new community group (dev-only). */
  simulateNewGroup() {
    if (!this.currentUser?.id) {
      this.showSimMessage('Sign in first');
      return;
    }
    const newGroup: CommunityGroup = {
      id: 'dev-group-' + Date.now(),
      name: 'Simulated group ' + new Date().toLocaleTimeString(),
      description: 'Created by Developer Tools for testing',
      category: 'focus' as any,
      location: 'Dev',
      memberCount: 1,
      maxMembers: 50,
      isPublic: true,
      tags: ['dev', 'test'],
      icon: 'fas fa-flask',
      color: '#6B7280',
      createdBy: this.currentUser.id,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      rules: [],
      events: [],
      recentActivity: [],
      isJoined: true,
      adminIds: [this.currentUser.id],
      memberIds: [this.currentUser.id],
      joinRequests: [],
      requiresApproval: true
    };
    this.dataService.createCommunityGroup(newGroup).pipe(take(1)).subscribe({
      next: (res) => {
        this.showSimMessage(res.success ? 'New group created. Check Community.' : (res as any).error || 'Failed');
      },
      error: () => this.showSimMessage('Simulation failed')
    });
  }

  /** Simulate a new join request on a group you admin (dev-only). */
  simulateJoinRequest() {
    if (!this.currentUser?.id) {
      this.showSimMessage('Sign in first');
      return;
    }
    this.dataService.getCommunityGroups().pipe(take(1)).subscribe(groups => {
      const adminGroup = groups.find(
        g => g.requiresApproval && (g.adminIds || []).includes(this.currentUser!.id!)
      );
      if (!adminGroup) {
        this.showSimMessage('No group with approval required. Create one first.');
        return;
      }
      const newRequest: JoinRequest = {
        id: 'dev-req-' + Date.now(),
        userId: '999',
        userName: 'Simulated User',
        groupId: adminGroup.id,
        requestedAt: new Date().toISOString(),
        status: JoinRequestStatus.PENDING
      };
      const updatedGroup: CommunityGroup = {
        ...adminGroup,
        joinRequests: [...(adminGroup.joinRequests || []), newRequest],
        updatedAt: new Date().toISOString()
      };
      this.dataService.updateCommunityGroup(updatedGroup).pipe(take(1)).subscribe({
        next: (res) => {
          this.showSimMessage(res.success ? 'Join request added. Check Community.' : (res as any).error || 'Failed');
        },
        error: () => this.showSimMessage('Simulation failed')
      });
    });
  }

  /** Simulate a distraction during an active focus session (dev-only). */
  simulateDistraction(type: DistractionType) {
    this.focusSimulationService.simulateDistraction(type);
    this.showSimMessage('Distraction simulated (active session only)');
  }

  /** Simulate a notification (dev-only). */
  simulateNotification() {
    this.focusSimulationService.simulateNotification();
    this.showSimMessage('Notification simulated');
  }

  /** Simulate a completed focus session (dev-only). */
  simulateFocusSession() {
    if (!this.currentUser?.id) {
      this.showSimMessage('Sign in first');
      return;
    }
    const session = {
      id: 'dev-session-' + Date.now(),
      userId: this.currentUser.id,
      startTime: new Date(Date.now() - 25 * 60 * 1000).toISOString(),
      endTime: new Date().toISOString(),
      duration: 25,
      type: SessionType.STUDY,
      status: SessionStatus.COMPLETED,
      goals: [],
      achievements: [],
      accomplishments: 'Simulated study session',
      distractions: [{ id: 'd1', type: DistractionType.PHONE, description: 'Simulated distraction', duration: 2, timestamp: new Date().toISOString(), handled: true }],
      socialInteractions: [],
      phoneUsageReduction: 5,
      mindfulMoments: [],
      location: { type: LocationType.HOME, name: 'Dev', environment: EnvironmentType.QUIET },
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    this.dataService.createFocusSession(session).pipe(take(1)).subscribe({
      next: (res) => {
        this.showSimMessage(res.success ? 'Focus session added. Check Focus/Insights.' : (res as any).error || 'Failed');
      },
      error: () => this.showSimMessage('Simulation failed')
    });
  }
}
