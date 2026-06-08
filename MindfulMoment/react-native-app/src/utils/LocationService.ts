import * as Location from 'expo-location';
import * as TaskManager from 'expo-task-manager';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { GPSMode, getGPSModeConfig, getRecommendedGPSMode } from './GPSConfig';

export interface GeofenceZone {
  id: string;
  name: string;
  type: 'mrt_station' | 'busy_crossing' | 'public_space' | 'high_risk';
  latitude: number;
  longitude: number;
  radius: number; // in meters
  safetyLevel: 'low' | 'medium' | 'high';
}

export interface LocationEvent {
  timestamp: Date;
  zoneId: string;
  zoneName: string;
  eventType: 'entered' | 'exited';
  screenTimeInZone?: number; // minutes
  safetyReminderShown?: boolean;
}

export interface GPSStatus {
  isEnabled: boolean;
  accuracy: number;        // Accuracy in meters
  signalQuality: 'excellent' | 'good' | 'fair' | 'poor' | 'none';
  provider: 'gps' | 'network' | 'passive' | 'unknown';
  satelliteCount?: number; // Available on Android
  lastUpdate: Date;
}

// Singapore MRT stations and key public areas
const SINGAPORE_GEOFENCES: GeofenceZone[] = [
  // MRT Stations (major ones)
  { id: 'mrt_raffles_place', name: 'Raffles Place MRT', type: 'mrt_station', latitude: 1.2838, longitude: 103.8513, radius: 200, safetyLevel: 'high' },
  { id: 'mrt_city_hall', name: 'City Hall MRT', type: 'mrt_station', latitude: 1.2932, longitude: 103.8522, radius: 200, safetyLevel: 'high' },
  { id: 'mrt_orchard', name: 'Orchard MRT', type: 'mrt_station', latitude: 1.3041, longitude: 103.8324, radius: 200, safetyLevel: 'high' },
  { id: 'mrt_somerset', name: 'Somerset MRT', type: 'mrt_station', latitude: 1.3002, longitude: 103.8390, radius: 200, safetyLevel: 'high' },
  { id: 'mrt_dhoby_ghaut', name: 'Dhoby Ghaut MRT', type: 'mrt_station', latitude: 1.2990, longitude: 103.8457, radius: 200, safetyLevel: 'high' },
  { id: 'mrt_marina_bay', name: 'Marina Bay MRT', type: 'mrt_station', latitude: 1.2767, longitude: 103.8545, radius: 200, safetyLevel: 'high' },
  { id: 'mrt_bugis', name: 'Bugis MRT', type: 'mrt_station', latitude: 1.3009, longitude: 103.8559, radius: 200, safetyLevel: 'high' },
  { id: 'mrt_lavender', name: 'Lavender MRT', type: 'mrt_station', latitude: 1.3074, longitude: 103.8630, radius: 200, safetyLevel: 'high' },
  { id: 'mrt_kallang', name: 'Kallang MRT', type: 'mrt_station', latitude: 1.3114, longitude: 103.8714, radius: 200, safetyLevel: 'high' },
  { id: 'mrt_aljunied', name: 'Aljunied MRT', type: 'mrt_station', latitude: 1.3164, longitude: 103.8829, radius: 200, safetyLevel: 'high' },
  
  // Busy crossings and intersections
  { id: 'crossing_orchard_road', name: 'Orchard Road Crossing', type: 'busy_crossing', latitude: 1.3041, longitude: 103.8324, radius: 150, safetyLevel: 'high' },
  { id: 'crossing_raffles_place', name: 'Raffles Place Crossing', type: 'busy_crossing', latitude: 1.2838, longitude: 103.8513, radius: 150, safetyLevel: 'high' },
  { id: 'crossing_marina_bay', name: 'Marina Bay Crossing', type: 'busy_crossing', latitude: 1.2767, longitude: 103.8545, radius: 150, safetyLevel: 'high' },
  
  // Public spaces
  { id: 'marina_bay_sands', name: 'Marina Bay Sands', type: 'public_space', latitude: 1.2838, longitude: 103.8591, radius: 300, safetyLevel: 'medium' },
  { id: 'gardens_by_bay', name: 'Gardens by the Bay', type: 'public_space', latitude: 1.2816, longitude: 103.8636, radius: 400, safetyLevel: 'low' },
  { id: 'merlion_park', name: 'Merlion Park', type: 'public_space', latitude: 1.2868, longitude: 103.8545, radius: 200, safetyLevel: 'medium' },
  { id: 'clarke_quay', name: 'Clarke Quay', type: 'public_space', latitude: 1.2889, longitude: 103.8467, radius: 250, safetyLevel: 'medium' },
  
  // High-risk areas (platform edges, busy roads)
  { id: 'high_risk_platform_1', name: 'MRT Platform Edge', type: 'high_risk', latitude: 1.2838, longitude: 103.8513, radius: 50, safetyLevel: 'high' },
  { id: 'high_risk_platform_2', name: 'MRT Platform Edge', type: 'high_risk', latitude: 1.2932, longitude: 103.8522, radius: 50, safetyLevel: 'high' },
];

