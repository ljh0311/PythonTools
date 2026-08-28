import React, { useRef, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  IconButton,
  Chip,
  Tooltip,
  CircularProgress,
  Skeleton,
  Switch,
  FormControlLabel,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import VideocamIcon from '@mui/icons-material/Videocam';
import VideocamOffIcon from '@mui/icons-material/VideocamOff';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import CameraAltIcon from '@mui/icons-material/CameraAlt';
import FullscreenIcon from '@mui/icons-material/Fullscreen';
import MotionPhotosAutoIcon from '@mui/icons-material/MotionPhotosAuto';
import CropFreeIcon from '@mui/icons-material/CropFree';
import ZoneEditor from './ZoneEditor';

const FeedFrame = styled(Box)({
  position: 'relative',
  width: '100%',
  aspectRatio: '16 / 9',
  borderRadius: 8,
  overflow: 'hidden',
  backgroundColor: '#000',
  border: '1px solid rgba(255,255,255,0.12)',
  '&:hover .camera-controls': {
    opacity: 1,
  },
});

const FeedMedia = styled('img')({
  width: '100%',
  height: '100%',
  objectFit: 'contain',
  display: 'block',
});

const LocalVideo = styled('video')({
  width: '100%',
  height: '100%',
  objectFit: 'contain',
  display: 'block',
});

const ControlsOverlay = styled(Box)({
  position: 'absolute',
  bottom: 8,
  right: 8,
  display: 'flex',
  gap: 4,
  zIndex: 3,
  opacity: 0.55,
  transition: 'opacity 0.2s ease',
});

const MotionBadge = styled(Chip)({
  position: 'absolute',
  top: 8,
  right: 8,
  zIndex: 2,
  animation: 'motionPulse 1.2s ease-in-out infinite',
  '@keyframes motionPulse': {
    '0%, 100%': { opacity: 1 },
    '50%': { opacity: 0.65 },
  },
});

const LoadingOverlay = styled(Box)({
  position: 'absolute',
  inset: 0,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  backgroundColor: 'rgba(0,0,0,0.55)',
  zIndex: 2,
});

export default function CameraView({
  cameraId,
  cameraName,
  frame,
  status = 'offline',
  source = 'browser',
  apiReachable = true,
  isRecording = false,
  motionDetected = false,
  showLocalPreview = false,
  preferLocalPreview = false,
  videoRefCallback,
  onSnapshot,
  onRecordToggle,
  zones = [],
  showZoneOutlines = false,
  onEditZones,
  cameraEnabled = true,
  onPowerToggle,
}) {
  const feedRef = useRef(null);
  const [controlsHint, setControlsHint] = useState(false);

  const getStatusText = () => {
    if (!cameraEnabled) return 'Off';
    if (!apiReachable) return 'API offline';
    if (status === 'connecting') return 'Connecting';
    switch (status) {
      case 'online':
        return 'Online';
      case 'offline':
        return 'Offline';
      case 'error':
        return 'Error';
      default:
        return 'Unknown';
    }
  };

  const getStatusColor = () => {
    if (!cameraEnabled) return 'default';
    if (!apiReachable) return 'warning';
    if (status === 'connecting') return 'info';
    switch (status) {
      case 'online':
        return 'success';
      case 'offline':
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  const hasFrame = Boolean(frame);

  const getSourceLabel = () => {
    if (source === 'rtsp') return 'RTSP';
    if (source === 'virtual') return 'Virtual';
    if (source === 'browser') return 'Browser';
    return source;
  };

  const getSourceColor = () => {
    if (source === 'rtsp') return 'info';
    if (source === 'virtual') return 'warning';
    return 'default';
  };

  const isFeedLive =
    cameraEnabled &&
    (status === 'online' || status === 'connecting' || (source === 'rtsp' && hasFrame));
  const canUseControls = cameraEnabled && apiReachable && isFeedLive;
  const localPreviewActive = cameraEnabled && showLocalPreview;
  // Keep <video> mounted while camera is on so stream teardown/setup races don't lose the ref.
  const showLocalVideo = preferLocalPreview
    ? localPreviewActive
    : showLocalPreview && !hasFrame && localPreviewActive;
  const showProcessedFrame = hasFrame && !preferLocalPreview;
  const isConnecting = status === 'connecting';

  const handleFullscreen = () => {
    const el = feedRef.current;
    if (el?.requestFullscreen) el.requestFullscreen();
  };

  const emptyMessage = () => {
    if (!cameraEnabled) {
      return {
        title: 'Camera off',
        detail: 'Turn the camera on to resume the live feed.',
      };
    }
    if (!apiReachable) {
      return {
        title: 'Waiting for API',
        detail: 'Start the backend (npm run start:all) to process and display feeds.',
      };
    }
    if (status === 'error') {
      return {
        title: 'Camera error',
        detail:
          'Camera may be in use by another app (NVIDIA Broadcast, Zoom, desktop GUI). Close it, or leave virtual cameras off.',
      };
    }
    if (status === 'offline') {
      if (source === 'rtsp') {
        return { title: 'RTSP offline', detail: 'Check URL, credentials, and network reachability.' };
      }
      return { title: 'Camera offline', detail: 'Allow camera access or reconnect the device.' };
    }
    return { title: 'No feed yet', detail: 'Stream should appear when the API receives frames.' };
  };

  return (
    <Card sx={{ height: '100%' }}>
      <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 1, mb: 1 }}>
          <Typography variant="subtitle2" noWrap title={cameraName || cameraId} sx={{ flex: 1 }}>
            {cameraName || cameraId}
          </Typography>
          <Box sx={{ display: 'flex', gap: 0.5, flexShrink: 0, alignItems: 'center' }}>
            <Tooltip title={cameraEnabled ? 'Turn camera off' : 'Turn camera on'}>
              <FormControlLabel
                control={
                  <Switch
                    size="small"
                    checked={cameraEnabled}
                    onChange={(e) => onPowerToggle?.(cameraId, e.target.checked)}
                    inputProps={{ 'aria-label': `${cameraEnabled ? 'Turn off' : 'Turn on'} ${cameraName || cameraId}` }}
                  />
                }
                label=""
                sx={{ m: 0, mr: -0.5 }}
              />
            </Tooltip>
            <Chip label={getSourceLabel()} color={getSourceColor()} size="small" variant="outlined" />
            <Chip
              label={getStatusText()}
              color={getStatusColor()}
              size="small"
              icon={cameraEnabled && apiReachable && isFeedLive ? <VideocamIcon /> : <VideocamOffIcon />}
            />
          </Box>
        </Box>

        <FeedFrame ref={feedRef} onMouseEnter={() => setControlsHint(true)} onMouseLeave={() => setControlsHint(false)}>
          {cameraEnabled && showProcessedFrame && <FeedMedia src={frame} alt={cameraName} />}

          {cameraEnabled && showLocalVideo && (
            <LocalVideo ref={videoRefCallback} autoPlay playsInline muted aria-label={`${cameraName} preview`} />
          )}

          {(!cameraEnabled ||
            (!hasFrame && !showLocalVideo) ||
            (showLocalVideo &&
              !hasFrame &&
              (status === 'offline' || status === 'error') &&
              !isConnecting)) && (
            <Box
              sx={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'text.secondary',
                px: 2,
                textAlign: 'center',
              }}
            >
              <VideocamOffIcon sx={{ fontSize: 40, mb: 1, opacity: 0.5 }} />
              <Typography variant="body2" color="text.primary">
                {emptyMessage().title}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                {emptyMessage().detail}
              </Typography>
            </Box>
          )}

          {cameraEnabled && showLocalVideo && !apiReachable && (
            <Chip
              label="Local preview"
              size="small"
              sx={{ position: 'absolute', top: 8, left: 8, zIndex: 2, bgcolor: 'rgba(0,0,0,0.7)' }}
            />
          )}

          {cameraEnabled && isConnecting && (
            <LoadingOverlay>
              <Box sx={{ width: '70%', maxWidth: 220 }}>
                <Skeleton variant="rounded" height={12} sx={{ mb: 1 }} animation="wave" />
                <Skeleton variant="rounded" height={12} width="60%" animation="wave" />
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
                  <CircularProgress size={28} />
                </Box>
              </Box>
            </LoadingOverlay>
          )}

          {cameraEnabled && isRecording && (
            <Chip
              icon={<FiberManualRecordIcon />}
              label="REC"
              color="error"
              size="small"
              sx={{ position: 'absolute', top: 8, left: 8, zIndex: 2 }}
            />
          )}

          {cameraEnabled && motionDetected && (
            <MotionBadge
              icon={<MotionPhotosAutoIcon />}
              label="Motion"
              color="warning"
              size="small"
            />
          )}

          {cameraEnabled && showZoneOutlines && zones.length > 0 && (
            <ZoneEditor zones={zones} showOutlines editable={false} />
          )}

          <ControlsOverlay className="camera-controls" sx={{ opacity: controlsHint ? 1 : 0.35 }}>
            <Tooltip title={hasFrame || showLocalVideo ? 'Save snapshot' : 'No frame to capture'}>
              <span>
                <IconButton
                  size="small"
                  disabled={!hasFrame && !showLocalVideo}
                  onClick={() => onSnapshot?.(cameraId)}
                  aria-label="Take snapshot"
                  sx={{ bgcolor: 'rgba(0,0,0,0.65)', color: 'white', '&:hover': { bgcolor: 'rgba(0,0,0,0.85)' } }}
                >
                  <CameraAltIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip
              title={
                !apiReachable
                  ? 'Connect API to record'
                  : isRecording
                    ? 'Stop recording'
                    : 'Start recording'
              }
            >
              <span>
                <IconButton
                  size="small"
                  disabled={!canUseControls}
                  onClick={() => onRecordToggle?.(cameraId)}
                  aria-label={isRecording ? 'Stop recording' : 'Start recording'}
                  sx={{
                    bgcolor: isRecording ? 'error.main' : 'rgba(0,0,0,0.65)',
                    color: 'white',
                    '&:hover': { bgcolor: isRecording ? 'error.dark' : 'rgba(0,0,0,0.85)' },
                  }}
                >
                  <FiberManualRecordIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip title="Fullscreen">
              <IconButton
                size="small"
                onClick={handleFullscreen}
                aria-label="Fullscreen"
                sx={{ bgcolor: 'rgba(0,0,0,0.65)', color: 'white', '&:hover': { bgcolor: 'rgba(0,0,0,0.85)' } }}
              >
                <FullscreenIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title={apiReachable ? 'Edit detection zones' : 'Connect API to edit zones'}>
              <span>
                <IconButton
                  size="small"
                  disabled={!apiReachable}
                  onClick={() => onEditZones?.(cameraId)}
                  aria-label="Edit zones"
                  sx={{ bgcolor: 'rgba(0,0,0,0.65)', color: 'white', '&:hover': { bgcolor: 'rgba(0,0,0,0.85)' } }}
                >
                  <CropFreeIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
          </ControlsOverlay>
        </FeedFrame>
      </CardContent>
    </Card>
  );
}
