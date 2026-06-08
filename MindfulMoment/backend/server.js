require('dotenv').config();

const express = require('express');
const cors = require('cors');
const http = require('http');
const https = require('https');
const store = require('./store');
const llm = require('./llm');

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors({ origin: ['http://localhost:4200', 'http://127.0.0.1:4200'] }));
app.use(express.json());

function storageUserToUser(u) {
  if (!u) return null;
  const stats = u.stats || {};
  const todayStats = stats.todayStats || {};
  return {
    id: String(u.id),
    email: u.email || '',
    username: u.username || u.name || u.email?.split('@')[0] || '',
    firstName: u.firstName || u.name?.split(' ')[0] || '',
    lastName: u.lastName || u.name?.split(' ').slice(1).join(' ') || '',
    community: u.community || '',
    preferences: u.preferences || {},
    stats: {
      totalSessions: todayStats.sessionsCompleted || 0,
      totalMindfulMinutes: todayStats.totalMinutes || 0,
      totalSafetyAlerts: (stats.publicAwarenessStats && stats.publicAwarenessStats.safetyAlerts) || 0,
      totalSocialEngagements: 0,
      focusSessionStats: {},
      publicAwarenessStats: stats.publicAwarenessStats || {},
    },
    achievements: (u.achievements || []).map((a) => (typeof a === 'string' ? a : a.id)),
    badges: [],
    points: (u.achievements || []).reduce((sum, a) => sum + (a.points || 0), 0),
    level: 1,
    homeSettings: {},
    publicAwarenessSettings: {},
    joinDate: u.joinDate || new Date().toISOString(),
    lastActive: new Date().toISOString(),
  };
}

// User stats
app.put('/api/user/:userId/stats', (req, res) => {
  const { userId } = req.params;
  const stats = req.body;
  const updated = store.updateUserStats(userId, stats);
  if (updated === null) return res.status(404).json({ success: false, error: 'User not found' });
  res.json({ success: true, stats: updated });
});

// Focus sessions
app.post('/api/focus-sessions', (req, res) => {
  const session = req.body;
  const ok = store.addFocusSession(session);
  if (!ok) return res.status(400).json({ success: false, error: 'Invalid session or user not found' });
  res.json({ success: true });
});

app.put('/api/focus-sessions/:sessionId', (req, res) => {
  const { sessionId } = req.params;
  const ok = store.updateFocusSession(sessionId, req.body);
  if (!ok) return res.status(404).json({ success: false, error: 'Session not found' });
  res.json({ success: true });
});

// Community groups
app.get('/api/community/groups', (req, res) => {
  const groups = store.getCommunityGroups();
  res.json(groups);
});

app.post('/api/community/groups', (req, res) => {
  const group = store.createCommunityGroup(req.body);
  res.status(201).json({ success: true });
});

app.put('/api/community/groups/:id', (req, res) => {
  const { id } = req.params;
  const updated = store.updateCommunityGroup(id, req.body);
  if (!updated) return res.status(404).json({ success: false, error: 'Group not found' });
  res.json({ success: true });
});

app.delete('/api/community/groups/:groupId', (req, res) => {
  const { groupId } = req.params;
  const ok = store.deleteCommunityGroup(groupId);
  if (!ok) return res.status(404).json({ success: false, error: 'Group not found' });
  res.json({ success: true });
});

app.post('/api/community/groups/:groupId/join', (req, res) => {
  const { groupId } = req.params;
  const { userId } = req.body || {};
  if (!userId) return res.status(400).json({ success: false, error: 'userId required' });
  const ok = store.joinCommunityGroup(groupId, userId);
  if (!ok) return res.status(404).json({ success: false, error: 'Group not found' });
  res.json({ success: true });
});

app.post('/api/community/groups/:groupId/join-requests/:requestId/approve', (req, res) => {
  const { groupId, requestId } = req.params;
  const ok = store.approveJoinRequest(groupId, requestId);
  if (!ok) return res.status(404).json({ success: false, error: 'Not found' });
  res.json({ success: true });
});

app.post('/api/community/groups/:groupId/join-requests/:requestId/reject', (req, res) => {
  const { groupId, requestId } = req.params;
  const ok = store.rejectJoinRequest(groupId, requestId);
  if (!ok) return res.status(404).json({ success: false, error: 'Not found' });
  res.json({ success: true });
});

