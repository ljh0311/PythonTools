const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, 'data');
const STORE_FILE = path.join(DATA_DIR, 'store.json');
const SEED_FILE = path.join(__dirname, '../mindful-moment-angular/src/assets/storage.json');

let data = { users: [], communityGroups: [], safetyTips: [], emergencyContacts: [] };

function ensureDataDir() {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
  }
}

function load() {
  ensureDataDir();
  if (fs.existsSync(STORE_FILE)) {
    try {
      const raw = fs.readFileSync(STORE_FILE, 'utf8');
      data = JSON.parse(raw);
      if (!Array.isArray(data.users)) data.users = [];
      if (!Array.isArray(data.communityGroups)) data.communityGroups = [];
      return;
    } catch (e) {
      console.warn('Store load failed:', e.message);
    }
  }
  if (fs.existsSync(SEED_FILE)) {
    try {
      const raw = fs.readFileSync(SEED_FILE, 'utf8');
      data = JSON.parse(raw);
      if (!Array.isArray(data.users)) data.users = [];
      if (!Array.isArray(data.communityGroups)) data.communityGroups = [];
      save();
      console.log('Seeded store from storage.json');
      return;
    } catch (e) {
      console.warn('Seed failed:', e.message);
    }
  }
  data = { users: [], communityGroups: [], safetyTips: [], emergencyContacts: [] };
  save();
}

function save() {
  ensureDataDir();
  fs.writeFileSync(STORE_FILE, JSON.stringify(data, null, 2), 'utf8');
}

load();

function getUserById(id) {
  const num = parseInt(id, 10);
  if (Number.isNaN(num)) return null;
  return data.users.find((u) => u.id === num) || null;
}

function getUserByEmail(email) {
  if (!email) return null;
  return data.users.find((u) => u.email.toLowerCase() === email.toLowerCase()) || null;
}

function getCommunityGroups() {
  return data.communityGroups || [];
}

function getFocusSessionsByUserId(userId) {
  const user = getUserById(userId);
  if (!user || !user.stats || !Array.isArray(user.stats.focusSessions)) return [];
  return user.stats.focusSessions;
}

function updateUserStats(userId, stats) {
  const user = getUserById(userId);
  if (!user) return null;
  if (!user.stats) user.stats = {};
  if (stats !== null && typeof stats === 'object') {
    if (stats.todayStats !== undefined) user.stats.todayStats = stats.todayStats;
    if (stats.publicAwarenessStats !== undefined) user.stats.publicAwarenessStats = stats.publicAwarenessStats;
    if (stats.focusSessionStats !== undefined) user.stats.focusSessionStats = stats.focusSessionStats;
    if (stats.focusSessions !== undefined) user.stats.focusSessions = stats.focusSessions;
    for (const key of Object.keys(stats)) {
      if (!['todayStats', 'publicAwarenessStats', 'focusSessionStats', 'focusSessions'].includes(key)) {
        user.stats[key] = stats[key];
      }
    }
  }
  save();
  return user.stats;
}

function addFocusSession(session) {
  const userId = session.userId ? parseInt(session.userId, 10) : null;
  if (userId == null || Number.isNaN(userId)) return false;
  const user = getUserById(userId);
  if (!user) return false;
  if (!user.stats) user.stats = {};
  if (!user.stats.focusSessions) user.stats.focusSessions = [];
  const fullSession = {
    id: session.id || 'sess-' + Date.now(),
    userId,
    startTime: session.startTime || new Date().toISOString(),
    endTime: session.endTime,
    duration: session.duration || 0,
    location: session.location || null,
    type: session.type || 'focus',
    status: session.status || 'active',
    goals: session.goals || [],
    achievements: session.achievements || [],
    accomplishments: session.accomplishments,
    distractions: session.distractions || [],
    socialInteractions: session.socialInteractions || [],
    phoneUsageReduction: session.phoneUsageReduction || 0,
    mindfulMoments: session.mindfulMoments || [],
    typeMetrics: session.typeMetrics || null,
    createdAt: session.createdAt || new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    notes: session.notes,
    moodBefore: session.moodBefore,
    moodAfter: session.moodAfter,
    llmEvaluation: session.llmEvaluation || null,
  };
  user.stats.focusSessions.push(fullSession);
  save();
  return true;
}

