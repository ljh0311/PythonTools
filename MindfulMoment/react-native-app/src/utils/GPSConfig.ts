import * as Location from 'expo-location';

export type GPSMode = 'battery_saver' | 'balanced' | 'high_accuracy' | 'navigation';

export interface GPSModeConfig {
  accuracy: Location.Accuracy;
  timeInterval: number;
  distanceInterval: number;
  batteryImpact: 'low' | 'medium' | 'high';
  expectedAccuracy: string;
  description: string;
}

export const GPS_MODE_CONFIGS: Record<GPSMode, GPSModeConfig> = {
  battery_saver: {
    accuracy: Location.Accuracy.Low,
    timeInterval: 30000, // 30 seconds
    distanceInterval: 100, // 100 meters
    batteryImpact: 'low',
    expectedAccuracy: '~100m',
    description: 'Uses WiFi and cell towers. Minimal battery usage.',
  },
  balanced: {
    accuracy: Location.Accuracy.Balanced,
    timeInterval: 10000, // 10 seconds
    distanceInterval: 50, // 50 meters
    batteryImpact: 'medium',
    expectedAccuracy: '~50m',
    description: 'Balanced GPS and network usage. Moderate battery drain.',
  },
  high_accuracy: {
    accuracy: Location.Accuracy.High,
    timeInterval: 5000, // 5 seconds
    distanceInterval: 10, // 10 meters
    batteryImpact: 'high',
    expectedAccuracy: '~10m',
    description: 'Prioritizes GPS. Higher battery usage.',
  },
  navigation: {
    accuracy: Location.Accuracy.BestForNavigation,
    timeInterval: 2000, // 2 seconds
    distanceInterval: 5, // 5 meters
    batteryImpact: 'high',
    expectedAccuracy: '~5m',
    description: 'Maximum GPS accuracy with multi-satellite support. Highest battery drain.',
  },
};

export const getGPSModeConfig = (mode: GPSMode): GPSModeConfig => {
  return GPS_MODE_CONFIGS[mode];
};

export const getRecommendedGPSMode = (batteryLevel: number): GPSMode => {
  if (batteryLevel < 20) return 'battery_saver';
  if (batteryLevel < 50) return 'balanced';
  return 'high_accuracy';
};
