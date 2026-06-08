import { Injectable } from '@angular/core';
import { Observable, BehaviorSubject, Subscription } from 'rxjs';
import { filter } from 'rxjs/operators';
import { LocationService, LocationData } from './location.service';

export interface NoiseLevelData {
  level: number; // 1-10 scale
  amplitude: number; // Raw amplitude
  timestamp: number;
}

export interface StepData {
  steps: number;
  distance: number; // in meters
  timestamp: number;
}

export interface DeviceMetrics {
  noiseLevel?: NoiseLevelData;
  steps?: StepData;
  location?: LocationData;
}

@Injectable({
  providedIn: 'root'
})
export class DeviceMetricsService {
  // Noise meter state
  private noiseMeterStream: MediaStream | null = null;
  private noiseMeterAudioContext: AudioContext | null = null;
  private noiseMeterAnalyser: AnalyserNode | null = null;
  private noiseMeterInterval: any = null;
  private noiseLevelSubject = new BehaviorSubject<NoiseLevelData | null>(null);
  public noiseLevel$ = this.noiseLevelSubject.asObservable();

  // Step counter state (placeholder for device sensor integration)
  private stepCounterInterval: any = null;
  private stepDataSubject = new BehaviorSubject<StepData | null>(null);
  public stepData$ = this.stepDataSubject.asObservable();
  private accumulatedSteps = 0;
  private accumulatedDistance = 0;

  // Combined metrics observable
  private metricsSubject = new BehaviorSubject<DeviceMetrics>({});
  public metrics$ = this.metricsSubject.asObservable();

  /** Subscribes to `LocationService.startTracking()` so `watchPosition` actually runs (Observable is lazy). */
  private locationWatchSub: Subscription | null = null;

  constructor(private locationService: LocationService) {
    // Combine all device metrics into a single observable
    this.setupMetricsCombination();
  }

  /**
   * Setup combined metrics observable
   */
  private setupMetricsCombination(): void {
    // Combine noise level, steps, and location into single metrics object
    this.noiseLevel$.subscribe(noise => {
      const current = this.metricsSubject.value;
      this.metricsSubject.next({ ...current, noiseLevel: noise || undefined });
    });

    this.stepData$.subscribe(steps => {
      const current = this.metricsSubject.value;
      this.metricsSubject.next({ ...current, steps: steps || undefined });
    });

    this.locationService.currentLocation$.subscribe(location => {
      const current = this.metricsSubject.value;
      this.metricsSubject.next({ ...current, location: location || undefined });
    });
  }

  /**
   * Start noise level tracking using device microphone
   * @param intervalMs Sampling interval in milliseconds (default: 5000)
   * @returns Observable that emits noise level updates
   */
  startNoiseTracking(intervalMs: number = 5000): Observable<NoiseLevelData> {
    if (this.noiseMeterStream) {
      // Already tracking, return existing observable
      return this.noiseLevel$.pipe(
        filter((data: NoiseLevelData | null): data is NoiseLevelData => data !== null)
      );
    }

    // Request microphone permission and start audio meter
    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(stream => {
        this.noiseMeterStream = stream;
        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
        this.noiseMeterAudioContext = audioContext;
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 2048;
        this.noiseMeterAnalyser = analyser;
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);

        // Start polling for noise level
        this.noiseMeterInterval = setInterval(() => {
          const bufferLength = analyser.fftSize;
          const dataArray = new Uint8Array(bufferLength);
          analyser.getByteTimeDomainData(dataArray);

          // Calculate peak-to-peak amplitude as a simple volume metric
          let min = 255, max = 0;
          for (let i = 0; i < bufferLength; i++) {
            if (dataArray[i] < min) min = dataArray[i];
            if (dataArray[i] > max) max = dataArray[i];
          }

          const amplitude = max - min;

          // Map amplitude (about 2-60 ambient; 80+ for talking/noise) to 1-10
          let mappedNoise = 1;
          if (amplitude > 80) mappedNoise = 10;
          else if (amplitude > 60) mappedNoise = 8;
          else if (amplitude > 45) mappedNoise = 6;
          else if (amplitude > 35) mappedNoise = 5;
          else if (amplitude > 20) mappedNoise = 4;
          else if (amplitude > 12) mappedNoise = 3;
          else if (amplitude > 6) mappedNoise = 2;

          // Smooth out transitions
          const currentNoise = this.noiseLevelSubject.value;
          const smoothedNoise = currentNoise
            ? Math.round((currentNoise.level * 2 + mappedNoise) / 3)
            : mappedNoise;

          const noiseData: NoiseLevelData = {
            level: smoothedNoise,
            amplitude,
            timestamp: Date.now()
          };

          this.noiseLevelSubject.next(noiseData);
        }, intervalMs);
      })
      .catch(err => {
        console.error('Error accessing microphone:', err);
        // Fallback to simulated noise level
        const fallbackNoise: NoiseLevelData = {
          level: Math.floor(Math.random() * 4) + 2,
          amplitude: 0,
          timestamp: Date.now()
        };
        this.noiseLevelSubject.next(fallbackNoise);
      });