function updateFocusSession(sessionId, updates) {
  for (const user of data.users) {
    if (!user.stats || !Array.isArray(user.stats.focusSessions)) continue;
    const idx = user.stats.focusSessions.findIndex((s) => s.id === sessionId);
    if (idx !== -1) {
      user.stats.focusSessions[idx] = { ...user.stats.focusSessions[idx], ...updates, updatedAt: new Date().toISOString() };
      save();
      return true;
    }
  }
  return false;
}

function getCommunityGroupById(id) {
  return (data.communityGroups || []).find((g) => g.id === id) || null;
}

function createCommunityGroup(group) {
  const id = group.id || 'group-' + Date.now();
  const now = new Date().toISOString();
  const newGroup = {
    id,
    name: group.name || '',
    description: group.description || '',
    category: group.category || 'focus',
    location: group.location || '',
    memberCount: group.memberCount != null ? group.memberCount : 0,
    maxMembers: group.maxMembers,
    isPublic: group.isPublic !== false,
    tags: Array.isArray(group.tags) ? group.tags : [],
    icon: group.icon || 'fas fa-users',
    color: group.color || '#4A90E2',
    createdBy: group.createdBy || '',
    createdAt: group.createdAt || now,
    updatedAt: now,
    rules: Array.isArray(group.rules) ? group.rules : [],
    events: Array.isArray(group.events) ? group.events : [],
    recentActivity: Array.isArray(group.recentActivity) ? group.recentActivity : [],
    isJoined: false,
    adminIds: Array.isArray(group.adminIds) ? group.adminIds : [group.createdBy || ''].filter(Boolean),
    memberIds: Array.isArray(group.memberIds) ? group.memberIds : [],
    joinRequests: Array.isArray(group.joinRequests) ? group.joinRequests : [],
    requiresApproval: group.requiresApproval === true,
  };
  data.communityGroups.push(newGroup);
  save();
  return newGroup;
}

function updateCommunityGroup(id, group) {
  const idx = (data.communityGroups || []).findIndex((g) => g.id === id);
  if (idx === -1) return null;
  data.communityGroups[idx] = { ...data.communityGroups[idx], ...group, id, updatedAt: new Date().toISOString() };
  save();
  return data.communityGroups[idx];
}

function deleteCommunityGroup(id) {
  const idx = (data.communityGroups || []).findIndex((g) => g.id === id);
  if (idx === -1) return false;
  data.communityGroups.splice(idx, 1);
  save();
  return true;
}

function joinCommunityGroup(groupId, userId) {
  const g = getCommunityGroupById(groupId);
  if (!g) return false;
  const uid = String(userId);
  if (!g.memberIds) g.memberIds = [];
  if (g.memberIds.includes(uid)) return true;
  if (g.requiresApproval) {
    if (!g.joinRequests) g.joinRequests = [];
    g.joinRequests.push({
      id: 'req-' + Date.now(),
      userId: uid,
      userName: '',
      groupId,
      requestedAt: new Date().toISOString(),
      status: 'pending',
    });
  } else {
    g.memberIds.push(uid);
    g.memberCount = (g.memberCount || 0) + 1;
  }
  save();
  return true;
}

function approveJoinRequest(groupId, requestId) {
  const g = getCommunityGroupById(groupId);
  if (!g || !g.joinRequests) return false;
  const req = g.joinRequests.find((r) => r.id === requestId);
  if (!req || req.status !== 'pending') return false;
  req.status = 'approved';
  if (!g.memberIds) g.memberIds = [];
  if (!g.memberIds.includes(req.userId)) {
    g.memberIds.push(req.userId);
    g.memberCount = (g.memberCount || 0) + 1;
  }
  save();
  return true;
}

