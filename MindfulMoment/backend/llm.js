/**
 * LLM-based session evaluation for MindfulMoment.
 * Uses OpenAI API (set OPENAI_API_KEY) or returns a structured fallback when no key is set.
 */

const OPENAI_API_URL = 'https://api.openai.com/v1/chat/completions';

function buildSessionContext(session) {
  const parts = [];
  parts.push(`Type: ${session.type || 'focus'}`);
  parts.push(`Duration: ${session.duration || 0} minutes`);
  if (session.accomplishments) parts.push(`Accomplishments: ${session.accomplishments}`);
  if (session.notes) parts.push(`Notes: ${session.notes}`);
  if (session.distractions && session.distractions.length > 0) {
    parts.push('Distractions: ' + session.distractions.map(d => `${d.type}: ${d.description}`).join('; '));
  }
  if (session.goals && session.goals.length > 0) {
    parts.push('Goals: ' + session.goals.map(g => g.description + (g.completed ? ' (done)' : '')).join(', '));
  }
  if (session.typeMetrics) {
    const m = session.typeMetrics;
    if (m.distractionCount != null) parts.push(`Distraction count: ${m.distractionCount}`);
    if (m.tasksCompleted != null) parts.push(`Tasks completed: ${m.tasksCompleted}`);
    if (m.focusIntensity != null) parts.push(`Focus intensity (1-10): ${m.focusIntensity}`);
    if (m.safeZoneMinutes != null) parts.push(`Safe zone minutes: ${m.safeZoneMinutes}`);
  }
  if (session.moodBefore != null) parts.push(`Mood before (1-10): ${session.moodBefore}`);
  if (session.moodAfter != null) parts.push(`Mood after (1-10): ${session.moodAfter}`);
  return parts.join('\n');
}

function buildPrompt(sessions) {
  const isSingle = sessions.length === 1;
  const sessionContext = sessions.map((s, i) => {
    const header = isSingle ? 'Session' : `Session ${i + 1}`;
    return `${header}:\n${buildSessionContext(s)}\n`;
  }).join('\n');

  return `You are a supportive mindfulness and focus coach. Analyze the following focus session(s) and respond in JSON only, no other text.

${sessionContext}

Respond with a single JSON object with exactly these keys (use empty string if not applicable):
- summary: Brief 1-2 sentence overall summary of the session(s).
- whatHappened: What actually happened during the session(s) (activities, distractions, outcomes).
- impactOnUser: How this likely affected the user (productivity, mood, focus).
- whatCanBeImproved: Concrete, kind suggestions for what could be improved next time (environment, habits, handling distractions).
- whatWasImproved: What the user did well or what has improved compared to typical sessions (positive reinforcement).

Keep each value concise (1-3 sentences). Be encouraging and specific.`;
}

/**
 * Call OpenAI API to evaluate session(s). Returns structured evaluation or fallback.
 * @param {object[]} sessions - Array of focus session objects
 * @returns {Promise<{ summary, whatHappened, impactOnUser, whatCanBeImproved, whatWasImproved }>}
 */
async function evaluateWithOpenAI(sessions) {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey || !apiKey.trim()) {
    return getFallbackEvaluation(sessions);
  }

  const prompt = buildPrompt(sessions);
  const body = {
    model: process.env.OPENAI_MODEL || 'gpt-4o-mini',
    messages: [
      { role: 'system', content: 'You respond only with valid JSON. No markdown, no code block wrapper.' },
      { role: 'user', content: prompt }
    ],
    temperature: 0.5,
    max_tokens: 800
  };

  const res = await fetch(OPENAI_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`
    },
    body: JSON.stringify(body)
  });

  if (!res.ok) {
    const errText = await res.text();
    console.error('OpenAI API error:', res.status, errText);
    return getFallbackEvaluation(sessions);
  }

  const data = await res.json();
  const content = data.choices?.[0]?.message?.content?.trim();
  if (!content) return getFallbackEvaluation(sessions);

  try {
    const parsed = JSON.parse(content);
    return {
      summary: parsed.summary ?? '',
      whatHappened: parsed.whatHappened ?? '',
      impactOnUser: parsed.impactOnUser ?? '',
      whatCanBeImproved: parsed.whatCanBeImproved ?? '',
      whatWasImproved: parsed.whatWasImproved ?? '',
      generatedAt: new Date().toISOString()
    };
  } catch (e) {
    console.error('Failed to parse LLM JSON:', e.message);
    return getFallbackEvaluation(sessions);
  }
}

function getFallbackEvaluation(sessions) {
  const s = sessions[0];
  const hasAccomplishments = s?.accomplishments?.trim();
  const hasDistractions = s?.distractions?.length > 0;
  return {
    summary: sessions.length === 1
      ? `Session: ${s?.type || 'focus'}, ${s?.duration || 0} min. ${hasAccomplishments ? 'You noted accomplishments.' : ''} ${hasDistractions ? 'Some distractions were logged.' : ''}`
      : `${sessions.length} sessions reviewed.`,
    whatHappened: sessions.length === 1 && s
      ? `Duration ${s.duration || 0} min (${s.type || 'focus'}). ${hasAccomplishments ? `Accomplishments: ${s.accomplishments}.` : ''} ${hasDistractions ? `Distractions: ${(s.distractions || []).map(d => d.description || d.type).join(', ')}.` : ''}`
      : '',
    impactOnUser: 'Reflect on how this session felt. Setting aside time for focus is already a positive step.',
    whatCanBeImproved: hasDistractions
      ? 'Consider reducing or planning for the distractions you noted (e.g. phone away, quieter space).'
      : 'Keep tracking accomplishments and distractions to spot patterns over time.',
    whatWasImproved: hasAccomplishments
      ? 'You took time to note what you accomplished—that supports awareness and motivation.'
      : 'Completing a focus session is an improvement in itself.',
    generatedAt: new Date().toISOString()
  };
}

module.exports = {
  evaluateWithOpenAI,
  buildSessionContext,
  buildPrompt
};
