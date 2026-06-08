import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, of, timer } from 'rxjs';
import { catchError, filter, map, switchMap } from 'rxjs/operators';

const NOMINATIM_URL = 'https://nominatim.openstreetmap.org/reverse';
const NOMINATIM_USER_AGENT = 'MindfulMoment/1.0 (https://github.com/mindfulmoment)';
const NOMINATIM_THROTTLE_MS = 1100; // Slightly over 1s to respect usage policy

export interface LocationData {
  latitude: number;
  longitude: number;
  accuracy?: number;
  altitude?: number;
  heading?: number;
  speed?: number;
  timestamp: number;
}

export interface LocationInfo {
  type: 'home' | 'public' | 'work' | 'transport' | 'outdoor';
  name: string;
  address?: string;
  city?: string;
  country?: string;
  environment: 'quiet' | 'noisy' | 'crowded' | 'natural' | 'urban';
  coordinates?: {
    latitude: number;
    longitude: number;
  };
}

export type GPSStatus = 'searching' | 'locked' | 'unavailable' | 'denied';

@Injectable({
  providedIn: 'root'
})
export class LocationService {
  private currentLocationSubject = new BehaviorSubject<LocationData | null>(null);
  public currentLocation$ = this.currentLocationSubject.asObservable();

  private gpsStatusSubject = new BehaviorSubject<GPSStatus>('searching');
  public gpsStatus$ = this.gpsStatusSubject.asObservable();

  private watchId: number | null = null;
  private isTracking = false;
  private lastNominatimCall = 0;

  constructor(private http: HttpClient) {}

