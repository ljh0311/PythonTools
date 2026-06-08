export interface CommunityGroup {
  id: string;
  name: string;
  description: string;
  category: GroupCategory;
  location: string;
  memberCount: number;
  maxMembers?: number;
  isPublic: boolean;
  tags: string[];
  icon: string;
  color: string;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  rules: GroupRule[];
  events: GroupEvent[];
  recentActivity: GroupActivity[];
  isJoined: boolean;
  joinDate?: string;
  adminIds: string[]; // Array of admin user IDs
  memberIds: string[]; // Array of member user IDs
  joinRequests?: JoinRequest[]; // Pending join requests
  requiresApproval: boolean; // Whether join requests need admin approval
}

export interface JoinRequest {
  id: string;
  userId: string;
  userName: string;
  userAvatar?: string;
  groupId: string;
  message?: string;
  requestedAt: string;
  status: JoinRequestStatus;
}

export enum JoinRequestStatus {
  PENDING = 'pending',
  APPROVED = 'approved',
  REJECTED = 'rejected'
}

export interface GroupRule {
  id: string;
  title: string;
  description: string;
  type: RuleType;
  isRequired: boolean;
}

export interface GroupEvent {
  id: string;
  title: string;
  description: string;
  date: string;
  time: string;
  location: string;
  maxParticipants?: number;
  currentParticipants: number;
  isJoined: boolean;
  organizer: string;
  category: EventCategory;
}

export interface GroupActivity {
  id: string;
  type: ActivityType;
  userId: string;
  userName: string;
  userAvatar?: string;
  description: string;
  timestamp: string;
  metadata?: any;
}

export enum GroupCategory {
  FOCUS = 'focus',
  MINDFULNESS = 'mindfulness',
  SAFETY = 'safety',
  WELLNESS = 'wellness',
  SOCIAL = 'social',
  LEARNING = 'learning',
  SUPPORT = 'support'
}

export enum RuleType {
  BEHAVIOR = 'behavior',
  PARTICIPATION = 'participation',
  CONTENT = 'content',
  SAFETY = 'safety'
}

export enum EventCategory {
  MEETUP = 'meetup',
  WORKSHOP = 'workshop',
  CHALLENGE = 'challenge',
  DISCUSSION = 'discussion',
  PRACTICE = 'practice'
}

export enum ActivityType {
  JOINED = 'joined',
  POSTED = 'posted',
  COMMENTED = 'commented',
  COMPLETED = 'completed',
  ACHIEVED = 'achieved',
  SHARED = 'shared'
}
