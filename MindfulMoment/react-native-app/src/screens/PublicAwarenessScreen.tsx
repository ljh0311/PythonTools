import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../context/ThemeContext';
import { useApp } from '../context/AppContext';
import { Card } from '../components/Card';
import { locationService } from '../utils/LocationService';
import { GPSStatusIndicator } from '../components/GPSStatusIndicator';

const { width } = Dimensions.get('window');

interface PublicUsageStats {
  isInPublic: boolean;
  publicUsageTime: number;
  safetyAlerts: number;
  socialPrompts: number;
  mindfulScore: number;
}

export default function PublicAwarenessScreen() {
  const { theme } = useTheme();
  const { user } = useApp();
  const [publicStats, setPublicStats] = useState<PublicUsageStats>({
    isInPublic: false,
    publicUsageTime: 0,
    safetyAlerts: 0,
    socialPrompts: 0,
    mindfulScore: 85,
  });

  const [currentZone, setCurrentZone] = useState<any>(null);
  const [gpsEnabled, setGpsEnabled] = useState(false);

  useEffect(() => {
    // Check if GPS is enabled and start tracking
    const checkGPS = async () => {
      const initialized = await locationService.initialize();
      setGpsEnabled(initialized);
      
      if (initialized) {
        await locationService.startTracking();
      }
    };

    checkGPS();

    // Update current zone every 10 seconds
    const interval = setInterval(() => {
      const zone = locationService.getCurrentZone();
      setCurrentZone(zone);
      
      // Update public usage stats based on real zone data
      if (zone && (zone.type === 'public_space' || zone.type === 'mrt_station')) {
        setPublicStats(prev => ({
          ...prev,
          isInPublic: true,
          publicUsageTime: prev.publicUsageTime + 10,
        }));
      }
    }, 10000);

    return () => {
      clearInterval(interval);
      locationService.stopTracking();
    };
  }, []);

  const updatePublicStats = () => {
    // Simulate updating public usage stats
    setPublicStats(prev => ({
      ...prev,
      publicUsageTime: prev.publicUsageTime + 30, // Add 30 seconds
      mindfulScore: Math.max(0, 100 - Math.floor(prev.publicUsageTime / 60) * 2),
    }));
  };

  const startPublicSession = () => {
    setPublicStats(prev => ({ ...prev, isInPublic: true }));
    Alert.alert(
      'Public Session Started',
      'Public environment tracking is now active. You\'ll receive safety alerts and social engagement prompts.',
      [{ text: 'OK' }]
    );
  };

  const resetPublicSession = () => {
    setPublicStats({
      isInPublic: false,
      publicUsageTime: 0,
      safetyAlerts: 0,
      socialPrompts: 0,
      mindfulScore: 85,
    });
    Alert.alert('Session Reset', 'Public session has been reset.');
  };

  const showSafetyGuidelines = () => {
    Alert.alert(
      'Safety Guidelines',
      '• Stay aware of your surroundings\n• Avoid phone use while walking\n• Keep headphone volume low\n• Trust your instincts about safety',
      [{ text: 'Got it' }]
    );
  };

  const showSocialTip = (type: string) => {
    const tips = {
      conversation: {
        title: 'Start a Conversation',
        message: 'Try saying hello to someone nearby, ask for directions, or compliment something you notice.',
      },
      observation: {
        title: 'Observe Your Surroundings',
        message: 'Take in the sights, sounds, and smells around you. Notice the architecture, nature, and people.',
      },
      help: {
        title: 'Offer Help to Others',
        message: 'Look for opportunities to help someone - hold a door, offer directions, or assist with carrying something.',
      },
      gratitude: {
        title: 'Practice Gratitude',
        message: 'Take a moment to appreciate where you are, the people around you, and the simple pleasures of being present.',
      },
    };

    const tip = tips[type as keyof typeof tips];
    if (tip) {
      Alert.alert(tip.title, tip.message, [{ text: 'Thanks' }]);
    }
  };

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    return `${minutes}m`;
  };

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent}>
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={[styles.title, { color: theme.colors.text }]}>
              Public Environment Awareness
            </Text>
            <Text style={[styles.subtitle, { color: theme.colors.textSecondary }]}>
              Stay safe and socially engaged in public spaces
            </Text>
          </View>
          <View style={[styles.avatar, { backgroundColor: theme.colors.primary }]}>
            <Ionicons name="people" size={24} color="#FFFFFF" />
          </View>
        </View>

        {/* GPS Status Indicator */}
        <View style={styles.gpsContainer}>
          <GPSStatusIndicator showDetails={true} />
          {currentZone && (
            <View style={styles.zoneInfo}>
              <Ionicons name="location" size={16} color={theme.colors.primary} />
              <Text style={[styles.zoneText, { color: theme.colors.text }]}>
                {currentZone.name} ({currentZone.type.replace('_', ' ')})
              </Text>
            </View>
          )}
        </View>

        {/* GPS Warning */}
        {!gpsEnabled && (
          <Card style={styles.warningCard}>
            <View style={styles.warningContent}>
              <Ionicons name="warning" size={24} color="#FFC107" />
              <Text style={[styles.warningText, { color: theme.colors.text }]}>
                GPS is disabled. Please enable location services for accurate public space detection.
              </Text>
            </View>
          </Card>
        )}

        {/* Public Usage Dashboard */}
        <Card style={styles.publicUsageCard}>
          <View style={styles.publicUsageHeader}>
            <Text style={[styles.publicUsageTitle, { color: '#FFFFFF' }]}>
              Public Environment Status
            </Text>
            <View style={styles.publicUsageStatus}>
              <Ionicons 
                name={publicStats.isInPublic ? "location" : "home"} 
                size={16} 
                color="#FFFFFF" 
              />
              <Text style={[styles.publicUsageStatusText, { color: '#FFFFFF' }]}>
                {publicStats.isInPublic ? 'In Public Environment' : 'At Home/Private Space'}
              </Text>
            </View>
          </View>

          <View style={styles.publicUsageStats}>
            <View style={styles.publicUsageStat}>
              <Text style={[styles.publicUsageStatValue, { color: '#FFFFFF' }]}>
                {formatTime(publicStats.publicUsageTime)}
              </Text>
              <Text style={[styles.publicUsageStatLabel, { color: '#FFFFFF' }]}>
                Public Usage
              </Text>
            </View>
            <View style={styles.publicUsageStat}>
              <Text style={[styles.publicUsageStatValue, { color: '#FFFFFF' }]}>
                {publicStats.safetyAlerts}
              </Text>
              <Text style={[styles.publicUsageStatLabel, { color: '#FFFFFF' }]}>
                Safety Alerts
              </Text>
            </View>
            <View style={styles.publicUsageStat}>
              <Text style={[styles.publicUsageStatValue, { color: '#FFFFFF' }]}>
                {publicStats.socialPrompts}
              </Text>
              <Text style={[styles.publicUsageStatLabel, { color: '#FFFFFF' }]}>
                Social Prompts
              </Text>
            </View>
            <View style={styles.publicUsageStat}>
              <Text style={[styles.publicUsageStatValue, { color: '#FFFFFF' }]}>
                {publicStats.mindfulScore}%
              </Text>
              <Text style={[styles.publicUsageStatLabel, { color: '#FFFFFF' }]}>
                Mindful Score
              </Text>
            </View>
          </View>

          <View style={styles.publicUsageActions}>
            <TouchableOpacity
              style={[styles.publicUsageBtn, styles.primaryBtn]}
              onPress={startPublicSession}
            >
              <Ionicons name="play" size={16} color="#FFFFFF" />
              <Text style={[styles.publicUsageBtnText, { color: '#FFFFFF' }]}>
                Start Tracking
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.publicUsageBtn, styles.outlineBtn]}
              onPress={resetPublicSession}
            >
              <Ionicons name="refresh" size={16} color="#FFFFFF" />
              <Text style={[styles.publicUsageBtnText, { color: '#FFFFFF' }]}>
                Reset Session
              </Text>
            </TouchableOpacity>
          </View>
        </Card>

        {/* Safety Guidelines */}
        <Card style={styles.card}>
          <View style={styles.cardHeader}>
            <Ionicons name="shield-checkmark" size={24} color={theme.colors.primary} />
            <Text style={[styles.cardTitle, { color: theme.colors.text }]}>
              Safety Guidelines
            </Text>
          </View>
          <View style={styles.guidelinesContainer}>
            <View style={styles.guidelineItem}>
              <Ionicons name="eye" size={20} color={theme.colors.primary} />
              <View style={styles.guidelineContent}>
                <Text style={[styles.guidelineTitle, { color: theme.colors.text }]}>
                  Stay Aware of Surroundings
                </Text>
                <Text style={[styles.guidelineText, { color: theme.colors.textSecondary }]}>
                  Keep your head up and be aware of people, traffic, and potential hazards.
                </Text>
              </View>
            </View>
            <View style={styles.guidelineItem}>
              <Ionicons name="walk" size={20} color={theme.colors.primary} />
              <View style={styles.guidelineContent}>
                <Text style={[styles.guidelineTitle, { color: theme.colors.text }]}>
                  Avoid Phone Use While Walking
                </Text>
                <Text style={[styles.guidelineText, { color: theme.colors.textSecondary }]}>
                  Stop in a safe location if you need to use your phone while on the move.
                </Text>
              </View>
            </View>
            <View style={styles.guidelineItem}>
              <Ionicons name="volume-low" size={20} color={theme.colors.primary} />
              <View style={styles.guidelineContent}>
                <Text style={[styles.guidelineTitle, { color: theme.colors.text }]}>
                  Use Headphones Responsibly
                </Text>
                <Text style={[styles.guidelineText, { color: theme.colors.textSecondary }]}>
                  Keep volume low enough to hear important sounds like traffic.
                </Text>
              </View>
            </View>
          </View>
          <TouchableOpacity style={styles.moreInfoBtn} onPress={showSafetyGuidelines}>
            <Text style={[styles.moreInfoText, { color: theme.colors.primary }]}>
              More Safety Tips
            </Text>
          </TouchableOpacity>
        </Card>

        {/* Social Engagement */}
        <Card style={styles.socialCard}>
          <View style={styles.cardHeader}>
            <Ionicons name="heart" size={24} color="#FF6B6B" />
            <Text style={[styles.cardTitle, { color: theme.colors.text }]}>
              Social Engagement Opportunities
            </Text>
          </View>
          <Text style={[styles.socialMessage, { color: theme.colors.textSecondary }]}>
            Instead of scrolling on your phone, consider these ways to connect:
          </Text>
          <View style={styles.socialSuggestions}>
            <TouchableOpacity
              style={styles.socialSuggestion}
              onPress={() => showSocialTip('conversation')}
            >
              <Ionicons name="chatbubbles" size={24} color="#FF6B6B" />
              <Text style={[styles.socialSuggestionText, { color: theme.colors.text }]}>
                Start a Conversation
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.socialSuggestion}
              onPress={() => showSocialTip('observation')}
            >
              <Ionicons name="eye" size={24} color="#FF6B6B" />
              <Text style={[styles.socialSuggestionText, { color: theme.colors.text }]}>
                Observe Surroundings
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.socialSuggestion}
              onPress={() => showSocialTip('help')}
            >
              <Ionicons name="hand-left" size={24} color="#FF6B6B" />
              <Text style={[styles.socialSuggestionText, { color: theme.colors.text }]}>
                Offer Help
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.socialSuggestion}
              onPress={() => showSocialTip('gratitude')}
            >
              <Ionicons name="happy" size={24} color="#FF6B6B" />
              <Text style={[styles.socialSuggestionText, { color: theme.colors.text }]}>
                Practice Gratitude
              </Text>
            </TouchableOpacity>
          </View>
        </Card>

        {/* Quick Actions */}
        <Card style={styles.card}>
          <View style={styles.cardHeader}>
            <Ionicons name="flash" size={24} color={theme.colors.primary} />
            <Text style={[styles.cardTitle, { color: theme.colors.text }]}>
              Quick Actions
            </Text>
          </View>
          <View style={styles.quickActionsGrid}>
            <TouchableOpacity style={styles.quickActionBtn}>
              <Ionicons name="warning" size={24} color={theme.colors.primary} />
              <Text style={[styles.quickActionText, { color: theme.colors.text }]}>
                Emergency Info
              </Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.quickActionBtn}>
              <Ionicons name="shield" size={24} color={theme.colors.primary} />
              <Text style={[styles.quickActionText, { color: theme.colors.text }]}>
                Safety Tips
              </Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.quickActionBtn}>
              <Ionicons name="handshake" size={24} color={theme.colors.primary} />
              <Text style={[styles.quickActionText, { color: theme.colors.text }]}>
                Social Guidelines
              </Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.quickActionBtn}>
              <Ionicons name="leaf" size={24} color={theme.colors.primary} />
              <Text style={[styles.quickActionText, { color: theme.colors.text }]}>
                Mindfulness
              </Text>
            </TouchableOpacity>
          </View>
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 16,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 24,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 16,
    opacity: 0.7,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
  },
  publicUsageCard: {
    backgroundColor: '#667eea',
    marginBottom: 24,
  },
  publicUsageHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  publicUsageTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  publicUsageStatus: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  publicUsageStatusText: {
    fontSize: 14,
    opacity: 0.9,
  },
  publicUsageStats: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  publicUsageStat: {
    alignItems: 'center',
    flex: 1,
  },
  publicUsageStatValue: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  publicUsageStatLabel: {
    fontSize: 12,
    opacity: 0.8,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  publicUsageActions: {
    flexDirection: 'row',
    gap: 12,
  },
  publicUsageBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    borderRadius: 8,
    gap: 8,
  },
  primaryBtn: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.3)',
  },
  outlineBtn: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.3)',
  },
  publicUsageBtnText: {
    fontSize: 14,
    fontWeight: '500',
  },
  card: {
    marginBottom: 16,
  },
  socialCard: {
    marginBottom: 16,
    backgroundColor: '#fff3cd',
    borderLeftWidth: 4,
    borderLeftColor: '#FFC107',
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  guidelinesContainer: {
    gap: 16,
  },
  guidelineItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  guidelineContent: {
    flex: 1,
  },
  guidelineTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  guidelineText: {
    fontSize: 14,
    lineHeight: 20,
  },
  moreInfoBtn: {
    marginTop: 16,
    paddingVertical: 8,
  },
  moreInfoText: {
    fontSize: 14,
    fontWeight: '500',
    textAlign: 'center',
  },
  socialMessage: {
    fontSize: 16,
    lineHeight: 24,
    marginBottom: 20,
  },
  socialSuggestions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  socialSuggestion: {
    width: (width - 64) / 2 - 6,
    backgroundColor: 'rgba(255, 255, 255, 0.7)',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
    gap: 8,
  },
  socialSuggestionText: {
    fontSize: 14,
    fontWeight: '500',
    textAlign: 'center',
  },
  quickActionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  quickActionBtn: {
    width: (width - 64) / 2 - 6,
    padding: 20,
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
  },
  quickActionText: {
    fontSize: 14,
    fontWeight: '500',
    textAlign: 'center',
  },
  gpsContainer: {
    marginBottom: 16,
    gap: 12,
  },
  zoneInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: '#E3F2FD',
    borderRadius: 8,
  },
  zoneText: {
    fontSize: 14,
    fontWeight: '500',
    flex: 1,
  },
  warningCard: {
    marginBottom: 16,
    backgroundColor: '#FFF3CD',
    borderLeftWidth: 4,
    borderLeftColor: '#FFC107',
  },
  warningContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  warningText: {
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
  },
}); 