// Task names for background operations
const GEOFENCE_TASK_NAME = 'geofence-task';
const LOCATION_TASK_NAME = 'background-location-task';

class LocationService {
  private currentLocation: Location.LocationObject | null = null;
  private currentZone: GeofenceZone | null = null;
  private locationEvents: LocationEvent[] = [];
  private isTracking = false;
  private locationSubscription: Location.LocationSubscription | null = null;
  private screenTimeInCurrentZone = 0;
  private zoneEntryTime: Date | null = null;
  private gpsStatus: GPSStatus = {
    isEnabled: false,
    accuracy: 0,
    signalQuality: 'none',
    provider: 'unknown',
    lastUpdate: new Date(),
  };
  private useFallbackLocation = false;
  private lastKnownGoodLocation: Location.LocationObject | null = null;
  private gpsMode: GPSMode = 'high_accuracy'; // Default mode

  async initialize(): Promise<boolean> {
    try {
      // Check if location permission is granted
      const { status } = await Location.getForegroundPermissionsAsync();
      if (status !== 'granted') {
        return false;
      }

      // Load saved location events
      await this.loadLocationEvents();
      
      // Load saved GPS mode
      await this.loadGPSMode();
      
      return true;
    } catch (error) {
      console.error('Error initializing LocationService:', error);
      return false;
    }
  }

  async startTracking(): Promise<void> {
    if (this.isTracking) return;

    try {
      // Get GPS configuration for current mode
      const gpsConfig = getGPSModeConfig(this.gpsMode);
      
      this.locationSubscription = await Location.watchPositionAsync(
        {
          accuracy: gpsConfig.accuracy,
          timeInterval: gpsConfig.timeInterval,
          distanceInterval: gpsConfig.distanceInterval,
          mayShowUserSettingsDialog: true, // Prompt user if GPS is off
        },
        (location) => {
          this.handleLocationUpdate(location);
        }
      );

      this.isTracking = true;
      console.log(`Location tracking started with ${this.gpsMode} mode`);
    } catch (error) {
      console.error('Error starting location tracking:', error);
    }
  }

  async stopTracking(): Promise<void> {
    if (this.locationSubscription) {
      this.locationSubscription.remove();
      this.locationSubscription = null;
    }
    this.isTracking = false;
    console.log('Location tracking stopped');
  }

  async registerGeofences(): Promise<void> {
    try {
      const geofences = SINGAPORE_GEOFENCES.map(zone => ({
        identifier: zone.id,
        latitude: zone.latitude,
        longitude: zone.longitude,
        radius: zone.radius,
        notifyOnEnter: true,
        notifyOnExit: true,
      }));

      await Location.startGeofencingAsync(GEOFENCE_TASK_NAME, geofences);
      console.log('Geofences registered successfully');
    } catch (error) {
      console.error('Error registering geofences:', error);
    }
  }

