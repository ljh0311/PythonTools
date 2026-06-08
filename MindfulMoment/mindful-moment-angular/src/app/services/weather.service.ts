import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, of, timer } from 'rxjs';
import { catchError, filter, map, switchMap, timeout } from 'rxjs/operators';

const NOMINATIM_URL = 'https://nominatim.openstreetmap.org/reverse';
const NOMINATIM_USER_AGENT =
  'MindfulMoment/1.0 (https://github.com/mindfulmoment)';
const NOMINATIM_THROTTLE_MS = 1100; // Slightly over 1s to respect usage policy

export interface WeatherData {
  temperature: number;
  humidity: number;
  windSpeed: number;
  weatherCondition: string;
  visibility: number;
  pressure: number;
  cloudCover: number;
  uvIndex: number;
  sunriseTime: string;
  sunsetTime: string;
  moonPhase: string;
}

export interface WeatherInfo {
  temperature: number;
  humidity: number;
  windSpeed: number;
  weatherCondition: string;
  visibility: number;
  pressure: number;
  cloudCover: number;
  uvIndex: number;
  sunriseTime: string;
  sunsetTime: string;
  moonPhase: string;
}

export type WeatherStatus = 'loading' | 'loaded' | 'error';

@Injectable({
  providedIn: 'root',
})
export class WeatherService {
  private weatherSubject = new BehaviorSubject<WeatherData | null>(null);
  public weather$ = this.weatherSubject.asObservable();

  constructor(private http: HttpClient) {}

  /**
   * Get current weather
   */
  getCurrentWeather(): Observable<WeatherData> {
    return new Observable((observer) => {
      if (!navigator.geolocation) {
        observer.error('Geolocation not supported');
        return;
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;

          // TODO: Replace this static object with a proper weather API call based on (latitude, longitude)
          // Example: Call your backend endpoint or an external service (OpenWeatherMap, etc) here

          // Example, static data for now:
          const weather: WeatherData = {
            temperature: 20,
            humidity: 50,
            windSpeed: 10,
            weatherCondition: 'sunny',
            visibility: 10,
            pressure: 1013,
            cloudCover: 50,
            uvIndex: 5,
            sunriseTime: '06:00',
            sunsetTime: '18:00',
            moonPhase: 'full',
          };

          // Optionally handle position accuracy/warnings
          if (position.coords.accuracy && position.coords.accuracy > 100) {
            console.warn(`Low GPS accuracy: ${position.coords.accuracy}m`);
          }

          observer.next(weather);
          observer.complete();
        },
        (error) => {
          console.error('Error getting location:', error);
          // TODO: Use a more robust error handling and user-friendly messaging here if needed
          observer.error(
            error.message || 'Unable to retrieve location for weather',
          );
        },
        {
          enableHighAccuracy: true,
          timeout: 15000,
          maximumAge: 0,
        },
      );
    });
  }

  /**
   * Start continuous location tracking
   */
  /**
   * Starts continuous weather tracking based on live geolocation.
   * Emits the latest WeatherData when location changes significantly.
   * Falls back to last known or static weather if geolocation not available.
   *
   * TODO: Replace static example and implement actual weather API integration
   * (fetch weather data for current coords each time location updates)
   */
  startTracking(): Observable<WeatherData> {
    return new Observable<WeatherData>((observer) => {
      if (!navigator.geolocation) {
        observer.error('Geolocation not supported');
        return;
      }

      let watchId: number;

      const handleSuccess = (position: GeolocationPosition) => {
        const { latitude, longitude } = position.coords;
        // TODO: Call weather API/backend with lat/lng and emit the result
        // Example: Replace static below with actual request + handle errors
        const weather: WeatherData = {
          temperature: 20,
          humidity: 50,
          windSpeed: 10,
          weatherCondition: 'sunny',
          visibility: 10,
          pressure: 1013,
          cloudCover: 50,
          uvIndex: 5,
          sunriseTime: '06:00',
          sunsetTime: '18:00',
          moonPhase: 'full',
        };

        observer.next(weather);
        // Do not complete; continuous tracking
      };

      const handleError = (error: GeolocationPositionError) => {
        observer.error(error.message || 'Unable to get location');
      };

      watchId = navigator.geolocation.watchPosition(
        handleSuccess,
        handleError,
        {
          enableHighAccuracy: true,
          timeout: 20000,
          maximumAge: 0,
        },
      );

      // Clean up on unsubscribe
      return () => {
        if (watchId !== undefined) {
          navigator.geolocation.clearWatch(watchId);
        }
      };
    });
  }

  /**
   * Given a Nominatim API reverse geocode result, return a formatted address string.
   * Used for getting descriptive weather-related location names.
   */
  private formatNominatimAddress(res: {
    display_name?: string;
    address?: Record<string, string>;
  }): string {
    if (res.display_name && res.display_name.trim()) {
      return res.display_name.trim();
    }
    const address = res.address;
    if (address) {
      const parts = [
        address['road'],
        address['suburb'] || address['neighbourhood'],
        address['city'] || address['town'] || address['village'],
        address['state'],
        address['country'],
      ].filter(Boolean);
      if (parts.length > 0) {
        return parts.join(', ');
      }
    }
    return '';
  }

  /**
   * Get signal quality based on accuracy
   */
  getSignalQuality(
    accuracy?: number,
  ): 'excellent' | 'good' | 'fair' | 'poor' | 'none' {
    if (!accuracy) return 'none';
    if (accuracy <= 5) return 'excellent';
    if (accuracy <= 15) return 'good';
    if (accuracy <= 50) return 'fair';
    if (accuracy <= 200) return 'poor';
    return 'none';
  }
}
