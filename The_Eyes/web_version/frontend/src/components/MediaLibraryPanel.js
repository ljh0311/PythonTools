import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Tabs,
  Tab,
  Grid,
  Chip,
  Button,
  Collapse,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Checkbox,
  Tooltip,
  TextField,
  Stack,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import PhotoLibraryIcon from '@mui/icons-material/PhotoLibrary';
import MovieIcon from '@mui/icons-material/Movie';
import RefreshIcon from '@mui/icons-material/Refresh';
import DeleteIcon from '@mui/icons-material/Delete';
import DeleteSweepIcon from '@mui/icons-material/DeleteSweep';
import PersonIcon from '@mui/icons-material/Person';
import PersonOffIcon from '@mui/icons-material/PersonOff';
import FilterListIcon from '@mui/icons-material/FilterList';
import {
  apiUrl,
  fetchJson,
  deleteMediaFile,
  deleteMotionSession,
  deleteMediaBulk,
} from '../apiConfig';
import { MediaLibrarySkeleton } from './skeletons/SurveillanceSkeletons';

function mediaFileUrl(relativePath) {
  if (!relativePath) return null;
  return apiUrl(`/api/media/file?path=${encodeURIComponent(relativePath)}`);
}

function formatTime(ts) {
  if (!ts) return '—';
  const d = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString();
}

function sessionTimestamp(session) {
  if (session?.started_at) return session.started_at;
  const match = String(session?.session_id || '').match(/^(\d{8})_(\d{6})/);
  if (!match) return 0;
  const date = match[1];
  const time = match[2];
  const iso = `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}T${time.slice(0, 2)}:${time.slice(2, 4)}:${time.slice(4, 6)}`;
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? 0 : parsed.getTime() / 1000;
}

