import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { AuthService } from '../../../services/auth.service';
import { DataService } from '../../../services/data.service';
import { User } from '../../../models/user.model';
import {
  CommunityGroup,
  GroupRule,
  GroupEvent,
  GroupActivity
} from '../../../models/community-group.model';
import { PageBackBarComponent } from '../../../components/page-back-bar/page-back-bar.component';
import { PageSectionComponent } from '../../../components/page-section/page-section.component';

@Component({
  selector: 'app-community-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, PageBackBarComponent, PageSectionComponent],
  templateUrl: './community-detail.component.html',
  styleUrls: ['./community-detail.component.scss']
})
export class CommunityDetailComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  group: CommunityGroup | null = null;
  currentUser: User | null = null;
  isLoading = true;
  isJoining = false;
  isLeaving = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private authService: AuthService,
    private dataService: DataService
  ) {}

  ngOnInit() {
    this.authService.currentUser$
      .pipe(takeUntil(this.destroy$))
      .subscribe(user => (this.currentUser = user));

    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      this.router.navigate(['/community']);
      return;
    }

    this.dataService
      .getGroupById(id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (group) => {
          this.group = group;
          this.isLoading = false;
          if (!group) {
            this.router.navigate(['/community']);
          }
        },
        error: () => {
          this.isLoading = false;
          this.router.navigate(['/community']);
        }
      });
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  isGroupAdmin(): boolean {
    if (!this.currentUser || !this.group) return false;
    const userId = this.currentUser.id;
    return (
      this.group.adminIds?.includes(userId) ||
      this.group.adminIds?.includes(userId.toString()) ||
      this.group.createdBy === userId ||
      this.group.createdBy === userId.toString()
    );
  }

  joinGroup() {
    if (!this.currentUser || !this.group) return;
    this.isJoining = true;
    this.dataService
      .joinCommunityGroup(this.group.id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          this.isJoining = false;
          if (response && (response as { success?: boolean }).success) {
            this.group!.isJoined = true;
            this.group!.memberCount = (this.group!.memberCount || 0) + 1;
            this.dataService.getCommunityGroups().pipe(takeUntil(this.destroy$)).subscribe();
          }
        },
        error: () => (this.isJoining = false)
      });
  }

  leaveGroup() {
    if (!this.group) return;
    this.isLeaving = true;
    this.group.isJoined = false;
    this.group.memberCount = Math.max(0, (this.group.memberCount || 1) - 1);
    this.isLeaving = false;
    this.dataService.getCommunityGroups().pipe(takeUntil(this.destroy$)).subscribe();
  }

  goToCommunity() {
    this.router.navigate(['/community']);
  }

  get rules(): GroupRule[] {
    return this.group?.rules ?? [];
  }

  get events(): GroupEvent[] {
    return this.group?.events ?? [];
  }

  get recentActivity(): GroupActivity[] {
    return this.group?.recentActivity ?? [];
  }
}
