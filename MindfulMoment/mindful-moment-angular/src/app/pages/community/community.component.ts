import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { AuthService } from '../../services/auth.service';
import { DataService } from '../../services/data.service';
import { User } from '../../models/user.model';
import { CommunityGroup, JoinRequest, JoinRequestStatus } from '../../models/community-group.model';
import { GroupCategory } from '../../models/community-group.model';
import { GroupCardComponent } from '../../components/group-card/group-card.component';
import { PageSectionComponent } from '../../components/page-section/page-section.component';

@Component({
  selector: 'app-community',
  templateUrl: './community.component.html',
  styleUrls: ['./community.component.scss'],
  imports: [CommonModule, FormsModule, GroupCardComponent, PageSectionComponent],
  standalone: true
})
export class CommunityComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  
  currentUser: User | null = null;
  communityGroups: CommunityGroup[] = [];
  joinedGroups: CommunityGroup[] = [];
  isLoading = false;
  
  // Community categories
  categories = [
    { id: 'all', name: 'All Groups', icon: 'fas fa-globe' },
    { id: 'focus', name: 'Focus & Mindfulness', icon: 'fas fa-bolt' },
    { id: 'safety', name: 'Public Safety', icon: 'fas fa-shield-alt' },
    { id: 'wellness', name: 'Wellness', icon: 'fas fa-heart' },
    { id: 'social', name: 'Social Connection', icon: 'fas fa-users' },
    { id: 'learning', name: 'Learning', icon: 'fas fa-graduation-cap' }
  ];
  
  selectedCategory = 'all';
  searchQuery = '';
  
  // Community stats
  communityStats = {
    totalGroups: 0,
    joinedGroups: 0,
    totalMembers: 0,
    activeEvents: 0
  };

  // Group management
  showCreateGroupModal = false;
  showEditGroupModal = false;
  showJoinRequestsModal = false;
  selectedGroup: CommunityGroup | null = null;
  managedGroups: CommunityGroup[] = [];

  // Form data for creating/editing groups
  groupForm = {
    name: '',
    description: '',
    category: 'focus' as GroupCategory,
    location: '',
    maxMembers: undefined as number | undefined,
    isPublic: true,
    requiresApproval: false,
    tags: [] as string[],
    tagInput: '',
    icon: 'fas fa-users',
    color: '#4A90E2'
  };

  // Available icons for groups
  availableIcons = [
    { value: 'fas fa-users', label: 'Users' },
    { value: 'fas fa-heart', label: 'Heart' },
    { value: 'fas fa-bolt', label: 'Bolt' },
    { value: 'fas fa-shield-alt', label: 'Shield' },
    { value: 'fas fa-graduation-cap', label: 'Graduation Cap' },
    { value: 'fas fa-leaf', label: 'Leaf' },
    { value: 'fas fa-star', label: 'Star' },
    { value: 'fas fa-fire', label: 'Fire' },
    { value: 'fas fa-globe', label: 'Globe' },
    { value: 'fas fa-handshake', label: 'Handshake' },
    { value: 'fas fa-lightbulb', label: 'Lightbulb' },
    { value: 'fas fa-trophy', label: 'Trophy' },
    { value: 'fas fa-book', label: 'Book' },
    { value: 'fas fa-music', label: 'Music' },
    { value: 'fas fa-paint-brush', label: 'Paint Brush' },
    { value: 'fas fa-dumbbell', label: 'Dumbbell' },
    { value: 'fas fa-utensils', label: 'Utensils' },
    { value: 'fas fa-camera', label: 'Camera' },
    { value: 'fas fa-gamepad', label: 'Gamepad' },
    { value: 'fas fa-code', label: 'Code' }
  ];

  constructor(
    private authService: AuthService,
    private dataService: DataService,
    private router: Router
  ) {}

  ngOnInit() {
    this.loadUserData();
    this.dataService.communityGroups$
      .pipe(takeUntil(this.destroy$))
      .subscribe(groups => {
        this.communityGroups = groups;
        this.joinedGroups = groups.filter(group => group.isJoined);
        this.updateManagedGroups();
        this.loadCommunityStats();
        // Keep selectedGroup in sync so the join-requests modal shows latest data (e.g. after dev-tool simulate)
        if (this.selectedGroup) {
          const updated = groups.find(g => g.id === this.selectedGroup!.id);
          this.selectedGroup = updated ?? this.selectedGroup;
        }
      });
    this.loadCommunityGroups();
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
        this.updateManagedGroups();
      });
  }

  private loadCommunityGroups() {
    this.isLoading = true;
    this.dataService.getCommunityGroups()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.isLoading = false;
        },
        error: (error) => {
          console.error('Error loading community groups:', error);
          this.isLoading = false;
        }
      });
  }

  private updateManagedGroups() {
    if (!this.currentUser) {
      this.managedGroups = [];
      return;
    }
    if (this.authService.isAdmin() || this.authService.isDeveloper()) {
      this.managedGroups = [...this.communityGroups];
      return;
    }
    const userId = this.currentUser.id;
    this.managedGroups = this.communityGroups.filter(group => {
      const isGroupAdmin = group.adminIds?.includes(userId) ||
                     group.adminIds?.includes(userId.toString()) ||
                     group.adminIds?.includes(parseInt(userId).toString()) ||
                     group.createdBy === userId ||
                     group.createdBy === userId.toString() ||
                     group.createdBy === parseInt(userId).toString();
      return isGroupAdmin;
    });
  }

  private loadCommunityStats() {
    // Calculate community statistics from loaded groups
    const now = new Date();
    const activeEvents = this.communityGroups
      .flatMap(group => group.events || [])
      .filter(event => {
        const eventDate = new Date(event.date);
        return eventDate >= now;
      });

    this.communityStats = {
      totalGroups: this.communityGroups.length,
      joinedGroups: this.joinedGroups.length,
      totalMembers: this.communityGroups.reduce((sum, group) => sum + (group.memberCount || 0), 0),
      activeEvents: activeEvents.length
    };
  }

  get filteredGroups(): CommunityGroup[] {
    let filtered = this.communityGroups;

    // Filter by category
    if (this.selectedCategory !== 'all') {
      filtered = filtered.filter(group => group.category === this.selectedCategory);
    }

    // Filter by search query
    if (this.searchQuery.trim()) {
      const query = this.searchQuery.toLowerCase();
      filtered = filtered.filter(group => 
        group.name.toLowerCase().includes(query) ||
        group.description.toLowerCase().includes(query) ||
        group.tags.some(tag => tag.toLowerCase().includes(query))
      );
    }

    return filtered;
  }

  joinGroup(group: CommunityGroup) {
    if (!this.currentUser) {
      this.router.navigate(['/login']);
      return;
    }

    this.dataService.joinCommunityGroup(group.id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          if (response.success) {
            group.isJoined = true;
            group.joinDate = new Date().toISOString();
            this.joinedGroups.push(group);
            this.loadCommunityStats();
          }
        },
        error: (error) => {
          console.error('Error joining group:', error);
        }
      });
  }

  leaveGroup(group: CommunityGroup) {
    // Implementation for leaving a group
    group.isJoined = false;
    group.joinDate = undefined;
    this.joinedGroups = this.joinedGroups.filter(g => g.id !== group.id);
    this.loadCommunityStats();
  }

  viewGroupDetails(group: CommunityGroup) {
    this.router.navigate(['/community', group.id]);
  }

  getCategoryIcon(category: string): string {
    const cat = this.categories.find(c => c.id === category);
    return cat?.icon || 'fas fa-users';
  }

  getCategoryName(category: string): string {
    const cat = this.categories.find(c => c.id === category);
    return cat?.name || 'Community';
  }

  navigateToHome() {
    this.router.navigate(['/home']);
  }

  navigateToEvents() {
    this.router.navigate(['/events']);
  }

  // Group Management Methods
  isGroupAdmin(group: CommunityGroup): boolean {
    if (!this.currentUser) return false;
    if (this.authService.isAdmin() || this.authService.isDeveloper()) return true;
    const userId = this.currentUser.id;
    return group.adminIds?.includes(userId) ||
           group.adminIds?.includes(userId.toString()) ||
           group.adminIds?.includes(parseInt(userId).toString()) ||
           group.createdBy === userId ||
           group.createdBy === userId.toString() ||
           group.createdBy === parseInt(userId).toString();
  }

  openCreateGroupModal() {
    this.resetGroupForm();
    this.showCreateGroupModal = true;
  }

  openEditGroupModal(group: CommunityGroup) {
    if (!this.isGroupAdmin(group)) return;
    this.selectedGroup = group;
    this.groupForm = {
      name: group.name,
      description: group.description,
      category: group.category,
      location: group.location,
      maxMembers: group.maxMembers,
      isPublic: group.isPublic,
      requiresApproval: group.requiresApproval || false,
      tags: [...group.tags],
      tagInput: '',
      icon: group.icon,
      color: group.color
    };
    this.showEditGroupModal = true;
  }

  closeModals() {
    this.showCreateGroupModal = false;
    this.showEditGroupModal = false;
    this.showJoinRequestsModal = false;
    this.selectedGroup = null;
    this.resetGroupForm();
  }

  resetGroupForm() {
    this.groupForm = {
      name: '',
      description: '',
      category: 'focus' as GroupCategory,
      location: '',
      maxMembers: undefined,
      isPublic: true,
      requiresApproval: false,
      tags: [],
      tagInput: '',
      icon: 'fas fa-users',
      color: '#4A90E2'
    };
  }

  addTag() {
    const tag = this.groupForm.tagInput.trim();
    if (tag && !this.groupForm.tags.includes(tag)) {
      this.groupForm.tags.push(tag);
      this.groupForm.tagInput = '';
    }
  }

  removeTag(tag: string) {
    this.groupForm.tags = this.groupForm.tags.filter(t => t !== tag);
  }

  createGroup() {
    if (!this.currentUser || !this.groupForm.name.trim()) return;

    const newGroup: CommunityGroup = {
      id: `group-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      name: this.groupForm.name.trim(),
      description: this.groupForm.description.trim(),
      category: this.groupForm.category,
      location: this.groupForm.location.trim(),
      maxMembers: this.groupForm.maxMembers,
      isPublic: this.groupForm.isPublic,
      requiresApproval: this.groupForm.requiresApproval,
      tags: this.groupForm.tags,
      icon: this.groupForm.icon,
      color: this.groupForm.color,
      createdBy: this.currentUser.id,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      adminIds: [this.currentUser.id],
      memberIds: [this.currentUser.id],
      memberCount: 1,
      isJoined: true,
      rules: [],
      events: [],
      recentActivity: [],
      joinRequests: []
    };

    this.dataService.createCommunityGroup(newGroup)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          if (response.success) {
            this.loadCommunityGroups();
            this.closeModals();
          }
        },
        error: (error) => {
          console.error('Error creating group:', error);
        }
      });
  }

  updateGroup() {
    if (!this.selectedGroup || !this.currentUser || !this.groupForm.name.trim()) return;

    const updatedGroup: CommunityGroup = {
      ...this.selectedGroup,
      name: this.groupForm.name.trim(),
      description: this.groupForm.description.trim(),
      category: this.groupForm.category,
      location: this.groupForm.location.trim(),
      maxMembers: this.groupForm.maxMembers,
      isPublic: this.groupForm.isPublic,
      requiresApproval: this.groupForm.requiresApproval,
      tags: this.groupForm.tags,
      icon: this.groupForm.icon,
      color: this.groupForm.color,
      updatedAt: new Date().toISOString()
    };

    this.dataService.updateCommunityGroup(updatedGroup)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          if (response.success) {
            this.loadCommunityGroups();
            this.closeModals();
          }
        },
        error: (error) => {
          console.error('Error updating group:', error);
        }
      });
  }

  deleteGroup(group: CommunityGroup) {
    if (!this.isGroupAdmin(group)) return;
    if (!confirm(`Are you sure you want to delete "${group.name}"? This action cannot be undone.`)) return;

    this.dataService.deleteCommunityGroup(group.id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          if (response.success) {
            this.loadCommunityGroups();
          }
        },
        error: (error) => {
          console.error('Error deleting group:', error);
        }
      });
  }

  openJoinRequestsModal(group: CommunityGroup) {
    if (!this.isGroupAdmin(group)) return;
    this.selectedGroup = group;
    this.showJoinRequestsModal = true;
  }

  getPendingJoinRequests(group: CommunityGroup): JoinRequest[] {
    return (group.joinRequests || []).filter(req => req.status === JoinRequestStatus.PENDING);
  }

  approveJoinRequest(request: JoinRequest) {
    if (!this.selectedGroup || !this.isGroupAdmin(this.selectedGroup)) return;

    this.dataService.approveJoinRequest(this.selectedGroup.id, request.id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          if (response.success) {
            // Update the request status
            const req = this.selectedGroup!.joinRequests?.find(r => r.id === request.id);
            if (req) {
              req.status = JoinRequestStatus.APPROVED;
            }
            // Reload groups to update member count
            this.loadCommunityGroups();
          }
        },
        error: (error) => {
          console.error('Error approving join request:', error);
        }
      });
  }

  rejectJoinRequest(request: JoinRequest) {
    if (!this.selectedGroup || !this.isGroupAdmin(this.selectedGroup)) return;

    this.dataService.rejectJoinRequest(this.selectedGroup.id, request.id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          if (response.success) {
            // Update the request status
            const req = this.selectedGroup!.joinRequests?.find(r => r.id === request.id);
            if (req) {
              req.status = JoinRequestStatus.REJECTED;
            }
            // Remove from pending requests
            if (this.selectedGroup!.joinRequests) {
              this.selectedGroup!.joinRequests = this.selectedGroup!.joinRequests.filter(
                r => r.id !== request.id || r.status !== JoinRequestStatus.REJECTED
              );
            }
          }
        },
        error: (error) => {
          console.error('Error rejecting join request:', error);
        }
      });
  }
}
