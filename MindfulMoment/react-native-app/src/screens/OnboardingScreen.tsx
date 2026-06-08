import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Dimensions,
  Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../context/ThemeContext';
import { useApp } from '../context/AppContext';
import { Button } from '../components/Button';
import { Card } from '../components/Card';

const { width } = Dimensions.get('window');

const onboardingSteps = [
  {
    id: 1,
    title: 'Welcome to MindfulMoment',
    subtitle: 'Your digital wellness companion',
    description: 'Stay present and mindful in public spaces while building healthy phone habits. Reduce smartphone overuse and improve safety.',
    icon: 'leaf-outline',
  },
  {
    id: 2,
    title: 'Privacy-First Design',
    subtitle: 'Your data stays on your device',
    description: 'All raw usage logs and location data stay on-device. Only anonymized summary events are shared if you opt into community features.',
    icon: 'shield-checkmark-outline',
  },
  {
    id: 3,
    title: 'Context-Aware Nudges',
    subtitle: 'Smart reminders for safety',
    description: 'Get gentle nudges when you\'re in public spaces like MRT stations. Safety reminders help you stay alert near busy crossings.',
    icon: 'notifications-outline',
  },
  {
    id: 4,
    title: 'Focus Sessions',
    subtitle: 'Self-regulation tools',
    description: 'Start focus sessions before boarding public transport. Block distracting apps and earn mindful minutes for community challenges.',
    icon: 'timer-outline',
  },
  {
    id: 5,
    title: 'Community & Rewards',
    subtitle: 'Join the mindful movement',
    description: 'Earn points and badges for mindful behavior. Join anonymous group challenges and redeem rewards from local businesses.',
    icon: 'people-outline',
  },
];