// Achievements
app.get('/api/achievements/:userId', (req, res) => {
  const { userId } = req.params;
  const achievements = store.getUserAchievements(userId);
  res.json(achievements);
});

// Public awareness (aggregate)
app.get('/api/public-awareness', (req, res) => {
  const data = store.getPublicAwarenessAggregate();
  res.json(data);
});

// Insights
app.get('/api/insights/:userId', (req, res) => {
  const { userId } = req.params;
  const period = req.query.period || 'week';
  const insights = store.getInsightsForUser(userId, period);
  res.json(insights || { period, totalSessions: 0, totalMinutes: 0, focusSessions: 0, mindfulTime: 0, socialInteractions: 0, phoneReduction: 0 });
});

// Session evaluation via LLM
app.post('/api/sessions/evaluate', async (req, res) => {
  try {
    const { userId, sessionIds, sessions: sessionsPayload, saveToSessions } = req.body || {};
    let sessions = [];

    if (Array.isArray(sessionsPayload) && sessionsPayload.length > 0) {
      sessions = sessionsPayload;
    } else if (userId && Array.isArray(sessionIds) && sessionIds.length > 0) {
      const all = store.getFocusSessionsByUserId(userId);
      sessions = all.filter((s) => sessionIds.includes(s.id));
    }

    if (sessions.length === 0) {
      return res.status(400).json({ success: false, error: 'No sessions provided or found' });
    }

    const evaluation = await llm.evaluateWithOpenAI(sessions);

    if (saveToSessions === true && sessions.length === 1 && sessions[0].id) {
      store.updateFocusSession(sessions[0].id, { llmEvaluation: evaluation });
    }

    res.json({ success: true, evaluation });
  } catch (err) {
    console.error('Session evaluate error:', err);
    res.status(500).json({ success: false, error: err.message || 'Evaluation failed' });
  }
});

// Location (placeholder)
app.get('/api/location', (req, res) => {
  res.json({});
});

// --- LTA DataMall (shared) ---
const LTA_HOST = 'datamall2.mytransport.sg';

/**
 * GET path must start with /ltaodataservice/...
 * @returns {Promise<object>} Parsed JSON body on HTTP 200
 */
function ltaDatamallGet(pathnameAndSearch) {
  return new Promise((resolve, reject) => {
    const apiKey = process.env.LTA_ACCOUNT_KEY;
    if (!apiKey) {
      const err = new Error('LTA_ACCOUNT_KEY not set');
      err.ltaNotConfigured = true;
      return reject(err);
    }
    const opts = {
      hostname: LTA_HOST,
      port: 443,
      path: pathnameAndSearch,
      method: 'GET',
      headers: { AccountKey: apiKey }
    };
    const proxyReq = https.request(opts, (proxyRes) => {
      let body = '';
      proxyRes.on('data', (chunk) => { body += chunk; });
      proxyRes.on('end', () => {
        const statusCode = proxyRes.statusCode;
        let data = {};
        if (body) {
          try {
            data = JSON.parse(body);
          } catch {
            if (statusCode === 200) {
              return reject(new Error('Invalid LTA response (not JSON)'));
            }
          }
        }
        if (statusCode !== 200) {
          let msg = data?.message || data?.error || 'LTA request failed';
          if (statusCode === 401) {
            msg =
              'LTA 401 Unauthorized: AccountKey was rejected. Open LTA DataMall → "Request for API Access" (https://datamall.lta.gov.sg/content/datamall/en.html), sign in or register, then copy your Account Key into backend/.env as LTA_ACCOUNT_KEY=... (no quotes, no spaces around the value).';
          }
          const err = new Error(msg);
          err.statusCode = statusCode >= 400 ? statusCode : 502;
          err.body = data;
          return reject(err);
        }
        resolve(data);
      });
    });
    proxyReq.on('error', reject);
    proxyReq.end();
  });
}

