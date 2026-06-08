import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth.service';
import { User } from '../../models/user.model';
import { StorageService } from '../../services/storage.service';

@Component({
  selector: 'app-settings',
  templateUrl: './settings.component.html',
  styleUrls: ['./settings.component.scss'],
  imports: [CommonModule, FormsModule],
  standalone: true
})
export class SettingsComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  currentUser: User | null = null;

  // Settings categories
  settingsCategories = [
    {
      id: 'notifications',
      title: 'Notifications',
      icon: 'fas fa-bell',
      description: 'Manage your notification preferences',
    },
    {
      id: 'privacy',
      title: 'Privacy & Security',
      icon: 'fas fa-shield-alt',
      description: 'Control your data and privacy settings',
    },
    {
      id: 'accessibility',
      title: 'Accessibility',
      icon: 'fas fa-universal-access',
      description: 'Customize accessibility options',
    },
    {
      id: 'appearance',
      title: 'Appearance',
      icon: 'fas fa-palette',
      description: 'Customize the app appearance',
    },
    {
      id: 'focus',
      title: 'Focus Sessions',
      icon: 'fas fa-bolt',
      description: 'Configure focus session settings',
    },
    {
      id: 'community',
      title: 'Community',
      icon: 'fas fa-users',
      description: 'Manage community preferences',
    },
  ];

  // Notification settings
  notificationSettings = {
    enabled: true,
    mindfulNudges: true,
    safetyReminders: true,
    focusSessionAlerts: true,
    communityUpdates: false,
    quietHours: {
      enabled: false,
      start: '22:00',
      end: '07:00',
    },
  };

  // Privacy settings
  privacySettings = {
    tracking: true,
    shareUsageStats: false,
    anonymousMode: false,
    dataRetention: '1 year',
  };

  // Accessibility settings
  accessibilitySettings = {
    highContrast: false,
    largeText: false,
    screenReader: false,
    fontSize: 'medium',
  };

  // Appearance settings
  appearanceSettings = {
    theme: 'light',
    language: 'en',
    timezone: 'Asia/Singapore',
  };

  constructor(
    private authService: AuthService,
    private router: Router,
    private storageService: StorageService
  ) {}

  ngOnInit() {
    this.loadUserData();
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private loadUserData() {
    this.authService.currentUser$
      .pipe(takeUntil(this.destroy$))
      .subscribe((user) => {
        this.currentUser = user;
        if (user) {
          this.loadUserSettings(user);
        }
      });
  }

  private loadUserSettings(user: User) {
    // Load user's current settings from preferences or use defaults
    this.notificationSettings = user.preferences?.notificationSettings || {
      enabled: user.preferences?.notifications ?? true,
      mindfulNudges: true,
      safetyReminders: true,
      focusSessionAlerts: true,
      communityUpdates: false,
      quietHours: {
        enabled: false,
        start: '22:00',
        end: '07:00',
      },
    };

    this.privacySettings = user.preferences?.privacySettings || {
      tracking: user.preferences?.location ?? true,
      shareUsageStats: false,
      anonymousMode: false,
      dataRetention: '1 year',
    };

    this.accessibilitySettings = {
      highContrast: user.preferences?.accessibility?.highContrast ?? false,
      largeText: user.preferences?.accessibility?.largeText ?? false,
      screenReader: user.preferences?.accessibility?.screenReader ?? false,
      fontSize: 'medium',
    };

    this.appearanceSettings = {
      theme: user.preferences?.theme ?? 'light',
      language: user.preferences?.language ?? 'en',
      timezone: 'Asia/Singapore',
    };
  }

  toggleSetting(category: string, setting: string) {
    switch (category) {
      case 'notifications':
        // Handle nested settings (like quietHours.enabled)
        if (setting.includes('.')) {
          const [parent, child] = setting.split('.');
          (this.notificationSettings as any)[parent][child] = !(this.notificationSettings as any)[parent][child];
        } else {
          (this.notificationSettings as any)[setting] = !(
            this.notificationSettings as any
          )[setting];
        }
        break;
      case 'privacy':
        (this.privacySettings as any)[setting] = !(this.privacySettings as any)[
          setting
        ];
        break;
      case 'accessibility':
        (this.accessibilitySettings as any)[setting] = !(
          this.accessibilitySettings as any
        )[setting];
        break;
    }
    this.saveSettings();
  }

  updateSetting(category: string, setting: string, value: any) {
    switch (category) {
      case 'notifications':
        (this.notificationSettings as any)[setting] = value;
        break;
      case 'privacy':
        (this.privacySettings as any)[setting] = value;
        break;
      case 'accessibility':
        (this.accessibilitySettings as any)[setting] = value;
        break;
      case 'appearance':
        (this.appearanceSettings as any)[setting] = value;
        break;
    }
    this.saveSettings();
  }

  private saveSettings() {
    if (!this.currentUser) return;

    const updatedPreferences = {
      ...this.currentUser.preferences,
      // Main notification toggle
      notifications: this.notificationSettings.enabled,
      // Detailed notification settings
      notificationSettings: {
        ...this.notificationSettings,
        enabled: this.notificationSettings.enabled, // Keep in sync
      },
      // Privacy settings
      privacySettings: {
        ...this.privacySettings,
      },
      // Location tracking (from privacy settings)
      location: this.privacySettings.tracking,
      // Appearance settings
      theme: this.appearanceSettings.theme,
      language: this.appearanceSettings.language,
      // Accessibility settings
      accessibility: {
        highContrast: this.accessibilitySettings.highContrast,
        largeText: this.accessibilitySettings.largeText,
        screenReader: this.accessibilitySettings.screenReader,
      },
    };

    this.authService
      .updateUser({ preferences: updatedPreferences })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          if (response.success) {
            console.log('Settings saved successfully');
            // Optionally show a success message/toast
          } else {
            console.error('Failed to save settings:', response.error);
          }
        },
        error: (error) => {
          console.error('Error saving settings:', error);
        }
      });
  }

  exportData() {
    // Export user data
    const data = {
      user: this.currentUser,
      settings: {
        notifications: this.notificationSettings,
        privacy: this.privacySettings,
        accessibility: this.accessibilitySettings,
        appearance: this.appearanceSettings,
      },
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'mindful-moment-data.json';
    a.click();
    URL.revokeObjectURL(url);
  }

  deleteAccount() {
    if (
      confirm(
        'Are you sure you want to delete your account? This action cannot be undone.'
      )
    ) {
      // Delete account logic
      console.log('Account deletion requested');
    }
  }

  navigateToHome() {
    this.router.navigate(['/home']);
  }

  navigateToProfile() {
    this.router.navigate(['/profile']);
  }
}
