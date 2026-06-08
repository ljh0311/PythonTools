import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { locationService, GPSStatus } from '../utils/LocationService';

export interface GPSStatusProps {
  showDetails?: boolean;
  style?: any;
}

export const GPSStatusIndicator: React.FC<GPSStatusProps> = ({ 
  showDetails = false,
  style 
}) => {
  const [gpsStatus, setGpsStatus] = useState<GPSStatus>(locationService.getGPSStatus());

  useEffect(() => {
    // Update GPS status every 5 seconds
    const interval = setInterval(() => {
      setGpsStatus(locationService.getGPSStatus());
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (): string => {
    switch (gpsStatus.signalQuality) {
      case 'excellent': return '#28A745';
      case 'good': return '#5CB85C';
      case 'fair': return '#FFC107';
      case 'poor': return '#FF9800';
      case 'none': return '#DC3545';
      default: return '#6C757D';
    }
  };

  const getStatusIcon = (): keyof typeof Ionicons.glyphMap => {
    switch (gpsStatus.signalQuality) {
      case 'excellent':
      case 'good':
        return 'location';
      case 'fair':
      case 'poor':
        return 'location-outline';
      case 'none':
        return 'location-off';
      default:
        return 'location-outline';
    }
  };

  const getStatusText = () => {
    if (!gpsStatus.isEnabled) return 'GPS Off';
    return `${gpsStatus.signalQuality} (±${Math.round(gpsStatus.accuracy)}m)`;
  };

  if (!showDetails) {
    // Compact view
    return (
      <View style={[styles.compactContainer, style]}>
        <Ionicons 
          name={getStatusIcon()} 
          size={16} 
          color={getStatusColor()} 
        />
        <Text style={[styles.compactText, { color: getStatusColor() }]}>
          GPS: {gpsStatus.signalQuality}
        </Text>
      </View>
    );
  }

  // Detailed view
  return (
    <View style={[styles.detailedContainer, style]}>
      <View style={styles.statusHeader}>
        <Ionicons 
          name={getStatusIcon()} 
          size={20} 
          color={getStatusColor()} 
        />
        <Text style={[styles.statusTitle, { color: getStatusColor() }]}>
          {getStatusText()}
        </Text>
      </View>
      {showDetails && gpsStatus.isEnabled && (
        <View style={styles.statusDetails}>
          <Text style={styles.detailText}>
            Accuracy: ±{Math.round(gpsStatus.accuracy)}m
          </Text>
          <Text style={styles.detailText}>
            Provider: {gpsStatus.provider}
          </Text>
          <Text style={styles.detailText}>
            Updated: {new Date(gpsStatus.lastUpdate).toLocaleTimeString()}
          </Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  compactContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  compactText: {
    fontSize: 12,
    fontWeight: '500',
  },
  detailedContainer: {
    padding: 12,
    backgroundColor: '#F8F9FA',
    borderRadius: 8,
  },
  statusHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statusTitle: {
    fontSize: 14,
    fontWeight: '600',
  },
  statusDetails: {
    marginTop: 8,
    gap: 4,
  },
  detailText: {
    fontSize: 12,
    color: '#6C757D',
  },
});