function localDateKey(ts) {
  const d = new Date(ts * 1000);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function localMinutesOfDay(ts) {
  const d = new Date(ts * 1000);
  return d.getHours() * 60 + d.getMinutes();
}

function hhmmToMinutes(value) {
  if (!value) return null;
  const [h, m] = value.split(':').map((part) => Number(part));
  if (Number.isNaN(h) || Number.isNaN(m)) return null;
  return h * 60 + m;
}

function matchesDateRange(ts, dateFrom, dateTo) {
  if (!dateFrom && !dateTo) return true;
  if (!ts) return false;
  const key = localDateKey(ts);
  if (dateFrom && key < dateFrom) return false;
  if (dateTo && key > dateTo) return false;
  return true;
}

function matchesTimeRange(ts, timeFrom, timeTo) {
  const fromMin = hhmmToMinutes(timeFrom);
  const toMin = hhmmToMinutes(timeTo);
  if (fromMin === null && toMin === null) return true;
  if (!ts) return false;
  const minutes = localMinutesOfDay(ts);
  if (fromMin !== null && toMin !== null) {
    if (fromMin <= toMin) return minutes >= fromMin && minutes <= toMin;
    return minutes >= fromMin || minutes <= toMin;
  }
  if (fromMin !== null) return minutes >= fromMin;
  return minutes <= toMin;
}

function buildSessionPersonIndex(sightings, persons) {
  const personsById = Object.fromEntries((persons || []).map((p) => [p.id, p]));
  const index = new Map();

  const addPerson = (key, personId) => {
    if (!key || !personId) return;
    const bucket = index.get(key) || new Map();
    const person = personsById[personId];
    bucket.set(personId, { id: personId, name: person?.name || personId });
    index.set(key, bucket);
  };

  (sightings || []).forEach((row) => {
    const personId = row.person_id;
    if (row.session_id) {
      addPerson(`${row.camera_id}::${row.session_id}`, personId);
    }
    const path = row.snapshot_path || '';
    const match = path.match(/_evt_(\d{8}_\d{6}_[a-f0-9]+)_/i);
    if (match) {
      addPerson(`${row.camera_id}::${match[1]}`, personId);
    }
    if (path) {
      addPerson(`path::${path}`, personId);
    }
  });

  return index;
}

function resolveSessionPeople(session, personIndex) {
  const peopleMap = new Map();
  (session.face_detection?.people || []).forEach((p) => peopleMap.set(p.id, p));

  const sessionKey = `${session.camera_id}::${session.session_id}`;
  personIndex.get(sessionKey)?.forEach((p, id) => peopleMap.set(id, p));
  [session.first_snapshot, session.last_snapshot].forEach((path) => {
    personIndex.get(`path::${path}`)?.forEach((p, id) => peopleMap.set(id, p));
  });

  return [...peopleMap.values()];
}

function sessionMatchesPerson(session, personFilter, personIndex) {
  if (!personFilter) return true;
  const people = resolveSessionPeople(session, personIndex);
  if (personFilter === '__no_face__') {
    return people.length === 0;
  }
  return people.some((p) => p.id === personFilter);
}

function recordingTimestamp(recording) {
  return recording?.modified_at || 0;
}

function sessionKey(session) {
  return `${session.camera_id}::${session.session_id}`;
}

function ConfirmDeleteDialog({ open, title, message, onCancel, onConfirm, busy }) {
  return (
    <Dialog open={open} onClose={busy ? undefined : onCancel} maxWidth="xs" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <DialogContentText>{message}</DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
        <Button color="error" variant="contained" onClick={onConfirm} disabled={busy}>
          {busy ? 'Deleting…' : 'Delete'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function MotionSessionCard({
  session,
  onDelete,
  faceRecognitionEnabled = false,
  personIndex,
  checked = false,
  onToggleCheck,
}) {
  const firstUrl = mediaFileUrl(session.first_snapshot);
  const lastUrl = mediaFileUrl(session.last_snapshot);
  const detectedPeople = resolveSessionPeople(session, personIndex || new Map());
  const showFaceInfo = faceRecognitionEnabled || detectedPeople.length > 0;

  return (
    <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 2, height: '100%' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, minWidth: 0, flex: 1 }}>
          <Checkbox
            size="small"
            checked={checked}
            onChange={() => onToggleCheck?.(sessionKey(session))}
            inputProps={{ 'aria-label': `Select event ${session.session_id}` }}
            sx={{ p: 0.25 }}
          />
          <Typography variant="subtitle2" fontWeight={600} noWrap>
            {session.camera_id}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Chip
            size="small"
            label={session.complete ? 'Paired' : 'Partial'}
            color={session.complete ? 'success' : 'warning'}
            variant="outlined"
          />
          <Tooltip title="Delete session snapshots">
            <IconButton
              size="small"
              color="error"
              aria-label="Delete motion session"
              onClick={() => onDelete(session)}
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.5 }}>
        Event {session.session_id}
      </Typography>
      {showFaceInfo && (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 1 }}>
          {detectedPeople.length > 0 ? (
            detectedPeople.map((person) => (
              <Chip
                key={person.id}
                size="small"
                icon={<PersonIcon />}
                label={person.name}
                color="info"
                variant="outlined"
              />
            ))
          ) : (
            <Chip
              size="small"
              icon={<PersonOffIcon />}
              label="No face detected"
              variant="outlined"
            />
          )}
        </Box>
      )}
      <Grid container spacing={1}>
        <Grid item xs={6}>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.5 }}>
            Motion started
          </Typography>
          {firstUrl ? (
            <Box
              component="img"
              src={firstUrl}
              alt="Motion started"
              sx={{
                width: '100%',
                aspectRatio: '4/3',
                objectFit: 'cover',
                borderRadius: 1,
                bgcolor: 'action.hover',
              }}
            />
          ) : (
            <Box
              sx={{
                aspectRatio: '4/3',
                bgcolor: 'action.hover',
                borderRadius: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Typography variant="caption" color="text.secondary">
                No image
              </Typography>
            </Box>
          )}
        </Grid>
        <Grid item xs={6}>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.5 }}>
            Motion ended
          </Typography>
          {lastUrl ? (
            <Box
              component="img"
              src={lastUrl}
              alt="Motion ended"
              sx={{
                width: '100%',
                aspectRatio: '4/3',
                objectFit: 'cover',
                borderRadius: 1,
                bgcolor: 'action.hover',
              }}
            />
          ) : (
            <Box
              sx={{
                aspectRatio: '4/3',
                bgcolor: 'action.hover',
                borderRadius: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Typography variant="caption" color="text.secondary">
                Waiting…
              </Typography>
            </Box>
          )}
        </Grid>
      </Grid>
    </Paper>
  );
}

