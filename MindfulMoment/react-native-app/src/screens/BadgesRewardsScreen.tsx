import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../context/ThemeContext';
import { useApp } from '../context/AppContext';
import { Button } from '../components/Button';
import { Card } from '../components/Card';

const badges = [
  {
    id: '1',
    name: 'Safe Commuter',
    description: 'Complete 10 mindful minutes while commuting',
    icon: 'car-outline',
    color: '#4A90E2',
    unlocked: true,
    progress: 100,
  },
  {
    id: '2',
    name: 'Park Explorer',
    description: 'Spend 30 minutes in nature without phone',
    icon: 'leaf-outline',
    color: '#28A745',
    unlocked: true,
    progress: 100,
  },
  {
    id: '3',
    name: 'Focus Master',
    description: 'Complete 5 focus sessions in a week',
    icon: 'timer-outline',
    color: '#FF6B6B',
    unlocked: false,
    progress: 60,
  },
  {
    id: '4',
    name: 'Mindful Beginner',
    description: 'Complete your first focus session',
    icon: 'star-outline',
    color: '#FFC107',
    unlocked: true,
    progress: 100,
  },
  {
    id: '5',
    name: 'Digital Detox',
    description: 'Reduce screen time by 50% for a week',
    icon: 'phone-portrait-outline',
    color: '#7B68EE',
    unlocked: false,
    progress: 30,
  },
  {
    id: '6',
    name: 'Community Champion',
    description: 'Join 3 community challenges',
    icon: 'people-outline',
    color: '#17A2B8',
    unlocked: false,
    progress: 0,
  },
];

const rewards = [
  {
    id: '1',
    name: 'Coffee Voucher',
    description: 'Free coffee at participating cafes',
    points: 500,
    icon: 'cafe-outline',
    color: '#8B4513',
    available: true,
  },
  {
    id: '2',
    name: 'Book Store Credit',
    description: '$10 credit at local bookstores',
    points: 1000,
    icon: 'library-outline',
    color: '#2E8B57',
    available: true,
  },
  {
    id: '3',
    name: 'Fitness Class Pass',
    description: 'Free yoga or meditation class',
    points: 750,
    icon: 'fitness-outline',
    color: '#FF6B6B',
    available: true,
  },
  {
    id: '4',
    name: 'Movie Ticket',
    description: 'Free movie ticket at local theaters',
    points: 1500,
    icon: 'film-outline',
    color: '#9C27B0',
    available: false,
  },
];

