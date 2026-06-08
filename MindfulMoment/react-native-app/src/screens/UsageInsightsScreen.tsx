import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../context/ThemeContext';
import { useApp } from '../context/AppContext';
import { Button } from '../components/Button';
import { Card } from '../components/Card';

const { width } = Dimensions.get('window');

// Mock chart data - in a real app, you'd use a charting library
const mockChartData = [
  { day: 'Mon', public: 45, private: 120, mindful: 30 },
  { day: 'Tue', public: 60, private: 90, mindful: 45 },
  { day: 'Wed', public: 30, private: 150, mindful: 60 },
  { day: 'Thu', public: 75, private: 80, mindful: 25 },
  { day: 'Fri', public: 50, private: 110, mindful: 40 },
  { day: 'Sat', public: 40, private: 130, mindful: 35 },
  { day: 'Sun', public: 35, private: 140, mindful: 50 },
];

export default function UsageInsightsScreen() {
  const { theme } = useTheme();
  const { user, usageData } = useApp();
  const [selectedPeriod, setSelectedPeriod] = useState<'week' | 'month'>('week');
  const [goal, setGoal] = useState(30);

  const getWeeklyStats = () => {
    const last7Days = mockChartData;
    const totalPublic = last7Days.reduce((sum, day) => sum + day.public, 0);
    const totalPrivate = last7Days.reduce((sum, day) => sum + day.private, 0);
    const totalMindful = last7Days.reduce((sum, day) => sum + day.mindful, 0);
    const totalNudges = 12; // Mock data
    const totalSessions = 8; // Mock data

    return {
      totalPublic,
      totalPrivate,
      totalMindful,
      totalNudges,
      totalSessions,
      averagePublic: Math.round(totalPublic / 7),
      averagePrivate: Math.round(totalPrivate / 7),
      averageMindful: Math.round(totalMindful / 7),
    };
  };

  const weeklyStats = getWeeklyStats();

  const formatTime = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  };

  const getProgressPercentage = (current: number, target: number) => {
    return Math.min((current / target) * 100, 100);
  };

  const renderChart = () => {
    const maxValue = Math.max(...mockChartData.map(d => Math.max(d.public, d.private, d.mindful)));
    
    return (
      <View style={styles.chartContainer}>
        <Text style={[styles.chartTitle, { color: theme.colors.text }]}>
          This Week's Activity
        </Text>
        
        <View style={styles.chartLegend}>
          <View style={styles.legendItem}>
            <View style={[styles.legendDot, { backgroundColor: theme.colors.primary }]} />
            <Text style={[styles.legendText, { color: theme.colors.textSecondary }]}>Public</Text>
          </View>
          <View style={styles.legendItem}>
            <View style={[styles.legendDot, { backgroundColor: theme.colors.secondary }]} />
            <Text style={[styles.legendText, { color: theme.colors.textSecondary }]}>Private</Text>
          </View>
          <View style={styles.legendItem}>
            <View style={[styles.legendDot, { backgroundColor: theme.colors.success }]} />
            <Text style={[styles.legendText, { color: theme.colors.textSecondary }]}>Mindful</Text>
          </View>
        </View>

        <View style={styles.chartBars}>
          {mockChartData.map((day, index) => (
            <View key={index} style={styles.chartColumn}>
              <View style={styles.barContainer}>
                <View
                  style={[
                    styles.bar,
                    {
                      height: (day.public / maxValue) * 100,
                      backgroundColor: theme.colors.primary,
                    },
                  ]}
                />
                <View
                  style={[
                    styles.bar,
                    {
                      height: (day.private / maxValue) * 100,
                      backgroundColor: theme.colors.secondary,
                    },
                  ]}
                />
                <View
                  style={[
                    styles.bar,
                    {
                      height: (day.mindful / maxValue) * 100,
                      backgroundColor: theme.colors.success,
                    },
                  ]}
                />
              </View>
              <Text style={[styles.chartLabel, { color: theme.colors.textSecondary }]}>
                {day.day}
              </Text>
            </View>
          ))}
        </View>
      </View>
    );
  };

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={[styles.title, { color: theme.colors.text }]}>
            Usage Insights
          </Text>
          <View style={styles.periodSelector}>
            <Button
              title="Week"
              onPress={() => setSelectedPeriod('week')}
              variant={selectedPeriod === 'week' ? 'primary' : 'outline'}
              size="small"
              style={styles.periodButton}
            />
            <Button
              title="Month"
              onPress={() => setSelectedPeriod('month')}
              variant={selectedPeriod === 'month' ? 'primary' : 'outline'}
              size="small"
              style={styles.periodButton}
            />
          </View>
        </View>

        {/* Weekly Summary */}
        <View style={styles.summaryContainer}>
          <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
            Weekly Summary
          </Text>
          
          <View style={styles.summaryGrid}>
            <Card style={styles.summaryCard}>
              <Ionicons name="time-outline" size={24} color={theme.colors.primary} />
              <Text style={[styles.summaryValue, { color: theme.colors.text }]}>
                {formatTime(weeklyStats.totalPublic)}
              </Text>
              <Text style={[styles.summaryLabel, { color: theme.colors.textSecondary }]}>
                Public Screen Time
              </Text>
              <Text style={[styles.summaryAverage, { color: theme.colors.textSecondary }]}>
                Avg: {formatTime(weeklyStats.averagePublic)}/day
              </Text>
            </Card>

            <Card style={styles.summaryCard}>
              <Ionicons name="home-outline" size={24} color={theme.colors.secondary} />
              <Text style={[styles.summaryValue, { color: theme.colors.text }]}>
                {formatTime(weeklyStats.totalPrivate)}
              </Text>
              <Text style={[styles.summaryLabel, { color: theme.colors.textSecondary }]}>
                Private Screen Time
              </Text>
              <Text style={[styles.summaryAverage, { color: theme.colors.textSecondary }]}>
                Avg: {formatTime(weeklyStats.averagePrivate)}/day
              </Text>
            </Card>

            <Card style={styles.summaryCard}>
              <Ionicons name="leaf-outline" size={24} color={theme.colors.success} />
              <Text style={[styles.summaryValue, { color: theme.colors.text }]}>
                {formatTime(weeklyStats.totalMindful)}
              </Text>
              <Text style={[styles.summaryLabel, { color: theme.colors.textSecondary }]}>
                Mindful Minutes
              </Text>
              <Text style={[styles.summaryAverage, { color: theme.colors.textSecondary }]}>
                Avg: {formatTime(weeklyStats.averageMindful)}/day
              </Text>
            </Card>

            <Card style={styles.summaryCard}>
              <Ionicons name="notifications-outline" size={24} color={theme.colors.warning} />
              <Text style={[styles.summaryValue, { color: theme.colors.text }]}>
                {weeklyStats.totalNudges}
              </Text>
              <Text style={[styles.summaryLabel, { color: theme.colors.textSecondary }]}>
                Nudges Triggered
              </Text>
              <Text style={[styles.summaryAverage, { color: theme.colors.textSecondary }]}>
                {weeklyStats.totalSessions} sessions
              </Text>
            </Card>
          </View>
        </View>

        {/* Chart */}
        <Card style={styles.chartCard}>
          {renderChart()}
        </Card>

        {/* Goal Setting */}
        <Card style={styles.goalCard}>
          <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
            Weekly Goal
          </Text>
          
          <View style={styles.goalProgress}>
            <View style={styles.goalInfo}>
              <Text style={[styles.goalLabel, { color: theme.colors.textSecondary }]}>
                Mindful Minutes Goal
              </Text>
              <Text style={[styles.goalValue, { color: theme.colors.text }]}>
                {weeklyStats.totalMindful} / {goal} minutes
              </Text>
            </View>
            
            <View style={[styles.progressBar, { backgroundColor: theme.colors.border }]}>
              <View
                style={[
                  styles.progressFill,
                  {
                    width: `${getProgressPercentage(weeklyStats.totalMindful, goal)}%`,
                    backgroundColor: theme.colors.success,
                  },
                ]}
              />
            </View>
            
            <Text style={[styles.progressText, { color: theme.colors.textSecondary }]}>
              {getProgressPercentage(weeklyStats.totalMindful, goal).toFixed(0)}% complete
            </Text>
          </View>

          <Button
            title="Update Goal"
            onPress={() => {/* Handle goal update */}}
            variant="outline"
            size="small"
            style={styles.updateGoalButton}
          />
        </Card>

        {/* Reflection */}
        <Card style={styles.reflectionCard}>
          <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
            Weekly Reflection
          </Text>
          <Text style={[styles.reflectionText, { color: theme.colors.textSecondary }]}>
            How did you feel about your phone usage this week? Take a moment to reflect on your digital wellness journey.
          </Text>
          <Button
            title="Add Reflection"
            onPress={() => {/* Handle reflection */}}
            variant="outline"
            size="medium"
            style={styles.reflectionButton}
          />
        </Card>

        {/* Insights */}
        <Card style={styles.insightsCard}>
          <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
            💡 Insights
          </Text>
          
          <View style={styles.insightItem}>
            <Ionicons name="trending-up" size={20} color={theme.colors.success} />
            <Text style={[styles.insightText, { color: theme.colors.textSecondary }]}>
              Your mindful minutes increased by 25% this week!
            </Text>
          </View>
          
          <View style={styles.insightItem}>
            <Ionicons name="time" size={20} color={theme.colors.warning} />
            <Text style={[styles.insightText, { color: theme.colors.textSecondary }]}>
              You're most active on your phone between 7-9 PM
            </Text>
          </View>
          
          <View style={styles.insightItem}>
            <Ionicons name="calendar" size={20} color={theme.colors.info} />
            <Text style={[styles.insightText, { color: theme.colors.textSecondary }]}>
              Wednesday was your most mindful day
            </Text>
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
  scrollContent: {
    padding: 20,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
  },
  periodSelector: {
    flexDirection: 'row',
  },
  periodButton: {
    marginLeft: 8,
  },
  summaryContainer: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 16,
  },
  summaryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  summaryCard: {
    width: '48%',
    alignItems: 'center',
    marginBottom: 12,
    padding: 16,
  },
  summaryValue: {
    fontSize: 18,
    fontWeight: 'bold',
    marginTop: 8,
    marginBottom: 4,
  },
  summaryLabel: {
    fontSize: 12,
    textAlign: 'center',
    marginBottom: 4,
  },
  summaryAverage: {
    fontSize: 10,
    textAlign: 'center',
  },
  chartCard: {
    marginBottom: 24,
  },
  chartContainer: {
    padding: 16,
  },
  chartTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 16,
    textAlign: 'center',
  },
  chartLegend: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 20,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  legendDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: 6,
  },
  legendText: {
    fontSize: 12,
  },
  chartBars: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'flex-end',
    height: 120,
  },
  chartColumn: {
    alignItems: 'center',
    flex: 1,
  },
  barContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    height: 100,
    marginBottom: 8,
  },
  bar: {
    width: 8,
    marginHorizontal: 1,
    borderRadius: 4,
  },
  chartLabel: {
    fontSize: 12,
  },
  goalCard: {
    marginBottom: 24,
  },
  goalProgress: {
    marginBottom: 16,
  },
  goalInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  goalLabel: {
    fontSize: 14,
  },
  goalValue: {
    fontSize: 16,
    fontWeight: '600',
  },
  progressBar: {
    height: 8,
    borderRadius: 4,
    marginBottom: 8,
  },
  progressFill: {
    height: '100%',
    borderRadius: 4,
  },
  progressText: {
    fontSize: 12,
    textAlign: 'center',
  },
  updateGoalButton: {
    alignSelf: 'flex-start',
  },
  reflectionCard: {
    marginBottom: 24,
  },
  reflectionText: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 16,
  },
  reflectionButton: {
    alignSelf: 'flex-start',
  },
  insightsCard: {
    marginBottom: 20,
  },
  insightItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  insightText: {
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
    marginLeft: 8,
  },
}); 