  /**
   * Get current location (one-time)
   */
  getCurrentLocation(): Observable<LocationData> {
    return new Observable(observer => {
      if (!navigator.geolocation) {
        observer.error('Geolocation not supported');
        return;
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          const location: LocationData = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            altitude: position.coords.altitude || undefined,
            heading: position.coords.heading || undefined,
            speed: position.coords.speed || undefined,
            timestamp: position.timestamp
          };
          
          // Check if accuracy is acceptable
          if (position.coords.accuracy && position.coords.accuracy > 100) {
            console.warn(`Low GPS accuracy: ${position.coords.accuracy}m`);
          }
          
          this.currentLocationSubject.next(location);
          this.gpsStatusSubject.next('locked');
          observer.next(location);
          observer.complete();
        },
        (error) => {
          console.error('Error getting location:', error);
          this.gpsStatusSubject.next(error.code === 1 ? 'denied' : 'unavailable');
          observer.error(this.getLocationErrorMessage(error));
        },
        {
          enableHighAccuracy: true,  // Force GPS usage
          timeout: 15000,            // Increased timeout for GPS lock (was 10000)
          maximumAge: 0              // Never use cached location (was 60000)
        }
      );
    });
  }

  /**
   * Start continuous location tracking
   */
  startTracking(): Observable<LocationData> {
    if (this.isTracking) {
      return this.currentLocation$.pipe(
        filter((location): location is LocationData => location !== null),
        map(location => location as LocationData)
      );
    }

    return new Observable(observer => {
      if (!navigator.geolocation) {
        observer.error('Geolocation not supported');
        return;
      }

      this.isTracking = true;
      this.watchId = navigator.geolocation.watchPosition(
        (position) => {
          const location: LocationData = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            altitude: position.coords.altitude || undefined,
            heading: position.coords.heading || undefined,
            speed: position.coords.speed || undefined,
            timestamp: position.timestamp
          };
          
          // Warn if accuracy is poor
          if (position.coords.accuracy && position.coords.accuracy > 100) {
            console.warn(`Low GPS accuracy: ${position.coords.accuracy}m`);
          }
          
          this.currentLocationSubject.next(location);
          this.gpsStatusSubject.next('locked');
          observer.next(location);
        },
        (error) => {
          console.error('Error tracking location:', error);
          this.gpsStatusSubject.next(error.code === 1 ? 'denied' : 'unavailable');
          observer.error(this.getLocationErrorMessage(error));
        },
        {
          enableHighAccuracy: true,  // Force GPS usage
          timeout: 15000,            // Increased timeout for GPS lock
          maximumAge: 0              // Never use cached location
        }
      );
    });
  }

  /**
   * Stop location tracking
   */
  stopTracking(): void {
    if (this.watchId !== null) {
      navigator.geolocation.clearWatch(this.watchId);
      this.watchId = null;
      this.isTracking = false;
    }
  }

  /**
   * Get location info (type, name, environment) from coordinates
   */
  getLocationInfo(location: LocationData): Observable<LocationInfo> {
    // In a real app, you would reverse geocode using a service like Google Maps Geocoding API
    // For now, we'll use a simple heuristic-based approach
    
    return new Observable(observer => {
      // Try to reverse geocode (simplified - in production use a proper API)
      this.reverseGeocode(location.latitude, location.longitude).subscribe({
        next: (address) => {
          const info = this.determineLocationType(location, address);
          observer.next(info);
          observer.complete();
        },
        error: () => {
          // Fallback to heuristic
          const info = this.determineLocationType(location);
          observer.next(info);
          observer.complete();
        }
      });
    });
  }

  /**
   * Reverse geocode coordinates to address using OpenStreetMap Nominatim (free, no key).
   * Throttled to 1 request per second per Nominatim usage policy. Falls back to heuristic on error.
   */
  private reverseGeocode(lat: number, lng: number): Observable<string> {
    const now = Date.now();
    const elapsed = now - this.lastNominatimCall;
    const delayMs = elapsed < NOMINATIM_THROTTLE_MS ? NOMINATIM_THROTTLE_MS - elapsed : 0;

    const doRequest = () => {
      this.lastNominatimCall = Date.now();
      const params = { lat: lat.toString(), lon: lng.toString(), format: 'json' };
      const headers = { 'User-Agent': NOMINATIM_USER_AGENT };
      return this.http
        .get<{ display_name?: string; address?: Record<string, string> }>(NOMINATIM_URL, {
          params,
          headers
        })
        .pipe(
          map((res) => this.formatNominatimAddress(res)),
          catchError(() => of(this.getLocationNameFromCoordinates(lat, lng)))
        );
    };

    if (delayMs > 0) {
      return timer(delayMs).pipe(switchMap(doRequest));
    }
    return doRequest();
  }

  private formatNominatimAddress(res: { display_name?: string; address?: Record<string, string> }): string {
    if (res.display_name && res.display_name.trim()) {
      return res.display_name.trim();
    }
    const addr = res.address;
    if (addr) {
      const parts = [
        addr['road'],
        addr['suburb'] || addr['neighbourhood'],
        addr['city'] || addr['town'] || addr['village'],
        addr['state'],
        addr['country']
      ].filter(Boolean);
      if (parts.length > 0) return parts.join(', ');
    }
    return '';
  }

  /**
   * Get a user-friendly location name from coordinates
   * This is a simplified version - in production use proper geocoding
   */
  private getLocationNameFromCoordinates(lat: number, lng: number): string {
    // Singapore coordinates roughly: 1.3521, 103.8198
    // Check if in Singapore
    if (lat >= 1.15 && lat <= 1.5 && lng >= 103.6 && lng <= 104.0) {
      // Check for known Singapore areas (simplified)
      if (lat >= 1.28 && lat <= 1.35 && lng >= 103.8 && lng <= 103.9) {
        return 'Central Singapore';
      } else if (lat >= 1.35 && lat <= 1.45) {
        return 'Northern Singapore';
      } else if (lat >= 1.25 && lat <= 1.35 && lng >= 103.9) {
        return 'Eastern Singapore';
      } else if (lat >= 1.25 && lat <= 1.35 && lng <= 103.8) {
        return 'Western Singapore';
      } else {
        return 'Singapore';
      }
    }
    
    // Default to generic location name
    return 'Current Location';
  }

  /**
   * Determine location type and environment from coordinates and context
   */
  private determineLocationType(location: LocationData, address?: string): LocationInfo {
    // Check if moving (transport)
    if (location.speed && location.speed > 5) {
      return {
        type: 'transport',
        name: 'In Transit',
        environment: 'noisy',
        coordinates: {
          latitude: location.latitude,
          longitude: location.longitude
        }
      };
    }

    // Check time of day and other factors for home/work
    const hour = new Date().getHours();
    const dayOfWeek = new Date().getDay();
    
    // Check if likely at home (evening/night, weekends, or very early morning)
    if ((hour >= 20 || hour <= 6) || (dayOfWeek === 0 || dayOfWeek === 6)) {
      return {
        type: 'home',
        name: address || 'Home',
        environment: 'quiet',
        coordinates: {
          latitude: location.latitude,
          longitude: location.longitude
        }
      };
    }

    // Check if likely at work (9-5 on weekdays)
    if (hour >= 9 && hour <= 17 && dayOfWeek >= 1 && dayOfWeek <= 5) {
      return {
        type: 'work',
        name: address || 'Work',
        environment: 'quiet',
        coordinates: {
          latitude: location.latitude,
          longitude: location.longitude
        }
      };
    }

    // Check if morning commute time
    if (hour >= 6 && hour <= 9) {
      return {
        type: 'transport',
        name: address || 'Commute',
        environment: 'crowded',
        coordinates: {
          latitude: location.latitude,
          longitude: location.longitude
        }
      };
    }

    // Default to public space
    return {
      type: 'public',
      name: address || 'Public Space',
      environment: 'crowded',
      coordinates: {
        latitude: location.latitude,
        longitude: location.longitude
      }
    };
  }

  /**
   * Check if location tracking is enabled in user settings
   */
  isLocationEnabled(): boolean {
    try {
      const userRaw = localStorage.getItem('currentUser');
      if (userRaw) {
        const user = JSON.parse(userRaw) as { preferences?: { location?: boolean } };
        if (user?.preferences && typeof user.preferences.location === 'boolean') {
          return user.preferences.location;
        }
      }
    } catch {
      // ignore
    }
    const settings = localStorage.getItem('mindfulMoment_userPreferences');
    if (settings) {
      try {
        const prefs = JSON.parse(settings);
        return prefs.location !== false;
      } catch {
        return true;
      }
    }
    return true;
  }

  /**
   * Calculate distance between two coordinates (Haversine formula)
   */
  calculateDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
    const R = 6371e3; // Earth's radius in meters
    const φ1 = lat1 * Math.PI / 180;
    const φ2 = lat2 * Math.PI / 180;
    const Δφ = (lat2 - lat1) * Math.PI / 180;
    const Δλ = (lon2 - lon1) * Math.PI / 180;

    const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
              Math.cos(φ1) * Math.cos(φ2) *
              Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return R * c; // Distance in meters
  }

  /**
   * Get user-friendly error message for location errors
   */
  private getLocationErrorMessage(error: GeolocationPositionError): string {
    switch (error.code) {
      case error.PERMISSION_DENIED:
        return 'Location permission denied. Please enable location services in your browser settings.';
      case error.POSITION_UNAVAILABLE:
        return 'Location unavailable. Please ensure GPS is enabled and you have a clear view of the sky.';
      case error.TIMEOUT:
        return 'Location request timed out. Please check your GPS signal and try again.';
      default:
        return 'An unknown error occurred while getting location.';
    }
  }

  /**
   * Get signal quality based on accuracy
   */
  getSignalQuality(accuracy?: number): 'excellent' | 'good' | 'fair' | 'poor' | 'none' {
    if (!accuracy) return 'none';
    if (accuracy <= 5) return 'excellent';
    if (accuracy <= 15) return 'good';
    if (accuracy <= 50) return 'fair';
    if (accuracy <= 200) return 'poor';
    return 'none';
  }
}

