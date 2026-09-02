import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Stack,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  Typography,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import AddIcon from '@mui/icons-material/Add';
import { apiUrl, readJson } from '../apiConfig';

function slugifyId(value) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '')
    .slice(0, 48);
}

export default function AddCameraDialog({ open, onClose, onAdded }) {
  const [name, setName] = useState('');
  const [cameraId, setCameraId] = useState('');
  const [url, setUrl] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanResults, setScanResults] = useState([]);
  const [scanInfo, setScanInfo] = useState(null);

  const resetForm = () => {
    setName('');
    setCameraId('');
    setUrl('');
    setUsername('');
    setPassword('');
    setError(null);
    setScanResults([]);
    setScanInfo(null);
  };

  const handleClose = () => {
    resetForm();
    onClose?.();
  };

  const handleNameChange = (value) => {
    setName(value);
    if (!cameraId || cameraId === slugifyId(name)) {
      setCameraId(slugifyId(value));
    }
  };

  const handleScan = async () => {
    setScanning(true);
    setError(null);
    setScanInfo(null);
    setScanResults([]);
    try {
      const response = await fetch(apiUrl('/api/cameras/scan'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await readJson(response);
      if (!response.ok) {
        if (response.status === 404) {
          const detail = typeof data.detail === 'string' ? data.detail : '';
          if (detail === 'Not Found' || detail.toLowerCase().includes('not found')) {
            throw new Error('Backend needs restart — run npm run start:all');
          }
        }
        throw new Error(data.detail || `HTTP ${response.status}`);
      }
      const devices = data.devices || [];
      setScanResults(devices);
      setScanInfo({
        network: data.network,
        total: devices.length,
      });
    } catch (err) {
      setError(err.message || 'Network scan failed');
    } finally {
      setScanning(false);
    }
  };

  const handleSelectScanResult = (device) => {
    const label = device.hostname || device.ip;
    handleNameChange(label);
    if (device.suggested_rtsp_url) {
      setUrl(device.suggested_rtsp_url);
    } else if (device.ip) {
      setUrl(`rtsp://${device.ip}:554/`);
    }
  };

  const handleSubmit = async () => {
    const id = (cameraId || slugifyId(name)).trim();
    if (!id) {
      setError('Camera ID is required');
      return;
    }
    if (!url.trim()) {
      setError('RTSP URL is required');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        id,
        name: name.trim() || id,
        url: url.trim(),
      };
      if (username.trim()) payload.username = username.trim();
      if (password) payload.password = password;

      const response = await fetch(apiUrl('/api/cameras'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await readJson(response);
      if (!response.ok) {
        throw new Error(data.detail || `HTTP ${response.status}`);
      }
      onAdded?.(data.camera);
      handleClose();
    } catch (err) {
      setError(err.message || 'Failed to add camera');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add RTSP camera</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}

          <TextField
            label="Friendly name"
            value={name}
            onChange={(e) => handleNameChange(e.target.value)}
            fullWidth
            autoFocus
          />
          <TextField
            label="Camera ID"
            value={cameraId}
            onChange={(e) => setCameraId(e.target.value)}
            helperText="Used in URLs and config (e.g. garden)"
            fullWidth
          />
          <TextField
            label="RTSP URL"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="rtsp://192.168.1.50:554/stream1"
            fullWidth
            required
          />
          <TextField
            label="Username (optional)"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            fullWidth
            autoComplete="username"
          />
          <TextField
            label="Password (optional)"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            fullWidth
            autoComplete="current-password"
          />

          <Typography variant="body2" color="text.secondary">
            Scan network looks for IP cameras on your Wi‑Fi (RTSP ports). It can take 1–3 minutes.
            Results appear below — click one to fill the form. You can also type an RTSP URL manually.
          </Typography>

          <Button
            variant="outlined"
            startIcon={scanning ? <CircularProgress size={18} /> : <SearchIcon />}
            onClick={handleScan}
            disabled={scanning}
          >
            {scanning ? 'Scanning network…' : 'Scan network'}
          </Button>

          {scanning && (
            <Alert severity="info">
              Scanning your local network for cameras. The button shows a spinner while this runs.
            </Alert>
          )}

          {!scanning && scanInfo && scanResults.length === 0 && (
            <Alert severity="warning">
              Scan finished on {scanInfo.network || 'your network'} — no IP cameras found.
              Enter the RTSP URL from your camera app or manual if you know it.
            </Alert>
          )}

          {scanResults.length > 0 && (
            <Stack spacing={0.5}>
              <Typography variant="caption" color="text.secondary">
                Found {scanResults.length} potential camera(s) — click to fill form
              </Typography>
              <List dense disablePadding sx={{ maxHeight: 160, overflow: 'auto' }}>
                {scanResults.map((device) => (
                  <ListItem key={device.ip} disablePadding>
                    <ListItemButton onClick={() => handleSelectScanResult(device)}>
                      <ListItemText
                        primary={device.hostname || device.ip}
                        secondary={
                          device.suggested_rtsp_url ||
                          `Ports: ${(device.open_ports || []).join(', ')}`
                        }
                      />
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
            </Stack>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button
          variant="contained"
          startIcon={submitting ? <CircularProgress size={18} color="inherit" /> : <AddIcon />}
          onClick={handleSubmit}
          disabled={submitting}
        >
          Add camera
        </Button>
      </DialogActions>
    </Dialog>
  );
}