  async unregisterGeofences(): Promise<void> {
    try {
      await Location.stopGeofencingAsync(GEOFENCE_TASK_NAME);
      console.log('Geofences unregistered');
    } catch (error) {
      console.error('Error unregistering geofences:', error);
    }
  }

  async handleZoneEntryById(zoneId: string): Promise<void> {
    const zone = SINGAPORE_GEOFENCES.find(z => z.id === zoneId);
    if (zone) {
      await this.handleZoneEntry(zone);
    }
  }

  async handleZoneExitById(zoneId: string): Promise<void> {
    if (this.currentZone?.id === zoneId) {
      await this.handleZoneExit();
    }
  }

  async startBackgroundLocationUpdates(): Promise<boolean> {
    try {
      const { status } = await Location.requestBackgroundPermissionsAsync();
      if (status !== 'granted') {
        console.warn('Background location permission not granted');
        return false;
      }

      // Use a battery-friendly configuration for background
      // Always use 'balanced' mode for background to conserve battery
      const backgroundConfig = getGPSModeConfig('balanced');

      await Location.startLocationUpdatesAsync(LOCATION_TASK_NAME, {
        accuracy: backgroundConfig.accuracy,
        timeInterval: 30000,  // Every 30 seconds in background (battery-friendly)
        distanceInterval: 20, // Update when moved 20 meters
        foregroundService: {
          notificationTitle: 'MindfulMoment Active',
          notificationBody: 'Tracking location for safety reminders and contextual nudges',
          notificationColor: '#4A90E2',
        },
        pausesUpdatesAutomatically: true, // Pause when stationary
        showsBackgroundLocationIndicator: true,
      });

      console.log('Background location tracking started');
      return true;
    } catch (error) {
      console.error('Error starting background location:', error);
      return false;
    }
  }

  async stopBackgroundLocationUpdates(): Promise<void> {
    try {
      const isRegistered = await TaskManager.isTaskRegisteredAsync(LOCATION_TASK_NAME);
      if (isRegistered) {
        await Location.stopLocationUpdatesAsync(LOCATION_TASK_NAME);
        console.log('Background location tracking stopped');
      }
    } catch (error) {
      console.error('Error stopping background location:', error);
    }
  }

  async isBackgroundLocationEnabled(): Promise<boolean> {
    try {
      return await TaskManager.isTaskRegisteredAsync(LOCATION_TASK_NAME);
    } catch {
      return false;
    }
  }

  private async handleLocationUpdate(location: Location.LocationObject): Promise<void> {
    const accuracy = location.coords.accuracy || 999;

    // Store last known good location (< 20m accuracy)
    if (accuracy < 20) {
      this.lastKnownGoodLocation = location;
      this.useFallbackLocation = false;
    }

    // Use last known good location if current is poor
    if (accuracy > 100 && this.lastKnownGoodLocation) {
      console.warn(`Poor GPS (${accuracy}m), using last known good location`);
      this.useFallbackLocation = true;
      location = this.lastKnownGoodLocation;
    }

    this.currentLocation = location;
    this.updateGPSStatus(location);
    
    // Check if we're in any geofence
    const nearbyZone = this.findNearbyZone(location.coords.latitude, location.coords.longitude);
    
    if (nearbyZone && nearbyZone.id !== this.currentZone?.id) {
      // Entered a new zone
      await this.handleZoneEntry(nearbyZone);
    } else if (!nearbyZone && this.currentZone) {
      // Exited current zone
      await this.handleZoneExit();
    } else if (nearbyZone && this.currentZone) {
      // Still in the same zone - update screen time
      this.updateScreenTimeInZone();
    }
  }

  private findNearbyZone(latitude: number, longitude: number): GeofenceZone | null {
    for (const zone of SINGAPORE_GEOFENCES) {
      const distance = this.calculateDistance(
        latitude,
        longitude,
        zone.latitude,
        zone.longitude
      );
      
      if (distance <= zone.radius) {
        return zone;
      }
    }
    return null;
  }