function RecordingRow({ recording, selected, onSelect, checked, onToggleCheck, onDelete }) {
  const url = mediaFileUrl(recording.path);
  const label = recording.motion_triggered ? 'Motion' : 'Continuous';
  const [playbackError, setPlaybackError] = useState(false);

  useEffect(() => {
    setPlaybackError(false);
  }, [recording.path]);

  return (
    <Paper
      variant="outlined"
      sx={{
        p: 1.5,
        borderRadius: 2,
        cursor: 'pointer',
        borderColor: selected ? 'primary.main' : 'divider',
        bgcolor: selected ? 'action.selected' : 'background.paper',
      }}
      onClick={() => onSelect(recording)}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0, flex: 1 }}>
          <Checkbox
            size="small"
            checked={checked}
            onClick={(e) => e.stopPropagation()}
            onChange={(e) => {
              e.stopPropagation();
              onToggleCheck(recording.path);
            }}
            inputProps={{ 'aria-label': `Select ${recording.filename}` }}
          />
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="body2" fontWeight={600} noWrap>
              {recording.filename}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {recording.camera_id} · {recording.size_mb} MB · {formatTime(recording.modified_at)}
            </Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Chip size="small" label={label} variant="outlined" />
          <Tooltip title="Delete recording">
            <IconButton
              size="small"
              color="error"
              aria-label="Delete recording"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(recording);
              }}
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>
      {selected && url && (
        <Box sx={{ mt: 1.5 }} onClick={(e) => e.stopPropagation()}>
          {!playbackError ? (
            <Box
              component="video"
              src={url}
              controls
              preload="metadata"
              type="video/mp4"
              onError={() => setPlaybackError(true)}
              sx={{ width: '100%', maxHeight: 320, borderRadius: 1, bgcolor: 'black' }}
            />
          ) : (
            <Alert severity="warning" sx={{ borderRadius: 1 }}>
              This recording uses an older codec (MPEG-4) that browsers cannot play. New recordings
              use H.264. You can{' '}
              <Button size="small" href={url} download={recording.filename}>
                download
              </Button>{' '}
              to play locally.
            </Alert>
          )}
        </Box>
      )}
    </Paper>
  );
}

