import AsyncStorage from '@react-native-async-storage/async-storage';
import { notificationService } from './NotificationService';
import { locationService } from './LocationService';
import { focusSessionService } from './FocusSessionService';

export interface CommunityGroup {
  id: string;
  name: string;
  code: string;
  type: 'school' | 'workplace' | 'neighborhood' | 'public';
  memberCount: number;
  totalMindfulMinutes: number;
  currentChallenge?: CommunityChallenge;
  createdAt: Date;
}

export interface CommunityChallenge {
  id: string;
  title: string;
  description: string;
  goal: number; // mindful minutes
  currentProgress: number;
  startDate: Date;
  endDate: Date;
  isActive: boolean;
  participants: number;
}

export interface Badge {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: 'safety' | 'mindfulness' | 'community' | 'achievement';
  unlockedAt?: Date;
  progress?: number;
  maxProgress?: number;
}

export interface Reward {
  id: string;
  name: string;
  description: string;
  pointsCost: number;
  type: 'voucher' | 'discount' | 'badge' | 'feature';
  partner?: string;
  location?: string;
  isAvailable: boolean;
  redeemedAt?: Date;
}

export interface UserProgress {
  totalPoints: number;
  mindfulMinutes: number;
  focusSessions: number;
  badges: string[];
  currentStreak: number;
  longestStreak: number;
  groupContributions: Record<string, number>;
}

// Predefined badges
const PREDEFINED_BADGES: Badge[] = [
  {
    id: 'first_focus',
    name: 'First Steps',
    description: 'Complete your first focus session',
    icon: '🌱',
    category: 'mindfulness',
    maxProgress: 1,
  },
  {
    id: 'safe_commuter',
    name: 'Safe Commuter',
    description: 'Complete 10 focus sessions during commutes',
    icon: '🚇',
    category: 'safety',
    maxProgress: 10,
  },
  {
    id: 'park_explorer',
    name: 'Park Explorer',
    description: 'Complete focus sessions in 5 different public spaces',
    icon: '🌳',
    category: 'mindfulness',
    maxProgress: 5,
  },
  {
    id: 'streak_master',
    name: 'Streak Master',
    description: 'Maintain a 7-day focus session streak',
    icon: '🔥',
    category: 'achievement',
    maxProgress: 7,
  },
  {
    id: 'community_champion',
    name: 'Community Champion',
    description: 'Contribute 100 mindful minutes to group challenges',
    icon: '🏆',
    category: 'community',
    maxProgress: 100,
  },
  {
    id: 'safety_guardian',
    name: 'Safety Guardian',
    description: 'Acknowledge 20 safety reminders',
    icon: '🛡️',
    category: 'safety',
    maxProgress: 20,
  },
  {
    id: 'mindful_minutes_100',
    name: 'Century Club',
    description: 'Accumulate 100 mindful minutes',
    icon: '💯',
    category: 'achievement',
    maxProgress: 100,
  },
  {
    id: 'mindful_minutes_500',
    name: 'Half Millennium',
    description: 'Accumulate 500 mindful minutes',
    icon: '🌟',
    category: 'achievement',
    maxProgress: 500,
  },
  {
    id: 'mindful_minutes_1000',
    name: 'Mindful Master',
    description: 'Accumulate 1000 mindful minutes',
    icon: '👑',
    category: 'achievement',
    maxProgress: 1000,
  },
];

// Sample rewards (partner businesses)
const SAMPLE_REWARDS: Reward[] = [
  {
    id: 'coffee_voucher',
    name: 'Free Coffee',
    description: 'Free coffee at participating cafes near MRT stations',
    pointsCost: 50,
    type: 'voucher',
    partner: 'Local Cafes',
    location: 'MRT Stations',
    isAvailable: true,
  },
  {
    id: 'park_discount',
    name: 'Park Entry Discount',
    description: '20% off entry to Gardens by the Bay',
    pointsCost: 100,
    type: 'discount',
    partner: 'Gardens by the Bay',
    location: 'Marina Bay',
    isAvailable: true,
  },
  {
    id: 'museum_pass',
    name: 'Museum Pass',
    description: 'Free entry to National Museum of Singapore',
    pointsCost: 200,
    type: 'voucher',
    partner: 'National Museum',
    location: 'Bras Basah',
    isAvailable: true,
  },
  {
    id: 'transit_credit',
    name: 'Transit Credit',
    description: '$5 credit for public transport',
    pointsCost: 150,
    type: 'voucher',
    partner: 'LTA',
    location: 'Singapore',
    isAvailable: true,
  },
];

