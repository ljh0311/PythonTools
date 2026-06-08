import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule, DatePipe, TitleCasePipe, UpperCasePipe } from '@angular/common';
import { Router } from '@angular/router';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, AbstractControl, ValidationErrors } from '@angular/forms';
import { Subject } from 'rxjs';
import { takeUntil, debounceTime } from 'rxjs/operators';
import { AuthService } from '../../services/auth.service';
import { DataService } from '../../services/data.service';
import { PasswordService } from '../../services/password.service';
import { User } from '../../models/user.model';

@Component({
  selector: 'app-profile',
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.scss'],
  imports: [CommonModule, DatePipe, TitleCasePipe, UpperCasePipe, ReactiveFormsModule],
  standalone: true
})
export class ProfileComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  
  currentUser: User | null = null;
  isEditing = false;
  isSaving = false;
  errorMessage = '';
  successMessage = '';
  passwordStrength: { strength: 'weak' | 'medium' | 'strong'; score: number; feedback: string[] } | null = null;
  
  editForm!: FormGroup;
  
  // Profile stats
  profileStats = {
    totalSessions: 0,
    totalMinutes: 0,
    currentStreak: 0,
    badgesEarned: 0,
    level: 1,
    points: 0
  };
  
  // Recent achievements
  recentAchievements: any[] = [];
  hasStaticAchievements = false;

  constructor(
    private authService: AuthService,
    private dataService: DataService,
    private passwordService: PasswordService,
    private router: Router,
    private fb: FormBuilder
  ) {
    this.initializeForm();
  }

  ngOnInit() {
    this.loadUserData();
    this.loadProfileStats();
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
          // Load sessions first for streak calculation
          this.dataService.getFocusSessions()
            .pipe(takeUntil(this.destroy$))
            .subscribe(sessions => {
              // Load stats from DataService (which uses storage.json)
              this.dataService.getUserStats()
                .pipe(takeUntil(this.destroy$))
                .subscribe(stats => {
                  if (stats) {
                    this.profileStats = {
                      totalSessions: stats.totalSessions || 0,
                      totalMinutes: stats.totalMindfulMinutes || 0,
                      currentStreak: this.calculateStreak(sessions),
                      badgesEarned: user.badges?.length || 0,
                      level: user.level || 1,
                      points: user.points || 0
                    };
                  } else {
                    // Fallback to user stats
                    this.profileStats = {
                      totalSessions: user.stats?.totalSessions || 0,
                      totalMinutes: user.stats?.totalMindfulMinutes || 0,
                      currentStreak: this.calculateStreak(sessions),
                      badgesEarned: user.badges?.length || 0,
                      level: user.level || 1,
                      points: user.points || 0
                    };
                  }
                });
            });
        }
      });
  }

  private calculateStreak(sessions: any[] = []): number {
    if (sessions.length === 0) return 0;

    const completedSessions = sessions
      .filter(s => s.status === 'completed')
      .map(s => new Date(s.startTime).toDateString())
      .filter((date, index, self) => self.indexOf(date) === index)
      .sort((a, b) => new Date(b).getTime() - new Date(a).getTime());

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
        streak = 1;
        expectedDate.setDate(expectedDate.getDate() - 1);
      } else {
        break;
      }
    }

    return streak;
  }

  private loadProfileStats() {
    // Load additional profile statistics from DataService (uses storage.json)
    this.dataService.getAchievements()
      .pipe(takeUntil(this.destroy$))
      .subscribe(achievements => {
        // Update recent achievements if available
        if (achievements && achievements.length > 0) {
          // Filter completed achievements and sort by date
          const completedAchievements = achievements
            .filter(a => a.progress === 100 && a.completedDate)
            .sort((a, b) => new Date(b.completedDate || 0).getTime() - new Date(a.completedDate || 0).getTime())
            .slice(0, 3);

          if (completedAchievements.length > 0) {
            this.recentAchievements = completedAchievements.map(a => {
              const date = new Date(a.completedDate || '');
              const now = new Date();
              const diffTime = Math.abs(now.getTime() - date.getTime());
              const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
              
              let dateStr = '';
              if (diffDays === 0) dateStr = 'Today';
              else if (diffDays === 1) dateStr = 'Yesterday';
              else if (diffDays < 7) dateStr = `${diffDays} days ago`;
              else if (diffDays < 30) dateStr = `${Math.floor(diffDays / 7)} week${Math.floor(diffDays / 7) > 1 ? 's' : ''} ago`;
              else dateStr = `${Math.floor(diffDays / 30)} month${Math.floor(diffDays / 30) > 1 ? 's' : ''} ago`;

              return {
                name: a.name,
                icon: a.icon || 'fas fa-trophy',
                date: dateStr,
                points: a.points || 0
              };
            });
            this.hasStaticAchievements = false;
          } else {
            // Use static values temporarily
            this.recentAchievements = [
              { name: 'First Focus Session', icon: 'fas fa-bolt', date: '2 days ago', points: 10 },
              { name: 'Week Warrior', icon: 'fas fa-calendar-week', date: '1 week ago', points: 25 },
              { name: 'Social Butterfly', icon: 'fas fa-users', date: '2 weeks ago', points: 15 }
            ];
            this.hasStaticAchievements = true;
          }
        } else {
          // Use static values temporarily
          this.recentAchievements = [
            { name: 'First Focus Session', icon: 'fas fa-bolt', date: '2 days ago', points: 10 },
            { name: 'Week Warrior', icon: 'fas fa-calendar-week', date: '1 week ago', points: 25 },
            { name: 'Social Butterfly', icon: 'fas fa-users', date: '2 weeks ago', points: 15 }
          ];
          this.hasStaticAchievements = true;
        }
      });
  }

  private initializeForm() {
    this.editForm = this.fb.group({
      firstName: ['', [Validators.required]],
      lastName: ['', [Validators.required]],
      username: ['', [Validators.required]],
      email: ['', [Validators.required, Validators.email]],
      currentPassword: [''],
      newPassword: ['', [
        Validators.minLength(8),
        Validators.pattern(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/)
      ]],
      confirmPassword: ['']
    }, { validators: this.passwordMatchValidator });

    // Watch for password changes to check strength
    this.editForm.get('newPassword')?.valueChanges
      .pipe(
        debounceTime(300),
        takeUntil(this.destroy$)
      )
      .subscribe(password => {
        if (password && password.length > 0) {
          this.passwordStrength = this.passwordService.checkPasswordStrength(password);
        } else {
          this.passwordStrength = null;
        }
      });

    // Watch for new password to require current password
    this.editForm.get('newPassword')?.valueChanges
      .pipe(takeUntil(this.destroy$))
      .subscribe(newPassword => {
        const currentPasswordControl = this.editForm.get('currentPassword');
        if (newPassword && newPassword.length > 0) {
          currentPasswordControl?.setValidators([Validators.required]);
        } else {
          currentPasswordControl?.clearValidators();
        }
        currentPasswordControl?.updateValueAndValidity({ emitEvent: false });
      });
  }

  private passwordMatchValidator(control: AbstractControl): ValidationErrors | null {
    const newPassword = control.get('newPassword');
    const confirmPassword = control.get('confirmPassword');
    
    if (!newPassword || !confirmPassword) {
      return null;
    }
    
    if (newPassword.value && confirmPassword.value && newPassword.value !== confirmPassword.value) {
      confirmPassword.setErrors({ passwordMismatch: true });
      return { passwordMismatch: true };
    }
    
    if (confirmPassword.hasError('passwordMismatch') && newPassword.value === confirmPassword.value) {
      confirmPassword.setErrors(null);
    }
    
    return null;
  }

  toggleEdit() {
    this.isEditing = !this.isEditing;
    this.errorMessage = '';
    this.successMessage = '';
    
    if (this.isEditing && this.currentUser) {
      // Populate form with current user data
      this.editForm.patchValue({
        firstName: this.currentUser.firstName || '',
        lastName: this.currentUser.lastName || '',
        username: this.currentUser.username || '',
        email: this.currentUser.email || '',
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      });
    }
  }

  async saveProfile() {
    if (this.editForm.invalid) {
      this.markFormGroupTouched(this.editForm);
      return;
    }

    this.isSaving = true;
    this.errorMessage = '';
    this.successMessage = '';

    const formValue = this.editForm.value;
    const updates: Partial<User> = {
      firstName: formValue.firstName,
      lastName: formValue.lastName,
      username: formValue.username,
      email: formValue.email
    };

    try {
      // Update user profile data
      this.authService.updateUser(updates).subscribe({
        next: (result) => {
          if (result.success) {
            // If password is being changed, update it separately
            if (formValue.newPassword && formValue.newPassword.length > 0) {
              this.authService.updatePassword(formValue.newPassword, formValue.currentPassword).subscribe({
                next: (passwordResult) => {
                  this.isSaving = false;
                  if (passwordResult.success) {
                    this.successMessage = 'Profile updated successfully!';
                    setTimeout(() => {
                      this.isEditing = false;
                      this.successMessage = '';
                    }, 2000);
                  } else {
                    this.errorMessage = passwordResult.error || 'Failed to update password';
                  }
                },
                error: (error) => {
                  this.isSaving = false;
                  this.errorMessage = 'Failed to update password. Please try again.';
                  console.error('Password update error:', error);
                }
              });
            } else {
              // No password change, just close the form
              this.isSaving = false;
              this.successMessage = 'Profile updated successfully!';
              setTimeout(() => {
                this.isEditing = false;
                this.successMessage = '';
              }, 2000);
            }
          } else {
            this.isSaving = false;
            this.errorMessage = result.error || 'Failed to update profile';
          }
        },
        error: (error) => {
          this.isSaving = false;
          this.errorMessage = 'Failed to update profile. Please try again.';
          console.error('Profile update error:', error);
        }
      });
    } catch (error) {
      this.isSaving = false;
      this.errorMessage = 'An unexpected error occurred. Please try again.';
      console.error('Save profile error:', error);
    }
  }

  private markFormGroupTouched(formGroup: FormGroup) {
    Object.keys(formGroup.controls).forEach(key => {
      const control = formGroup.get(key);
      control?.markAsTouched();

      if (control instanceof FormGroup) {
        this.markFormGroupTouched(control);
      }
    });
  }

  logout() {
    this.authService.logout().subscribe(() => {
      this.router.navigate(['/login']);
    });
  }

  navigateToHome() {
    this.router.navigate(['/home']);
  }

  navigateToSettings() {
    this.router.navigate(['/settings']);
  }

  getInitials(): string {
    if (!this.currentUser) return 'U';
    const firstName = this.currentUser.firstName || '';
    const lastName = this.currentUser.lastName || '';
    return (firstName.charAt(0) + lastName.charAt(0)).toUpperCase() || 'U';
  }

  getDisplayName(): string {
    if (!this.currentUser) return 'User';
    return this.currentUser.firstName && this.currentUser.lastName 
      ? `${this.currentUser.firstName} ${this.currentUser.lastName}`
      : this.currentUser.username || 'User';
  }
}
