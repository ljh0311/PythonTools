import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Alert,
  TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../context/ThemeContext';
import { useApp } from '../context/AppContext';
import { Button } from '../components/Button';
import { Card } from '../components/Card';

const mockGroups = [
  {
    id: '1',
    name: 'Mindful Students',
    code: 'STUDENT2024',
    members: 156,
    totalMindfulMinutes: 2847,
    weeklyGoal: 500,
    isMember: true,
  },
  {
    id: '2',
    name: 'Digital Wellness Office',
    code: 'OFFICE2024',
    members: 89,
    totalMindfulMinutes: 1923,
    weeklyGoal: 300,
    isMember: false,
  },
  {
    id: '3',
    name: 'Mindful Parents',
    code: 'PARENT2024',
    members: 234,
    totalMindfulMinutes: 4156,
    weeklyGoal: 750,
    isMember: false,
  },
];

const mockLeaderboard = [
  { rank: 1, name: 'Anonymous User', mindfulMinutes: 245, isCurrentUser: false },
  { rank: 2, name: 'Anonymous User', mindfulMinutes: 198, isCurrentUser: true },
  { rank: 3, name: 'Anonymous User', mindfulMinutes: 187, isCurrentUser: false },
  { rank: 4, name: 'Anonymous User', mindfulMinutes: 156, isCurrentUser: false },
  { rank: 5, name: 'Anonymous User', mindfulMinutes: 134, isCurrentUser: false },
];