class CommunityService {
  private userProgress: UserProgress;
  private badges: Badge[];
  private rewards: Reward[];
  private joinedGroups: CommunityGroup[];
  private isInitialized = false;

  constructor() {
    this.userProgress = {
      totalPoints: 0,
      mindfulMinutes: 0,
      focusSessions: 0,
      badges: [],
      currentStreak: 0,
      longestStreak: 0,
      groupContributions: {},
    };
    this.badges = [...PREDEFINED_BADGES];
    this.rewards = [...SAMPLE_REWARDS];
    this.joinedGroups = [];
  }

  async initialize(): Promise<void> {
    await this.loadUserProgress();
    await this.loadBadges();
    await this.loadRewards();
    await this.loadJoinedGroups();
    this.isInitialized = true;
  }

  // User Progress Management
  async addMindfulMinutes(minutes: number, location?: string): Promise<void> {
    this.userProgress.mindfulMinutes += minutes;
    this.userProgress.totalPoints += minutes * 2; // 2 points per mindful minute

    // Update group contributions if in a group
    if (location) {
      this.userProgress.groupContributions[location] = 
        (this.userProgress.groupContributions[location] || 0) + minutes;
    }

    await this.checkAndAwardBadges();
    await this.saveUserProgress();
  }

  async addFocusSession(): Promise<void> {
    this.userProgress.focusSessions += 1;
    this.userProgress.totalPoints += 10; // 10 points per focus session

    await this.checkAndAwardBadges();
    await this.saveUserProgress();
  }

  async updateStreak(streak: number): Promise<void> {
    this.userProgress.currentStreak = streak;
    this.userProgress.longestStreak = Math.max(this.userProgress.longestStreak, streak);

    await this.checkAndAwardBadges();
    await this.saveUserProgress();
  }

  getUserProgress(): UserProgress {
    return { ...this.userProgress };
  }

  // Badge Management
  async checkAndAwardBadges(): Promise<Badge[]> {
    const newlyAwarded: Badge[] = [];

    for (const badge of this.badges) {
      if (this.userProgress.badges.includes(badge.id)) continue;

      let shouldAward = false;
      let progress = 0;

      switch (badge.id) {
        case 'first_focus':
          shouldAward = this.userProgress.focusSessions >= 1;
          progress = this.userProgress.focusSessions;
          break;

        case 'safe_commuter':
          // This would need location data to be more accurate
          shouldAward = this.userProgress.focusSessions >= 10;
          progress = this.userProgress.focusSessions;
          break;

        case 'streak_master':
          shouldAward = this.userProgress.currentStreak >= 7;
          progress = this.userProgress.currentStreak;
          break;

        case 'community_champion':
          const totalGroupMinutes = Object.values(this.userProgress.groupContributions).reduce((sum, minutes) => sum + minutes, 0);
          shouldAward = totalGroupMinutes >= 100;
          progress = totalGroupMinutes;
          break;

        case 'mindful_minutes_100':
          shouldAward = this.userProgress.mindfulMinutes >= 100;
          progress = this.userProgress.mindfulMinutes;
          break;

        case 'mindful_minutes_500':
          shouldAward = this.userProgress.mindfulMinutes >= 500;
          progress = this.userProgress.mindfulMinutes;
          break;

        case 'mindful_minutes_1000':
          shouldAward = this.userProgress.mindfulMinutes >= 1000;
          progress = this.userProgress.mindfulMinutes;
          break;
      }

      if (shouldAward) {
        badge.unlockedAt = new Date();
        badge.progress = progress;
        this.userProgress.badges.push(badge.id);
        newlyAwarded.push(badge);

        // Award bonus points for new badges
        this.userProgress.totalPoints += 50;
      }
    }

    if (newlyAwarded.length > 0) {
      await this.saveBadges();
      await this.saveUserProgress();
    }

    return newlyAwarded;
  }

  getBadges(): Badge[] {
    return this.badges.map(badge => ({
      ...badge,
      unlockedAt: this.userProgress.badges.includes(badge.id) ? badge.unlockedAt : undefined,
    }));
  }

