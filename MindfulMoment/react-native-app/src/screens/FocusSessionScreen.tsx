import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Alert,
  Animated,
  Switch,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../context/ThemeContext';
import { useApp } from '../context/AppContext';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { focusSessionService } from '../utils/FocusSessionService';
import { locationService } from '../utils/LocationService';
import { GPSStatusIndicator } from '../components/GPSStatusIndicator';

const sessionDurations = [
  { label: 'Quick Break', value: 5, icon: 'time-outline' },
  { label: 'Short Focus', value: 15, icon: 'timer-outline' },
  { label: 'Deep Work', value: 30, icon: 'hourglass-outline' },
  { label: 'Extended', value: 60, icon: 'stopwatch-outline' },
];

const sessionCategories = [
  { label: 'commute', icon: 'train-outline', color: '#4A90E2', description: 'MRT and public transport' },
  { label: 'social', icon: 'people-outline', color: '#28A745', description: 'Public spaces and gatherings' },
  { label: 'work', icon: 'briefcase-outline', color: '#7B68EE', description: 'Work and productivity' },
  { label: 'exercise', icon: 'fitness-outline', color: '#FF6B6B', description: 'Outdoor activities' },
  { label: 'custom', icon: 'settings-outline', color: '#FFC107', description: 'Custom focus time' },
];

