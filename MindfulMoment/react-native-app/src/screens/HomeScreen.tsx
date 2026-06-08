import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../context/ThemeContext';
import { useApp } from '../context/AppContext';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { GPSStatusIndicator } from '../components/GPSStatusIndicator';
import { fetchRandomQuote, FALLBACK_QUOTES } from '../utils/quotes';

export default function HomeScreen() {
  const { theme } = useTheme();
  const { 
    user, 
    currentFocusSession, 
    usageData, 
    currentZone, 
    notificationStats, 
    communityProgress 
  } = useApp();
  const [refreshing, setRefreshing] = useState(false);
  const [currentQuote, setCurrentQuote] = useState('');
  const [quoteAuthor, setQuoteAuthor] = useState<string | null>(null);

  const loadQuote = async () => {
    const result = await fetchRandomQuote();
    if (result) {
      setCurrentQuote(result.text);
      setQuoteAuthor(result.author);
    } else {
      const randomIndex = Math.floor(Math.random() * FALLBACK_QUOTES.length);
      setCurrentQuote(FALLBACK_QUOTES[randomIndex]);
      setQuoteAuthor(null);
    }
  };

  useEffect(() => {
    loadQuote();
  }, []);

  const setRandomQuote = () => {
    loadQuote();
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadQuote();
    setTimeout(() => setRefreshing(false), 1000);
  };

  const handleStartFocusSession = () => {
    Alert.alert(
      'Start Focus Session',
      'Choose session duration:',
      [
        { text: '10 min', onPress: () => startFocusSession(10, 'commute') },
        { text: '15 min', onPress: () => startFocusSession(15, 'commute') },
        { text: '30 min', onPress: () => startFocusSession(30, 'commute') },
        { text: 'Cancel', style: 'cancel' },
      ]
    );
  };

  const startFocusSession = (duration: number, category: string) => {
    // This would be handled by the navigation to FocusSessionScreen
    console.log(`Starting ${duration} minute ${category} session`);
  };

  const getTodayStats = () => {
    const today = new Date().toISOString().split('T')[0];
    const todayData = usageData.find(data => data.date === today);
    
    return {
      screenTimePublic: todayData?.screenTimePublic || 0,
      nudgesTriggered: todayData?.nudgesTriggered || 0,
      focusSessions: todayData?.focusSessions || 0,
      mindfulMinutes: todayData?.mindfulMinutes || 0,
    };
  };

  const todayStats = getTodayStats();

  const formatTime = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  };

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {/* Header with GPS Status */}
        <View style={styles.header}>
          <View style={styles.headerLeft}>
            <Text style={[styles.greeting, { color: theme.colors.text }]}>
              Good {getGreeting()}, {user?.name || 'there'}!
            </Text>
            <Text style={[styles.subtitle, { color: theme.colors.textSecondary }]}>
              Ready for a mindful day?
            </Text>
          </View>
          <View style={styles.headerRight}>
            <GPSStatusIndicator style={styles.gpsIndicator} />
            <View style={[styles.avatar, { backgroundColor: theme.colors.primary }]}>
              <Ionicons name="person" size={24} color="#FFFFFF" />
            </View>
          </View>
        </View>

        {/* Current Location Zone */}
        {currentZone && (
          <Card style={styles.locationCard}>
            <View style={styles.locationHeader}>
              <Ionicons name="location" size={24} color={theme.colors.primary} />
              <Text style={[styles.locationTitle, { color: theme.colors.text }]}>
                {currentZone.name}
              </Text>
            </View>
            <Text style={[styles.locationType, { color: theme.colors.textSecondary }]}>
              {currentZone.type.replace('_', ' ')} • Safety Level: {currentZone.safetyLevel}
            </Text>
          </Card>
        )}

        {/* Current Focus Session */}
        {currentFocusSession && (
          <Card style={styles.focusSessionCard}>
            <View style={styles.focusSessionHeader}>
              <Ionicons name="timer" size={24} color={theme.colors.primary} />
              <Text style={[styles.focusSessionTitle, { color: theme.colors.text }]}>
                Active Focus Session
              </Text>
            </View>
            <Text style={[styles.focusSessionDuration, { color: theme.colors.primary }]}>
              {currentFocusSession.duration} minutes • {currentFocusSession.category}
            </Text>
            <Button
              title="End Session"
              onPress={() => {/* Handle end session */}}
              variant="outline"
              size="small"
              style={styles.endSessionButton}
            />
          </Card>
        )}

        {/* Quick Start Focus Session */}
        {!currentFocusSession && (
          <Card style={styles.quickStartCard}>
            <View style={styles.quickStartContent}>
              <View>
                <Text style={[styles.quickStartTitle, { color: theme.colors.text }]}>
                  Start a Focus Session
                </Text>
                <Text style={[styles.quickStartSubtitle, { color: theme.colors.textSecondary }]}>
                  Take a break from your phone
                </Text>
              </View>
              <Ionicons name="play-circle" size={48} color={theme.colors.primary} />
            </View>
            <Button
              title="Start Session"
              onPress={handleStartFocusSession}
              size="medium"
              style={styles.startSessionButton}
            />
          </Card>
        )}

        {/* Today's Stats */}
        <View style={styles.statsContainer}>
          <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
            Today's Progress
          </Text>
          
          <View style={styles.statsGrid}>
            <Card style={styles.statCard}>
              <Ionicons name="time-outline" size={24} color={theme.colors.primary} />
              <Text style={[styles.statValue, { color: theme.colors.text }]}>
                {formatTime(todayStats.screenTimePublic)}
              </Text>
              <Text style={[styles.statLabel, { color: theme.colors.textSecondary }]}>
                Screen Time (Public)
              </Text>
            </Card>

            <Card style={styles.statCard}>
              <Ionicons name="notifications-outline" size={24} color={theme.colors.warning} />
              <Text style={[styles.statValue, { color: theme.colors.text }]}>
                {notificationStats?.mindfulNudges || 0}
              </Text>
              <Text style={[styles.statLabel, { color: theme.colors.textSecondary }]}>
                Mindful Nudges
              </Text>
            </Card>

            <Card style={styles.statCard}>
              <Ionicons name="timer-outline" size={24} color={theme.colors.success} />
              <Text style={[styles.statValue, { color: theme.colors.text }]}>
                {todayStats.focusSessions}
              </Text>
              <Text style={[styles.statLabel, { color: theme.colors.textSecondary }]}>
                Focus Sessions
              </Text>
            </Card>

            <Card style={styles.statCard}>
              <Ionicons name="leaf-outline" size={24} color={theme.colors.info} />
              <Text style={[styles.statValue, { color: theme.colors.text }]}>
                {communityProgress?.mindfulMinutes || 0}
              </Text>
              <Text style={[styles.statLabel, { color: theme.colors.textSecondary }]}>
                Mindful Minutes
              </Text>
            </Card>
          </View>
        </View>

        {/* Community Progress */}
        {communityProgress && (
          <View style={styles.communityContainer}>
            <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
              Community Progress
            </Text>
            
            <View style={styles.statsGrid}>
              <Card style={styles.statCard}>
                <Ionicons name="trophy-outline" size={24} color={theme.colors.primary} />
                <Text style={[styles.statValue, { color: theme.colors.text }]}>
                  {communityProgress.totalPoints}
                </Text>
                <Text style={[styles.statLabel, { color: theme.colors.textSecondary }]}>
                  Total Points
                </Text>
              </Card>

              <Card style={styles.statCard}>
                <Ionicons name="medal-outline" size={24} color={theme.colors.warning} />
                <Text style={[styles.statValue, { color: theme.colors.text }]}>
                  {communityProgress.badges?.length || 0}
                </Text>
                <Text style={[styles.statLabel, { color: theme.colors.textSecondary }]}>
                  Badges Earned
                </Text>
              </Card>

              <Card style={styles.statCard}>
                <Ionicons name="flame-outline" size={24} color={theme.colors.success} />
                <Text style={[styles.statValue, { color: theme.colors.text }]}>
                  {communityProgress.currentStreak || 0}
                </Text>
                <Text style={[styles.statLabel, { color: theme.colors.textSecondary }]}>
                  Current Streak
                </Text>
              </Card>

              <Card style={styles.statCard}>
                <Ionicons name="people-outline" size={24} color={theme.colors.info} />
                <Text style={[styles.statValue, { color: theme.colors.text }]}>
                  {Object.keys(communityProgress.groupContributions || {}).length}
                </Text>
                <Text style={[styles.statLabel, { color: theme.colors.textSecondary }]}>
                  Groups Joined
                </Text>
              </Card>
            </View>
          </View>
        )}

        {/* Motivational Quote */}
        <Card style={styles.quoteCard}>
          <Ionicons name="quote" size={24} color={theme.colors.primary} />
          <Text style={[styles.quoteText, { color: theme.colors.text }]}>
            "{currentQuote}"
          </Text>
          {quoteAuthor ? (
            <Text style={[styles.quoteAuthor, { color: theme.colors.textSecondary }]}>
              — {quoteAuthor}
            </Text>
          ) : null}
          <Button
            title="New Quote"
            onPress={setRandomQuote}
            variant="ghost"
            size="small"
            style={styles.newQuoteButton}
          />
        </Card>

        {/* Quick Actions */}
        <View style={styles.quickActions}>
          <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
            Quick Actions
          </Text>
          
          <View style={styles.actionButtons}>
            <Button
              title="View Insights"
              onPress={() => {/* Navigate to insights */}}
              variant="outline"
              size="medium"
              style={styles.actionButton}
            />
            <Button
              title="Join Community"
              onPress={() => {/* Navigate to community */}}
              variant="outline"
              size="medium"
              style={styles.actionButton}
            />
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const getGreeting = () => {
  const hour = new Date().getHours();
  if (hour < 12) return 'morning';
  if (hour < 17) return 'afternoon';
  return 'evening';
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 24,
  },
  headerLeft: {
    flex: 1,
  },
  headerRight: {
    alignItems: 'flex-end',
    gap: 8,
  },
  gpsIndicator: {
    marginBottom: 4,
  },
  greeting: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 16,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  focusSessionCard: {
    marginBottom: 20,
  },
  focusSessionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  focusSessionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginLeft: 8,
  },
  focusSessionDuration: {
    fontSize: 16,
    marginBottom: 12,
  },
  endSessionButton: {
    alignSelf: 'flex-start',
  },
  quickStartCard: {
    marginBottom: 20,
  },
  quickStartContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  quickStartTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 4,
  },
  quickStartSubtitle: {
    fontSize: 14,
  },
  startSessionButton: {
    width: '100%',
  },
  statsContainer: {
    marginBottom: 24,
  },
  communityContainer: {
    marginBottom: 24,
  },
  locationCard: {
    marginBottom: 20,
  },
  locationHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  locationTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginLeft: 8,
  },
  locationType: {
    fontSize: 14,
    textTransform: 'capitalize',
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 16,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  statCard: {
    width: '48%',
    alignItems: 'center',
    marginBottom: 12,
    padding: 16,
  },
  statValue: {
    fontSize: 20,
    fontWeight: 'bold',
    marginTop: 8,
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 12,
    textAlign: 'center',
  },
  quoteCard: {
    marginBottom: 24,
    alignItems: 'center',
  },
  quoteText: {
    fontSize: 16,
    fontStyle: 'italic',
    textAlign: 'center',
    marginTop: 12,
    marginBottom: 16,
    lineHeight: 24,
  },
  quoteAuthor: {
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 12,
  },
  newQuoteButton: {
    alignSelf: 'center',
  },
  quickActions: {
    marginBottom: 20,
  },
  actionButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  actionButton: {
    flex: 1,
    marginHorizontal: 4,
  },
}); 