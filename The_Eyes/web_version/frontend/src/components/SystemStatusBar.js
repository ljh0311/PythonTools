import React from 'react';
import { Box, Chip, Stack, Typography } from '@mui/material';
import CloudDoneIcon from '@mui/icons-material/CloudDone';
import CloudOffIcon from '@mui/icons-material/CloudOff';
import VideocamIcon from '@mui/icons-material/Videocam';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import MotionPhotosAutoIcon from '@mui/icons-material/MotionPhotosAuto';

export default function SystemStatusBar({
  apiReachable,
  cameraCount = 0,
  recordingCount = 0,
  motionCount = 0,
}) {
  return (
    <Box
      sx={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: 1.5,
        py: 1.5,
        px: 2,
        mb: 2,
        borderRadius: 2,
        bgcolor: 'background.paper',
        border: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Typography variant="caption" color="text.secondary" sx={{ mr: 0.5 }}>
        System
      </Typography>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip
          size="small"
          icon={apiReachable ? <CloudDoneIcon /> : <CloudOffIcon />}
          label={apiReachable ? 'API connected' : 'API offline'}
          color={apiReachable ? 'success' : 'warning'}
          variant={apiReachable ? 'filled' : 'outlined'}
        />
        <Chip
          size="small"
          icon={<VideocamIcon />}
          label={`${cameraCount} camera${cameraCount === 1 ? '' : 's'}`}
          variant="outlined"
        />
        {recordingCount > 0 && (
          <Chip
            size="small"
            icon={<FiberManualRecordIcon />}
            label={`${recordingCount} recording`}
            color="error"
          />
        )}
        {motionCount > 0 && (
          <Chip
            size="small"
            icon={<MotionPhotosAutoIcon />}
            label={`${motionCount} motion`}
            color="warning"
          />
        )}
      </Stack>
    </Box>
  );
}