  getUnlockedBadges(): Badge[] {
    return this.badges.filter(badge => this.userProgress.badges.includes(badge.id));
  }

  // Reward Management
  async redeemReward(rewardId: string): Promise<Reward | null> {
    const reward = this.rewards.find(r => r.id === rewardId);
    if (!reward || !reward.isAvailable || this.userProgress.totalPoints < reward.pointsCost) {
      return null;
    }

    // Deduct points
    this.userProgress.totalPoints -= reward.pointsCost;
    reward.redeemedAt = new Date();

    await this.saveRewards();
    await this.saveUserProgress();

    return reward;
  }

  getAvailableRewards(): Reward[] {
    return this.rewards.filter(reward => 
      reward.isAvailable && this.userProgress.totalPoints >= reward.pointsCost
    );
  }

  getRedeemedRewards(): Reward[] {
    return this.rewards.filter(reward => reward.redeemedAt);
  }

  // Community Groups
  async joinGroup(groupCode: string): Promise<CommunityGroup | null> {
    // In a real app, this would validate against a backend
    // For now, we'll create a mock group
    const group: CommunityGroup = {
      id: `group_${Date.now()}`,
      name: `Group ${groupCode.toUpperCase()}`,
      code: groupCode,
      type: 'public',
      memberCount: Math.floor(Math.random() * 50) + 10,
      totalMindfulMinutes: Math.floor(Math.random() * 1000) + 500,
      createdAt: new Date(),
    };

    this.joinedGroups.push(group);
    await this.saveJoinedGroups();

    // Send welcome notification
    await notificationService.sendCommunityUpdate(
      `Welcome to ${group.name}! Start contributing mindful minutes to group challenges.`
    );

    return group;
  }

  async leaveGroup(groupId: string): Promise<void> {
    this.joinedGroups = this.joinedGroups.filter(group => group.id !== groupId);
    await this.saveJoinedGroups();
  }

  getJoinedGroups(): CommunityGroup[] {
    return [...this.joinedGroups];
  }

  async createGroupChallenge(
    groupId: string,
    title: string,
    goal: number,
    duration: number // days
  ): Promise<CommunityChallenge | null> {
    const group = this.joinedGroups.find(g => g.id === groupId);
    if (!group) return null;

    const challenge: CommunityChallenge = {
      id: `challenge_${Date.now()}`,
      title,
      description: `Collect ${goal} mindful minutes as a group`,
      goal,
      currentProgress: 0,
      startDate: new Date(),
      endDate: new Date(Date.now() + duration * 24 * 60 * 60 * 1000),
      isActive: true,
      participants: group.memberCount,
    };

    group.currentChallenge = challenge;
    await this.saveJoinedGroups();

    return challenge;
  }

  async contributeToGroupChallenge(groupId: string, mindfulMinutes: number): Promise<void> {
    const group = this.joinedGroups.find(g => g.id === groupId);
    if (!group || !group.currentChallenge) return;

    group.currentChallenge.currentProgress += mindfulMinutes;
    group.totalMindfulMinutes += mindfulMinutes;

    // Check if challenge is completed
    if (group.currentChallenge.currentProgress >= group.currentChallenge.goal) {
      group.currentChallenge.isActive = false;
      
      // Award bonus points for completing group challenge
      this.userProgress.totalPoints += 100;
      
      await notificationService.sendCommunityUpdate(
        `🎉 ${group.name} completed the "${group.currentChallenge.title}" challenge!`
      );
    }

    await this.saveJoinedGroups();
    await this.saveUserProgress();
  }

  // Anonymous Community Features
  async getCommunityStats(): Promise<{
    totalUsers: number;
    totalMindfulMinutes: number;
    activeChallenges: number;
    topLocations: Array<{ name: string; minutes: number }>;
  }> {
    // In a real app, this would fetch from backend
    // For now, return mock data
    return {
      totalUsers: 15420,
      totalMindfulMinutes: 284750,
      activeChallenges: 156,
      topLocations: [
        { name: 'Orchard MRT', minutes: 12500 },
        { name: 'Raffles Place MRT', minutes: 11800 },
        { name: 'Marina Bay Sands', minutes: 8900 },
        { name: 'Gardens by the Bay', minutes: 7600 },
        { name: 'Bugis MRT', minutes: 7200 },
      ],
    };
  }

