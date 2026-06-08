import React from 'react';
import { Box, Button, Typography, Switch, FormControlLabel, Paper, Tooltip } from '@mui/material';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import StopIcon from '@mui/icons-material/Stop';

export default function RecordingControls({
  isRecording,
  motionTriggered,
  onToggleRecording,
  onToggleMotionTriggered,
  apiReachable = true,
  disabled = false,
}) {
  const blocked = disabled || !apiReachable;

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
        Recording
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {blocked
          ? 'Connect the API to control recording from the dashboard.'
          : 'Toggle recording on all active camera feeds.'}
      </Typography>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Tooltip title={blocked ? 'API required' : isRecording ? 'Stop all recordings' : 'Start recording on all cameras'}>
          <span>
            <Button
              variant={isRecording ? 'contained' : 'outlined'}
              color={isRecording ? 'error' : 'primary'}
              disabled={blocked}
              startIcon={isRecording ? <StopIcon /> : <FiberManualRecordIcon />}
              onClick={onToggleRecording}
            >
              {isRecording ? 'Stop all' : 'Record all'}
            </Button>
          </span>
        </Tooltip>

        <Tooltip title="Motion-triggered recording is configured on the server">
          <FormControlLabel
            control={
              <Switch
                checked={motionTriggered}
                onChange={(e) => onToggleMotionTriggered?.(e.target.checked)}
                disabled={blocked || isRecording}
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
