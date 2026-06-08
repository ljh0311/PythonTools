import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of, switchMap, map, from } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { tap, catchError } from 'rxjs/operators';
import { User } from '../models/user.model';
import { StorageService } from './storage.service';
import { JwtService } from './jwt.service';
import { PasswordService } from './password.service';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  private readonly API_URL = '/api'; // For future backend integration

  constructor(
    private http: HttpClient,
    private storageService: StorageService,
    private jwtService: JwtService,
    private passwordService: PasswordService
  ) {
    this.loadUserFromToken();
  }

  // Check if user is authenticated
  isAuthenticated(): boolean {
    return this.jwtService.isTokenValid() && !!this.currentUserSubject.value;
  }

  // Get current user
  getCurrentUser(): User | null {
    return this.currentUserSubject.value;
  }

  // Login user
  login(email: string, password: string): Observable<any> {
    return this.storageService.getUserByEmail(email).pipe(
      switchMap(storageUser => {
        if (!storageUser) {
          return of({ success: false, error: 'Invalid email or password' });
        }

        // Verify password (async)
        return from(this.passwordService.verifyPassword(password, storageUser.password)).pipe(
          switchMap(isValid => {
            if (!isValid) {
              return of({ success: false, error: 'Invalid email or password' });
            }

            // Convert StorageUser to User model
            const user = this.convertStorageUserToUser(storageUser);
            
            // Generate JWT token
            const token = this.jwtService.encode({
              userId: storageUser.id,
              email: storageUser.email
            }, 24); // 24 hours expiration

            // Save token
            this.jwtService.saveToken(token);
            
            // Set current user
            this.setCurrentUser(user);

            return of({ success: true, user, token });
          })
        );
      }),
      catchError(error => {
        console.error('Login error:', error);
        return of({ success: false, error: 'Login failed. Please try again.' });
      })
    );
  }

  // Register new user
  register(userData: any): Observable<any> {
    // Check if user already exists
    return this.storageService.getUserByEmail(userData.email).pipe(
      switchMap(existingUser => {
        if (existingUser) {
          return of({ success: false, error: 'Email already registered' });
        }

        // Hash password (async)
        return from(this.passwordService.hashPassword(userData.password)).pipe(
          switchMap(hashedPassword => {
            // Create new storage user
            const newStorageUser = {
              email: userData.email,
              password: hashedPassword,
              firstName: userData.firstName,
              lastName: userData.lastName,
              name: `${userData.firstName} ${userData.lastName}`,
              username: userData.email.split('@')[0],
              community: userData.community || 'singapore',
              stats: {
                todayStats: {
                  sessionsCompleted: 0,
                  totalMinutes: 0,
                  averageSession: 0,
                  streak: 0
                },
                focusSessions: []
              }
            };

            // Add user to storage
            return this.storageService.addUser(newStorageUser).pipe(
              switchMap(storageUser => {
                // Convert to User model
                const user = this.convertStorageUserToUser(storageUser);

                // Generate JWT token
                const token = this.jwtService.encode({
                  userId: storageUser.id,
                  email: storageUser.email
                }, 24);

                // Save token
                this.jwtService.saveToken(token);

                // Set current user
                this.setCurrentUser(user);

                return of({ success: true, user, token });
              })
            );
          })
        );
      }),
      catchError(error => {
        console.error('Registration error:', error);
        return of({ success: false, error: 'Registration failed. Please try again.' });
      })
    );
  }

  // Logout user
  logout(): Observable<any> {
    this.clearCurrentUser();
    this.jwtService.removeToken();
    return of({ success: true });
  }

  // Update user data
  updateUser(userData: Partial<User>): Observable<any> {
    const currentUser = this.getCurrentUser();
    if (!currentUser) {
      return of({ success: false, error: 'No user logged in' });
    }

    // Update current user in memory
    const updatedUser = { ...currentUser, ...userData };
    this.setCurrentUser(updatedUser);

    // Save to storage.json via StorageService
    const userId = parseInt(currentUser.id);
    if (!isNaN(userId)) {
      // Convert User back to StorageUser format
      const storageUpdates: any = {};
      
      // Get current user from storage to merge all updates
      return this.storageService.getUserById(userId).pipe(
        switchMap(storageUser => {
          if (!storageUser) {
            return of({ success: false, error: 'User not found in storage', user: updatedUser });
          }

          // Prepare storage updates
          if (userData.preferences) {
            storageUpdates.preferences = {
              ...(storageUser.preferences || {}),
              ...userData.preferences
            };
          }
          
          if (userData.firstName || userData.lastName) {
            storageUpdates.firstName = userData.firstName || currentUser.firstName || storageUser.firstName;
            storageUpdates.lastName = userData.lastName || currentUser.lastName || storageUser.lastName;
            storageUpdates.name = `${storageUpdates.firstName} ${storageUpdates.lastName}`.trim();
          }
          
          if (userData.email) {
            storageUpdates.email = userData.email;
          }
          
          if (userData.username) {
            storageUpdates.username = userData.username;
          }

          // Password updates are handled separately via updatePassword method
          // Don't include password in userData updates

          // Update storage
          return this.storageService.updateUser(userId, storageUpdates).pipe(
            map(success => ({ success: !!success, user: updatedUser })),
            catchError((error) => {
              console.error('Error updating user in storage:', error);
              // Still return success since we updated in memory and localStorage
              return of({ success: true, user: updatedUser });
            })
          );
        }),
        catchError((error) => {
          console.error('Error fetching user from storage:', error);
          return of({ success: true, user: updatedUser });
        })
      );
    }

    // Fallback to API (if backend is available)
    return this.http.put(`${this.API_URL}/auth/user/${currentUser.id}`, userData).pipe(
      tap((response: any) => {
        if (response.success && response.user) {
          this.setCurrentUser(response.user);
        }
      }),
      catchError((error) => {
        console.error('Update user error:', error);
        // Still return success since we updated in memory
        return of({ success: true, user: updatedUser });
      })
    );
  }

  // Update password with hashing
  updatePassword(newPassword: string, currentPassword?: string): Observable<any> {
    const currentUser = this.getCurrentUser();
    if (!currentUser) {
      return of({ success: false, error: 'No user logged in' });
    }

    const userId = parseInt(currentUser.id);
    if (isNaN(userId)) {
      return of({ success: false, error: 'Invalid user ID' });
    }

    // If current password is provided, verify it first
    if (currentPassword) {
      return this.storageService.getUserById(userId).pipe(
        switchMap(storageUser => {
          if (!storageUser) {
            return of({ success: false, error: 'User not found' });
          }

          return from(this.passwordService.verifyPassword(currentPassword, storageUser.password)).pipe(
            switchMap(isValid => {
              if (!isValid) {
                return of({ success: false, error: 'Current password is incorrect' });
              }

              // Hash new password and update
              return from(this.passwordService.hashPassword(newPassword)).pipe(
                switchMap(hashedPassword => {
                  return this.storageService.updateUser(userId, { password: hashedPassword }).pipe(
                    map(success => ({ success: !!success }))
                  );
                })
              );
            })
          );
        })
      );
    }

    // If no current password provided, just hash and update (for admin/reset scenarios)
    return from(this.passwordService.hashPassword(newPassword)).pipe(
      switchMap(hashedPassword => {
        return this.storageService.updateUser(userId, { password: hashedPassword }).pipe(
          map(success => ({ success: !!success }))
        );
      })
    );
  }

  // Set current user and save to storage
  private setCurrentUser(user: User): void {
    this.currentUserSubject.next(user);
    localStorage.setItem('currentUser', JSON.stringify(user));
  }

  // Clear current user and remove from storage
  private clearCurrentUser(): void {
    this.currentUserSubject.next(null);
    localStorage.removeItem('currentUser');
  }

  // Load user from JWT token
  private loadUserFromToken(): void {
    const payload = this.jwtService.getPayload();
    if (payload && this.jwtService.isTokenValid()) {
      // Load user from storage using token payload
      this.storageService.getUserById(payload.userId).subscribe(storageUser => {
        if (storageUser) {
          const user = this.convertStorageUserToUser(storageUser);
          this.currentUserSubject.next(user);
        } else {
          // Token valid but user not found - clear token
          this.jwtService.removeToken();
        }
      });
    }
  }

  // Convert StorageUser to User model
  private convertStorageUserToUser(storageUser: any): User {
    const stats = storageUser.stats || {};
    const todayStats = stats.todayStats || {};
    const focusSessions = stats.focusSessions || [];

    // Calculate stats from sessions
    const totalMinutes = focusSessions.reduce((sum: number, s: any) => sum + (s.duration || 0), 0);
    const totalSessions = focusSessions.length;
    const phoneUsageReduction = focusSessions.reduce((sum: number, s: any) => sum + (s.phoneUsageReduction || 0), 0);
    const socialInteractions = focusSessions.reduce((sum: number, s: any) => 
      sum + (s.socialInteractions?.length || 0), 0);
    const mindfulMoments = focusSessions.reduce((sum: number, s: any) => 
      sum + (s.mindfulMoments?.length || 0), 0);

    return {
      id: storageUser.id.toString(),
      email: storageUser.email,
      username: storageUser.username || storageUser.email.split('@')[0],
      firstName: storageUser.firstName || storageUser.name?.split(' ')[0] || '',
      lastName: storageUser.lastName || storageUser.name?.split(' ').slice(1).join(' ') || '',
      community: storageUser.community || 'singapore',
      role: storageUser.role || 'user',
      preferences: {
        // Merge preferences from storage with defaults
        ...(storageUser.preferences || {}),
        language: storageUser.preferences?.language || 'en',
        alertFrequency: storageUser.preferences?.alertFrequency || 5,
        primaryGoal: storageUser.preferences?.primaryGoal || 'mindfulness',
        notifications: storageUser.preferences?.notifications ?? true,
        location: storageUser.preferences?.location ?? true,
        screenTime: storageUser.preferences?.screenTime ?? true,
        focusMode: storageUser.preferences?.focusMode ?? true,
        theme: storageUser.preferences?.theme || 'light',
        accessibility: {
          highContrast: storageUser.preferences?.accessibility?.highContrast ?? false,
          largeText: storageUser.preferences?.accessibility?.largeText ?? false,
          screenReader: storageUser.preferences?.accessibility?.screenReader ?? false,
          ...(storageUser.preferences?.accessibility || {})
        },
        // Preserve notification and privacy settings if they exist
        notificationSettings: storageUser.preferences?.notificationSettings,
        privacySettings: storageUser.preferences?.privacySettings
      },
      stats: {
        totalSessions: todayStats.sessionsCompleted || totalSessions,
        totalMindfulMinutes: todayStats.totalMinutes || totalMinutes,
        totalSafetyAlerts: 0,
        totalSocialEngagements: socialInteractions,
        joinDate: new Date().toISOString(),
        lastActive: new Date().toISOString(),
        focusSessionStats: {
          totalPublicFocusTime: totalMinutes,
          totalSocialInteractions: socialInteractions,
          phoneUsageReduction: phoneUsageReduction,
          mindfulMoments: mindfulMoments
        },
        publicAwarenessStats: {
          totalPublicTime: 0,
          safetyAlerts: 0,
          socialPrompts: 0,
          mindfulScore: 0
        }
      },
      achievements: [],
      badges: [],
      points: 0,
      level: 1,
      homeSettings: {
        wifiNetworks: [],
        location: null,
        isConfigured: false
      },
      publicAwarenessSettings: {
        isEnabled: true,
        alertFrequency: 5,
        socialPrompts: true,
        safetyAlerts: true
      },
      joinDate: new Date().toISOString(),
      lastActive: new Date().toISOString()
    };
  }

  // Check if user has specific permission
  hasPermission(permission: string): boolean {
    const user = this.getCurrentUser();
    return user?.permissions?.includes(permission) || false;
  }

  getRole(): 'developer' | 'admin' | 'user' {
    const user = this.getCurrentUser();
    return user?.role || 'user';
  }

  isDeveloper(): boolean {
    return this.getRole() === 'developer';
  }

  isAdmin(): boolean {
    return this.getRole() === 'admin';
  }

  isUser(): boolean {
    return this.getRole() === 'user';
  }

  // Get user's community
  getUserCommunity(): string {
    const user = this.getCurrentUser();
    return user?.community || 'singapore';
  }
}
