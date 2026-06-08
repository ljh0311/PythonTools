import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import * as Notifications from 'expo-notifications';
import { locationService } from '../utils/LocationService';
import { notificationService } from '../utils/NotificationService';
import { focusSessionService } from '../utils/FocusSessionService';
import { communityService } from '../utils/CommunityService';

export interface UserData {
  id: string;
  name: string;
  email?: string;
  isGuest: boolean;
  mindfulMinutes: number;
  totalFocusSessions: number;
  badges: string[];
  joinDate: Date;
  preferences: {
    notifications: boolean;
    location: boolean;
    community: boolean;
    language: string;
  };
}

export interface FocusSession {
  id: string;
  duration: number;
  startTime: Date;
  endTime?: Date;
  isActive: boolean;
  category: string;
}

export interface UsageData {
  date: string;
  screenTimePublic: number;
  screenTimePrivate: number;
  nudgesTriggered: number;
  nudgesAcknowledged: number;
  focusSessions: number;
  mindfulMinutes: number;
}

export interface AppState {
  user: UserData | null;
  isOnboarded: boolean;
  permissions: {
    location: boolean;
    notifications: boolean;
    usageStats: boolean;
  };
  currentFocusSession: FocusSession | null;
  usageData: UsageData[];
  isLoading: boolean;
  currentZone: any;
  notificationStats: any;
  communityProgress: any;
}

interface AppContextType extends AppState {
  setUser: (user: UserData) => void;
  updateUser: (updates: Partial<UserData>) => void;
  setOnboarded: (onboarded: boolean) => void;
  requestPermissions: () => Promise<void>;
  startFocusSession: (duration: number, category: string) => void;
  endFocusSession: () => void;
  addUsageData: (data: UsageData) => void;
  addMindfulMinutes: (minutes: number) => void;
  addBadge: (badge: string) => void;
  resetApp: () => void;
  continueAsGuest: () => Promise<void>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};

const defaultUser: UserData = {
  id: '1',
  name: 'User',
  isGuest: false,
  mindfulMinutes: 0,
  totalFocusSessions: 0,
  badges: [],
  joinDate: new Date(),
  preferences: {
    notifications: true,
    location: true,
    community: false,
    language: 'en',
  },
};

const initialState: AppState = {
  user: null,
  isOnboarded: false,
  permissions: {
    location: false,
    notifications: false,
    usageStats: false,
  },
  currentFocusSession: null,
  usageData: [],
  isLoading: true,
  currentZone: null,
  notificationStats: null,
  communityProgress: null,
};

interface AppProviderProps {
  children: ReactNode;
}