function rejectJoinRequest(groupId, requestId) {
  const g = getCommunityGroupById(groupId);
  if (!g || !g.joinRequests) return false;
  const req = g.joinRequests.find((r) => r.id === requestId);
  if (!req || req.status !== 'pending') return false;
  req.status = 'rejected';
  save();
  return true;
}

function getUserAchievements(userId) {
  const user = getUserById(userId);
  return (user && user.achievements) ? user.achievements : [];
}

function updateUserProfile(userId, userData) {
  const user = getUserById(userId);
  if (!user) return null;
  const allowed = ['name', 'firstName', 'lastName', 'username', 'community', 'preferences', 'dateOfBirth', 'phone'];
  for (const key of allowed) {
    if (userData[key] !== undefined) user[key] = userData[key];
  }
  save();
  return user;
}

function getPublicAwarenessAggregate() {
  let totalPublicTime = 0, safetyAlerts = 0, socialPrompts = 0, mindfulScoreSum = 0, count = 0;
  const locationScores = { publicSpaces: 0, mrtStations: 0, shoppingCenters: 0 };
  for (const u of data.users) {
    const s = u.stats && u.stats.publicAwarenessStats;
    if (!s) continue;
    totalPublicTime += s.totalPublicTime || 0;
    safetyAlerts += s.safetyAlerts || 0;
    socialPrompts += s.socialPrompts || 0;
    mindfulScoreSum += s.mindfulScore || 0;
    count++;
    const ls = s.locationScores || {};
    locationScores.publicSpaces += ls.publicSpaces || 0;
    locationScores.mrtStations += ls.mrtStations || 0;
    locationScores.shoppingCenters += ls.shoppingCenters || 0;
  }
  return {
    totalPublicTime,
    safetyAlerts,
    socialPrompts,
    mindfulScore: count ? Math.round(mindfulScoreSum / count) : 0,
    locationScores: {
      publicSpaces: count ? Math.round(locationScores.publicSpaces / count) : 0,
      mrtStations: count ? Math.round(locationScores.mrtStations / count) : 0,
      shoppingCenters: count ? Math.round(locationScores.shoppingCenters / count) : 0,
    },
  };
}

function getInsightsForUser(userId, period) {
  const user = getUserById(userId);
  if (!user || !user.stats) return null;
  const sessions = user.stats.focusSessions || [];
  const now = new Date();
  const cutoff = new Date(now);
  if (period === 'month') cutoff.setMonth(cutoff.getMonth() - 1);
  else cutoff.setDate(cutoff.getDate() - 7);
  const filtered = sessions.filter((s) => new Date(s.startTime) >= cutoff);
  const totalMinutes = filtered.reduce((sum, s) => sum + (s.duration || 0), 0);
  return {
    period,
    totalSessions: filtered.length,
    totalMinutes,
    focusSessions: filtered.length,
    mindfulTime: totalMinutes,
    socialInteractions: filtered.reduce((sum, s) => sum + (s.socialInteractions && s.socialInteractions.length || 0), 0),
    phoneReduction: filtered.reduce((sum, s) => sum + (s.phoneUsageReduction || 0), 0),
  };
}

module.exports = {
  load,
  save,
  getUserById,
  getUserByEmail,
  getCommunityGroups,
  getCommunityGroupById,
  getFocusSessionsByUserId,
  updateUserStats,
  addFocusSession,
  updateFocusSession,
  createCommunityGroup,
  updateCommunityGroup,
  deleteCommunityGroup,
  joinCommunityGroup,
  approveJoinRequest,
  rejectJoinRequest,
  getUserAchievements,
  updateUserProfile,
  getPublicAwarenessAggregate,
  getInsightsForUser,
  get data() { return data; },
};