export default function OnboardingScreen() {
  const { theme } = useTheme();
  const { setOnboarded, setUser, requestPermissions, continueAsGuest } = useApp();
  const [currentStep, setCurrentStep] = useState(0);
  const [permissionsGranted, setPermissionsGranted] = useState(false);

  const handleNext = () => {
    if (currentStep < onboardingSteps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleComplete();
    }
  };

  const handleSkip = () => {
    setCurrentStep(onboardingSteps.length - 1);
  };

  const handleComplete = async () => {
    try {
      await requestPermissions();
      setPermissionsGranted(true);
      
      // Set default user
      setUser({
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
      });
      
      await setOnboarded(true);
    } catch (error) {
      console.error('Error completing onboarding:', error);
    }
  };

  const currentStepData = onboardingSteps[currentStep];

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Progress Indicator */}
        <View style={styles.progressContainer}>
          {onboardingSteps.map((_, index) => (
            <View
              key={index}
              style={[
                styles.progressDot,
                {
                  backgroundColor: index <= currentStep ? theme.colors.primary : theme.colors.border,
                },
              ]}
            />
          ))}
        </View>

        {/* Skip Button */}
        {currentStep < onboardingSteps.length - 1 && (
          <Button
            title="Skip"
            onPress={handleSkip}
            variant="ghost"
            size="small"
            style={styles.skipButton}
          />
        )}

        {/* Content */}
        <View style={styles.content}>
          {/* Icon */}
          <View style={[styles.iconContainer, { backgroundColor: theme.colors.primary + '20' }]}>
            <Ionicons
              name={currentStepData.icon as any}
              size={48}
              color={theme.colors.primary}
            />
          </View>

          {/* Title */}
          <Text style={[styles.title, { color: theme.colors.text }]}>
            {currentStepData.title}
          </Text>

          {/* Subtitle */}
          <Text style={[styles.subtitle, { color: theme.colors.primary }]}>
            {currentStepData.subtitle}
          </Text>

          {/* Description */}
          <Text style={[styles.description, { color: theme.colors.textSecondary }]}>
            {currentStepData.description}
          </Text>

          {/* Image Placeholder */}
          <View style={[styles.imageContainer, { backgroundColor: theme.colors.surface }]}>
            <Text style={[styles.imagePlaceholder, { color: theme.colors.textSecondary }]}>
              📱 MindfulMoment
            </Text>
          </View>
        </View>

        {/* Permissions Section (Last Step) */}
        {currentStep === onboardingSteps.length - 1 && (
          <Card style={styles.permissionsCard}>
            <Text style={[styles.permissionsTitle, { color: theme.colors.text }]}>
              Permissions We Need
            </Text>
            
            <View style={styles.permissionItem}>
              <Ionicons name="location-outline" size={24} color={theme.colors.primary} />
              <View style={styles.permissionText}>
                <Text style={[styles.permissionLabel, { color: theme.colors.text }]}>
                  Location Access
                </Text>
                <Text style={[styles.permissionDescription, { color: theme.colors.textSecondary }]}>
                  To provide contextual nudges based on your surroundings
                </Text>
              </View>
            </View>

            <View style={styles.permissionItem}>
              <Ionicons name="notifications-outline" size={24} color={theme.colors.primary} />
              <View style={styles.permissionText}>
                <Text style={[styles.permissionLabel, { color: theme.colors.text }]}>
                  Notifications
                </Text>
                <Text style={[styles.permissionDescription, { color: theme.colors.textSecondary }]}>
                  To send gentle reminders and focus session alerts
                </Text>
              </View>
            </View>

            <View style={styles.permissionItem}>
              <Ionicons name="analytics-outline" size={24} color={theme.colors.primary} />
              <View style={styles.permissionText}>
                <Text style={[styles.permissionLabel, { color: theme.colors.text }]}>
                  Usage Statistics
                </Text>
                <Text style={[styles.permissionDescription, { color: theme.colors.textSecondary }]}>
                  To track your screen time and provide insights (optional)
                </Text>
              </View>
            </View>

            <View style={styles.permissionItem}>
              <Ionicons name="people-outline" size={24} color={theme.colors.primary} />
              <View style={styles.permissionText}>
                <Text style={[styles.permissionLabel, { color: theme.colors.text }]}>
                  Community Features
                </Text>
                <Text style={[styles.permissionDescription, { color: theme.colors.textSecondary }]}>
                  Join anonymous group challenges and earn rewards (optional)
                </Text>
              </View>
            </View>
          </Card>
        )}

        {/* Action Buttons */}
        <View style={styles.buttonContainer}>
          {currentStep < onboardingSteps.length - 1 ? (
            <Button
              title="Next"
              onPress={handleNext}
              size="large"
              style={styles.nextButton}
            />
          ) : (
            <Button
              title={permissionsGranted ? "Get Started" : "Grant Permissions"}
              onPress={handleComplete}
              size="large"
              style={styles.getStartedButton}
            />
          )}
          <Button
            title="Continue as guest"
            onPress={continueAsGuest}
            variant="ghost"
            size="small"
            style={{ marginTop: 12 }}
          />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    paddingHorizontal: 24,
  },
  progressContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 20,
    marginBottom: 20,
  },
  progressDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginHorizontal: 4,
  },
  skipButton: {
    alignSelf: 'flex-end',
    marginBottom: 20,
  },
  content: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 40,
  },
  iconContainer: {
    width: 100,
    height: 100,
    borderRadius: 50,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 32,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 18,
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 16,
  },
  description: {
    fontSize: 16,
    textAlign: 'center',
    lineHeight: 24,
    paddingHorizontal: 20,
    marginBottom: 32,
  },
  imageContainer: {
    width: width * 0.7,
    height: 200,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 20,
  },
  imagePlaceholder: {
    fontSize: 18,
    fontWeight: '600',
  },
  permissionsCard: {
    marginTop: 20,
    marginBottom: 20,
  },
  permissionsTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 16,
  },
  permissionItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  permissionText: {
    flex: 1,
    marginLeft: 12,
  },
  permissionLabel: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  permissionDescription: {
    fontSize: 14,
    lineHeight: 20,
  },
  buttonContainer: {
    paddingBottom: 40,
  },
  nextButton: {
    width: '100%',
  },
  getStartedButton: {
    width: '100%',
  },
}); 