    return this.noiseLevel$.pipe(
      filter((data: NoiseLevelData | null): data is NoiseLevelData => data !== null)
    );
  }

  /**
   * Stop noise level tracking
   */
  stopNoiseTracking(): void {
    if (this.noiseMeterInterval) {
      clearInterval(this.noiseMeterInterval);
      this.noiseMeterInterval = null;
    }

    if (this.noiseMeterStream) {
      this.noiseMeterStream.getTracks().forEach(track => track.stop());
      this.noiseMeterStream = null;
    }

    if (this.noiseMeterAudioContext) {
      this.noiseMeterAudioContext.close().catch(() => {
        // Ignore errors when closing audio context
      });
      this.noiseMeterAudioContext = null;
    }

    this.noiseMeterAnalyser = null;
    this.noiseLevelSubject.next(null);
  }

  /**
   * Start step counting using device accelerometer (DeviceMotionEvent) when available.
   * Falls back to simulated steps when accelerometer is unavailable or permission denied.
   * @param intervalMs Update interval for emitting step data in ms (default: 600)
   * @returns Observable that emits step data updates
   */
  startStepTracking(intervalMs: number = 600): Observable<StepData> {
    if (this.stepCounterInterval || this.stepEmitInterval) {
      return this.stepData$.pipe(
        filter((data: StepData | null): data is StepData => data !== null)
      );
    }

    this.accumulatedSteps = 0;
    this.accumulatedDistance = 0;

    const tryAccelerometer = (): void => {
      if (typeof window === 'undefined' || !window.DeviceMotionEvent) {
        this.startStepTrackingSimulated(intervalMs);
        return;
      }
      const dm = window.DeviceMotionEvent as unknown as { requestPermission?: () => Promise<string> };
      if (typeof dm.requestPermission === 'function') {
        dm.requestPermission()
          .then((permission) => {
            if (permission === 'granted') {
              this.startStepTrackingAccelerometer(intervalMs);
            } else {
              this.startStepTrackingSimulated(intervalMs);
            }
          })
          .catch(() => this.startStepTrackingSimulated(intervalMs));
      } else {
        this.startStepTrackingAccelerometer(intervalMs);
      }
    };

    tryAccelerometer();
    return this.stepData$.pipe(
      filter((data: StepData | null): data is StepData => data !== null)
    );
  }

  private stepEmitInterval: number | null = null;
  private lastStepEmit = 0;
  private motionHandler: ((event: DeviceMotionEvent) => void) | null = null;

  /**
   * Step detection from accelerometer: low-pass filter + peak detection.
   * Uses accelerationIncludingGravity magnitude; a step is counted when
   * filtered magnitude crosses above then below threshold with cooldown.
   */
  private startStepTrackingAccelerometer(intervalMs: number): void {
    const STEP_COOLDOWN_MS = 380;
    const MAG_THRESHOLD_LOW = 9.2;
    const MAG_THRESHOLD_HIGH = 10.2;
    const LOW_PASS_ALPHA = 0.2;
    const METERS_PER_STEP = 0.72;

    let smoothed = 9.8;
    let lastStepTime = 0;
    let phase: 'low' | 'high' = 'low';

    const onMotion = (event: DeviceMotionEvent): void => {
      const a = event.accelerationIncludingGravity;
      if (a == null || [a.x, a.y, a.z].some(v => v == null)) return;
      const mag = Math.sqrt(a.x! * a.x! + a.y! * a.y! + a.z! * a.z!);
      smoothed = LOW_PASS_ALPHA * smoothed + (1 - LOW_PASS_ALPHA) * mag;
      const now = Date.now();

      if (phase === 'low' && smoothed > MAG_THRESHOLD_HIGH) {
        phase = 'high';
      } else if (phase === 'high' && smoothed < MAG_THRESHOLD_LOW && (now - lastStepTime) >= STEP_COOLDOWN_MS) {
        phase = 'low';
        lastStepTime = now;
        this.accumulatedSteps++;
        this.accumulatedDistance = Math.floor(this.accumulatedSteps * METERS_PER_STEP);
      }
    };

    this.motionHandler = onMotion;
    window.addEventListener('devicemotion', onMotion);

    this.stepEmitInterval = window.setInterval(() => {
      const now = Date.now();
      if (now - this.lastStepEmit >= intervalMs) {
        this.lastStepEmit = now;
        this.stepDataSubject.next({
          steps: this.accumulatedSteps,
          distance: this.accumulatedDistance,
          timestamp: now
        });
      }
    }, intervalMs);
  }

  /**
   * Fallback when accelerometer is unavailable or permission denied.
   */
  private startStepTrackingSimulated(intervalMs: number): void {
    const stepsPerSec = 1.19;
    const METERS_PER_STEP = 0.7;

    this.stepCounterInterval = setInterval(() => {
      const baseSteps = stepsPerSec * (intervalMs / 1000);
      const variation = baseSteps * (Math.random() * 0.2 - 0.1);
      const steps = Math.max(0, Math.round(baseSteps + variation));
      this.accumulatedSteps += steps;
      this.accumulatedDistance = Math.floor(this.accumulatedSteps * METERS_PER_STEP);
      this.stepDataSubject.next({
        steps: this.accumulatedSteps,
        distance: this.accumulatedDistance,
        timestamp: Date.now()
      });
    }, intervalMs);
  }

  /**
   * Stop step tracking (accelerometer or simulated)
   */
  stopStepTracking(): void {
    if (this.stepCounterInterval) {
      clearInterval(this.stepCounterInterval);
      this.stepCounterInterval = null;
    }
    if (this.stepEmitInterval) {
      clearInterval(this.stepEmitInterval);
      this.stepEmitInterval = null;
    }
    if (this.motionHandler) {
      window.removeEventListener('devicemotion', this.motionHandler);
      this.motionHandler = null;
    }

    this.accumulatedSteps = 0;
    this.accumulatedDistance = 0;
    this.stepDataSubject.next(null);
  }

  private beginLocationWatch(): void {
    this.endLocationWatch();
    this.locationWatchSub = this.locationService.startTracking().subscribe({
      error: (err) => console.warn('[DeviceMetrics] Geolocation watch error:', err)
    });
  }

  private endLocationWatch(): void {
    if (this.locationWatchSub) {
      this.locationWatchSub.unsubscribe();
      this.locationWatchSub = null;
    }
    this.locationService.stopTracking();
  }

  /**
   * Get current location (one-time)
   */
  getCurrentLocation(): Observable<LocationData> {
    return this.locationService.getCurrentLocation();
  }

  /**
   * Start all device metrics tracking for a session type
   * @param sessionType Type of session (e.g., 'meditation', 'walking')
   */
  startSessionMetrics(sessionType: string): Observable<DeviceMetrics> {
    // All session types now have noise level tracking
    this.startNoiseTracking(5000);

    // Additional device tracking based on session type
    switch (sessionType) {
      case 'walking':
      case 'travel-safety':
        this.startStepTracking(600);
        this.beginLocationWatch();
        break;
      case 'study':
        // Only noise tracking
        break;
    }

    return this.metrics$;
  }

  /**
   * Stop all device metrics tracking
   */
  stopAllMetrics(): void {
    this.stopNoiseTracking();
    this.stopStepTracking();
    this.endLocationWatch();
  }

  /**
   * Get current metrics snapshot
   */
  getCurrentMetrics(): DeviceMetrics {
    return this.metricsSubject.value;
  }

  /**
   * Check if noise tracking is active
   */
  isNoiseTrackingActive(): boolean {
    return this.noiseMeterStream !== null;
  }

  /**
   * Check if step tracking is active (accelerometer or simulated)
   */
  isStepTrackingActive(): boolean {
    return this.stepCounterInterval !== null || this.stepEmitInterval !== null;
  }
}
