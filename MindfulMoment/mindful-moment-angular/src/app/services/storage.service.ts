import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of, BehaviorSubject } from 'rxjs';
import { map, catchError, tap, switchMap } from 'rxjs/operators';

export type StorageUserRole = 'developer' | 'admin' | 'user';

export interface StorageUser {
  id: number;
  name?: string;
  email: string;
  password: string; // Hashed password
  firstName?: string;
  lastName?: string;
  username?: string;
  community?: string;
  role?: StorageUserRole;
  preferences?: any; // User preferences including notification settings
  stats?: {
    todayStats?: {
      sessionsCompleted: number;
      totalMinutes: number;
      averageSession: number;
      streak: number;
    };
    focusSessions?: any[];
    publicAwarenessStats?: {
      totalPublicTime?: number;
      safetyAlerts?: number;
      socialPrompts?: number;
      mindfulScore?: number;
      locationScores?: {
        publicSpaces?: number;
        mrtStations?: number;
        shoppingCenters?: number;
      };
    };
  };
  achievements?: any[];
  goals?: any[];
}

export interface StorageData {
  users: StorageUser[];
  communityGroups?: any[];
  safetyTips?: any[];
  emergencyContacts?: any[];
}

@Injectable({
  providedIn: 'root'
})
export class StorageService {
  private readonly STORAGE_KEY = 'mindfulMoment_storage';
  private readonly STORAGE_FILE = 'assets/storage.json';
  private storageDataSubject = new BehaviorSubject<StorageData | null>(null);
  public storageData$ = this.storageDataSubject.asObservable();
  private isLoaded = false;

  constructor(private http: HttpClient) {
    this.loadStorage().subscribe();
  }

  /**
   * Load storage data from assets/storage.json or localStorage
   */
  loadStorage(): Observable<StorageData> {
    if (this.isLoaded && this.storageDataSubject.value) {
      return of(this.storageDataSubject.value);
    }

    // Try localStorage first (for user modifications)
    const localData = this.getLocalStorage();
    if (localData) {
      this.storageDataSubject.next(localData);
      this.isLoaded = true;
      return of(localData);
    }

    // Fallback to assets/storage.json
    return this.http.get<StorageData>(this.STORAGE_FILE).pipe(
      tap(data => {
        this.storageDataSubject.next(data);
        this.saveLocalStorage(data);
        this.isLoaded = true;
      }),
      catchError(error => {
        console.error('Error loading storage.json:', error);
        // Return empty storage if file doesn't exist
        const emptyStorage: StorageData = { users: [] };
        this.storageDataSubject.next(emptyStorage);
        this.isLoaded = true;
        return of(emptyStorage);
      })
    );
  }

  /**
   * Get user by email
   */
  getUserByEmail(email: string): Observable<StorageUser | null> {
    // Ensure storage is loaded first
    const currentData = this.storageDataSubject.value;
    if (currentData) {
      const user = currentData.users.find(user => user.email.toLowerCase() === email.toLowerCase()) || null;
      return of(user);
    }
    
    // Load storage if not loaded yet
    return this.loadStorage().pipe(
      map(data => {
        return data.users.find(user => user.email.toLowerCase() === email.toLowerCase()) || null;
      })
    );
  }

  /**
   * Get user by ID
   */
  getUserById(id: number): Observable<StorageUser | null> {
    // Ensure storage is loaded first
    const currentData = this.storageDataSubject.value;
    if (currentData) {
      const user = currentData.users.find(user => user.id === id) || null;
      return of(user);
    }
    
    // Load storage if not loaded yet
    return this.loadStorage().pipe(
      map(data => {
        return data.users.find(user => user.id === id) || null;
      })
    );
  }

  /**
   * Add new user to storage
   */
  addUser(user: Omit<StorageUser, 'id'>): Observable<StorageUser> {
    // Ensure storage is loaded first
    let currentData = this.storageDataSubject.value;
    if (!currentData) {
      currentData = { users: [] };
    }

    // Generate new ID
    const maxId = currentData.users.length > 0 
      ? Math.max(...currentData.users.map(u => u.id)) 
      : 0;
    const newUser: StorageUser = {
      ...user,
      id: maxId + 1
    };

    currentData.users.push(newUser);
    this.saveLocalStorage(currentData);
    this.storageDataSubject.next(currentData);
    
    return of(newUser);
  }

  /**
   * Update user in storage
   */
  updateUser(userId: number, updates: Partial<StorageUser>): Observable<boolean> {
    const currentData = this.storageDataSubject.value;
    if (!currentData) {
      return of(false);
    }

    const userIndex = currentData.users.findIndex(u => u.id === userId);
    if (userIndex === -1) {
      return of(false);
    }

    currentData.users[userIndex] = {
      ...currentData.users[userIndex],
      ...updates
    };

    this.saveLocalStorage(currentData);
    this.storageDataSubject.next(currentData);
    return of(true);
  }

  /**
   * Update community groups in storage (used by dev tools and DataService to persist join requests etc.)
   */
  updateCommunityGroups(groups: any[]): void {
    let currentData = this.storageDataSubject.value;
    if (!currentData) {
      currentData = { users: [] };
    }
    currentData = { ...currentData, communityGroups: groups };
    this.saveLocalStorage(currentData);
    this.storageDataSubject.next(currentData);
  }

  /**
   * Save to localStorage (since we can't write to static files)
   */
  private saveLocalStorage(data: StorageData): void {
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(data));
    } catch (error) {
      console.error('Error saving to localStorage:', error);
    }
  }

  /**
   * Get from localStorage
   */
  private getLocalStorage(): StorageData | null {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch (error) {
      console.error('Error reading from localStorage:', error);
      return null;
    }
  }

  /**
   * Export storage data as JSON
   */
  exportStorage(): string {
    const data = this.storageDataSubject.value || { users: [] };
    return JSON.stringify(data, null, 2);
  }
}