  private calculateDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
    const R = 6371e3; // Earth's radius in meters
    const φ1 = lat1 * Math.PI / 180;
    const φ2 = lat2 * Math.PI / 180;
    const Δφ = (lat2 - lat1) * Math.PI / 180;
    const Δλ = (lon2 - lon1) * Math.PI / 180;

    const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
              Math.cos(φ1) * Math.cos(φ2) *
              Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return R * c;
  }

  private async handleZoneEntry(zone: GeofenceZone): Promise<void> {
    this.currentZone = zone;
    this.zoneEntryTime = new Date();
    this.screenTimeInCurrentZone = 0;

    const event: LocationEvent = {
      timestamp: new Date(),
      zoneId: zone.id,
      zoneName: zone.name,
      eventType: 'entered',
    };

    this.locationEvents.push(event);
    await this.saveLocationEvents();

    console.log(`Entered zone: ${zone.name} (${zone.type})`);
  }

  private async handleZoneExit(): Promise<void> {
    if (!this.currentZone || !this.zoneEntryTime) return;

    const event: LocationEvent = {
      timestamp: new Date(),
      zoneId: this.currentZone.id,
      zoneName: this.currentZone.name,
      eventType: 'exited',
      screenTimeInZone: this.screenTimeInCurrentZone,
    };

    this.locationEvents.push(event);
    await this.saveLocationEvents();

    console.log(`Exited zone: ${this.currentZone.name} (Screen time: ${this.screenTimeInCurrentZone} minutes)`);

    this.currentZone = null;
    this.zoneEntryTime = null;
    this.screenTimeInCurrentZone = 0;
  }

  private updateScreenTimeInZone(): void {
    if (this.zoneEntryTime) {
      const now = new Date();
      const timeDiff = (now.getTime() - this.zoneEntryTime.getTime()) / (1000 * 60); // minutes
      this.screenTimeInCurrentZone = Math.floor(timeDiff);
    }
  }

  getCurrentZone(): GeofenceZone | null {
    return this.currentZone;
  }

  getLocationEvents(): LocationEvent[] {
    return this.locationEvents;
  }

  getScreenTimeInCurrentZone(): number {
    return this.screenTimeInCurrentZone;
  }

  getGPSStatus(): GPSStatus {
    return this.gpsStatus;
  }

  private updateGPSStatus(location: Location.LocationObject): void {
    const accuracy = location.coords.accuracy || 999;
    
    this.gpsStatus = {
      isEnabled: true,
      accuracy: accuracy,
      signalQuality: this.getSignalQuality(accuracy),
      provider: this.determineProvider(location),
      lastUpdate: new Date(),
    };
  }

  private getSignalQuality(accuracy: number): GPSStatus['signalQuality'] {
    if (accuracy <= 5) return 'excellent';  // GPS high accuracy
    if (accuracy <= 15) return 'good';      // GPS normal
    if (accuracy <= 50) return 'fair';      // GPS + WiFi
    if (accuracy <= 200) return 'poor';     // WiFi/Cell only
    return 'none';
  }

  private determineProvider(location: Location.LocationObject): GPSStatus['provider'] {
    const accuracy = location.coords.accuracy || 999;
    if (accuracy <= 15) return 'gps';      // Likely GPS
    if (accuracy <= 100) return 'network'; // Likely WiFi/Cell
    return 'passive';
  }

  shouldShowSafetyReminder(): boolean {
    if (!this.currentZone) return false;
    
    // Show safety reminder for high-risk areas or after extended screen time
    return this.currentZone.safetyLevel === 'high' || 
           (this.screenTimeInCurrentZone > 5 && this.currentZone.type === 'mrt_station');
  }

  shouldShowMindfulNudge(): boolean {
    if (!this.currentZone) return false;
    
    // Show mindful nudge after 2+ minutes of screen time in public spaces
    return this.screenTimeInCurrentZone > 2 && 
           (this.currentZone.type === 'public_space' || this.currentZone.type === 'mrt_station');
  }

  async getAnonymizedSummary(): Promise<any> {
    // Only send anonymized data for community features
    const today = new Date().toISOString().split('T')[0];
    const todayEvents = this.locationEvents.filter(event => 
      event.timestamp.toISOString().startsWith(today)
    );

    return {
      date: today,
      zonesVisited: todayEvents.length,
      totalScreenTimeInPublic: todayEvents.reduce((sum, event) => 
        sum + (event.screenTimeInZone || 0), 0
      ),
      safetyRemindersTriggered: todayEvents.filter(event => 
        event.safetyReminderShown
      ).length,
    };
  }

  private async loadLocationEvents(): Promise<void> {
    try {
      const eventsData = await AsyncStorage.getItem('locationEvents');
      if (eventsData) {
        this.locationEvents = JSON.parse(eventsData).map((event: any) => ({
          ...event,
          timestamp: new Date(event.timestamp),
        }));
      }
    } catch (error) {
      console.error('Error loading location events:', error);
    }
  }

  private async saveLocationEvents(): Promise<void> {
    try {
      await AsyncStorage.setItem('locationEvents', JSON.stringify(this.locationEvents));
    } catch (error) {
      console.error('Error saving location events:', error);
    }
  }

  async clearLocationData(): Promise<void> {
    this.locationEvents = [];
    await AsyncStorage.removeItem('locationEvents');
  }

  async setGPSMode(mode: GPSMode): Promise<void> {
    this.gpsMode = mode;
    await this.saveGPSMode();
    
    // Restart tracking if currently active
    if (this.isTracking) {
      await this.stopTracking();
      await this.startTracking();
    }
    
    console.log(`GPS mode changed to: ${mode}`);
  }

  getGPSMode(): GPSMode {
    return this.gpsMode;
  }

  getGPSModeConfig() {
    return getGPSModeConfig(this.gpsMode);
  }

  async autoAdjustGPSMode(batteryLevel: number): Promise<void> {
    const recommendedMode = getRecommendedGPSMode(batteryLevel);
    if (recommendedMode !== this.gpsMode) {
      console.log(`Auto-adjusting GPS mode to ${recommendedMode} (battery: ${batteryLevel}%)`);
      await this.setGPSMode(recommendedMode);
    }
  }

  private async loadGPSMode(): Promise<void> {
    try {
      const savedMode = await AsyncStorage.getItem('gpsMode');
      if (savedMode) {
        this.gpsMode = savedMode as GPSMode;
      }
    } catch (error) {
      console.error('Error loading GPS mode:', error);
    }
  }

  private async saveGPSMode(): Promise<void> {
    try {
      await AsyncStorage.setItem('gpsMode', this.gpsMode);
    } catch (error) {
      console.error('Error saving GPS mode:', error);
    }
  }
}

export const locationService = new LocationService();

// Define geofence task handler
TaskManager.defineTask(GEOFENCE_TASK_NAME, async ({ data, error }) => {
  if (error) {
    console.error('Geofence task error:', error);
    return;
  }
  if (data) {
    const { eventType, region } = data as any;
    if (eventType === Location.GeofencingEventType.Enter) {
      await locationService.handleZoneEntryById(region.identifier);
    } else if (eventType === Location.GeofencingEventType.Exit) {
      await locationService.handleZoneExitById(region.identifier);
    }
  }
});

// Define background location task handler
TaskManager.defineTask(LOCATION_TASK_NAME, async ({ data, error }) => {
  if (error) {
    console.error('Background location task error:', error);
    return;
  }
  if (data) {
    const { locations } = data as any;
    if (locations && locations.length > 0) {
      const location = locations[0];
      await locationService['handleLocationUpdate'](location);
    }
  }
}); 