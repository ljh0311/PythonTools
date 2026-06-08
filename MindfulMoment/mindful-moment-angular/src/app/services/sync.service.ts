import { Injectable } from '@angular/core';
import { Observable, from, of } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';
import { DataService } from './data.service';
import { StorageService } from './storage.service';

/**
 * Offline Sync Service
 * Handles syncing data when coming back online
 */
@Injectable({
  providedIn: 'root'
})
export class SyncService {
  private syncQueue: Array<{ type: string; data: any; timestamp: number }> = [];
  private isOnline = navigator.onLine;
  private isSyncing = false;

  constructor(
    private dataService: DataService,
    private storageService: StorageService
  ) {
    this.initializeSync();
  }

  /**
   * Initialize sync service and listen for online/offline events
   */
  private initializeSync(): void {
    // Listen for online event
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.syncPendingData();
    });

    // Listen for offline event
    window.addEventListener('offline', () => {
      this.isOnline = false;
    });

    // Check if online on init
    if (this.isOnline) {
      // Small delay to ensure app is fully loaded
      setTimeout(() => this.syncPendingData(), 2000);
    }

    // Load sync queue from storage
    this.loadSyncQueue();
  }

  /**
   * Add item to sync queue
   */
  addToSyncQueue(type: string, data: any): void {
    const queueItem = {
      type,
      data,
      timestamp: Date.now()
    };

    this.syncQueue.push(queueItem);
    this.saveSyncQueue();

    // Try to sync immediately if online
    if (this.isOnline) {
      this.syncPendingData();
    }
  }

  /**
   * Sync pending data from queue
   */
  syncPendingData(): Observable<boolean> {
    if (this.isSyncing || !this.isOnline || this.syncQueue.length === 0) {
      return of(false);
    }

    this.isSyncing = true;

    return from(this.performSync()).pipe(
      switchMap(success => {
        this.isSyncing = false;
        if (success) {
          this.syncQueue = [];
          this.saveSyncQueue();
        }
        return of(success);
      }),
      catchError(error => {
        console.error('Sync error:', error);
        this.isSyncing = false;
        return of(false);
      })
    );
  }

  /**
   * Perform actual sync operation
   */
  private async performSync(): Promise<boolean> {
    try {
      const itemsToSync = [...this.syncQueue];
      let allSuccess = true;

      for (const item of itemsToSync) {
        try {
          await this.syncItem(item);
        } catch (error) {
          console.error(`Failed to sync item ${item.type}:`, error);
          allSuccess = false;
          // Keep failed items in queue for retry
        }
      }

      return allSuccess;
    } catch (error) {
      console.error('Sync operation failed:', error);
      return false;
    }
  }

  /**
   * Sync individual item based on type
   */
  private async syncItem(item: { type: string; data: any }): Promise<void> {
    switch (item.type) {
      case 'focus-session':
        // Sync focus session
        await this.dataService.createFocusSession(item.data).toPromise();
        break;
      case 'user-update':
        // Sync user updates
        await this.dataService.updateUserStats(item.data).toPromise();
        break;
      case 'achievement':
        // Sync achievements
        // Implementation depends on your API structure
        break;
      default:
        console.warn(`Unknown sync type: ${item.type}`);
    }
  }

  /**
   * Save sync queue to localStorage
   */
  private saveSyncQueue(): void {
    try {
      localStorage.setItem('syncQueue', JSON.stringify(this.syncQueue));
    } catch (error) {
      console.error('Failed to save sync queue:', error);
    }
  }

  /**
   * Load sync queue from localStorage
   */
  private loadSyncQueue(): void {
    try {
      const stored = localStorage.getItem('syncQueue');
      if (stored) {
        this.syncQueue = JSON.parse(stored);
        // Remove items older than 7 days
        const sevenDaysAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
        this.syncQueue = this.syncQueue.filter(item => item.timestamp > sevenDaysAgo);
        this.saveSyncQueue();
      }
    } catch (error) {
      console.error('Failed to load sync queue:', error);
      this.syncQueue = [];
    }
  }

  /**
   * Get sync queue status
   */
  getSyncStatus(): { pending: number; isOnline: boolean; isSyncing: boolean } {
    return {
      pending: this.syncQueue.length,
      isOnline: this.isOnline,
      isSyncing: this.isSyncing
    };
  }

  /**
   * Clear sync queue (use with caution)
   */
  clearSyncQueue(): void {
    this.syncQueue = [];
    this.saveSyncQueue();
  }
}