export default function BadgesRewardsScreen() {
  const { theme } = useTheme();
  const { user } = useApp();
  const [selectedTab, setSelectedTab] = useState<'badges' | 'rewards'>('badges');

  const userPoints = user?.mindfulMinutes || 0;
  const unlockedBadges = badges.filter(badge => badge.unlocked).length;
  const totalBadges = badges.length;

  const handleRedeemReward = (reward: typeof rewards[0]) => {
    if (userPoints >= reward.points) {
      Alert.alert(
        'Redeem Reward',
        `Would you like to redeem "${reward.name}" for ${reward.points} points?`,
        [
          { text: 'Cancel', style: 'cancel' },
          { 
            text: 'Redeem', 
            onPress: () => {
              Alert.alert(
                'Success!',
                `You've redeemed "${reward.name}". Check your email for details.`,
                [{ text: 'OK' }]
              );
            }
          },
        ]
      );
    } else {
      Alert.alert(
        'Insufficient Points',
        `You need ${reward.points - userPoints} more points to redeem this reward.`,
        [{ text: 'OK' }]
      );
    }
  };

  const renderBadges = () => (
    <View style={styles.badgesContainer}>
      <Card style={styles.progressCard}>
        <View style={styles.progressHeader}>
          <Ionicons name="trophy" size={24} color={theme.colors.primary} />
          <Text style={[styles.progressTitle, { color: theme.colors.text }]}>
            Badge Progress
          </Text>
        </View>
        <Text style={[styles.progressText, { color: theme.colors.textSecondary }]}>
          {unlockedBadges} of {totalBadges} badges unlocked
        </Text>
        <View style={[styles.progressBar, { backgroundColor: theme.colors.border }]}>
          <View
            style={[
              styles.progressFill,
              {
                width: `${(unlockedBadges / totalBadges) * 100}%`,
                backgroundColor: theme.colors.primary,
              },
            ]}
          />
        </View>
      </Card>

      <View style={styles.badgesGrid}>
        {badges.map((badge) => (
          <Card
            key={badge.id}
            style={[
              styles.badgeCard,
              !badge.unlocked && { opacity: 0.6 },
            ]}
          >
            <View style={[styles.badgeIcon, { backgroundColor: badge.color + '20' }]}>
              <Ionicons
                name={badge.icon as any}
                size={32}
                color={badge.unlocked ? badge.color : theme.colors.textSecondary}
              />
            </View>
            <Text style={[styles.badgeName, { color: theme.colors.text }]}>
              {badge.name}
            </Text>
            <Text style={[styles.badgeDescription, { color: theme.colors.textSecondary }]}>
              {badge.description}
            </Text>
            {!badge.unlocked && (
              <View style={styles.badgeProgress}>
                <View style={[styles.badgeProgressBar, { backgroundColor: theme.colors.border }]}>
                  <View
                    style={[
                      styles.badgeProgressFill,
                      {
                        width: `${badge.progress}%`,
                        backgroundColor: badge.color,
                      },
                    ]}
                  />
                </View>
                <Text style={[styles.badgeProgressText, { color: theme.colors.textSecondary }]}>
                  {badge.progress}%
                </Text>
              </View>
            )}
            {badge.unlocked && (
              <View style={styles.unlockedBadge}>
                <Ionicons name="checkmark-circle" size={20} color={theme.colors.success} />
                <Text style={[styles.unlockedText, { color: theme.colors.success }]}>
                  Unlocked
                </Text>
              </View>
            )}
          </Card>
        ))}
      </View>
    </View>
  );

  const renderRewards = () => (
    <View style={styles.rewardsContainer}>
      <Card style={styles.pointsCard}>
        <View style={styles.pointsHeader}>
          <Ionicons name="star" size={24} color={theme.colors.warning} />
          <Text style={[styles.pointsTitle, { color: theme.colors.text }]}>
            Your Points
          </Text>
        </View>
        <Text style={[styles.pointsValue, { color: theme.colors.primary }]}>
          {userPoints}
        </Text>
        <Text style={[styles.pointsSubtitle, { color: theme.colors.textSecondary }]}>
          Mindful Minutes earned
        </Text>
      </Card>

      <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
        Available Rewards
      </Text>

      <View style={styles.rewardsList}>
        {rewards.map((reward) => (
          <Card
            key={reward.id}
            style={[
              styles.rewardCard,
              !reward.available && { opacity: 0.6 },
            ]}
          >
            <View style={styles.rewardHeader}>
              <View style={[styles.rewardIcon, { backgroundColor: reward.color + '20' }]}>
                <Ionicons
                  name={reward.icon as any}
                  size={24}
                  color={reward.color}
                />
              </View>
              <View style={styles.rewardInfo}>
                <Text style={[styles.rewardName, { color: theme.colors.text }]}>
                  {reward.name}
                </Text>
                <Text style={[styles.rewardDescription, { color: theme.colors.textSecondary }]}>
                  {reward.description}
                </Text>
              </View>
              <View style={styles.rewardPoints}>
                <Text style={[styles.pointsLabel, { color: theme.colors.primary }]}>
                  {reward.points}
                </Text>
                <Text style={[styles.pointsText, { color: theme.colors.textSecondary }]}>
                  points
                </Text>
              </View>
            </View>
            
            <Button
              title={userPoints >= reward.points ? "Redeem" : "Not Enough Points"}
              onPress={() => handleRedeemReward(reward)}
              variant={userPoints >= reward.points ? "primary" : "outline"}
              size="small"
              disabled={!reward.available || userPoints < reward.points}
              style={styles.redeemButton}
            />
          </Card>
        ))}
      </View>
    </View>
  );

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <View style={styles.header}>
        <Text style={[styles.title, { color: theme.colors.text }]}>
          Badges & Rewards
        </Text>
      </View>

      {/* Tab Selector */}
      <View style={styles.tabContainer}>
        <Button
          title="Badges"
          onPress={() => setSelectedTab('badges')}
          variant={selectedTab === 'badges' ? 'primary' : 'outline'}
          size="medium"
          style={styles.tabButton}
        />
        <Button
          title="Rewards"
          onPress={() => setSelectedTab('rewards')}
          variant={selectedTab === 'rewards' ? 'primary' : 'outline'}
          size="medium"
          style={styles.tabButton}
        />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {selectedTab === 'badges' ? renderBadges() : renderRewards()}
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
  tabContainer: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    marginBottom: 20,
  },
  tabButton: {
    flex: 1,
    marginHorizontal: 4,
  },
  scrollContent: {
    padding: 20,
    paddingTop: 0,
  },
  badgesContainer: {
    marginBottom: 20,
  },
  progressCard: {
    marginBottom: 24,
  },
  progressHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  progressTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginLeft: 8,
  },
  progressText: {
    fontSize: 14,
    marginBottom: 12,
  },
  progressBar: {
    height: 8,
    borderRadius: 4,
  },
  progressFill: {
    height: '100%',
    borderRadius: 4,
  },
  badgesGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  badgeCard: {
    width: '48%',
    alignItems: 'center',
    marginBottom: 16,
    padding: 16,
  },
  badgeIcon: {
    width: 64,
    height: 64,
    borderRadius: 32,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  badgeName: {
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 4,
  },
  badgeDescription: {
    fontSize: 12,
    textAlign: 'center',
    lineHeight: 16,
    marginBottom: 8,
  },
  badgeProgress: {
    width: '100%',
  },
  badgeProgressBar: {
    height: 4,
    borderRadius: 2,
    marginBottom: 4,
  },
  badgeProgressFill: {
    height: '100%',
    borderRadius: 2,
  },
  badgeProgressText: {
    fontSize: 10,
    textAlign: 'center',
  },
  unlockedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  unlockedText: {
    fontSize: 12,
    fontWeight: '600',
    marginLeft: 4,
  },
  rewardsContainer: {
    marginBottom: 20,
  },
  pointsCard: {
    marginBottom: 24,
    alignItems: 'center',
  },
  pointsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  pointsTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginLeft: 8,
  },
  pointsValue: {
    fontSize: 36,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  pointsSubtitle: {
    fontSize: 14,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 16,
  },
  rewardsList: {
    marginBottom: 20,
  },
  rewardCard: {
    marginBottom: 16,
  },
  rewardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  rewardIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  rewardInfo: {
    flex: 1,
  },
  rewardName: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  rewardDescription: {
    fontSize: 14,
    lineHeight: 18,
  },
  rewardPoints: {
    alignItems: 'center',
  },
  pointsLabel: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  pointsText: {
    fontSize: 12,
  },
  redeemButton: {
    alignSelf: 'flex-start',
  },
}); 