  async getNearbyEvents(): Promise<Array<{
    id: string;
    title: string;
    description: string;
    location: string;
    date: Date;
    participants: number;
    qrCode?: string;
  }>> {
    // In a real app, this would fetch from backend based on location
    const currentZone = locationService.getCurrentZone();
    
    const events = [
      {
        id: 'event_1',
        title: 'Mindful Walking Group',
        description: 'Join us for a phone-free walking session in the park',
        location: 'Gardens by the Bay',
        date: new Date(Date.now() + 2 * 60 * 60 * 1000), // 2 hours from now
        participants: 12,
      },
      {
        id: 'event_2',
        title: 'Board Game Night',
        description: 'Social board games without phones - old school fun!',
        location: 'Community Center',
        date: new Date(Date.now() + 24 * 60 * 60 * 1000), // Tomorrow
        participants: 8,
      },
    ];

    // Filter by location if available
    if (currentZone) {
      return events.filter(event => 
        event.location.toLowerCase().includes(currentZone.name.toLowerCase())
      );
    }

    return events;
  }

  // Data Persistence
  private async loadUserProgress(): Promise<void> {
    try {
      const progressData = await AsyncStorage.getItem('userProgress');
      if (progressData) {
        this.userProgress = { ...this.userProgress, ...JSON.parse(progressData) };
      }
    } catch (error) {
      console.error('Error loading user progress:', error);
    }
  }

  private async saveUserProgress(): Promise<void> {
    try {
      await AsyncStorage.setItem('userProgress', JSON.stringify(this.userProgress));
    } catch (error) {
      console.error('Error saving user progress:', error);
    }
  }

  private async loadBadges(): Promise<void> {
    try {
      const badgesData = await AsyncStorage.getItem('badges');
      if (badgesData) {
        this.badges = JSON.parse(badgesData).map((badge: any) => ({
          ...badge,
          unlockedAt: badge.unlockedAt ? new Date(badge.unlockedAt) : undefined,
        }));
      }
    } catch (error) {
      console.error('Error loading badges:', error);
    }
  }

  private async saveBadges(): Promise<void> {
    try {
      await AsyncStorage.setItem('badges', JSON.stringify(this.badges));
    } catch (error) {
      console.error('Error saving badges:', error);
    }
  }

  private async loadRewards(): Promise<void> {
    try {
      const rewardsData = await AsyncStorage.getItem('rewards');
      if (rewardsData) {
        this.rewards = JSON.parse(rewardsData).map((reward: any) => ({
          ...reward,
          redeemedAt: reward.redeemedAt ? new Date(reward.redeemedAt) : undefined,
        }));
      }
    } catch (error) {
      console.error('Error loading rewards:', error);
    }
  }

  private async saveRewards(): Promise<void> {
    try {
      await AsyncStorage.setItem('rewards', JSON.stringify(this.rewards));
    } catch (error) {
      console.error('Error saving rewards:', error);
    }
  }

  private async loadJoinedGroups(): Promise<void> {
    try {
      const groupsData = await AsyncStorage.getItem('joinedGroups');
      if (groupsData) {
        this.joinedGroups = JSON.parse(groupsData).map((group: any) => ({
          ...group,
          createdAt: new Date(group.createdAt),
          currentChallenge: group.currentChallenge ? {
            ...group.currentChallenge,
            startDate: new Date(group.currentChallenge.startDate),
            endDate: new Date(group.currentChallenge.endDate),
          } : undefined,
        }));
      }
    } catch (error) {
      console.error('Error loading joined groups:', error);
    }
  }

  private async saveJoinedGroups(): Promise<void> {
    try {
      await AsyncStorage.setItem('joinedGroups', JSON.stringify(this.joinedGroups));
    } catch (error) {
      console.error('Error saving joined groups:', error);
    }
  }

  async clearCommunityData(): Promise<void> {
    this.userProgress = {
      totalPoints: 0,
      mindfulMinutes: 0,
      focusSessions: 0,
      badges: [],
      currentStreak: 0,
      longestStreak: 0,
      groupContributions: {},
    };
    this.joinedGroups = [];
    
    await AsyncStorage.multiRemove([
      'userProgress',
      'badges',
      'rewards',
      'joinedGroups',
    ]);
  }
}

export const communityService = new CommunityService(); 