// Bus arrivals (LTA DataMall proxy)
app.get('/api/bus/arrivals', (req, res) => {
  const busStopCode = req.query.BusStopCode;
  if (!busStopCode || String(busStopCode).trim() === '') {
    return res.status(400).json({ success: false, error: 'BusStopCode is required' });
  }
  const params = new URLSearchParams();
  params.set('BusStopCode', String(busStopCode).trim());
  const serviceNo = req.query.ServiceNo;
  if (serviceNo && String(serviceNo).trim() !== '') {
    params.set('ServiceNo', String(serviceNo).trim());
  }
  const path = `/ltaodataservice/BusArrivalv2?${params.toString()}`;
  ltaDatamallGet(path)
    .then((data) => res.json(data))
    .catch((err) => {
      if (err.ltaNotConfigured) {
        return res.status(503).json({ success: false, error: 'Bus arrivals not configured' });
      }
      console.error('Bus arrivals proxy error:', err);
      const code = err.statusCode && err.statusCode >= 400 ? err.statusCode : 500;
      res.status(code).json({ success: false, error: err.message || 'Unable to load bus arrivals' });
    });
});

// Bus stop lookup (search by name / road / code; cached server-side)
const BUS_STOPS_TTL_MS = 24 * 60 * 60 * 1000;
let busStopsCache = null;
let busStopsCacheAt = 0;
let busStopsLoadPromise = null;

function loadAllBusStopsFromLta() {
  const all = [];
  let skip = 0;
  const pageSize = 500;
  const step = async () => {
    const data = await ltaDatamallGet(`/ltaodataservice/BusStops?$skip=${skip}`);
    const batch = Array.isArray(data.value)
      ? data.value
      : Array.isArray(data.Value)
        ? data.Value
        : [];
    all.push(...batch);
    if (batch.length < pageSize) return all;
    skip += pageSize;
    return step();
  };
  return step();
}

function getAllBusStopsCached(forceRefresh) {
  if (forceRefresh) {
    busStopsCache = null;
    busStopsCacheAt = 0;
  }
  const now = Date.now();
  if (busStopsCache && now - busStopsCacheAt < BUS_STOPS_TTL_MS) {
    return Promise.resolve(busStopsCache);
  }
  if (busStopsLoadPromise) return busStopsLoadPromise;
  busStopsLoadPromise = loadAllBusStopsFromLta()
    .then((rows) => {
      busStopsCache = rows;
      busStopsCacheAt = Date.now();
      return rows;
    })
    .finally(() => {
      busStopsLoadPromise = null;
    });
  return busStopsLoadPromise;
}

app.get('/api/bus/stops/search', (req, res) => {
  const q = String(req.query.q || '').trim().toLowerCase();
  if (!process.env.LTA_ACCOUNT_KEY) {
    return res.status(503).json({ success: false, error: 'Bus stop search not configured' });
  }
  if (q.length < 2) {
    return res.json({ matches: [] });
  }
  const forceRefresh = req.query.refresh === '1' || req.query.refresh === 'true';
  getAllBusStopsCached(forceRefresh)
    .then((all) => {
      const matches = all
        .filter((s) => {
          const code = (s.BusStopCode && String(s.BusStopCode).toLowerCase()) || '';
          const desc = (s.Description && String(s.Description).toLowerCase()) || '';
          const road = (s.RoadName && String(s.RoadName).toLowerCase()) || '';
          return code.includes(q) || desc.includes(q) || road.includes(q);
        })
        .slice(0, 40)
        .map((s) => ({
          BusStopCode: s.BusStopCode,
          RoadName: s.RoadName || '',
          Description: s.Description || ''
        }));
      res.json({ matches });
    })
    .catch((err) => {
      if (err.ltaNotConfigured) {
        return res.status(503).json({ success: false, error: 'Bus stop search not configured' });
      }
      console.error('Bus stops search error:', err);
      res.status(500).json({ success: false, error: err.message || 'Stop search failed' });
    });
});

// Auth: update user profile
app.put('/api/auth/user/:id', (req, res) => {
  const { id } = req.params;
  const userData = req.body;
  const user = store.updateUserProfile(id, userData);
  if (!user) return res.status(404).json({ success: false, error: 'User not found' });
  res.json({ success: true, user: storageUserToUser(user) });
});

const server = app.listen(PORT, () => {
  console.log(`MindfulMoment API running at http://localhost:${PORT}`);
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`Port ${PORT} is already in use. Stop the other process (e.g. another backend) or set PORT to a different number.`);
    process.exit(1);
  }
  throw err;
});