export default function MediaLibraryPanel({ apiReachable = true, mediaApiSupported = false, facesApiSupported = false }) {
  const [expanded, setExpanded] = useState(true);
  const [tab, setTab] = useState(0);
  const [sessions, setSessions] = useState([]);
  const [recordings, setRecordings] = useState([]);
  const [selectedRecording, setSelectedRecording] = useState(null);
  const [selectedPaths, setSelectedPaths] = useState(new Set());
  const [selectedSessionKeys, setSelectedSessionKeys] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [olderThanDays, setOlderThanDays] = useState(30);
  const [confirm, setConfirm] = useState(null);
  const [faceRecognitionEnabled, setFaceRecognitionEnabled] = useState(false);
  const [knownPersons, setKnownPersons] = useState([]);
  const [faceSightings, setFaceSightings] = useState([]);
  const [filterPerson, setFilterPerson] = useState('');
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');
  const [filterTimeFrom, setFilterTimeFrom] = useState('');
  const [filterTimeTo, setFilterTimeTo] = useState('');

  const filtersActive = Boolean(
    filterPerson || filterDateFrom || filterDateTo || filterTimeFrom || filterTimeTo
  );

  const clearFilters = () => {
    setFilterPerson('');
    setFilterDateFrom('');
    setFilterDateTo('');
    setFilterTimeFrom('');
    setFilterTimeTo('');
  };

  const loadMedia = useCallback(async () => {
    if (!apiReachable || !mediaApiSupported) return;
    setLoading(true);
    setError(null);
    try {
      const [sessionsData, recordingsData] = await Promise.all([
        fetchJson('/api/media/motion-sessions?limit=100'),
        fetchJson('/api/media/recordings?limit=100'),
      ]);
      setSessions(sessionsData?.sessions || []);
      setFaceRecognitionEnabled(Boolean(sessionsData?.face_recognition_enabled));
      setRecordings(recordingsData?.recordings || []);
      if (apiReachable && facesApiSupported) {
        try {
          const [personsData, sightingsData] = await Promise.all([
            fetchJson('/api/faces/persons'),
            fetchJson('/api/faces/sightings?limit=500'),
          ]);
          setKnownPersons(personsData?.persons || []);
          setFaceSightings(sightingsData?.sightings || []);
          if (personsData.enabled) setFaceRecognitionEnabled(true);
        } catch {
          setKnownPersons([]);
          setFaceSightings([]);
        }
      }
      setSelectedPaths((prev) => {
        const paths = new Set((recordingsData?.recordings || []).map((r) => r.path));
        return new Set([...prev].filter((p) => paths.has(p)));
      });
      setSelectedSessionKeys((prev) => {
        const keys = new Set((sessionsData?.sessions || []).map(sessionKey));
        return new Set([...prev].filter((k) => keys.has(k)));
      });
    } catch (err) {
      setError(err.message || 'Failed to load media');
    } finally {
      setLoading(false);
    }
  }, [apiReachable, mediaApiSupported, facesApiSupported]);

  useEffect(() => {
    loadMedia();
    if (!apiReachable) return undefined;
    const id = setInterval(loadMedia, 15000);
    return () => clearInterval(id);
  }, [apiReachable, loadMedia]);

  const personIndex = useMemo(
    () => buildSessionPersonIndex(faceSightings, knownPersons),
    [faceSightings, knownPersons]
  );

  const filteredSessions = useMemo(
    () =>
      sessions.filter((session) => {
        const ts = sessionTimestamp(session);
        if (!matchesDateRange(ts, filterDateFrom, filterDateTo)) return false;
        if (!matchesTimeRange(ts, filterTimeFrom, filterTimeTo)) return false;
        if (!sessionMatchesPerson(session, filterPerson, personIndex)) return false;
        return true;
      }),
    [
      sessions,
      filterPerson,
      filterDateFrom,
      filterDateTo,
      filterTimeFrom,
      filterTimeTo,
      personIndex,
    ]
  );

  const filteredRecordings = useMemo(
    () =>
      recordings.filter((recording) => {
        const ts = recordingTimestamp(recording);
        if (!matchesDateRange(ts, filterDateFrom, filterDateTo)) return false;
        if (!matchesTimeRange(ts, filterTimeFrom, filterTimeTo)) return false;
        return true;
      }),
    [recordings, filterDateFrom, filterDateTo, filterTimeFrom, filterTimeTo]
  );

  const toggleRecordingCheck = (path) => {
    setSelectedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const toggleSessionCheck = (key) => {
    setSelectedSessionKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const allFilteredSessionsSelected =
    filteredSessions.length > 0 &&
    filteredSessions.every((s) => selectedSessionKeys.has(sessionKey(s)));

  const allFilteredRecordingsSelected =
    filteredRecordings.length > 0 &&
    filteredRecordings.every((r) => selectedPaths.has(r.path));

  const filterScopeLabel = useMemo(() => {
    if (filterPerson === '__no_face__') return 'no face detected';
    if (filterPerson) {
      const person = knownPersons.find((p) => p.id === filterPerson);
      return person?.name || 'selected person';
    }
    if (filtersActive) return 'filtered';
    return 'shown';
  }, [filterPerson, knownPersons, filtersActive]);

  const toggleSelectFilteredSessions = () => {
    const filteredKeys = filteredSessions.map(sessionKey);
    setSelectedSessionKeys((prev) => {
      const next = new Set(prev);
      if (allFilteredSessionsSelected) {
        filteredKeys.forEach((key) => next.delete(key));
      } else {
        filteredKeys.forEach((key) => next.add(key));
      }
      return next;
    });
  };

  const clearSessionSelection = () => setSelectedSessionKeys(new Set());

  const toggleSelectFilteredRecordings = () => {
    const filteredPaths = filteredRecordings.map((r) => r.path);
    setSelectedPaths((prev) => {
      const next = new Set(prev);
      if (allFilteredRecordingsSelected) {
        filteredPaths.forEach((path) => next.delete(path));
      } else {
        filteredPaths.forEach((path) => next.add(path));
      }
      return next;
    });
  };

  const clearRecordingSelection = () => setSelectedPaths(new Set());

  const runDelete = async (action) => {
    setDeleteBusy(true);
    setError(null);
    try {
      await action();
      setConfirm(null);
      if (selectedRecording && confirm?.recording?.path === selectedRecording.path) {
        setSelectedRecording(null);
      }
      await loadMedia();
    } catch (err) {
      setError(err.message || 'Delete failed');
    } finally {
      setDeleteBusy(false);
    }
  };

  const confirmDeleteRecording = (recording) => {
    setConfirm({
      title: 'Delete recording?',
      message: `Permanently delete "${recording.filename}"? This cannot be undone.`,
      onConfirm: () => runDelete(() => deleteMediaFile(recording.path)),
      recording,
    });
  };

  const confirmDeleteSession = (session) => {
    setConfirm({
      title: 'Delete motion session?',
      message: `Delete snapshots for ${session.camera_id} event ${session.session_id}?`,
      onConfirm: () =>
        runDelete(() => deleteMotionSession(session.session_id, session.camera_id)),
    });
  };

  const confirmDeleteSelected = () => {
    const paths = [...selectedPaths];
    if (!paths.length) return;
    setConfirm({
      title: 'Delete selected recordings?',
      message: `Permanently delete ${paths.length} recording(s)? This cannot be undone.`,
      onConfirm: () =>
        runDelete(async () => {
          await deleteMediaBulk({ paths });
          setSelectedPaths(new Set());
        }),
    });
  };

  const confirmDeleteSelectedSessions = () => {
    const keys = [...selectedSessionKeys];
    if (!keys.length) return;
    setConfirm({
      title: 'Delete selected motion events?',
      message: `Permanently delete ${keys.length} motion event(s)? This cannot be undone.`,
      onConfirm: () =>
        runDelete(async () => {
          const toDelete = sessions.filter((s) => selectedSessionKeys.has(sessionKey(s)));
          await Promise.all(
            toDelete.map((s) => deleteMotionSession(s.session_id, s.camera_id))
          );
          setSelectedSessionKeys(new Set());
        }),
    });
  };

  const confirmDeleteOlder = () => {
    const scope = tab === 0 ? 'motion snapshots' : 'recordings';
    const includeSnapshots = tab === 0;
    const includeRecordings = tab === 1;
    setConfirm({
      title: `Delete older ${scope}?`,
      message: `Delete all ${scope} older than ${olderThanDays} days? This cannot be undone.`,
      onConfirm: () =>
        runDelete(() =>
          deleteMediaBulk({
            olderThanDays,
            includeRecordings,
            includeSnapshots,
          })
        ),
    });
  };

  return (
    <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, overflow: 'hidden' }}>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          p: 1.5,
          bgcolor: 'background.paper',
        }}
      >
        <Box
          role="button"
          tabIndex={0}
          onClick={() => setExpanded(!expanded)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              setExpanded(!expanded);
            }
          }}
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            flex: 1,
            cursor: 'pointer',
            '&:hover': { opacity: 0.85 },
          }}
          aria-expanded={expanded}
        >
          <PhotoLibraryIcon color="action" />
          <Typography variant="subtitle1" fontWeight={600}>
            Media library
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <IconButton
            size="small"
            aria-label="Refresh media"
            onClick={loadMedia}
            disabled={!apiReachable || !mediaApiSupported}
          >
            <RefreshIcon fontSize="small" />
          </IconButton>
          <IconButton
            size="small"
            aria-label={expanded ? 'Collapse media library' : 'Expand media library'}
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Box>
      </Box>

      <Collapse in={expanded}>
        <Box sx={{ px: 2, pb: 2 }}>
          {!apiReachable ? (
            <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
              Connect to the API to browse snapshots and recordings.
            </Typography>
          ) : !mediaApiSupported ? (
            <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
              Media library needs a backend restart. Stop and run <code>npm run start:all</code> again.
            </Typography>
          ) : (
            <>
              <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
                <Tab icon={<PhotoLibraryIcon />} iconPosition="start" label="Motion events" />
                <Tab icon={<MovieIcon />} iconPosition="start" label="Recordings" />
              </Tabs>

              <Box
                sx={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  alignItems: 'center',
                  gap: 1,
                  mb: 2,
                  p: 1,
                  borderRadius: 1,
                  bgcolor: 'action.hover',
                }}
              >
                <DeleteSweepIcon fontSize="small" color="action" />
                <Typography variant="caption" color="text.secondary">
                  Data management
                </Typography>
                <FormControl size="small" sx={{ minWidth: 120 }}>
                  <InputLabel id="older-than-label">Older than</InputLabel>
                  <Select
                    labelId="older-than-label"
                    label="Older than"
                    value={olderThanDays}
                    onChange={(e) => setOlderThanDays(e.target.value)}
                  >
                    <MenuItem value={7}>7 days</MenuItem>
                    <MenuItem value={30}>30 days</MenuItem>
                    <MenuItem value={90}>90 days</MenuItem>
                  </Select>
                </FormControl>
                <Button
                  size="small"
                  color="error"
                  variant="outlined"
                  startIcon={<DeleteSweepIcon />}
                  onClick={confirmDeleteOlder}
                  disabled={deleteBusy}
                >
                  Delete old
                </Button>
                {tab === 0 ? (
                  <>
                    <Button
                      size="small"
                      onClick={toggleSelectFilteredSessions}
                      disabled={!filteredSessions.length}
                    >
                      {allFilteredSessionsSelected ? 'Deselect filtered' : 'Select filtered'}
                    </Button>
                    <Button
                      size="small"
                      onClick={clearSessionSelection}
                      disabled={selectedSessionKeys.size === 0}
                    >
                      Select none
                    </Button>
                    <Button
                      size="small"
                      color="error"
                      variant="outlined"
                      startIcon={<DeleteIcon />}
                      onClick={confirmDeleteSelectedSessions}
                      disabled={deleteBusy || selectedSessionKeys.size === 0}
                    >
                      Delete selected ({selectedSessionKeys.size})
                    </Button>
                  </>
                ) : (
                  <>
                    <Button
                      size="small"
                      onClick={toggleSelectFilteredRecordings}
                      disabled={!filteredRecordings.length}
                    >
                      {allFilteredRecordingsSelected ? 'Deselect filtered' : 'Select filtered'}
                    </Button>
                    <Button
                      size="small"
                      onClick={clearRecordingSelection}
                      disabled={selectedPaths.size === 0}
                    >
                      Select none
                    </Button>
                    <Button
                      size="small"
                      color="error"
                      variant="outlined"
                      startIcon={<DeleteIcon />}
                      onClick={confirmDeleteSelected}
                      disabled={deleteBusy || selectedPaths.size === 0}
                    >
                      Delete selected ({selectedPaths.size})
                    </Button>
                  </>
                )}
                {filtersActive && (
                  <Typography variant="caption" color="text.secondary">
                    Filter: {filterScopeLabel}
                  </Typography>
                )}
              </Box>

              <Box
                sx={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  alignItems: 'flex-end',
                  gap: 1,
                  mb: 2,
                  p: 1,
                  borderRadius: 1,
                  border: '1px solid',
                  borderColor: 'divider',
                }}
              >
                <FilterListIcon fontSize="small" color="action" sx={{ mb: 1 }} />
                <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'center', mr: 0.5 }}>
                  Filter
                </Typography>
                {tab === 0 && (
                  <FormControl size="small" sx={{ minWidth: 160 }}>
                    <InputLabel id="filter-person-label">Person</InputLabel>
                    <Select
                      labelId="filter-person-label"
                      label="Person"
                      value={filterPerson}
                      onChange={(e) => setFilterPerson(e.target.value)}
                      disabled={!facesApiSupported}
                    >
                      <MenuItem value="">All people</MenuItem>
                      <MenuItem value="__no_face__">No face detected</MenuItem>
                      {knownPersons.map((p) => (
                        <MenuItem key={p.id} value={p.id}>
                          {p.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                )}
                <TextField
                  size="small"
                  label="From date"
                  type="date"
                  value={filterDateFrom}
                  onChange={(e) => setFilterDateFrom(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  sx={{ width: 150 }}
                />
                <TextField
                  size="small"
                  label="To date"
                  type="date"
                  value={filterDateTo}
                  onChange={(e) => setFilterDateTo(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  sx={{ width: 150 }}
                />
                <TextField
                  size="small"
                  label="From time"
                  type="time"
                  value={filterTimeFrom}
                  onChange={(e) => setFilterTimeFrom(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  sx={{ width: 130 }}
                />
                <TextField
                  size="small"
                  label="To time"
                  type="time"
                  value={filterTimeTo}
                  onChange={(e) => setFilterTimeTo(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  sx={{ width: 130 }}
                />
                <Button size="small" onClick={clearFilters} disabled={!filtersActive}>
                  Clear
                </Button>
                <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }}>
                  {tab === 0
                    ? `Showing ${filteredSessions.length} of ${sessions.length}`
                    : `Showing ${filteredRecordings.length} of ${recordings.length}`}
                </Typography>
              </Box>

              <Box
                sx={{
                  maxHeight: 'min(60vh, 520px)',
                  overflowY: 'auto',
                  pr: 0.5,
                  '&::-webkit-scrollbar': { width: 8 },
                  '&::-webkit-scrollbar-thumb': {
                    borderRadius: 4,
                    bgcolor: 'action.disabled',
                  },
                }}
              >
                {loading && sessions.length === 0 && recordings.length === 0 ? (
                  <MediaLibrarySkeleton cards={6} />
                ) : error ? (
                  <Box sx={{ textAlign: 'center', py: 2 }}>
                    <Typography variant="body2" color="error" sx={{ mb: 1 }}>
                      {error}
                    </Typography>
                    <Button size="small" onClick={loadMedia}>
                      Retry
                    </Button>
                  </Box>
                ) : tab === 0 ? (
                  sessions.length === 0 ? (
                    <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
                      No motion snapshots yet. Enable motion detection and wait for activity.
                    </Typography>
                  ) : filteredSessions.length === 0 ? (
                    <Stack spacing={1} sx={{ py: 2, textAlign: 'center' }}>
                      <Typography variant="body2" color="text.secondary">
                        No events match your filters.
                      </Typography>
                      <Button size="small" onClick={clearFilters}>
                        Clear filters
                      </Button>
                    </Stack>
                  ) : (
                    <Grid container spacing={2}>
                      {filteredSessions.map((session) => (
                        <Grid item xs={12} sm={6} md={4} key={`${session.camera_id}-${session.session_id}`}>
                          <MotionSessionCard
                            session={session}
                            onDelete={confirmDeleteSession}
                            faceRecognitionEnabled={faceRecognitionEnabled}
                            personIndex={personIndex}
                            checked={selectedSessionKeys.has(sessionKey(session))}
                            onToggleCheck={toggleSessionCheck}
                          />
                        </Grid>
                      ))}
                    </Grid>
                  )
                ) : recordings.length === 0 ? (
                  <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
                    No recordings yet. Start recording from the controls above.
                  </Typography>
                ) : filteredRecordings.length === 0 ? (
                  <Stack spacing={1} sx={{ py: 2, textAlign: 'center' }}>
                    <Typography variant="body2" color="text.secondary">
                      No recordings match your filters.
                    </Typography>
                    <Button size="small" onClick={clearFilters}>
                      Clear filters
                    </Button>
                  </Stack>
                ) : (
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {filteredRecordings.map((rec) => (
                      <RecordingRow
                        key={rec.path}
                        recording={rec}
                        selected={selectedRecording?.path === rec.path}
                        onSelect={setSelectedRecording}
                        checked={selectedPaths.has(rec.path)}
                        onToggleCheck={toggleRecordingCheck}
                        onDelete={confirmDeleteRecording}
                      />
                    ))}
                  </Box>
                )}
              </Box>
            </>
          )}
        </Box>
      </Collapse>

      <ConfirmDeleteDialog
        open={Boolean(confirm)}
        title={confirm?.title || ''}
        message={confirm?.message || ''}
        onCancel={() => !deleteBusy && setConfirm(null)}
        onConfirm={() => confirm?.onConfirm?.()}
        busy={deleteBusy}
      />
    </Paper>
  );
}
