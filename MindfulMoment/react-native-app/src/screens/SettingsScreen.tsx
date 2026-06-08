import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Switch,
  Alert,
  Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../context/ThemeContext';
import { useApp } from '../context/AppContext';
import { Button } from '../components/Button';
import { Card } from '../components/Card';

export default function SettingsScreen() {
  const { theme, isDark, toggleTheme } = useTheme();
  const { user, updateUser, resetApp } = useApp();
  const [notifications, setNotifications] = useState(user?.preferences.notifications || true);
  const [location, setLocation] = useState(user?.preferences.location || true);
  const [community, setCommunity] = useState(user?.preferences.community || false);

  const handleToggleNotifications = (value: boolean) => {
    setNotifications(value);
    updateUser({
      preferences: {
        ...user?.preferences,
        notifications: value,
      },
    });
  };

  const handleToggleLocation = (value: boolean) => {
    setLocation(value);
    updateUser({
      preferences: {
        ...user?.preferences,
        location: value,
      },
    });
  };

  const handleToggleCommunity = (value: boolean) => {
    setCommunity(value);
    updateUser({
      preferences: {
        ...user?.preferences,
        community: value,
      },
    });
  };

  const handleResetApp = () => {
    Alert.alert(
      'Reset App',
      'This will delete all your data and reset the app to its initial state. This action cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Reset', 
          style: 'destructive',
          onPress: () => {
            resetApp();
            Alert.alert('App Reset', 'The app has been reset successfully.');
          }
        },
      ]
    );
  };

  const handlePrivacyPolicy = () => {
    Linking.openURL('https://mindfulmoment.app/privacy');
  };

  const handleTermsOfService = () => {
    Linking.openURL('https://mindfulmoment.app/terms');
  };

  const handleContactSupport = () => {
    Linking.openURL('mailto:support@mindfulmoment.app');
  };

  const renderSettingItem = (
    icon: string,
    title: string,
    subtitle?: string,
    rightComponent?: React.ReactNode,
    onPress?: () => void
  ) => (
    <View style={styles.settingItem}>
      <View style={styles.settingLeft}>
        <View style={[styles.settingIcon, { backgroundColor: theme.colors.primary + '20' }]}>
          <Ionicons name={icon as any} size={20} color={theme.colors.primary} />
        </View>
        <View style={styles.settingInfo}>
          <Text style={[styles.settingTitle, { color: theme.colors.text }]}>
            {title}
          </Text>
          {subtitle && (
            <Text style={[styles.settingSubtitle, { color: theme.colors.textSecondary }]}>
              {subtitle}
            </Text>
          )}
        </View>
      </View>
      {rightComponent && (
        <View style={styles.settingRight}>
          {rightComponent}
        </View>
      )}
    </View>
  );

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <View style={styles.header}>
        <Text style={[styles.title, { color: theme.colors.text }]}>
          Settings
        </Text>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* User Profile */}
        <Card style={styles.profileCard}>
          <View style={styles.profileHeader}>
            <View style={[styles.avatar, { backgroundColor: theme.colors.primary }]}>
              <Ionicons name="person" size={32} color="#FFFFFF" />
            </View>
            <View style={styles.profileInfo}>
              <Text style={[styles.profileName, { color: theme.colors.text }]}>
                {user?.name || 'User'}
              </Text>
              <Text style={[styles.profileStats, { color: theme.colors.textSecondary }]}>
                {user?.mindfulMinutes || 0} mindful minutes • {user?.totalFocusSessions || 0} sessions
              </Text>
            </View>
          </View>
        </Card>

        {/* Preferences */}
        <Card style={styles.sectionCard}>
          <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
            Preferences
          </Text>
          
          {renderSettingItem(
            'notifications-outline',
            'Notifications',
            'Receive gentle reminders and alerts',
            <Switch
              value={notifications}
              onValueChange={handleToggleNotifications}
              trackColor={{ false: theme.colors.border, true: theme.colors.primary + '40' }}
              thumbColor={notifications ? theme.colors.primary : theme.colors.textSecondary}
            />
          )}
          
          {renderSettingItem(
            'location-outline',
            'Location Services',
            'Enable contextual nudges based on location',
            <Switch
              value={location}
              onValueChange={handleToggleLocation}
              trackColor={{ false: theme.colors.border, true: theme.colors.primary + '40' }}
              thumbColor={location ? theme.colors.primary : theme.colors.textSecondary}
            />
          )}
          
          {renderSettingItem(
            'people-outline',
            'Community Features',
            'Share anonymous progress with groups',
            <Switch
              value={community}
              onValueChange={handleToggleCommunity}
              trackColor={{ false: theme.colors.border, true: theme.colors.primary + '40' }}
              thumbColor={community ? theme.colors.primary : theme.colors.textSecondary}
            />
          )}
          
          {renderSettingItem(
            'moon-outline',
            'Dark Mode',
            'Use dark theme for the app',
            <Switch
              value={isDark}
              onValueChange={toggleTheme}
              trackColor={{ false: theme.colors.border, true: theme.colors.primary + '40' }}
              thumbColor={isDark ? theme.colors.primary : theme.colors.textSecondary}
            />
          )}
        </Card>

        {/* App Information */}
        <Card style={styles.sectionCard}>
          <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
            App Information
          </Text>
          
          {renderSettingItem(
            'information-circle-outline',
            'About MindfulMoment',
            'Version 1.0.0',
            <Ionicons name="chevron-forward" size={20} color={theme.colors.textSecondary} />
          )}
          
          {renderSettingItem(
            'shield-checkmark-outline',
            'Privacy Policy',
            'How we protect your data',
            <Ionicons name="chevron-forward" size={20} color={theme.colors.textSecondary} />,
            handlePrivacyPolicy
          )}
          
          {renderSettingItem(
            'document-text-outline',
            'Terms of Service',
            'App usage terms and conditions',
            <Ionicons name="chevron-forward" size={20} color={theme.colors.textSecondary} />,
            handleTermsOfService
          )}
        </Card>

        {/* Support */}
        <Card style={styles.sectionCard}>
          <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
            Support
          </Text>
          
          {renderSettingItem(
            'help-circle-outline',
            'Help & FAQ',
            'Common questions and answers',
            <Ionicons name="chevron-forward" size={20} color={theme.colors.textSecondary} />
          )}
          
          {renderSettingItem(
            'mail-outline',
            'Contact Support',
            'Get help from our team',
            <Ionicons name="chevron-forward" size={20} color={theme.colors.textSecondary} />,
            handleContactSupport
          )}
          
          {renderSettingItem(
            'star-outline',
            'Rate the App',
            'Share your feedback',
            <Ionicons name="chevron-forward" size={20} color={theme.colors.textSecondary} />
          )}
        </Card>

        {/* Data Management */}
        <Card style={styles.sectionCard}>
          <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
            Data Management
          </Text>
          
          {renderSettingItem(
            'download-outline',
            'Export Data',
            'Download your mindful moments data',
            <Ionicons name="chevron-forward" size={20} color={theme.colors.textSecondary} />
          )}
          
          {renderSettingItem(
            'trash-outline',
            'Reset App',
            'Delete all data and start fresh',
            <Ionicons name="chevron-forward" size={20} color={theme.colors.textSecondary} />,
            handleResetApp
          )}
        </Card>

        {/* App Stats */}
        <Card style={styles.statsCard}>
          <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
            Your Journey
          </Text>
          
          <View style={styles.statsGrid}>
            <View style={styles.statItem}>
              <Text style={[styles.statValue, { color: theme.colors.primary }]}>
                {user?.mindfulMinutes || 0}
              </Text>
              <Text style={[styles.statLabel, { color: theme.colors.textSecondary }]}>
                Mindful Minutes
              </Text>
            </View>
            
            <View style={styles.statItem}>
              <Text style={[styles.statValue, { color: theme.colors.success }]}>
                {user?.totalFocusSessions || 0}
              </Text>
              <Text style={[styles.statLabel, { color: theme.colors.textSecondary }]}>
                Focus Sessions
              </Text>
            </View>
            
            <View style={styles.statItem}>
              <Text style={[styles.statValue, { color: theme.colors.warning }]}>
                {user?.badges?.length || 0}
              </Text>
              <Text style={[styles.statLabel, { color: theme.colors.textSecondary }]}>
                Badges Earned
              </Text>
            </View>
            
            <View style={styles.statItem}>
              <Text style={[styles.statValue, { color: theme.colors.info }]}>
                {Math.floor((user?.joinDate ? (Date.now() - new Date(user.joinDate).getTime()) / (1000 * 60 * 60 * 24) : 0))}
              </Text>
              <Text style={[styles.statLabel, { color: theme.colors.textSecondary }]}>
                Days Active
              </Text>
            </View>
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
  header: {
    padding: 20,
    paddingBottom: 0,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
  },
  scrollContent: {
    padding: 20,
    paddingTop: 0,
  },
  profileCard: {
    marginBottom: 20,
  },
  profileHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  avatar: {
    width: 64,
    height: 64,
    borderRadius: 32,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 16,
  },
  profileInfo: {
    flex: 1,
  },
  profileName: {
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 4,
  },
  profileStats: {
    fontSize: 14,
  },
  sectionCard: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 16,
  },
  settingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5E5',
  },
  settingLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  settingIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  settingInfo: {
    flex: 1,
  },
  settingTitle: {
    fontSize: 16,
    fontWeight: '500',
    marginBottom: 2,
  },
  settingSubtitle: {
    fontSize: 14,
  },
  settingRight: {
    alignItems: 'center',
  },
  statsCard: {
    marginBottom: 20,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  statItem: {
    width: '48%',
    alignItems: 'center',
    marginBottom: 16,
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 12,
    textAlign: 'center',
  },
}); 