import { Injectable } from '@angular/core';
import { Observable, from, of } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';

/**
 * Push Notification Service
 * Handles browser push notifications and permission requests
 */
@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  private permission: NotificationPermission = 'default';

  constructor() {
    this.checkPermission();
  }

  /**
   * Check current notification permission status
   */
  checkPermission(): NotificationPermission {
    if ('Notification' in window) {
      this.permission = Notification.permission;
    }
    return this.permission;
  }

  /**
   * Request notification permission from user
   */
  requestPermission(): Observable<NotificationPermission> {
    if (!('Notification' in window)) {
      console.warn('This browser does not support notifications');
      return of('denied');
    }

    if (this.permission === 'granted') {
      return of('granted');
    }

    if (this.permission === 'denied') {
      console.warn('Notification permission has been denied');
      return of('denied');
    }

    return from(Notification.requestPermission() as Promise<NotificationPermission>).pipe(
      switchMap((permission: NotificationPermission) => {
        this.permission = permission;
        return of(permission as NotificationPermission);
      }),
      catchError(error => {
        console.error('Error requesting notification permission:', error);
        return of('denied' as NotificationPermission);
      })
    ) as Observable<NotificationPermission>;
  }

  /**
   * Check if notifications are supported
   */
  isSupported(): boolean {
    return 'Notification' in window && 'serviceWorker' in navigator;
  }

  /**
   * Check if permission is granted
   */
  hasPermission(): boolean {
    return this.checkPermission() === 'granted';
  }

  /**
   * Show a notification
   */
  showNotification(title: string, options?: NotificationOptions): Observable<Notification | null> {
    if (!this.hasPermission()) {
      console.warn('Notification permission not granted');
      return of(null);
    }

    if (!('serviceWorker' in navigator)) {
      // Fallback to regular notification if service worker not available
      return from(this.showBrowserNotification(title, options));
    }

    // Use service worker for notifications
    return from(
      navigator.serviceWorker.ready.then(registration => {
        registration.showNotification(title, {
          icon: '/assets/icon-192x192.png',
          badge: '/assets/icon-192x192.png',
          vibrate: [200, 100, 200],
          ...options
        } as NotificationOptions & { vibrate?: number[] });
        return null; // Service worker notifications don't return a Notification object
      })
    ).pipe(
      catchError(error => {
        console.error('Error showing notification:', error);
        // Fallback to browser notification
        return from(this.showBrowserNotification(title, options));
      })
    );
  }

  /**
   * Show browser notification (fallback)
   */
  private async showBrowserNotification(title: string, options?: NotificationOptions): Promise<Notification | null> {
    try {
      const notification = new Notification(title, {
        icon: '/assets/icon-192x192.png',
        badge: '/assets/icon-192x192.png',
        ...options
      });

      // Auto-close after 5 seconds
      setTimeout(() => {
        notification.close();
      }, 5000);

      return notification;
    } catch (error) {
      console.error('Error creating browser notification:', error);
      return null;
    }
  }

  /**
   * Show session reminder notification
   */
  showSessionReminder(): Observable<Notification | null> {
    return this.showNotification('Time for a Focus Session!', {
      body: 'Take a moment to practice mindfulness and reduce phone usage.',
      tag: 'session-reminder',
      requireInteraction: false
    });
  }

  /**
   * Show achievement notification
   */
  showAchievementUnlocked(achievementName: string): Observable<Notification | null> {
    return this.showNotification('Achievement Unlocked! 🎉', {
      body: `You've earned: ${achievementName}`,
      tag: 'achievement',
      requireInteraction: true
    });
  }

  /**
   * Show goal completion notification
   */
  showGoalCompleted(goalName: string): Observable<Notification | null> {
    return this.showNotification('Goal Completed! ✅', {
      body: `Congratulations! You've completed: ${goalName}`,
      tag: 'goal-completed',
      requireInteraction: false
    });
  }

  /**
   * Show daily reminder notification
   */
  showDailyReminder(): Observable<Notification | null> {
    return this.showNotification('Daily Mindfulness Reminder', {
      body: 'Remember to practice mindfulness in public spaces today!',
      tag: 'daily-reminder',
      requireInteraction: false
    });
  }

  /**
   * Close all notifications with a specific tag
   */
  closeNotificationsByTag(tag: string): void {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.ready.then(registration => {
        registration.getNotifications({ tag }).then(notifications => {
          notifications.forEach(notification => notification.close());
        });
      });
    }
  }
}

