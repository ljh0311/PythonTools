import React, { useRef, useEffect, useState, useCallback } from 'react';
import {
  Box,
  Container,
  Typography,
  Grid,
  CircularProgress,
  Button,
  Alert,
  AlertTitle,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Paper,
  AppBar,
  Toolbar,
  IconButton,
  Tooltip,
  Stack,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import GridViewIcon from '@mui/icons-material/GridView';
import VideocamIcon from '@mui/icons-material/Videocam';
import CameraView from './components/CameraView';
import AlertsPanel from './components/AlertsPanel';
import RecordingControls from './components/RecordingControls';
import SystemStatusBar from './components/SystemStatusBar';
import { apiUrl, wsUrl, readJson } from './apiConfig';

function App() {
  const [devices, setDevices] = useState([]);
  const [backendCameras, setBackendCameras] = useState({});
  const [cameraFrames, setCameraFrames] = useState({});
  const [cameraStatus, setCameraStatus] = useState({});
  const [recordingStatus, setRecordingStatus] = useState({});
  const [motionStatus, setMotionStatus] = useState({});
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState(null);
  const [backendError, setBackendError] = useState(null);
  const [apiReachable, setApiReachable] = useState(false);
  const [backendStatus, setBackendStatus] = useState(null);
  const [layout, setLayout] = useState('auto');
  const [, setLoading] = useState({});
  const [permissionDenied, setPermissionDenied] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);

  const inputWsRef = useRef(null);
  const streamWsRefs = useRef({});
  const videoRefs = useRef({});
  const canvasRefs = useRef({});

  // Check backend status
  const checkBackendStatus = useCallback(async () => {
    try {
      const response = await fetch(apiUrl('/health'));
      const data = await readJson(response);
      setBackendStatus(data);

      // Get camera info
      const cameraResponse = await fetch(apiUrl('/api/cameras'));
      const cameraData = await readJson(cameraResponse);
      setBackendCameras(cameraData.cameras || {});
      setApiReachable(true);
      setBackendError(null);
    } catch (err) {
      setBackendStatus({ status: 'error', error: err.message });
      setApiReachable(false);
      setBackendError(err.message || 'Cannot reach API on port 8000');
    }
  }, []);

  // Fetch alerts
  const fetchAlerts = useCallback(async () => {
    try {
      const response = await fetch(apiUrl('/api/alerts?limit=20'));
      const data = await readJson(response);
      setAlerts(data.alerts || []);
    } catch (err) {
      console.error('Failed to fetch alerts:', err);
    }
  }, []);

  // Fetch recording status
  const fetchRecordingStatus = useCallback(async () => {
    try {
      const response = await fetch(apiUrl('/api/recording/status'));
      const data = await readJson(response);
      if (data.recordings) {
        setRecordingStatus(data.recordings);
      }
    } catch (err) {
      console.error('Failed to fetch recording status:', err);
    }
  }, []);

  // Request camera permission
  const requestCameraPermission = useCallback(async () => {
    try {
      setPermissionDenied(false);
      setError(null);
      setIsInitializing(true);

      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      stream.getTracks().forEach(track => track.stop());

      const deviceInfos = await navigator.mediaDevices.enumerateDevices();
      const videoInputs = deviceInfos.filter(d => d.kind === 'videoinput');
      
      const processedVideoInputs = videoInputs.map((device, index) => ({
        ...device,
        originalDeviceId: device.deviceId,
        deviceId: device.deviceId || `camera_${index}`,
        label: device.label || `Camera ${index + 1}`
      }));

      setDevices(processedVideoInputs);
      setLoading(Object.fromEntries(processedVideoInputs.map(device => [device.deviceId, true])));
      setIsInitializing(false);
    } catch (err) {
      console.error('Camera permission error:', err);
      setPermissionDenied(true);
      setError(`Camera access denied: ${err.message}`);
      setIsInitializing(false);
    }
  }, []);

  // Setup camera stream
  const setupCameraStream = useCallback(async (device) => {
    try {
      setLoading(prev => ({ ...prev, [device.deviceId]: true }));
      setCameraStatus(prev => ({ ...prev, [device.deviceId]: 'connecting' }));

      const mediaDeviceId = device.originalDeviceId || device.deviceId;
      const constraints = {
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          ...(mediaDeviceId && mediaDeviceId !== '' && !mediaDeviceId.startsWith('camera_') 
            ? { deviceId: { exact: mediaDeviceId } } 
            : {})
        }
      };

      // Stop existing stream if any
      const existingVideo = videoRefs.current[device.deviceId];
      if (existingVideo && existingVideo.srcObject) {
        const tracks = existingVideo.srcObject.getTracks();
        tracks.forEach(track => track.stop());
        existingVideo.srcObject = null;
      }

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      const videoElem = videoRefs.current[device.deviceId];
      
      if (videoElem) {
        // Wait a bit to ensure previous operations are complete
        await new Promise(resolve => setTimeout(resolve, 100));
        
        videoElem.srcObject = stream;
        
        // Set up event handlers
        const handleLoadedData = () => {
          setLoading(prev => ({ ...prev, [device.deviceId]: false }));
          setCameraStatus(prev => ({ ...prev, [device.deviceId]: 'online' }));
        };
        
        const handleError = () => {
          setLoading(prev => ({ ...prev, [device.deviceId]: false }));
          setCameraStatus(prev => ({ ...prev, [device.deviceId]: 'error' }));
        };
        
        videoElem.addEventListener('loadeddata', handleLoadedData, { once: true });
        videoElem.addEventListener('error', handleError, { once: true });
        
        // Play video with proper error handling
        try {
          const playPromise = videoElem.play();
          if (playPromise !== undefined) {
            await playPromise;
          }
        } catch (playError) {
          // Ignore play errors - video might autoplay anyway
          console.log(`Play error for ${device.deviceId}:`, playError);
          // Still mark as loaded if video is ready
          if (videoElem.readyState >= 2) {
            handleLoadedData();
          }
        }
      }

      // Setup canvas for frame capture
      if (!canvasRefs.current[device.deviceId]) {
        canvasRefs.current[device.deviceId] = document.createElement('canvas');
      }
    } catch (err) {
      console.error(`Failed to access camera ${device.deviceId}:`, err);
      setLoading(prev => ({ ...prev, [device.deviceId]: false }));
      setCameraStatus(prev => ({ ...prev, [device.deviceId]: 'error' }));
    }
  }, []);

  // Send frame to backend
  const sendFrame = useCallback((device) => {
    const videoElem = videoRefs.current[device.deviceId];
    const canvas = canvasRefs.current[device.deviceId];
    
    // Check if video is ready and WebSocket is open
    if (!videoElem || !canvas || !inputWsRef.current) return;
    
    // Only send if video is playing and has valid dimensions
    if (videoElem.readyState >= 2 && 
        videoElem.videoWidth > 0 && 
        videoElem.videoHeight > 0 &&
        inputWsRef.current.readyState === WebSocket.OPEN) {
      try {
        canvas.width = videoElem.videoWidth;
        canvas.height = videoElem.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(videoElem, 0, 0);
        const imageData = canvas.toDataURL('image/jpeg', 0.8);
        
        inputWsRef.current.send(JSON.stringify({
          camera_id: device.originalDeviceId || device.deviceId,
          image: imageData
        }));
      } catch (err) {
        // Silently handle frame capture errors
        console.debug('Frame capture error:', err);
      }
    }
  }, []);

  // Connect to camera stream WebSocket
  const connectCameraStream = useCallback((cameraId) => {
    if (streamWsRefs.current[cameraId]) {
      return; // Already connected
    }

    const ws = new WebSocket(wsUrl(`/ws/camera/${cameraId}`));
    streamWsRefs.current[cameraId] = ws;

    ws.onopen = () => {
      console.log(`Connected to camera stream: ${cameraId}`);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'frame' && data.frame) {
        setCameraFrames(prev => ({ ...prev, [cameraId]: data.frame }));
        if (data.motion_detected) {
          setMotionStatus((prev) => ({ ...prev, [cameraId]: true }));
          setTimeout(() => {
            setMotionStatus((prev) => ({ ...prev, [cameraId]: false }));
          }, 4000);
        }
      }
    };

    ws.onerror = (error) => {
      console.error(`Camera stream error for ${cameraId}:`, error);
    };

    ws.onclose = () => {
      delete streamWsRefs.current[cameraId];
      setTimeout(() => connectCameraStream(cameraId), 5000); // Reconnect
    };
  }, []);

  // Initialize
  useEffect(() => {
    checkBackendStatus();
    const statusInterval = setInterval(checkBackendStatus, 5000);
    const alertsInterval = setInterval(fetchAlerts, 2000);
    const recordingInterval = setInterval(fetchRecordingStatus, 2000);

    navigator.mediaDevices.enumerateDevices()
      .then(deviceInfos => {
        const videoInputs = deviceInfos.filter(d => d.kind === 'videoinput');
        const processedVideoInputs = videoInputs.map((device, index) => ({
          ...device,
          originalDeviceId: device.deviceId,
          deviceId: device.deviceId || `camera_${index}`,
          label: device.label || `Camera ${index + 1}`
        }));

        if (processedVideoInputs.length === 0) {
          setIsInitializing(false);
        } else {
          setDevices(processedVideoInputs);
          setLoading(Object.fromEntries(processedVideoInputs.map(device => [device.deviceId, true])));
          setIsInitializing(false);
        }
      })
      .catch(err => {
        console.error('Device enumeration failed:', err);
        setIsInitializing(false);
      });

    return () => {
      clearInterval(statusInterval);
      clearInterval(alertsInterval);
      clearInterval(recordingInterval);
    };
  }, [checkBackendStatus, fetchAlerts, fetchRecordingStatus]);

  // Setup camera streams
  useEffect(() => {
    if (devices.length === 0) return;

    // Copy refs to local variables for cleanup
    const currentVideoRefs = videoRefs.current;

    // Setup streams with a small delay to avoid race conditions
    const setupTimer = setTimeout(() => {
      devices.forEach(device => {
        // Only setup if not already set up
        const video = currentVideoRefs[device.deviceId];
        if (!video || !video.srcObject) {
          setupCameraStream(device);
        }
      });
    }, 200);

    return () => {
      clearTimeout(setupTimer);
      // Cleanup: stop all tracks
      Object.values(currentVideoRefs).forEach(video => {
        if (video?.srcObject) {
          const tracks = video.srcObject.getTracks();
          tracks.forEach(track => {
            track.stop();
          });
          video.srcObject = null;
        }
      });
    };
  }, [devices, setupCameraStream]);

  // Setup input WebSocket
  useEffect(() => {
    if (devices.length === 0) return;

    inputWsRef.current = new WebSocket(wsUrl('/ws/input'));
    inputWsRef.current.onopen = () => {
      setBackendError(null);
      setApiReachable(true);
      console.log('Input WebSocket connected');
    };
    inputWsRef.current.onerror = () => {
      setApiReachable(false);
      setBackendError('WebSocket to API failed — is the backend running on port 8000?');
    };

    let animationFrameId;
    const sendFrames = () => {
      devices.forEach(sendFrame);
      animationFrameId = requestAnimationFrame(sendFrames);
    };
    sendFrames();

    return () => {
      inputWsRef.current?.close();
      cancelAnimationFrame(animationFrameId);
    };
  }, [devices, sendFrame]);

  // Connect to camera streams from backend
  useEffect(() => {
    const currentStreamWsRefs = streamWsRefs.current;
    
    Object.keys(backendCameras).forEach(cameraId => {
      connectCameraStream(cameraId);
    });

    return () => {
      Object.values(currentStreamWsRefs).forEach(ws => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.close();
        }
      });
    };
  }, [backendCameras, connectCameraStream]);

  // Calculate grid layout
  const getGridLayout = () => {
    const cameraCount = Math.max(devices.length, Object.keys(backendCameras).length);
    if (layout === 'auto') {
      if (cameraCount === 1) return { cols: 1 };
      if (cameraCount <= 4) return { cols: 2 };
      if (cameraCount <= 9) return { cols: 3 };
      if (cameraCount <= 16) return { cols: 4 };
      const size = Math.ceil(Math.sqrt(cameraCount));
      return { cols: size };
    }
    const cols = parseInt(layout.split('x')[1] || layout.split('x')[0]);
    return { cols };
  };

  const handleSnapshot = async (cameraId) => {
    const frame = cameraFrames[cameraId];
    if (frame) {
      const link = document.createElement('a');
      link.href = frame;
      link.download = `snapshot_${cameraId}_${Date.now()}.jpg`;
      link.click();
    }
  };

  const handleRecordToggle = async (cameraId) => {
    try {
      const isRecording = recordingStatus[cameraId];
      const endpoint = isRecording
        ? apiUrl(`/api/recording/stop?camera_id=${encodeURIComponent(cameraId)}`)
        : apiUrl(`/api/recording/start?camera_id=${encodeURIComponent(cameraId)}&motion_triggered=false`);
      
      const response = await fetch(endpoint, { method: 'POST' });
      const data = await readJson(response);
      
      if (data.status === 'success') {
        fetchRecordingStatus();
      }
    } catch (err) {
      console.error('Failed to toggle recording:', err);
    }
  };

  const handleRecordAll = async () => {
    if (!apiReachable) return;
    const anyRecording = Object.values(recordingStatus).some(Boolean);
    const ids = [
      ...devices.map((d) => d.deviceId),
      ...Object.keys(backendCameras),
    ];
    try {
      await Promise.all(
        ids.map((cameraId) => {
          const endpoint = anyRecording
            ? apiUrl(`/api/recording/stop?camera_id=${encodeURIComponent(cameraId)}`)
            : apiUrl(
                `/api/recording/start?camera_id=${encodeURIComponent(cameraId)}&motion_triggered=false`
              );
          return fetch(endpoint, { method: 'POST' });
        })
      );
      fetchRecordingStatus();
    } catch (err) {
      console.error('Failed to toggle recording:', err);
    }
  };

  const handleAcknowledgeAlert = async (alert) => {
    try {
      await fetch(apiUrl('/api/alerts/acknowledge'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alert_id: alert.id })
      });
      fetchAlerts();
    } catch (err) {
      console.error('Failed to acknowledge alert:', err);
    }
  };

  const { cols } = getGridLayout();
  const allCameras = [
    ...devices.map((d) => ({ id: d.deviceId, name: d.label, type: 'browser' })),
    ...Object.keys(backendCameras).map((id) => ({
      id,
      name: backendCameras[id].id,
      type: 'backend',
    })),
  ];
  const recordingCount = Object.values(recordingStatus).filter(Boolean).length;
  const motionCount = Object.values(motionStatus).filter(Boolean).length;

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar position="sticky" elevation={0}>
        <Toolbar>
          <Typography variant="h6" component="h1" sx={{ flexGrow: 1 }}>
            The Eyes
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ mr: 2, display: { xs: 'none', sm: 'block' } }}>
            Home surveillance
          </Typography>
          <Tooltip title="Refresh API status">
            <IconButton color="inherit" onClick={checkBackendStatus} aria-label="Refresh status">
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ py: 3 }}>
        {backendError && (
          <Alert
            severity="warning"
            sx={{ mb: 2 }}
            onClose={() => setBackendError(null)}
            action={
              <Button color="inherit" size="small" onClick={checkBackendStatus}>
                Retry
              </Button>
            }
          >
            <AlertTitle>API not connected</AlertTitle>
            {backendError}. Start the backend from <strong>web_version/frontend</strong> with{' '}
            <code>npm run start:all</code>.
          </Alert>
        )}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <SystemStatusBar
          apiReachable={apiReachable}
          cameraCount={allCameras.length}
          recordingCount={recordingCount}
          motionCount={motionCount}
        />

        <Paper
          elevation={0}
          sx={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            gap: 2,
            p: 2,
            mb: 2,
            border: '1px solid',
            borderColor: 'divider',
          }}
        >
          <GridViewIcon color="action" />
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>Grid layout</InputLabel>
            <Select value={layout} label="Grid layout" onChange={(e) => setLayout(e.target.value)}>
              <MenuItem value="auto">Auto</MenuItem>
              <MenuItem value="1x1">1×1</MenuItem>
              <MenuItem value="2x2">2×2</MenuItem>
              <MenuItem value="3x3">3×3</MenuItem>
              <MenuItem value="4x4">4×4</MenuItem>
            </Select>
          </FormControl>

          {devices.length === 0 && !permissionDenied && (
            <Button variant="contained" startIcon={<VideocamIcon />} onClick={requestCameraPermission}>
              Allow cameras
            </Button>
          )}
        </Paper>

        {permissionDenied && (
          <Paper sx={{ p: 3, mb: 2, textAlign: 'center', border: '1px dashed', borderColor: 'warning.main' }}>
            <Typography variant="h6" gutterBottom>
              Camera access blocked
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Enable camera permission in your browser site settings, then reload or click below.
            </Typography>
            <Button variant="outlined" startIcon={<VideocamIcon />} onClick={requestCameraPermission}>
              Try again
            </Button>
          </Paper>
        )}

        {isInitializing && allCameras.length === 0 && (
          <Box sx={{ textAlign: 'center', py: 6 }}>
            <CircularProgress />
            <Typography variant="body1" sx={{ mt: 2 }} color="text.secondary">
              Detecting cameras…
            </Typography>
          </Box>
        )}

        {!isInitializing && allCameras.length === 0 && !permissionDenied && (
          <Paper sx={{ p: 4, textAlign: 'center', border: '1px solid', borderColor: 'divider' }}>
            <VideocamIcon sx={{ fontSize: 48, opacity: 0.4, mb: 1 }} />
            <Typography variant="h6" gutterBottom>
              No cameras yet
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Plug in a webcam or allow browser access to start monitoring.
            </Typography>
            <Button variant="contained" startIcon={<VideocamIcon />} onClick={requestCameraPermission}>
              Allow cameras
            </Button>
          </Paper>
        )}

        {allCameras.length > 0 && (
          <Grid container spacing={2}>
            {allCameras.map((camera) => (
              <Grid item xs={12} sm={6} md={12 / cols} key={camera.id}>
                <CameraView
                  cameraId={camera.id}
                  cameraName={camera.name}
                  frame={cameraFrames[camera.id]}
                  status={cameraStatus[camera.id] || 'offline'}
                  apiReachable={apiReachable}
                  isRecording={recordingStatus[camera.id] || false}
                  motionDetected={motionStatus[camera.id] || false}
                  showLocalPreview={camera.type === 'browser'}
                  videoRefCallback={(el) => {
                    videoRefs.current[camera.id] = el;
                  }}
                  onSnapshot={handleSnapshot}
                  onRecordToggle={handleRecordToggle}
                />
              </Grid>
            ))}
          </Grid>
        )}

        <Box
          sx={{
            mt: 3,
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', lg: '1.2fr 1fr' },
            gap: 2,
            alignItems: 'start',
          }}
        >
          <RecordingControls
            isRecording={recordingCount > 0}
            motionTriggered={false}
            apiReachable={apiReachable}
            onToggleRecording={handleRecordAll}
            onToggleMotionTriggered={() => {}}
          />
          <AlertsPanel
            alerts={alerts}
            apiReachable={apiReachable}
            onAcknowledge={handleAcknowledgeAlert}
          />
        </Box>
      </Container>
    </Box>
  );
}

export default App;
