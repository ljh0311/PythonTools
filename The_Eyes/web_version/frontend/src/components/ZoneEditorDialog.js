import React, { useEffect, useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Stack,
  Alert,
  Typography,
  IconButton,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import SaveIcon from '@mui/icons-material/Save';
import ZoneEditor from './ZoneEditor';
import { apiUrl, readJson } from '../apiConfig';

export default function ZoneEditorDialog({
  open,
  cameraId,
  cameraName,
  frame,
  onClose,
  onSaved,
}) {
  const [zones, setZones] = useState([]);
  const [showOutlines, setShowOutlines] = useState(true);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [selectedIndex, setSelectedIndex] = useState(null);

  useEffect(() => {
    if (!open || !cameraId) return undefined;

    let cancelled = false;
    setLoading(true);
    setError(null);
    setSelectedIndex(null);

    fetch(apiUrl(`/api/cameras/${encodeURIComponent(cameraId)}/zones`))
      .then(async (response) => {
        const data = await readJson(response);
        if (!response.ok) {
          throw new Error(data.detail || `HTTP ${response.status}`);
        }
        return data;
      })
      .then((data) => {
        if (cancelled) return;
        if (!data.zones) throw new Error('Invalid zones response');
        setZones(data.zones);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Failed to load zones');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, cameraId]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const response = await fetch(apiUrl(`/api/cameras/${encodeURIComponent(cameraId)}/zones`), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zones }),
      });
      const data = await readJson(response);
      if (!response.ok) {
        throw new Error(data.detail || `HTTP ${response.status}`);
      }
      onSaved?.(cameraId, data.zones || zones);
      onClose?.();
    } catch (err) {
      setError(err.message || 'Failed to save zones');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteSelected = () => {
    if (selectedIndex === null) return;
    setZones((prev) => prev.filter((_, i) => i !== selectedIndex));
    setSelectedIndex(null);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Edit detection zones — {cameraName || cameraId}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}
          <Typography variant="body2" color="text.secondary">
            Drag on the preview to add a zone. Motion is only detected inside zones when at least
            one zone is defined. Coordinates are saved as fractions of the frame (0–1).
          </Typography>

          <Stack direction="row" spacing={1} alignItems="center">
            <Tooltip title={showOutlines ? 'Hide zone outlines' : 'Show zone outlines'}>
              <IconButton size="small" onClick={() => setShowOutlines((v) => !v)}>
                {showOutlines ? <VisibilityIcon /> : <VisibilityOffIcon />}
              </IconButton>
            </Tooltip>
            <Tooltip title="Delete selected zone">
              <span>
                <IconButton
                  size="small"
                  disabled={selectedIndex === null}
                  onClick={handleDeleteSelected}
                >
                  <DeleteIcon />
                </IconButton>
              </span>
            </Tooltip>
            <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }}>
              {zones.length} zone{zones.length === 1 ? '' : 's'}
            </Typography>
          </Stack>

          <BoxFrame>
            {frame ? (
              <img src={frame} alt={cameraName} style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ p: 4, textAlign: 'center' }}>
                Waiting for camera feed… zones can still be drawn on the preview area.
              </Typography>
            )}
            {!loading && (
              <ZoneEditor
                zones={zones}
                editable
                showOutlines={showOutlines}
                onChange={setZones}
                onSelectZone={setSelectedIndex}
              />
            )}
            {loading && (
              <Stack
                alignItems="center"
                justifyContent="center"
                sx={{ position: 'absolute', inset: 0, bgcolor: 'rgba(0,0,0,0.45)' }}
              >
                <CircularProgress size={32} />
              </Stack>
            )}
          </BoxFrame>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          startIcon={saving ? <CircularProgress size={18} color="inherit" /> : <SaveIcon />}
          onClick={handleSave}
          disabled={saving || loading}
        >
          Save zones
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function BoxFrame({ children }) {
  return (
    <Stack
      sx={{
        position: 'relative',
        width: '100%',
        aspectRatio: '16 / 9',
        borderRadius: 1,
        overflow: 'hidden',
        bgcolor: '#000',
        border: '1px solid',
        borderColor: 'divider',
      }}
    >
      {children}
    </Stack>
  );
}
