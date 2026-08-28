import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Box,
  Button,
  Dialog,
  DialogContent,
  DialogTitle,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
  DialogActions,
  Chip,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import CloseIcon from '@mui/icons-material/Close';
import MergeTypeIcon from '@mui/icons-material/MergeType';
import { KnownPeopleSkeleton } from './skeletons/SurveillanceSkeletons';
import { apiUrl, fetchJson } from '../apiConfig';

function pairKey(pair) {
  return [pair.source_person_id, pair.target_person_id].sort().join('::');
}

function mediaFileUrl(relativePath) {
  if (!relativePath) return null;
  return apiUrl(`/api/media/file?path=${encodeURIComponent(relativePath)}`);
}

function timeLabel(ts) {
  if (!ts) return 'Never';
  const d = new Date(ts * 1000);
  if (Number.isNaN(d.getTime())) return 'Unknown';
  return d.toLocaleString();
}

/** Crop snapshot to face bbox for thumbnail display. */
function FaceThumb({ snapshotPath, bbox, size = 88, onClick }) {
  const url = mediaFileUrl(snapshotPath);
  const [natural, setNatural] = useState(null);

  if (!url) {
    return (
      <Box
        sx={{
          width: size,
          height: size,
          borderRadius: 1,
          bgcolor: 'action.hover',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Typography variant="caption" color="text.secondary">
          No image
        </Typography>
      </Box>
    );
  }

  const hasBbox = Array.isArray(bbox) && bbox.length >= 4 && natural;
  const [bx, by, bw, bh] = hasBbox ? bbox : [0, 0, natural?.w || 1, natural?.h || 1];
  const scale = hasBbox ? Math.max(size / Math.max(bw, 1), size / Math.max(bh, 1)) : 1;
  const imgW = hasBbox ? natural.w * scale : '100%';
  const imgH = hasBbox ? natural.h * scale : '100%';

  return (
    <Box
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
      sx={{
        width: size,
        height: size,
        borderRadius: 1,
        overflow: 'hidden',
        bgcolor: 'action.hover',
        position: 'relative',
        flexShrink: 0,
        cursor: onClick ? 'pointer' : 'default',
        border: '1px solid',
        borderColor: 'divider',
        '&:hover': onClick ? { borderColor: 'primary.main' } : undefined,
      }}
    >
      <Box
        component="img"
        src={url}
        alt=""
        onLoad={(e) => setNatural({ w: e.target.naturalWidth, h: e.target.naturalHeight })}
        sx={
          hasBbox
            ? {
                position: 'absolute',
                width: imgW,
                height: imgH,
                left: -bx * scale,
                top: -by * scale,
                maxWidth: 'none',
              }
            : {
                width: '100%',
                height: '100%',
                objectFit: 'cover',
              }
        }
      />
    </Box>
  );
}

function postJson(path, body) {
  return fetch(apiUrl(path), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(async (response) => {
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    return data;
  });
}

function putJson(path, body) {
  return fetch(apiUrl(path), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(async (response) => {
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    return data;
  });
}

export default function KnownPeoplePanel({ apiReachable = false }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [enabled, setEnabled] = useState(false);
  const [runtimeReady, setRuntimeReady] = useState(false);
  const [persons, setPersons] = useState([]);
  const [selectedPersonId, setSelectedPersonId] = useState('');
  const [sightings, setSightings] = useState([]);
  const [renameText, setRenameText] = useState('');
  const [mergeSource, setMergeSource] = useState('');
  const [mergeTarget, setMergeTarget] = useState('');
  const [enrollPath, setEnrollPath] = useState('');
  const [previewSighting, setPreviewSighting] = useState(null);
  const [similarPairs, setSimilarPairs] = useState([]);
  const [dismissedPairKeys, setDismissedPairKeys] = useState(new Set());
  const [mergeAllOpen, setMergeAllOpen] = useState(false);
  const [mergeBusy, setMergeBusy] = useState(false);

  const selectedPerson = useMemo(
    () => persons.find((p) => p.id === selectedPersonId) || null,
    [persons, selectedPersonId]
  );

  const loadPeople = useCallback(async () => {
    if (!apiReachable) return;
    setLoading(true);
    setError(null);
    try {
      const [personsData, sightingsData] = await Promise.all([
        fetchJson('/api/faces/persons'),
        fetchJson('/api/faces/sightings?limit=200'),
      ]);
      setEnabled(Boolean(personsData.enabled));
      setRuntimeReady(Boolean(personsData.runtime_ready));
      const rows = personsData.persons || [];
      setPersons(rows);
      if (!selectedPersonId && rows.length) {
        setSelectedPersonId(rows[0].id);
      }
      setSightings(sightingsData.sightings || []);
      try {
        const similarData = await fetchJson('/api/faces/similar-pairs');
        setSimilarPairs(similarData?.pairs || []);
      } catch {
        setSimilarPairs([]);
      }
    } catch (err) {
      setError(err.message || 'Failed to load known people');
    } finally {
      setLoading(false);
    }
  }, [apiReachable, selectedPersonId]);

  useEffect(() => {
    loadPeople();
  }, [loadPeople]);

  const filteredSightings = useMemo(
    () => sightings.filter((s) => !selectedPersonId || s.person_id === selectedPersonId),
    [sightings, selectedPersonId]
  );

  const representativeSighting = filteredSightings[0] || null;

  const visibleSimilarPairs = useMemo(
    () => similarPairs.filter((pair) => !dismissedPairKeys.has(pairKey(pair))),
    [similarPairs, dismissedPairKeys]
  );

  const mergePair = async (pair) => {
    setMergeBusy(true);
    setError(null);
    try {
      await postJson('/api/faces/persons/merge', {
        source_person_id: pair.source_person_id,
        target_person_id: pair.target_person_id,
      });
      setSelectedPersonId(pair.target_person_id);
      setDismissedPairKeys((prev) => new Set([...prev, pairKey(pair)]));
      await loadPeople();
    } catch (err) {
      setError(err.message || 'Merge failed');
    } finally {
      setMergeBusy(false);
    }
  };

  const mergeAllSimilar = async () => {
    setMergeBusy(true);
    setError(null);
    try {
      await postJson('/api/faces/persons/merge-similar', {});
      setMergeAllOpen(false);
      await loadPeople();
    } catch (err) {
      setError(err.message || 'Merge all failed');
    } finally {
      setMergeBusy(false);
    }
  };

  const renamePerson = async () => {
    if (!selectedPerson || !renameText.trim()) return;
    await putJson(`/api/faces/persons/${encodeURIComponent(selectedPerson.id)}`, {
      name: renameText.trim(),
    });
    setRenameText('');
    await loadPeople();
  };

  const mergePeople = async () => {
    if (!mergeSource || !mergeTarget || mergeSource === mergeTarget) return;
    await postJson('/api/faces/persons/merge', {
      source_person_id: mergeSource,
      target_person_id: mergeTarget,
    });
    setMergeSource('');
    setSelectedPersonId(mergeTarget);
    await loadPeople();
  };

  const reassignSighting = async (sightingId, targetPersonId) => {
    await postJson('/api/faces/sightings/reassign', {
      sighting_id: sightingId,
      target_person_id: targetPersonId || null,
      create_person_name: targetPersonId ? null : 'Unknown',
    });
    await loadPeople();
  };

  const enrollSnapshot = async () => {
    if (!enrollPath.trim()) return;
    await postJson('/api/faces/enroll', {
      snapshot_path: enrollPath.trim(),
      camera_id: 'manual',
      person_id: selectedPersonId || null,
    });
    setEnrollPath('');
    await loadPeople();
  };

  return (
    <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
        <Typography variant="subtitle1" fontWeight={600}>
          Known people
        </Typography>
        <IconButton size="small" onClick={loadPeople} disabled={loading}>
          <RefreshIcon fontSize="small" />
        </IconButton>
      </Box>

      {!apiReachable ? (
        <Typography variant="body2" color="text.secondary">
          Connect to API to manage people memory.
        </Typography>
      ) : loading && persons.length === 0 ? (
        <KnownPeopleSkeleton />
      ) : error ? (
        <Typography variant="body2" color="error">
          {error}
        </Typography>
      ) : !enabled ? (
        <Typography variant="body2" color="text.secondary">
          Face recognition is disabled in config (`security.face_recognition.enabled`).
        </Typography>
      ) : !runtimeReady ? (
        <Typography variant="body2" color="text.secondary">
          Face runtime is still initializing models.
        </Typography>
      ) : (
        <>
          <Box
            sx={{
              display: 'grid',
              gap: 1.5,
              gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
              mb: 2,
            }}
          >
            <FormControl size="small" fullWidth>
              <InputLabel>Person</InputLabel>
              <Select
                value={selectedPersonId}
                label="Person"
                onChange={(e) => setSelectedPersonId(e.target.value)}
              >
                {persons.map((p) => (
                  <MenuItem key={p.id} value={p.id}>
                    {p.name} ({p.sightings})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'center' }}>
              Last seen: {timeLabel(selectedPerson?.last_seen_at)}
            </Typography>
          </Box>

          {visibleSimilarPairs.length > 0 && (
            <Paper variant="outlined" sx={{ p: 1.5, mb: 2, bgcolor: 'action.hover' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="subtitle2" fontWeight={600}>
                  Looks like the same person
                </Typography>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<MergeTypeIcon />}
                  disabled={mergeBusy}
                  onClick={() => setMergeAllOpen(true)}
                >
                  Merge all ({visibleSimilarPairs.length})
                </Button>
              </Box>
              <Stack spacing={1}>
                {visibleSimilarPairs.map((pair) => (
                  <Paper key={pairKey(pair)} variant="outlined" sx={{ p: 1, display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
                    <FaceThumb
                      snapshotPath={pair.source?.sample_snapshot}
                      bbox={pair.source?.sample_bbox}
                      size={56}
                    />
                    <Typography variant="body2" fontWeight={600}>
                      {pair.source?.name}
                    </Typography>
                    <Chip size="small" label={`${pair.similarity_pct}% match`} color="warning" variant="outlined" />
                    <FaceThumb
                      snapshotPath={pair.target?.sample_snapshot}
                      bbox={pair.target?.sample_bbox}
                      size={56}
                    />
                    <Typography variant="body2" fontWeight={600}>
                      {pair.target?.name}
                    </Typography>
                    <Box sx={{ ml: 'auto', display: 'flex', gap: 0.5 }}>
                      <Button
                        size="small"
                        variant="contained"
                        disabled={mergeBusy}
                        onClick={() => mergePair(pair)}
                      >
                        Merge into {pair.target?.name}
                      </Button>
                      <Button
                        size="small"
                        onClick={() => setDismissedPairKeys((prev) => new Set([...prev, pairKey(pair)]))}
                      >
                        Dismiss
                      </Button>
                    </Box>
                  </Paper>
                ))}
              </Stack>
            </Paper>
          )}

          {selectedPerson && (
            <Paper
              variant="outlined"
              sx={{
                p: 2,
                mb: 2,
                display: 'flex',
                alignItems: 'center',
                gap: 2,
                bgcolor: 'action.hover',
              }}
            >
              <FaceThumb
                snapshotPath={representativeSighting?.snapshot_path || selectedPerson.sample_snapshot}
                bbox={representativeSighting?.bbox}
                size={120}
                onClick={
                  representativeSighting
                    ? () => setPreviewSighting(representativeSighting)
                    : undefined
                }
              />
              <Box sx={{ minWidth: 0 }}>
                <Typography variant="h6" fontWeight={600}>
                  {selectedPerson.name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {filteredSightings.length} photo{filteredSightings.length === 1 ? '' : 's'} classified
                  under this person
                </Typography>
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                  Last seen {timeLabel(selectedPerson.last_seen_at)}
                </Typography>
              </Box>
            </Paper>
          )}

          <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
            <TextField
              size="small"
              label="Rename person"
              value={renameText}
              onChange={(e) => setRenameText(e.target.value)}
              fullWidth
            />
            <Button variant="outlined" onClick={renamePerson}>
              Save
            </Button>
          </Stack>

          <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel>Merge from</InputLabel>
              <Select value={mergeSource} label="Merge from" onChange={(e) => setMergeSource(e.target.value)}>
                {persons
                  .filter((p) => p.id !== mergeTarget)
                  .map((p) => (
                    <MenuItem key={p.id} value={p.id}>
                      {p.name}
                    </MenuItem>
                  ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel>Merge into</InputLabel>
              <Select value={mergeTarget} label="Merge into" onChange={(e) => setMergeTarget(e.target.value)}>
                {persons
                  .filter((p) => p.id !== mergeSource)
                  .map((p) => (
                    <MenuItem key={p.id} value={p.id}>
                      {p.name}
                    </MenuItem>
                  ))}
              </Select>
            </FormControl>
            <Button
              variant="outlined"
              onClick={mergePeople}
              disabled={mergeBusy || !mergeSource || !mergeTarget || mergeSource === mergeTarget}
            >
              Merge
            </Button>
          </Stack>

          <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
            <TextField
              size="small"
              label="Enroll from snapshot path"
              value={enrollPath}
              onChange={(e) => setEnrollPath(e.target.value)}
              fullWidth
              placeholder="snapshots/motion/..._first.jpg"
            />
            <Button variant="outlined" onClick={enrollSnapshot}>
              Enroll
            </Button>
          </Stack>

          <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
            Photos for this person
          </Typography>

          <Box sx={{ maxHeight: 360, overflowY: 'auto', mb: 2, pr: 0.5 }}>
            {filteredSightings.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No photos yet. Motion snapshots with visible faces will appear here.
              </Typography>
            ) : (
              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
                  gap: 1.5,
                }}
              >
                {filteredSightings.map((sighting) => (
                  <Paper
                    key={sighting.id}
                    variant="outlined"
                    sx={{ p: 1, display: 'flex', flexDirection: 'column', gap: 0.75 }}
                  >
                    <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                      <FaceThumb
                        snapshotPath={sighting.snapshot_path}
                        bbox={sighting.bbox}
                        size={100}
                        onClick={() => setPreviewSighting(sighting)}
                      />
                    </Box>
                    <Typography variant="caption" color="text.secondary" display="block" noWrap>
                      {timeLabel(sighting.timestamp)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" display="block" noWrap>
                      {sighting.camera_id}
                    </Typography>
                    <FormControl size="small" fullWidth>
                      <Select
                        value={sighting.person_id || ''}
                        onChange={(e) => reassignSighting(sighting.id, e.target.value || null)}
                        displayEmpty
                      >
                        {persons.map((p) => (
                          <MenuItem key={p.id} value={p.id}>
                            {p.name}
                          </MenuItem>
                        ))}
                        <MenuItem value="">New person</MenuItem>
                      </Select>
                    </FormControl>
                  </Paper>
                ))}
              </Box>
            )}
          </Box>
        </>
      )}

      <Dialog
        open={Boolean(previewSighting)}
        onClose={() => setPreviewSighting(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span>
            {selectedPerson?.name || 'Person'} — {previewSighting ? timeLabel(previewSighting.timestamp) : ''}
          </span>
          <IconButton aria-label="Close preview" onClick={() => setPreviewSighting(null)} size="small">
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers>
          {previewSighting?.snapshot_path && (
            <Box
              component="img"
              src={mediaFileUrl(previewSighting.snapshot_path)}
              alt="Snapshot"
              sx={{ width: '100%', maxHeight: '70vh', objectFit: 'contain', borderRadius: 1 }}
            />
          )}
          {previewSighting && (
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
              {previewSighting.camera_id} · {previewSighting.phase || previewSighting.source}
            </Typography>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={mergeAllOpen} onClose={mergeBusy ? undefined : () => setMergeAllOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Merge all similar people?</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            This will merge {visibleSimilarPairs.length} suggested pair(s). The profile with more photos is kept.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setMergeAllOpen(false)} disabled={mergeBusy}>
            Cancel
          </Button>
          <Button variant="contained" onClick={mergeAllSimilar} disabled={mergeBusy}>
            {mergeBusy ? 'Merging…' : 'Merge all'}
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}
