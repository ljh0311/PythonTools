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
} from '@mui/material';
import { styled } from '@mui/material/styles';
import VideocamIcon from '@mui/icons-material/Videocam';
import VideocamOffIcon from '@mui/icons-material/VideocamOff';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import CameraAltIcon from '@mui/icons-material/CameraAlt';
import FullscreenIcon from '@mui/icons-material/Fullscreen';
import MotionPhotosAutoIcon from '@mui/icons-material/MotionPhotosAuto';

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
  opacity: 0.35,
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
  apiReachable = true,
  isRecording = false,
  motionDetected = false,
  showLocalPreview = false,
  videoRefCallback,
  onSnapshot,
  onRecordToggle,
}) {
  const feedRef = useRef(null);
  const [controlsHint, setControlsHint] = useState(false);

  const getStatusText = () => {
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

  const canUseControls = apiReachable && status === 'online';
  const hasFrame = Boolean(frame);
  const showLocalVideo =
    showLocalPreview && !hasFrame && (status === 'online' || status === 'connecting');
  const isConnecting = status === 'connecting';

  const handleFullscreen = () => {
    const el = feedRef.current;
    if (el?.requestFullscreen) el.requestFullscreen();
  };

  const emptyMessage = () => {
    if (!apiReachable) {
      return {
        title: 'Waiting for API',
        detail: 'Start the backend (npm run start:all) to process and display feeds.',
      };
    }
    if (status === 'error') {
      return { title: 'Camera error', detail: 'Check permissions or try another device.' };
    }
    if (status === 'offline') {
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
          <Chip
            label={getStatusText()}
            color={getStatusColor()}
            size="small"
            icon={
              apiReachable && status === 'online' ? (
                <VideocamIcon />
              ) : (
                <VideocamOffIcon />
              )
            }
          />
        </Box>

        <FeedFrame ref={feedRef} onMouseEnter={() => setControlsHint(true)} onMouseLeave={() => setControlsHint(false)}>
          {hasFrame && <FeedMedia src={frame} alt={cameraName} />}

          {showLocalVideo && (
            <LocalVideo ref={videoRefCallback} autoPlay playsInline muted aria-label={`${cameraName} preview`} />
          )}

          {!hasFrame && !showLocalVideo && (
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

          {showLocalVideo && !apiReachable && (
            <Chip
              label="Local preview"
              size="small"
              sx={{ position: 'absolute', top: 8, left: 8, zIndex: 2, bgcolor: 'rgba(0,0,0,0.7)' }}
            />
          )}

          {isConnecting && (
            <LoadingOverlay>
              <CircularProgress size={36} />
            </LoadingOverlay>
          )}

          {isRecording && (
            <Chip
              icon={<FiberManualRecordIcon />}
              label="REC"
              color="error"
              size="small"
              sx={{ position: 'absolute', top: 8, left: 8, zIndex: 2 }}
            />
          )}

          {motionDetected && (
            <MotionBadge
              icon={<MotionPhotosAutoIcon />}
              label="Motion"
              color="warning"
              size="small"
            />
          )}

          <ControlsOverlay className="camera-controls" sx={{ opacity: controlsHint ? 1 : 0.35 }}>
            <Tooltip title={hasFrame ? 'Save snapshot' : 'No frame to capture'}>
              <span>
                <IconButton
                  size="small"
                  disabled={!hasFrame}
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
          </ControlsOverlay>
        </FeedFrame>
      </CardContent>
    </Card>
  );
}
