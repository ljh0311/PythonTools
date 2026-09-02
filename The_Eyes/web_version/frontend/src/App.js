import React, { useRef, useEffect, useState, useCallback } from 'react';
import {
  Box,
  Typography,
  Grid,
  Button,
  Alert,
  AlertTitle,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Paper,
} from '@mui/material';
import DashboardLayout from './components/DashboardLayout';
import GridViewIcon from '@mui/icons-material/GridView';
import VideocamIcon from '@mui/icons-material/Videocam';
import AddIcon from '@mui/icons-material/Add';
import CropFreeIcon from '@mui/icons-material/CropFree';
import CameraView from './components/CameraView';
import AddCameraDialog from './components/AddCameraDialog';
import ZoneEditorDialog from './components/ZoneEditorDialog';
import AlertsPanel from './components/AlertsPanel';
import MediaLibraryPanel from './components/MediaLibraryPanel';
import AnalyticsPanel from './components/AnalyticsPanel';
import KnownPeoplePanel from './components/KnownPeoplePanel';
import RecordingControls from './components/RecordingControls';
import SystemStatusBar from './components/SystemStatusBar';
import { LiveViewSkeleton } from './components/skeletons/SurveillanceSkeletons';
import { optimisticMapPatch, optimisticListPatch } from './hooks/useOptimistic';
import {
  acquireCameraStream,
  attachStreamToVideo,
  hasLiveStream,
  isVirtualCameraLabel,
  releaseAllStreams,
  releaseStream,
  sameBrowserDeviceList,
} from './cameraStreamManager';
import { apiUrl, wsUrl, readJson, postRecording, fetchJson } from './apiConfig';
// TODO: Add react-router — public /login route (see pages/Login.js) and protect dashboard routes.
// TODO: Gate WebSocket and REST calls behind authenticated session when backend auth is ready.