export const AppProvider: React.FC<AppProviderProps> = ({ children }) => {
  const [state, setState] = useState<AppState>(initialState);

  // Load app data on startup
  useEffect(() => {
    loadAppData();
  }, []);

  // Initialize services and start monitoring
  useEffect(() => {
    if (!state.isLoading && state.isOnboarded) {
      initializeServices();
    }
  }, [state.isLoading, state.isOnboarded]);

  const loadAppData = async () => {
    try {
      const [onboarded, userData, usageData] = await Promise.all([
        AsyncStorage.getItem('isOnboarded'),
        AsyncStorage.getItem('userData'),
        AsyncStorage.getItem('usageData'),
      ]);

      setState(prev => ({
        ...prev,
        isOnboarded: onboarded === 'true',
        user: userData ? JSON.parse(userData) : null,
        usageData: usageData ? JSON.parse(usageData) : [],
        isLoading: false,
      }));
    } catch (error) {
      console.error('Error loading app data:', error);
      setState(prev => ({ ...prev, isLoading: false }));
    }
  };

  const setUser = async (user: UserData) => {
    setState(prev => ({ ...prev, user }));
    await AsyncStorage.setItem('userData', JSON.stringify(user));
  };

  const updateUser = async (updates: Partial<UserData>) => {
    if (!state.user) return;
    
    const updatedUser = { ...state.user, ...updates };
    setState(prev => ({ ...prev, user: updatedUser }));
    await AsyncStorage.setItem('userData', JSON.stringify(updatedUser));
  };

  const setOnboarded = async (onboarded: boolean) => {
    setState(prev => ({ ...prev, isOnboarded: onboarded }));
    await AsyncStorage.setItem('isOnboarded', onboarded.toString());
  };

  const requestPermissions = async () => {
    try {
      // Request location permission
      const locationPermission = await Location.requestForegroundPermissionsAsync();
      
      // Request notification permission
      const notificationPermission = await Notifications.requestPermissionsAsync();
      
      setState(prev => ({
        ...prev,
        permissions: {
          location: locationPermission.status === 'granted',
          notifications: notificationPermission.status === 'granted',
          usageStats: false, // This requires special handling on Android
        },
      }));
    } catch (error) {
      console.error('Error requesting permissions:', error);
    }
  };

  const initializeServices = async () => {
    try {
      // Initialize all services
      await Promise.all([
        locationService.initialize(),
        notificationService.initialize(),
        focusSessionService.initialize(),
        communityService.initialize(),
      ]);

      // Start location tracking if permission granted
      if (state.permissions.location) {
        await locationService.startTracking();
      }

      // Start monitoring for nudges and safety reminders
      startMonitoring();

      console.log('All services initialized successfully');
    } catch (error) {
      console.error('Error initializing services:', error);
    }
  };

  const startMonitoring = () => {
    // Check for nudges and safety reminders every 30 seconds
    const monitoringInterval = setInterval(async () => {
      if (!state.permissions.location) return;

      const currentZone = locationService.getCurrentZone();
      const screenTimeInZone = locationService.getScreenTimeInCurrentZone();

      // Update current zone in state
      setState(prev => ({ ...prev, currentZone }));

      // Check for safety reminders
      if (locationService.shouldShowSafetyReminder()) {
        await notificationService.sendSafetyReminder(currentZone);
      }

      // Check for mindful nudges
      if (locationService.shouldShowMindfulNudge()) {
        await notificationService.sendMindfulNudge(currentZone);
      }

      // Suggest focus sessions
      await focusSessionService.suggestFocusSession();

      // Update notification stats
      const notificationStats = notificationService.getNotificationStats();
      setState(prev => ({ ...prev, notificationStats }));

      // Update community progress
      const communityProgress = communityService.getUserProgress();
      setState(prev => ({ ...prev, communityProgress }));

    }, 30000); // 30 seconds

    // Cleanup interval on unmount
    return () => clearInterval(monitoringInterval);
  };

  const startFocusSession = async (duration: number, category: string) => {
    try {
      const session = await focusSessionService.startSession(duration, category);
      setState(prev => ({ ...prev, currentFocusSession: session }));
      
      // Update community progress
      await communityService.addFocusSession();
    } catch (error) {
      console.error('Error starting focus session:', error);
    }
  };

  const endFocusSession = async () => {
    try {
      const session = await focusSessionService.endSession();
      if (session) {
        setState(prev => ({ 
          ...prev, 
          currentFocusSession: null,
          user: prev.user ? {
            ...prev.user,
            totalFocusSessions: prev.user.totalFocusSessions + 1,
            mindfulMinutes: prev.user.mindfulMinutes + session.mindfulMinutes,
          } : null,
        }));

        // Update community progress
        await communityService.addMindfulMinutes(session.mindfulMinutes);
      }
    } catch (error) {
      console.error('Error ending focus session:', error);
    }
  };

  const addUsageData = async (data: UsageData) => {
    const newUsageData = [...state.usageData, data];
    setState(prev => ({ ...prev, usageData: newUsageData }));
    await AsyncStorage.setItem('usageData', JSON.stringify(newUsageData));
  };

  const addMindfulMinutes = async (minutes: number) => {
    if (!state.user) return;
    
    const updatedUser = {
      ...state.user,
      mindfulMinutes: state.user.mindfulMinutes + minutes,
    };
    
    setState(prev => ({ ...prev, user: updatedUser }));
    await AsyncStorage.setItem('userData', JSON.stringify(updatedUser));
    
    // Update community progress
    await communityService.addMindfulMinutes(minutes);
  };

  const addBadge = async (badge: string) => {
    if (!state.user || state.user.badges.includes(badge)) return;
    
    const updatedUser = {
      ...state.user,
      badges: [...state.user.badges, badge],
    };
    
    setState(prev => ({ ...prev, user: updatedUser }));
    await AsyncStorage.setItem('userData', JSON.stringify(updatedUser));
  };

  const resetApp = async () => {
    await AsyncStorage.clear();
    
    // Clear all service data
    await Promise.all([
      locationService.clearLocationData(),
      notificationService.clearNotificationData(),
      focusSessionService.clearSessionData(),
      communityService.clearCommunityData(),
    ]);
    
    setState(initialState);
  };

  const continueAsGuest = async () => {
    const guestUser: UserData = {
      id: `guest-${Date.now()}`,
      name: 'Guest',
      email: undefined,
      isGuest: true,
      mindfulMinutes: 0,
      totalFocusSessions: 0,
      badges: [],
      joinDate: new Date(),
      preferences: {
        notifications: false,
        location: false,
        community: false,
        language: 'en',
      },
    };

    await setUser(guestUser);
    await setOnboarded(true);
  };

  const contextValue: AppContextType = {
    ...state,
    setUser,
    updateUser,
    setOnboarded,
    requestPermissions,
    startFocusSession,
    endFocusSession,
    addUsageData,
    addMindfulMinutes,
    addBadge,
    resetApp,
    continueAsGuest,
  };

  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
}; 