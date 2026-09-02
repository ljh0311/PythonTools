import React from 'react';
import { Box, Button, Typography, Switch, FormControlLabel, Paper, Tooltip, CircularProgress } from '@mui/material';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import StopIcon from '@mui/icons-material/Stop';

export default function RecordingControls({
  isRecording,
  recordingBusy = false,
  motionDetectionEnabled,
  motionTriggered,
  onToggleRecording,
  onToggleMotionDetection,
  onToggleMotionTriggered,
  apiReachable = true,
  disabled = false,
}) {
  const blocked = disabled || !apiReachable || recordingBusy;

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2,
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 2,
        height: '100%',
      }}
    >
      <Typography variant="subtitle1" fontWeight={600} gutterBottom>
        Recording & motion
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {blocked
          ? 'Connect the API to control recording from the dashboard.'
          : 'Motion detection shows the live pill on feeds. Motion triggered only auto-starts recording.'}
      </Typography>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Tooltip
          title={
            blocked && recordingBusy
              ? 'Stopping recordings…'
              : blocked
                ? 'API required'
                : isRecording
                  ? 'Stop all recordings'
                  : 'Start recording on all cameras'
          }
        >
          <span>
            <Button
              variant={isRecording ? 'contained' : 'outlined'}
              color={isRecording ? 'error' : 'primary'}
              disabled={blocked}
              startIcon={
                recordingBusy ? (
                  <CircularProgress size={18} color="inherit" />
                ) : isRecording ? (
                  <StopIcon />
                ) : (
                  <FiberManualRecordIcon />
                )
              }
              onClick={onToggleRecording}
            >
              {recordingBusy ? 'Please wait…' : isRecording ? 'Stop all' : 'Record all'}
            </Button>
          </span>
        </Tooltip>

        <Tooltip title="Shows the Motion pill on feeds, snapshots, and alerts">
          <FormControlLabel
            control={
              <Switch
                checked={motionDetectionEnabled}
                onChange={(e) => onToggleMotionDetection?.(e.target.checked)}
                disabled={blocked}
              />
            }
            label="Motion detection"
          />
        </Tooltip>

        <Tooltip title="Automatically start recording when motion is detected (requires motion detection)">
          <FormControlLabel
            control={
              <Switch
                checked={motionTriggered}
                onChange={(e) => onToggleMotionTriggered?.(e.target.checked)}
                disabled={blocked || isRecording || !motionDetectionEnabled}
              />
            }
            label="Motion triggered"
          />
        </Tooltip>

        {isRecording && (
          <Typography variant="body2" color="error.main" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <FiberManualRecordIcon fontSize="small" />
            Recording in progress
          </Typography>
        )}
      </Box>
    </Paper>
  );
}