export default function FocusSessionScreen() {
  const { theme } = useTheme();
  const { currentFocusSession, startFocusSession, endFocusSession, addMindfulMinutes, currentZone } = useApp();
  const [selectedDuration, setSelectedDuration] = useState(15);
  const [selectedCategory, setSelectedCategory] = useState('commute');
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [isActive, setIsActive] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [showSetup, setShowSetup] = useState(true);
  const [blockNotifications, setBlockNotifications] = useState(true);
  const [autoStartInPublic, setAutoStartInPublic] = useState(false);
  
  const progressAnimation = useRef(new Animated.Value(0)).current;
  const pulseAnimation = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (currentFocusSession) {
      setTimeRemaining(currentFocusSession.duration * 60);
      setIsActive(true);
      setShowSetup(false);
    }
  }, [currentFocusSession]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (isActive && !isPaused && timeRemaining > 0) {
      interval = setInterval(() => {
        setTimeRemaining(prev => {
          const newTime = prev - 1;
          const progress = 1 - (newTime / (selectedDuration * 60));
          
          Animated.timing(progressAnimation, {
            toValue: progress,
            duration: 1000,
            useNativeDriver: false,
          }).start();
          
          if (newTime <= 0) {
            handleSessionComplete();
            return 0;
          }
          return newTime;
        });
      }, 1000);
    }

    return () => clearInterval(interval);
  }, [isActive, isPaused, timeRemaining]);

  useEffect(() => {
    if (isActive && !isPaused) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnimation, {
            toValue: 1.1,
            duration: 1000,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnimation, {
            toValue: 1,
            duration: 1000,
            useNativeDriver: true,
          }),
        ])
      ).start();
    } else {
      pulseAnimation.setValue(1);
    }
  }, [isActive, isPaused]);

  const handleStartSession = async () => {
    try {
      await startFocusSession(selectedDuration, selectedCategory);
      
      // Update focus session settings
      await focusSessionService.updateSettings({
        autoStartInPublic,
      });
      
      // If in a public zone, suggest contributing to community
      if (currentZone && currentZone.type === 'mrt_station') {
        Alert.alert(
          'Community Contribution',
          'You\'re in a public space! Your mindful minutes will contribute to community challenges.',
          [{ text: 'Great!', style: 'default' }]
        );
      }
    } catch (error) {
      console.error('Error starting focus session:', error);
      Alert.alert('Error', 'Failed to start focus session. Please try again.');
    }
  };

  const handlePauseSession = () => {
    setIsPaused(!isPaused);
  };

  const handleEndSession = () => {
    Alert.alert(
      'End Session',
      'Are you sure you want to end this focus session?',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'End Session', style: 'destructive', onPress: confirmEndSession },
      ]
    );
  };

  const confirmEndSession = () => {
    const completedMinutes = Math.floor((selectedDuration * 60 - timeRemaining) / 60);
    if (completedMinutes > 0) {
      addMindfulMinutes(completedMinutes);
    }
    endFocusSession();
    setIsActive(false);
    setIsPaused(false);
    setTimeRemaining(0);
    setShowSetup(true);
    progressAnimation.setValue(0);
  };

  const handleSessionComplete = () => {
    addMindfulMinutes(selectedDuration);
    endFocusSession();
    setIsActive(false);
    setIsPaused(false);
    setShowSetup(true);
    progressAnimation.setValue(0);
    
    Alert.alert(
      'Session Complete! 🎉',
      `Great job! You've completed ${selectedDuration} minutes of focused time.`,
      [{ text: 'Continue', style: 'default' }]
    );
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const getProgressColor = () => {
    const progress = 1 - (timeRemaining / (selectedDuration * 60));
    if (progress < 0.3) return theme.colors.success;
    if (progress < 0.7) return theme.colors.warning;
    return theme.colors.primary;
  };

  if (showSetup) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <Text style={[styles.title, { color: theme.colors.text }]}>
            Focus Session Setup
          </Text>
          
          {/* Duration Selection */}
          <View style={styles.section}>
            <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
              Choose Duration
            </Text>
            <View style={styles.durationGrid}>
              {sessionDurations.map((duration) => (
                <Card
                  key={duration.value}
                  style={[
                    styles.durationCard,
                    selectedDuration === duration.value && {
                      borderColor: theme.colors.primary,
                      borderWidth: 2,
                    },
                  ]}
                  onPress={() => setSelectedDuration(duration.value)}
                >
                  <Ionicons
                    name={duration.icon as any}
                    size={24}
                    color={selectedDuration === duration.value ? theme.colors.primary : theme.colors.textSecondary}
                  />
                  <Text style={[
                    styles.durationLabel,
                    { color: selectedDuration === duration.value ? theme.colors.primary : theme.colors.text }
                  ]}>
                    {duration.label}
                  </Text>
                  <Text style={[
                    styles.durationValue,
                    { color: selectedDuration === duration.value ? theme.colors.primary : theme.colors.textSecondary }
                  ]}>
                    {duration.value}m
                  </Text>
                </Card>
              ))}
            </View>
          </View>

          {/* Category Selection */}
          <View style={styles.section}>
            <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
              Choose Category
            </Text>
            <View style={styles.categoryGrid}>
              {sessionCategories.map((category) => (
                <Card
                  key={category.label}
                  style={[
                    styles.categoryCard,
                    selectedCategory === category.label && {
                      borderColor: category.color,
                      borderWidth: 2,
                    },
                  ]}
                  onPress={() => setSelectedCategory(category.label)}
                >
                  <Ionicons
                    name={category.icon as any}
                    size={24}
                    color={selectedCategory === category.label ? category.color : theme.colors.textSecondary}
                  />
                  <Text style={[
                    styles.categoryLabel,
                    { color: selectedCategory === category.label ? category.color : theme.colors.text }
                  ]}>
                    {category.label.charAt(0).toUpperCase() + category.label.slice(1)}
                  </Text>
                  <Text style={[
                    styles.categoryDescription,
                    { color: theme.colors.textSecondary }
                  ]}>
                    {category.description}
                  </Text>
                </Card>
              ))}
            </View>
          </View>

          {/* Session Settings */}
          <View style={styles.section}>
            <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
              Session Settings
            </Text>
            
            <Card style={styles.settingsCard}>
              <View style={styles.settingRow}>
                <View style={styles.settingInfo}>
                  <Text style={[styles.settingLabel, { color: theme.colors.text }]}>
                    Block Notifications
                  </Text>
                  <Text style={[styles.settingDescription, { color: theme.colors.textSecondary }]}>
                    Silence non-urgent notifications during session
                  </Text>
                </View>
                <Switch
                  value={blockNotifications}
                  onValueChange={setBlockNotifications}
                  trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                  thumbColor={blockNotifications ? '#FFFFFF' : '#FFFFFF'}
                />
              </View>
              
              <View style={styles.settingRow}>
                <View style={styles.settingInfo}>
                  <Text style={[styles.settingLabel, { color: theme.colors.text }]}>
                    Auto-suggest in Public
                  </Text>
                  <Text style={[styles.settingDescription, { color: theme.colors.textSecondary }]}>
                    Suggest sessions when in public spaces
                  </Text>
                </View>
                <Switch
                  value={autoStartInPublic}
                  onValueChange={setAutoStartInPublic}
                  trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                  thumbColor={autoStartInPublic ? '#FFFFFF' : '#FFFFFF'}
                />
              </View>
            </Card>
          </View>

          {/* Current Location Context with GPS Status */}
          {currentZone ? (
            <View style={styles.section}>
              <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
                Current Location
              </Text>
              <Card style={styles.locationCard}>
                <View style={styles.locationInfo}>
                  <Ionicons name="location" size={20} color={theme.colors.primary} />
                  <Text style={[styles.locationName, { color: theme.colors.text }]}>
                    {currentZone.name}
                  </Text>
                </View>
                <Text style={[styles.locationType, { color: theme.colors.textSecondary }]}>
                  {currentZone.type.replace('_', ' ')} • Safety Level: {currentZone.safetyLevel}
                </Text>
                
                {/* GPS Status Indicator */}
                <View style={styles.gpsStatusContainer}>
                  <GPSStatusIndicator showDetails={false} />
                </View>
              </Card>
            </View>
          ) : (
            <View style={styles.section}>
              <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
                Location Status
              </Text>
              <Card style={styles.locationCard}>
                <GPSStatusIndicator showDetails={true} />
                <Text style={[styles.noLocationText, { color: theme.colors.textSecondary }]}>
                  Waiting for GPS signal...
                </Text>
              </Card>
            </View>
          )}

          {/* Start Button */}
          <Button
            title="Start Focus Session"
            onPress={handleStartSession}
            size="large"
            icon={<Ionicons name="play" size={20} color="#FFFFFF" />}
            style={styles.startButton}
          />
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <View style={styles.sessionContainer}>
        {/* Timer Display */}
        <View style={styles.timerContainer}>
          <Animated.View
            style={[
              styles.progressCircle,
              {
                transform: [{ scale: pulseAnimation }],
              },
            ]}
          >
            <View style={[styles.progressRing, { borderColor: theme.colors.border }]}>
              <Animated.View
                style={[
                  styles.progressFill,
                  {
                    borderColor: getProgressColor(),
                    transform: [{ rotate: progressAnimation.interpolate({
                      inputRange: [0, 1],
                      outputRange: ['0deg', '360deg'],
                    }) }],
                  },
                ]}
              />
            </View>
            <View style={styles.timerTextContainer}>
              <Text style={[styles.timerText, { color: theme.colors.text }]}>
                {formatTime(timeRemaining)}
              </Text>
              <Text style={[styles.timerLabel, { color: theme.colors.textSecondary }]}>
                {selectedCategory} • {selectedDuration}m
              </Text>
            </View>
          </Animated.View>
        </View>

        {/* Session Controls */}
        <View style={styles.controlsContainer}>
          <Button
            title={isPaused ? "Resume" : "Pause"}
            onPress={handlePauseSession}
            variant="outline"
            size="large"
            icon={<Ionicons name={isPaused ? "play" : "pause"} size={20} color={theme.colors.primary} />}
            style={styles.controlButton}
          />
          <Button
            title="End Session"
            onPress={handleEndSession}
            variant="outline"
            size="large"
            icon={<Ionicons name="stop" size={20} color={theme.colors.error} />}
            style={[styles.controlButton, { borderColor: theme.colors.error }]}
          />
        </View>

        {/* Session Tips */}
        <Card style={styles.tipsCard}>
          <Text style={[styles.tipsTitle, { color: theme.colors.text }]}>
            💡 Focus Tips
          </Text>
          <Text style={[styles.tipsText, { color: theme.colors.textSecondary }]}>
            • Put your phone in another room{'\n'}
            • Take deep breaths if you feel distracted{'\n'}
            • Remember why you started this session
          </Text>
        </Card>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 32,
  },
  section: {
    marginBottom: 32,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 16,
  },
  durationGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  durationCard: {
    width: '48%',
    alignItems: 'center',
    marginBottom: 12,
    padding: 16,
  },
  durationLabel: {
    fontSize: 14,
    fontWeight: '600',
    marginTop: 8,
    marginBottom: 4,
  },
  durationValue: {
    fontSize: 12,
  },
  categoryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  categoryCard: {
    width: '48%',
    alignItems: 'center',
    marginBottom: 12,
    padding: 16,
  },
  categoryLabel: {
    fontSize: 14,
    fontWeight: '600',
    marginTop: 8,
    marginBottom: 4,
  },
  categoryDescription: {
    fontSize: 12,
    textAlign: 'center',
  },
  settingsCard: {
    padding: 16,
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  settingInfo: {
    flex: 1,
    marginRight: 16,
  },
  settingLabel: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  settingDescription: {
    fontSize: 14,
    lineHeight: 20,
  },
  locationCard: {
    padding: 16,
  },
  locationInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  locationName: {
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  locationType: {
    fontSize: 14,
    textTransform: 'capitalize',
  },
  gpsStatusContainer: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#E5E5E5',
  },
  noLocationText: {
    fontSize: 14,
    marginTop: 8,
    fontStyle: 'italic',
  },
  startButton: {
    marginTop: 20,
  },
  sessionContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  timerContainer: {
    alignItems: 'center',
    marginBottom: 40,
  },
  progressCircle: {
    width: 300,
    height: 300,
    alignItems: 'center',
    justifyContent: 'center',
  },
  progressRing: {
    position: 'absolute',
    width: 300,
    height: 300,
    borderRadius: 150,
    borderWidth: 8,
  },
  progressFill: {
    position: 'absolute',
    width: 300,
    height: 300,
    borderRadius: 150,
    borderWidth: 8,
    borderTopColor: 'transparent',
    borderRightColor: 'transparent',
    borderBottomColor: 'transparent',
  },
  timerTextContainer: {
    alignItems: 'center',
  },
  timerText: {
    fontSize: 48,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  timerLabel: {
    fontSize: 16,
  },
  controlsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    width: '100%',
    marginBottom: 40,
  },
  controlButton: {
    flex: 1,
    marginHorizontal: 8,
  },
  tipsCard: {
    width: '100%',
  },
  tipsTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
  },
  tipsText: {
    fontSize: 14,
    lineHeight: 20,
  },
}); 