function App() {
  const [devices, setDevices] = useState([]);
  const [backendCameras, setBackendCameras] = useState({});
  const [cameraFrames, setCameraFrames] = useState({});
  const [cameraStatus, setCameraStatus] = useState({});
  const [recordingStatus, setRecordingStatus] = useState({});
  const [motionStatus, setMotionStatus] = useState({});
  const [motionDetectionEnabled, setMotionDetectionEnabled] = useState(true);
  const [motionTriggeredRecording, setMotionTriggeredRecording] = useState(true);
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState(null);
  const [backendError, setBackendError] = useState(null);
  const [apiReachable, setApiReachable] = useState(false);
  const [mediaApiSupported, setMediaApiSupported] = useState(false);
  const [analyticsApiSupported, setAnalyticsApiSupported] = useState(false);
  const [facesApiSupported, setFacesApiSupported] = useState(false);
  const [layout, setLayout] = useState('auto');
  const [, setLoading] = useState({});
  const [permissionDenied, setPermissionDenied] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [addCameraOpen, setAddCameraOpen] = useState(false);
  const [cameraZones, setCameraZones] = useState({});
  const [showZoneOutlines, setShowZoneOutlines] = useState(false);
  const [zoneEditorCamera, setZoneEditorCamera] = useState(null);
  const [recordingBusy, setRecordingBusy] = useState(false);
  const [cameraPower, setCameraPower] = useState({});
  const [activeSection, setActiveSection] = useState('live');

  const inputWsRef = useRef(null);
  const streamWsRefs = useRef({});
  const streamWsDisabledRef = useRef(new Set());
  const videoRefs = useRef({});
  const canvasRefs = useRef({});
  const lastSendAtRef = useRef({});
  const streamConnectedRef = useRef(new Set());
  const devicesRef = useRef(devices);
  const cameraPowerRef = useRef(cameraPower);
  const lastFrameAtRef = useRef({});

  useEffect(() => {
    devicesRef.current = devices;
  }, [devices]);

  useEffect(() => {
    cameraPowerRef.current = cameraPower;
  }, [cameraPower]);

  // Check backend status
  const checkBackendStatus = useCallback(async () => {
    try {
      const response = await fetch(apiUrl('/health'));
      const health = await readJson(response);

      // Get camera info
      const cameraResponse = await fetch(apiUrl('/api/cameras'));
      const cameraData = await readJson(cameraResponse);
      const nextCameras = cameraData.cameras || {};
      setBackendCameras((prev) => {
        const prevKeys = Object.keys(prev);
        const nextKeys = Object.keys(nextCameras);
        if (prevKeys.length === nextKeys.length) {
          const unchanged = nextKeys.every((id) => {
            const a = prev[id];
            const b = nextCameras[id];
            return (
              a &&
              b &&
              a.source === b.source &&
              a.type === b.type &&
              a.name === b.name &&
              a.enabled === b.enabled &&
              a.is_open === b.is_open
            );
          });
          if (unchanged) return prev;
        }
        return nextCameras;
      });
      setCameraPower((prev) => {
        let changed = false;
        const next = { ...prev };
        Object.entries(nextCameras).forEach(([id, meta]) => {
          if (typeof meta.enabled === 'boolean') {
            if (next[id] !== meta.enabled) {
              next[id] = meta.enabled;
              changed = true;
            }
          } else if (next[id] === undefined) {
            next[id] = true;
            changed = true;
          }
        });
        return changed ? next : prev;
      });
      if (Object.values(nextCameras).some((cam) => cam.source === 'rtsp')) {
        setIsInitializing(false);
      }
      setMediaApiSupported(Boolean(health.media_api));
      setAnalyticsApiSupported(Boolean(health.analytics_api));
      setFacesApiSupported(Boolean(health.faces_api));
      setApiReachable(true);
      setBackendError(null);
    } catch (err) {
      setApiReachable(false);
      setBackendError(err.message || 'Cannot reach API on port 8000');
    }
  }, []);

  const fetchCameraZones = useCallback(async (cameraIds) => {
    if (!cameraIds.length) return;
    const entries = await Promise.all(
      cameraIds.map(async (cameraId) => {
        try {
          const data = await fetchJson(`/api/cameras/${encodeURIComponent(cameraId)}/zones`, {
            optional: true,
          });
          return [cameraId, data?.zones || []];
        } catch {
          return [cameraId, []];
        }
      })
    );
    setCameraZones((prev) => {
      let changed = false;
      const next = { ...prev };
      entries.forEach(([cameraId, zones]) => {
        const prevZones = prev[cameraId];
        if (JSON.stringify(prevZones || []) !== JSON.stringify(zones)) {
          next[cameraId] = zones;
          changed = true;
        }
      });
      return changed ? next : prev;
    });
  }, []);

  const mapDevicesToCanonicalIds = useCallback((videoInputs) => {
    return videoInputs.map((device, index) => {
      const label = device.label || `Camera ${index + 1}`;
      const canonicalId = `webcam_${index}`;
      return {
        ...device,
        originalDeviceId: device.deviceId,
        canonicalId,
        deviceId: canonicalId,
        label,
        isVirtual: isVirtualCameraLabel(label),
      };
    });
  }, []);

  const fetchSecuritySettings = useCallback(async () => {
    try {
      const response = await fetch(apiUrl('/api/security/settings'));
      const data = await readJson(response);
      if (typeof data.motion_detection_enabled === 'boolean') {
        setMotionDetectionEnabled(data.motion_detection_enabled);
        if (!data.motion_detection_enabled) {
          setMotionStatus({});
        }
      }
      if (typeof data.motion_triggered_recording === 'boolean') {
        setMotionTriggeredRecording(data.motion_triggered_recording);
      }
    } catch (err) {
      console.error('Failed to fetch security settings:', err);
    }
  }, []);

  // Fetch alerts
  const fetchAlerts = useCallback(async () => {
    try {
      const response = await fetch(apiUrl('/api/alerts?limit=20'));
      const data = await readJson(response);
      const next = data.alerts || [];
      setAlerts((prev) => {
        if (
          prev.length === next.length &&
          prev.every((a, i) => a.id === next[i]?.id && a.acknowledged === next[i]?.acknowledged)
        ) {
          return prev;
        }
        return next;
      });
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
        setRecordingStatus((prev) => {
          const next = data.recordings;
          const keys = Object.keys(next);
          if (
            keys.length === Object.keys(prev).length &&
            keys.every((k) => prev[k] === next[k])
          ) {
            return prev;
          }
          return next;
        });
      }
    } catch (err) {
      console.error('Failed to fetch recording status:', err);
    }
  }, []);

  // Request camera permission (do not keep a throwaway stream — that races setup)
  const requestCameraPermission = useCallback(async () => {
    try {
      setPermissionDenied(false);
      setError(null);
      setIsInitializing(true);

      // Permission probe only — release immediately so setup can own the device.
      const probe = await navigator.mediaDevices.getUserMedia({ video: true });
      probe.getTracks().forEach((track) => track.stop());
      // Brief yield so Windows releases the exclusive lock before we re-open.
      await new Promise((r) => setTimeout(r, 150));

      const deviceInfos = await navigator.mediaDevices.enumerateDevices();
      const videoInputs = deviceInfos.filter((d) => d.kind === 'videoinput');
      const processedVideoInputs = mapDevicesToCanonicalIds(videoInputs);

      setDevices((prev) =>
        sameBrowserDeviceList(prev, processedVideoInputs) ? prev : processedVideoInputs
      );
      setCameraPower((prev) => {
        const next = { ...prev };
        let changed = false;
        processedVideoInputs.forEach((device) => {
          const id = device.canonicalId || device.deviceId;
          if (next[id] === undefined) {
            // Virtual cams (NVIDIA Broadcast, OBS, …) default OFF — they hold the
            // physical webcam and cause NotReadableError: Device in use.
            next[id] = !device.isVirtual;
            changed = true;
          }
        });
        return changed ? next : prev;
      });
      setLoading(Object.fromEntries(processedVideoInputs.map((device) => [device.deviceId, true])));
      setIsInitializing(false);
    } catch (err) {
      console.error('Camera permission error:', err);
      setPermissionDenied(true);
      setError(`Camera access denied: ${err.message}`);
      setIsInitializing(false);
    }
  }, [mapDevicesToCanonicalIds]);

  // Setup camera stream (owned by cameraStreamManager — survives video remounts)
  const setupCameraStream = useCallback(async (device) => {
    const cameraId = device.canonicalId || device.deviceId;
    if (cameraPowerRef.current[cameraId] === false) return;

    try {
      if (hasLiveStream(cameraId)) {
        const videoElem = videoRefs.current[device.deviceId];
        attachStreamToVideo(cameraId, videoElem);
        if (videoElem) {
          try {
            await videoElem.play();
          } catch {
            /* autoplay may still work */
          }
        }
        setLoading((prev) => ({ ...prev, [device.deviceId]: false }));
        setCameraStatus((prev) => ({ ...prev, [device.deviceId]: 'online' }));
        setError((prev) => (prev && prev.includes('in use') ? null : prev));
        return;
      }

      setLoading((prev) => ({ ...prev, [device.deviceId]: true }));
      setCameraStatus((prev) => ({ ...prev, [device.deviceId]: 'connecting' }));

      const result = await acquireCameraStream(device, {
        onTrackEnded: (endedId) => {
          setCameraStatus((prev) => ({ ...prev, [endedId]: 'error' }));
          const endedDevice = devicesRef.current.find(
            (d) => (d.canonicalId || d.deviceId) === endedId
          );
          if (endedDevice && cameraPowerRef.current[endedId] !== false) {
            setTimeout(() => setupCameraStream(endedDevice), 1500);
          }
        },
      });

      if (result?.cancelled || !result?.stream) {
        return;
      }

      // Wait briefly for the video element if React hasn't mounted it yet.
      let videoElem = videoRefs.current[device.deviceId];
      for (let i = 0; i < 10 && !videoElem; i += 1) {
        await new Promise((r) => setTimeout(r, 50));
        videoElem = videoRefs.current[device.deviceId];
      }

      if (!videoElem) {
        // Keep stream owned — attach when the <video> mounts via videoRefCallback.
        setLoading((prev) => ({ ...prev, [device.deviceId]: false }));
        setCameraStatus((prev) => ({ ...prev, [device.deviceId]: 'online' }));
        return;
      }

      attachStreamToVideo(cameraId, videoElem);

      const handleLoadedData = () => {
        setLoading((prev) => ({ ...prev, [device.deviceId]: false }));
        setCameraStatus((prev) => ({ ...prev, [device.deviceId]: 'online' }));
      };

      videoElem.addEventListener('loadeddata', handleLoadedData, { once: true });
      try {
        await videoElem.play();
        if (videoElem.readyState >= 2) handleLoadedData();
      } catch (playError) {
        console.log(`Play error for ${device.deviceId}:`, playError);
        if (videoElem.readyState >= 2) handleLoadedData();
      }

      if (!canvasRefs.current[device.deviceId]) {
        canvasRefs.current[device.deviceId] = document.createElement('canvas');
      }
    } catch (err) {
      console.error(`Failed to access camera ${device.deviceId}:`, err);
      setLoading((prev) => ({ ...prev, [device.deviceId]: false }));
      setCameraStatus((prev) => ({ ...prev, [device.deviceId]: 'error' }));
      if (err?.code === 'device_in_use') {
        setError(err.message);
      }
    }
  }, []);

  // Send frame to backend (reads power from ref so poll updates don't restart the RAF loop)
  const sendFrame = useCallback((device) => {
    const cameraKey = device.canonicalId || device.deviceId;
    if (cameraPowerRef.current[cameraKey] === false) return;

    const videoElem = videoRefs.current[device.deviceId];
    const canvas = canvasRefs.current[device.deviceId];

    if (!videoElem || !canvas || !inputWsRef.current) return;

    const now = performance.now();
    if (now - (lastSendAtRef.current[cameraKey] || 0) < 100) return;

    if (
      videoElem.readyState >= 2 &&
      videoElem.videoWidth > 0 &&
      videoElem.videoHeight > 0 &&
      inputWsRef.current.readyState === WebSocket.OPEN
    ) {
      try {
        canvas.width = videoElem.videoWidth;
        canvas.height = videoElem.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(videoElem, 0, 0);
        const imageData = canvas.toDataURL('image/jpeg', 0.65);

        inputWsRef.current.send(
          JSON.stringify({
            camera_id: device.canonicalId || device.deviceId,
            source_camera_id: device.originalDeviceId || device.deviceId,
            image: imageData,
          })
        );
        lastSendAtRef.current[cameraKey] = now;
      } catch (err) {
        console.debug('Frame capture error:', err);
      }
    }
  }, []);

  // Connect to camera stream WebSocket
  const connectCameraStream = useCallback((cameraId) => {
    if (streamWsDisabledRef.current.has(cameraId)) {
      return;
    }
    if (streamWsRefs.current[cameraId]?.readyState === WebSocket.OPEN) {
      return;
    }
    if (streamWsRefs.current[cameraId]?.readyState === WebSocket.CONNECTING) {
      return;
    }

    const ws = new WebSocket(wsUrl(`/ws/camera/${cameraId}`));
    streamWsRefs.current[cameraId] = ws;

    ws.onopen = () => {
      streamConnectedRef.current.add(cameraId);
      console.log(`Connected to camera stream: ${cameraId}`);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const isBrowserDevice = devicesRef.current.some(
        (d) => (d.canonicalId || d.deviceId) === cameraId
      );

      // Browser cameras show local <video>; skip JPEG state updates to avoid ~30 React
      // re-renders/sec that look like buffering. RTSP still needs frame images.
      if (data.frame && !isBrowserDevice) {
        const now = performance.now();
        if (now - (lastFrameAtRef.current[cameraId] || 0) >= 100) {
          lastFrameAtRef.current[cameraId] = now;
          setCameraFrames((prev) => ({ ...prev, [cameraId]: data.frame }));
        }
        setCameraStatus((prev) =>
          prev[cameraId] === 'online' ? prev : { ...prev, [cameraId]: 'online' }
        );
      }

      const motion = Boolean(data.motion_detected);
      setMotionStatus((prev) =>
        prev[cameraId] === motion ? prev : { ...prev, [cameraId]: motion }
      );
    };

    ws.onerror = (error) => {
      console.error(`Camera stream error for ${cameraId}:`, error);
    };

    ws.onclose = () => {
      streamConnectedRef.current.delete(cameraId);
      delete streamWsRefs.current[cameraId];
      if (!streamWsDisabledRef.current.has(cameraId)) {
        setTimeout(() => connectCameraStream(cameraId), 5000);
      }
    };
  }, []);

  // Initialize
  useEffect(() => {
    checkBackendStatus();
    fetchSecuritySettings();
    const statusInterval = setInterval(checkBackendStatus, 5000);
    const alertsInterval = setInterval(fetchAlerts, 2000);
    const recordingInterval = setInterval(fetchRecordingStatus, 2000);
    const securityInterval = setInterval(fetchSecuritySettings, 5000);

    navigator.mediaDevices.enumerateDevices()
      .then(deviceInfos => {
        const videoInputs = deviceInfos.filter(d => d.kind === 'videoinput');
        const processedVideoInputs = mapDevicesToCanonicalIds(videoInputs);

        if (processedVideoInputs.length === 0) {
          setIsInitializing(false);
        } else {
          setDevices((prev) =>
            sameBrowserDeviceList(prev, processedVideoInputs) ? prev : processedVideoInputs
          );
          setCameraPower((prev) => {
            const next = { ...prev };
            let changed = false;
            processedVideoInputs.forEach((device) => {
              const id = device.canonicalId || device.deviceId;
              if (next[id] === undefined) {
                next[id] = !device.isVirtual;
                changed = true;
              }
            });
            return changed ? next : prev;
          });
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
      clearInterval(securityInterval);
      releaseAllStreams();
    };
  }, [checkBackendStatus, fetchAlerts, fetchRecordingStatus, fetchSecuritySettings, mapDevicesToCanonicalIds]);

  // Setup camera streams sequentially. Never stop tracks when `devices` identity
  // is stable — that was killing live feeds whenever React recreated the array.
  useEffect(() => {
    if (devices.length === 0) return undefined;

    let cancelled = false;
    const timer = setTimeout(async () => {
      for (const device of devices) {
        if (cancelled) return;
        const cameraKey = device.canonicalId || device.deviceId;
        if (cameraPowerRef.current[cameraKey] === false) continue;
        if (hasLiveStream(cameraKey)) {
          attachStreamToVideo(cameraKey, videoRefs.current[device.deviceId]);
          continue;
        }
        await setupCameraStream(device);
      }
    }, 200);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [devices, setupCameraStream]);

  // Setup input WebSocket (stable sendFrame — power checked via ref)
  useEffect(() => {
    if (devices.length === 0) return undefined;

    let cancelled = false;
    const ws = new WebSocket(wsUrl('/ws/input'));
    inputWsRef.current = ws;

    ws.onopen = () => {
      if (cancelled) return;
      setBackendError(null);
      setApiReachable(true);
      console.log('Input WebSocket connected');
    };
    ws.onerror = () => {
      if (cancelled) return;
      setApiReachable(false);
      setBackendError('WebSocket to API failed — is the backend running on port 8000?');
    };

    let animationFrameId;
    const sendFrames = () => {
      if (!cancelled) {
        devices.forEach(sendFrame);
        animationFrameId = requestAnimationFrame(sendFrames);
      }
    };
    sendFrames();

    return () => {
      cancelled = true;
      cancelAnimationFrame(animationFrameId);
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
      if (inputWsRef.current === ws) {
        inputWsRef.current = null;
      }
    };
  }, [devices, sendFrame]);

  // Connect stream WebSockets once per camera (avoid reconnecting on API polls).
  useEffect(() => {
    const streamIds = new Set([
      ...devices.map((device) => device.canonicalId || device.deviceId),
      ...Object.keys(backendCameras).filter(
        (id) => backendCameras[id]?.source === 'rtsp' || backendCameras[id]?.type === 'network'
      ),
    ]);

    streamIds.forEach((cameraId) => {
      if (cameraPowerRef.current[cameraId] !== false) {
        connectCameraStream(cameraId);
      }
    });
  }, [devices, backendCameras, connectCameraStream]);

  useEffect(() => {
    if (!apiReachable) return;
    const ids = [
      ...devices.map((d) => d.canonicalId || d.deviceId),
      ...Object.keys(backendCameras),
    ];
    fetchCameraZones([...new Set(ids)]);
  }, [apiReachable, devices, backendCameras, fetchCameraZones]);

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
      return;
    }

    const video = videoRefs.current[cameraId];
    if (video && video.readyState >= 2 && video.videoWidth > 0 && video.videoHeight > 0) {
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0);
      const imageData = canvas.toDataURL('image/jpeg', 0.9);
      const link = document.createElement('a');
      link.href = imageData;
      link.download = `snapshot_${cameraId}_${Date.now()}.jpg`;
      link.click();
    }
  };

  const getActiveCameraIds = useCallback(() => {
    const ids = new Set([
      ...devices.map((d) => d.canonicalId || d.deviceId),
      ...Object.keys(backendCameras),
    ]);
    return [...ids];
  }, [devices, backendCameras]);

  const handleRecordToggle = async (cameraId) => {
    const isRecording = Boolean(recordingStatus[cameraId]);
    const patch = optimisticMapPatch(setRecordingStatus, cameraId, !isRecording);
    try {
      const endpoint = isRecording
        ? `/api/recording/stop?camera_id=${encodeURIComponent(cameraId)}`
        : `/api/recording/start?camera_id=${encodeURIComponent(cameraId)}&motion_triggered=false`;

      const data = await postRecording(endpoint);
      if (data.status !== 'success') {
        patch.revert();
      } else {
        fetchRecordingStatus();
      }
    } catch (err) {
      patch.revert();
      console.error('Failed to toggle recording:', err);
    }
  };

  const handleRecordAll = async () => {
    if (!apiReachable || recordingBusy) return;
    setRecordingBusy(true);

    const cameraIds = getActiveCameraIds();
    const anyRecording = cameraIds.some((id) => recordingStatus[id]) ||
      Object.values(recordingStatus).some(Boolean);
    const snapshot = { ...recordingStatus };

    // Optimistic: flip UI immediately
    if (anyRecording) {
      setRecordingStatus((prev) => {
        const next = { ...prev };
        Object.keys(next).forEach((id) => {
          next[id] = false;
        });
        return next;
      });
    } else {
      setRecordingStatus((prev) => {
        const next = { ...prev };
        cameraIds.forEach((id) => {
          next[id] = true;
        });
        return next;
      });
    }

    try {
      const statusRes = await fetch(apiUrl('/api/recording/status'));
      const statusData = await readJson(statusRes);
      const liveRecordings = statusData.recordings || {};
      const recordingIds = [
        ...new Set([
          ...Object.keys(snapshot).filter((id) => snapshot[id]),
          ...Object.keys(liveRecordings).filter((id) => liveRecordings[id]),
        ]),
      ];
      const serverAnyRecording =
        recordingIds.length > 0 || Object.values(liveRecordings).some(Boolean);

      if (serverAnyRecording) {
        try {
          await postRecording('/api/recording/stop-all');
        } catch (stopAllErr) {
          console.warn('stop-all unavailable, stopping per camera:', stopAllErr.message);
          const idsToStop =
            recordingIds.length > 0 ? recordingIds : cameraIds;
          await Promise.all(
            idsToStop.map((cameraId) =>
              postRecording(`/api/recording/stop?camera_id=${encodeURIComponent(cameraId)}`)
            )
          );
        }
      } else {
        const results = await Promise.allSettled(
          cameraIds.map((cameraId) =>
            postRecording(
              `/api/recording/start?camera_id=${encodeURIComponent(cameraId)}&motion_triggered=false`
            )
          )
        );
        const failed = results.filter((r) => r.status === 'rejected');
        if (failed.length === results.length && results.length > 0) {
          setRecordingStatus(snapshot);
          console.warn('Could not start recording — wait for camera frames to reach the API.');
        }
      }
      await fetchRecordingStatus();
    } catch (err) {
      setRecordingStatus(snapshot);
      console.error('Failed to toggle recording:', err);
    } finally {
      setRecordingBusy(false);
    }
  };

  const handleToggleMotionTriggered = async (enabled) => {
    const previous = motionTriggeredRecording;
    setMotionTriggeredRecording(enabled);
    try {
      const response = await fetch(apiUrl('/api/security/settings'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ motion_triggered_recording: enabled }),
      });
      const data = await readJson(response);
      if (data.status !== 'success') {
        setMotionTriggeredRecording(previous);
      }
    } catch (err) {
      setMotionTriggeredRecording(previous);
      console.error('Failed to update motion-triggered setting:', err);
    }
  };

  const handleToggleMotionDetection = async (enabled) => {
    const previous = motionDetectionEnabled;
    const previousMotion = motionStatus;
    setMotionDetectionEnabled(enabled);
    if (!enabled) setMotionStatus({});
    try {
      const response = await fetch(apiUrl('/api/security/settings'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ motion_detection_enabled: enabled }),
      });
      const data = await readJson(response);
      if (data.status === 'success') {
        const updated = data.settings || {};
        setMotionDetectionEnabled(updated.motion_detection_enabled ?? enabled);
        if (typeof updated.motion_triggered_recording === 'boolean') {
          setMotionTriggeredRecording(updated.motion_triggered_recording);
        }
      } else {
        setMotionDetectionEnabled(previous);
        setMotionStatus(previousMotion);
      }
    } catch (err) {
      setMotionDetectionEnabled(previous);
      setMotionStatus(previousMotion);
      console.error('Failed to update motion detection setting:', err);
    }
  };

  const handleAcknowledgeAlert = async (alert) => {
    const patch = optimisticListPatch(setAlerts, alert.id, { acknowledged: true });
    try {
      const response = await fetch(apiUrl('/api/alerts/acknowledge'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alert_id: alert.id }),
      });
      if (!response.ok) {
        patch.revert();
        return;
      }
      fetchAlerts();
    } catch (err) {
      patch.revert();
      console.error('Failed to acknowledge alert:', err);
    }
  };

  const handleCameraAdded = useCallback((camera) => {
    if (!camera?.id) return;
    setBackendCameras((prev) => ({ ...prev, [camera.id]: camera }));
    setCameraPower((prev) => ({ ...prev, [camera.id]: true }));
    setCameraStatus((prev) => ({ ...prev, [camera.id]: camera.is_open ? 'connecting' : 'offline' }));
    connectCameraStream(camera.id);
    checkBackendStatus();
    fetchCameraZones([camera.id]);
  }, [checkBackendStatus, connectCameraStream, fetchCameraZones]);

  const stopBrowserCamera = useCallback((cameraId) => {
    releaseStream(cameraId);
    const device = devices.find((d) => (d.canonicalId || d.deviceId) === cameraId);
    if (!device) return;
    const video = videoRefs.current[device.deviceId];
    if (video) {
      video.srcObject = null;
    }
  }, [devices]);

  const disconnectCameraStream = useCallback((cameraId) => {
    streamWsDisabledRef.current.add(cameraId);
    const ws = streamWsRefs.current[cameraId];
    if (ws) {
      ws.onclose = null;
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
      delete streamWsRefs.current[cameraId];
    }
    streamConnectedRef.current.delete(cameraId);
  }, []);

  const handleCameraPowerToggle = useCallback(async (cameraId, enabled) => {
    setCameraPower((prev) => ({ ...prev, [cameraId]: enabled }));

    if (!enabled) {
      stopBrowserCamera(cameraId);
      disconnectCameraStream(cameraId);
      setCameraFrames((prev) => {
        const next = { ...prev };
        delete next[cameraId];
        return next;
      });
      setCameraStatus((prev) => ({ ...prev, [cameraId]: 'offline' }));
      setMotionStatus((prev) => ({ ...prev, [cameraId]: false }));
    } else {
      streamWsDisabledRef.current.delete(cameraId);
      const device = devices.find((d) => (d.canonicalId || d.deviceId) === cameraId);
      if (device) {
        setupCameraStream(device);
      }
      connectCameraStream(cameraId);
    }

    if (apiReachable) {
      try {
        const response = await fetch(apiUrl(`/api/cameras/${encodeURIComponent(cameraId)}/power`), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled }),
        });
        if (!response.ok) {
          const data = await readJson(response);
          throw new Error(data.detail || `HTTP ${response.status}`);
        }
      } catch (err) {
        console.warn('Camera power API:', err.message);
      }
    }
  }, [
    apiReachable,
    connectCameraStream,
    devices,
    disconnectCameraStream,
    setupCameraStream,
    stopBrowserCamera,
  ]);

  const handleZonesSaved = useCallback((cameraId, zones) => {
    setCameraZones((prev) => ({ ...prev, [cameraId]: zones }));
  }, []);

  const { cols } = getGridLayout();
  const allCamerasMap = new Map();
  devices.forEach((device) => {
    const id = device.canonicalId || device.deviceId;
    allCamerasMap.set(id, {
      id,
      name: device.label,
      source: 'browser',
      type: 'browser',
      isVirtual: Boolean(device.isVirtual),
    });
  });
  Object.entries(backendCameras).forEach(([id, meta]) => {
    const existing = allCamerasMap.get(id);
    const source = meta.source || (meta.type === 'network' ? 'rtsp' : 'backend');
    if (source === 'rtsp') {
      allCamerasMap.set(id, {
        id,
        name: meta.name || meta.config?.name || id,
        source: 'rtsp',
        type: 'rtsp',
      });
    } else if (!existing) {
      allCamerasMap.set(id, {
        id,
        name: meta.name || meta.config?.name || id,
        source,
        type: 'backend',
      });
    }
  });
  const allCameras = Array.from(allCamerasMap.values());
  const recordingCount = Object.values(recordingStatus).filter(Boolean).length;
  const motionCount = motionDetectionEnabled
    ? Object.values(motionStatus).filter(Boolean).length
    : 0;

  const unackedAlerts = alerts.filter((a) => !a.acknowledged).length;
  const hiddenSections = [
    ...(!analyticsApiSupported ? ['analytics'] : []),
    ...(!facesApiSupported ? ['people'] : []),
  ];
  const sectionBadges = {
    alerts: unackedAlerts || undefined,
    live: motionCount > 0 ? motionCount : undefined,
  };

  return (
    <DashboardLayout
      activeSection={activeSection}
      onSectionChange={setActiveSection}
      sectionBadges={sectionBadges}
      hiddenSections={hiddenSections}
      onRefresh={checkBackendStatus}
    >
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

        {activeSection === 'live' && (
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

          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={() => setAddCameraOpen(true)}
            disabled={!apiReachable}
          >
            Add RTSP camera
          </Button>

          <Button
            variant={showZoneOutlines ? 'contained' : 'outlined'}
            startIcon={<CropFreeIcon />}
            onClick={() => setShowZoneOutlines((v) => !v)}
            disabled={!apiReachable}
          >
            {showZoneOutlines ? 'Hide zones' : 'Show zones'}
          </Button>
        </Paper>
        )}

        <AddCameraDialog
          open={addCameraOpen}
          onClose={() => setAddCameraOpen(false)}
          onAdded={handleCameraAdded}
        />

        <ZoneEditorDialog
          open={Boolean(zoneEditorCamera)}
          cameraId={zoneEditorCamera?.id}
          cameraName={zoneEditorCamera?.name}
          frame={zoneEditorCamera ? cameraFrames[zoneEditorCamera.id] : null}
          onClose={() => setZoneEditorCamera(null)}
          onSaved={handleZonesSaved}
        />

        {activeSection === 'live' && permissionDenied && (
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

        {activeSection === 'live' && isInitializing && allCameras.length === 0 && (
          <LiveViewSkeleton count={2} cols={2} />
        )}

        {activeSection === 'live' && !isInitializing && allCameras.length === 0 && !permissionDenied && (
          <Paper sx={{ p: 4, textAlign: 'center', border: '1px solid', borderColor: 'divider' }}>
            <VideocamIcon sx={{ fontSize: 48, opacity: 0.4, mb: 1 }} />
            <Typography variant="h6" gutterBottom>
              No cameras yet
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Plug in a webcam, allow browser access, or add an RTSP/IP camera.
            </Typography>
            <Button variant="contained" startIcon={<VideocamIcon />} onClick={requestCameraPermission} sx={{ mr: 1 }}>
              Allow cameras
            </Button>
            <Button
              variant="outlined"
              startIcon={<AddIcon />}
              onClick={() => setAddCameraOpen(true)}
              disabled={!apiReachable}
            >
              Add RTSP camera
            </Button>
          </Paper>
        )}

        {activeSection === 'live' && allCameras.length > 0 && (
          <Grid container spacing={2}>
            {allCameras.map((camera) => (
              <Grid item xs={12} sm={6} md={12 / cols} key={camera.id}>
                <CameraView
                  cameraId={camera.id}
                  cameraName={camera.name}
                  frame={cameraFrames[camera.id]}
                  status={cameraStatus[camera.id] || (camera.source === 'rtsp' ? 'connecting' : 'offline')}
                  source={camera.isVirtual ? 'virtual' : camera.source}
                  apiReachable={apiReachable}
                  isRecording={recordingStatus[camera.id] || false}
                  motionDetected={motionDetectionEnabled && (motionStatus[camera.id] || false)}
                  showLocalPreview={camera.source === 'browser'}
                  preferLocalPreview={camera.source === 'browser'}
                  videoRefCallback={(el) => {
                    videoRefs.current[camera.id] = el;
                    if (el && camera.source === 'browser' && hasLiveStream(camera.id)) {
                      attachStreamToVideo(camera.id, el);
                      el.play?.().catch(() => {});
                    }
                  }}
                  onSnapshot={handleSnapshot}
                  onRecordToggle={handleRecordToggle}
                  zones={cameraZones[camera.id] || []}
                  showZoneOutlines={showZoneOutlines}
                  onEditZones={(cameraId) => {
                    const cam = allCameras.find((c) => c.id === cameraId);
                    setZoneEditorCamera(cam || { id: cameraId, name: cameraId });
                  }}
                  cameraEnabled={cameraPower[camera.id] !== false}
                  onPowerToggle={handleCameraPowerToggle}
                />
              </Grid>
            ))}
          </Grid>
        )}

        {activeSection === 'alerts' && (
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', lg: '1fr 1.2fr' },
              gap: 2,
              alignItems: 'start',
            }}
          >
            <RecordingControls
              isRecording={recordingCount > 0}
              recordingBusy={recordingBusy}
              motionDetectionEnabled={motionDetectionEnabled}
              motionTriggered={motionTriggeredRecording}
              apiReachable={apiReachable}
              onToggleRecording={handleRecordAll}
              onToggleMotionDetection={handleToggleMotionDetection}
              onToggleMotionTriggered={handleToggleMotionTriggered}
            />
            <AlertsPanel
              alerts={alerts}
              cameraNames={Object.fromEntries(allCameras.map((c) => [c.id, c.name]))}
              apiReachable={apiReachable}
              onAcknowledge={handleAcknowledgeAlert}
            />
          </Box>
        )}

        {activeSection === 'analytics' && analyticsApiSupported && (
          <AnalyticsPanel apiReachable={apiReachable} />
        )}

        {activeSection === 'people' && facesApiSupported && (
          <KnownPeoplePanel apiReachable={apiReachable} />
        )}

        {activeSection === 'media' && (
          <MediaLibraryPanel
            apiReachable={apiReachable}
            mediaApiSupported={mediaApiSupported}
            facesApiSupported={facesApiSupported}
          />
        )}
    </DashboardLayout>
  );
}

export default App;