export default function CommunityScreen() {
  const { theme } = useTheme();
  const { user } = useApp();
  const [selectedTab, setSelectedTab] = useState<'groups' | 'leaderboard'>('groups');
  const [joinCode, setJoinCode] = useState('');
  const [showJoinModal, setShowJoinModal] = useState(false);

  const currentGroup = mockGroups.find(group => group.isMember);
  const userRank = mockLeaderboard.find(entry => entry.isCurrentUser)?.rank || 0;

  const handleJoinGroup = () => {
    const group = mockGroups.find(g => g.code === joinCode.toUpperCase());
    if (group) {
      Alert.alert(
        'Join Group',
        `Would you like to join "${group.name}"?`,
        [
          { text: 'Cancel', style: 'cancel' },
          { 
            text: 'Join', 
            onPress: () => {
              Alert.alert('Success!', `You've joined ${group.name}.`);
              setShowJoinModal(false);
              setJoinCode('');
            }
          },
        ]
      );
    } else {
      Alert.alert('Invalid Code', 'Please check the group code and try again.');
    }
  };

  const handleLeaveGroup = (group: typeof mockGroups[0]) => {
    Alert.alert(
      'Leave Group',
      `Are you sure you want to leave "${group.name}"?`,
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Leave', 
          style: 'destructive',
          onPress: () => {
            Alert.alert('Left Group', `You've left ${group.name}.`);
          }
        },
      ]
    );
  };

  const renderGroups = () => (
    <View style={styles.groupsContainer}>
      {/* Current Group */}
      {currentGroup && (
        <Card style={styles.currentGroupCard}>
          <View style={styles.groupHeader}>
            <View style={styles.groupInfo}>
              <Text style={[styles.groupName, { color: theme.colors.text }]}>
                {currentGroup.name}
              </Text>
              <Text style={[styles.groupCode, { color: theme.colors.primary }]}>
                Code: {currentGroup.code}
              </Text>
            </View>
            <Ionicons name="people" size={24} color={theme.colors.primary} />
          </View>
          
          <View style={styles.groupStats}>
            <View style={styles.statItem}>
              <Text style={[styles.statValue, { color: theme.colors.text }]}>
                {currentGroup.members}
              </Text>
              <Text style={[styles.statLabel, { color: theme.colors.textSecondary }]}>
                Members
              </Text>
            </View>
            <View style={styles.statItem}>
              <Text style={[styles.statValue, { color: theme.colors.text }]}>
                {currentGroup.totalMindfulMinutes}
              </Text>
              <Text style={[styles.statLabel, { color: theme.colors.textSecondary }]}>
                Total Minutes
              </Text>
            </View>
            <View style={styles.statItem}>
              <Text style={[styles.statValue, { color: theme.colors.text }]}>
                {Math.round((currentGroup.totalMindfulMinutes / currentGroup.weeklyGoal) * 100)}%
              </Text>
              <Text style={[styles.statLabel, { color: theme.colors.textSecondary }]}>
                Weekly Goal
              </Text>
            </View>
          </View>

          <View style={[styles.progressBar, { backgroundColor: theme.colors.border }]}>
            <View
              style={[
                styles.progressFill,
                {
                  width: `${Math.min((currentGroup.totalMindfulMinutes / currentGroup.weeklyGoal) * 100, 100)}%`,
                  backgroundColor: theme.colors.success,
                },
              ]}
            />
          </View>

          <Button
            title="Leave Group"
            onPress={() => handleLeaveGroup(currentGroup)}
            variant="outline"
            size="small"
            style={styles.leaveButton}
          />
        </Card>
      )}

      {/* Join New Group */}
      <Card style={styles.joinCard}>
        <Text style={[styles.joinTitle, { color: theme.colors.text }]}>
          Join a Group
        </Text>
        <Text style={[styles.joinDescription, { color: theme.colors.textSecondary }]}>
          Connect with others on their mindful journey
        </Text>
        <Button
          title="Join with Code"
          onPress={() => setShowJoinModal(true)}
          size="medium"
          icon={<Ionicons name="add" size={20} color="#FFFFFF" />}
          style={styles.joinButton}
        />
      </Card>

      {/* Available Groups */}
      <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
        Popular Groups
      </Text>
      
      {mockGroups.filter(group => !group.isMember).map((group) => (
        <Card key={group.id} style={styles.groupCard}>
          <View style={styles.groupCardHeader}>
            <View style={styles.groupCardInfo}>
              <Text style={[styles.groupCardName, { color: theme.colors.text }]}>
                {group.name}
              </Text>
              <Text style={[styles.groupCardMembers, { color: theme.colors.textSecondary }]}>
                {group.members} members
              </Text>
            </View>
            <Button
              title="Join"
              onPress={() => {
                setJoinCode(group.code);
                setShowJoinModal(true);
              }}
              size="small"
            />
          </View>
        </Card>
      ))}
    </View>
  );

  const renderLeaderboard = () => (
    <View style={styles.leaderboardContainer}>
      {/* User's Position */}
      <Card style={styles.userPositionCard}>
        <View style={styles.userPositionHeader}>
          <Ionicons name="trophy" size={24} color={theme.colors.warning} />
          <Text style={[styles.userPositionTitle, { color: theme.colors.text }]}>
            Your Position
          </Text>
        </View>
        <Text style={[styles.userPositionRank, { color: theme.colors.primary }]}>
          #{userRank}
        </Text>
        <Text style={[styles.userPositionMinutes, { color: theme.colors.textSecondary }]}>
          {user?.mindfulMinutes || 0} mindful minutes
        </Text>
      </Card>

      {/* Leaderboard */}
      <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
        This Week's Leaders
      </Text>

      <Card style={styles.leaderboardCard}>
        {mockLeaderboard.map((entry, index) => (
          <View
            key={index}
            style={[
              styles.leaderboardRow,
              entry.isCurrentUser && { backgroundColor: theme.colors.primary + '10' },
            ]}
          >
            <View style={styles.rankContainer}>
              {entry.rank <= 3 ? (
                <Ionicons
                  name="trophy"
                  size={20}
                  color={entry.rank === 1 ? '#FFD700' : entry.rank === 2 ? '#C0C0C0' : '#CD7F32'}
                />
              ) : (
                <Text style={[styles.rankText, { color: theme.colors.textSecondary }]}>
                  #{entry.rank}
                </Text>
              )}
            </View>
            
            <View style={styles.userInfo}>
              <Text style={[styles.userName, { color: theme.colors.text }]}>
                {entry.name}
                {entry.isCurrentUser && ' (You)'}
              </Text>
            </View>
            
            <Text style={[styles.userMinutes, { color: theme.colors.primary }]}>
              {entry.mindfulMinutes}m
            </Text>
          </View>
        ))}
      </Card>
    </View>
  );

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <View style={styles.header}>
        <Text style={[styles.title, { color: theme.colors.text }]}>
          Community
        </Text>
      </View>

      {/* Tab Selector */}
      <View style={styles.tabContainer}>
        <Button
          title="Groups"
          onPress={() => setSelectedTab('groups')}
          variant={selectedTab === 'groups' ? 'primary' : 'outline'}
          size="medium"
          style={styles.tabButton}
        />
        <Button
          title="Leaderboard"
          onPress={() => setSelectedTab('leaderboard')}
          variant={selectedTab === 'leaderboard' ? 'primary' : 'outline'}
          size="medium"
          style={styles.tabButton}
        />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {selectedTab === 'groups' ? renderGroups() : renderLeaderboard()}
      </ScrollView>

      {/* Join Modal */}
      {showJoinModal && (
        <View style={styles.modalOverlay}>
          <Card style={styles.modalCard}>
            <Text style={[styles.modalTitle, { color: theme.colors.text }]}>
              Join Group
            </Text>
            <Text style={[styles.modalDescription, { color: theme.colors.textSecondary }]}>
              Enter the group code to join
            </Text>
            
            <TextInput
              style={[
                styles.codeInput,
                {
                  borderColor: theme.colors.border,
                  color: theme.colors.text,
                  backgroundColor: theme.colors.surface,
                },
              ]}
              placeholder="Enter group code"
              placeholderTextColor={theme.colors.textSecondary}
              value={joinCode}
              onChangeText={setJoinCode}
              autoCapitalize="characters"
              autoCorrect={false}
            />
            
            <View style={styles.modalButtons}>
              <Button
                title="Cancel"
                onPress={() => {
                  setShowJoinModal(false);
                  setJoinCode('');
                }}
                variant="outline"
                size="medium"
                style={styles.modalButton}
              />
              <Button
                title="Join"
                onPress={handleJoinGroup}
                size="medium"
                style={styles.modalButton}
              />
            </View>
          </Card>
        </View>
      )}
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
  groupsContainer: {
    marginBottom: 20,
  },
  currentGroupCard: {
    marginBottom: 24,
  },
  groupHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  groupInfo: {
    flex: 1,
  },
  groupName: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 4,
  },
  groupCode: {
    fontSize: 14,
  },
  groupStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 16,
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 12,
  },
  progressBar: {
    height: 8,
    borderRadius: 4,
    marginBottom: 16,
  },
  progressFill: {
    height: '100%',
    borderRadius: 4,
  },
  leaveButton: {
    alignSelf: 'flex-start',
  },
  joinCard: {
    marginBottom: 24,
    alignItems: 'center',
  },
  joinTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 8,
  },
  joinDescription: {
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 16,
  },
  joinButton: {
    width: '100%',
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 16,
  },
  groupCard: {
    marginBottom: 12,
  },
  groupCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  groupCardInfo: {
    flex: 1,
  },
  groupCardName: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  groupCardMembers: {
    fontSize: 14,
  },
  leaderboardContainer: {
    marginBottom: 20,
  },
  userPositionCard: {
    marginBottom: 24,
    alignItems: 'center',
  },
  userPositionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  userPositionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginLeft: 8,
  },
  userPositionRank: {
    fontSize: 36,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  userPositionMinutes: {
    fontSize: 14,
  },
  leaderboardCard: {
    marginBottom: 20,
  },
  leaderboardRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5E5',
  },
  rankContainer: {
    width: 40,
    alignItems: 'center',
  },
  rankText: {
    fontSize: 16,
    fontWeight: '600',
  },
  userInfo: {
    flex: 1,
    marginLeft: 12,
  },
  userName: {
    fontSize: 16,
    fontWeight: '500',
  },
  userMinutes: {
    fontSize: 16,
    fontWeight: '600',
  },
  modalOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalCard: {
    width: '100%',
    maxWidth: 300,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 8,
  },
  modalDescription: {
    fontSize: 14,
    marginBottom: 20,
  },
  codeInput: {
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    marginBottom: 20,
  },
  modalButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  modalButton: {
    flex: 1,
    marginHorizontal: 4,
  },
}); 