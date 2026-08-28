import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  Chip,
  IconButton,
  Collapse,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import NotificationsNoneIcon from '@mui/icons-material/NotificationsNone';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import CloseIcon from '@mui/icons-material/Close';
import PhotoCameraIcon from '@mui/icons-material/PhotoCamera';
import { apiUrl } from '../apiConfig';

const AlertPanel = styled(Paper)(({ theme }) => ({
  maxHeight: 360,
  overflow: 'auto',
  border: '1px solid',
  borderColor: theme.palette.divider,
}));

const AlertItem = styled(ListItem)(({ theme, severity }) => {
  const colors = {
    info: 'rgba(79, 195, 247, 0.12)',
    warning: 'rgba(210, 153, 34, 0.15)',
    error: 'rgba(248, 81, 73, 0.15)',
    critical: 'rgba(248, 81, 73, 0.25)',
  };
  return {
    backgroundColor: colors[severity] || theme.palette.action.hover,
    marginBottom: theme.spacing(0.75),
    borderRadius: theme.shape.borderRadius,
    border: '1px solid',
    borderColor: theme.palette.divider,
  };
});

function resolveCameraName(cameraId, cameraNames) {
  if (!cameraId) return 'System';
  return cameraNames?.[cameraId] || cameraId;
}

function formatAlertMessage(message, cameraId, cameraNames) {
  if (!message || !cameraId) return message;
  const friendly = resolveCameraName(cameraId, cameraNames);
  if (friendly === cameraId) return message;
  return message.replace(new RegExp(`\\b${cameraId.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'g'), friendly);
}

function formatRelativeTime(timestamp) {
  try {
    const date = new Date(timestamp);
    const sec = Math.floor((Date.now() - date.getTime()) / 1000);
    if (sec < 60) return 'Just now';
    if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
    if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
    return date.toLocaleString();
  } catch {
    return timestamp;
  }
}

export default function AlertsPanel({ alerts = [], cameraNames = {}, onAcknowledge, apiReachable = true }) {
  const [expanded, setExpanded] = useState(true);
  const [unreadCount, setUnreadCount] = useState(0);
  const [snapshotPreview, setSnapshotPreview] = useState(null);

  useEffect(() => {
    setUnreadCount(alerts.filter((a) => !a.acknowledged).length);
  }, [alerts]);

  const getSeverity = (level) => {
    switch (level) {
      case 'critical':
        return 'critical';
      case 'error':
        return 'error';
      case 'warning':
        return 'warning';
      default:
        return 'info';
    }
  };

  const handleAcknowledgeAll = () => {
    const first = alerts.find((a) => !a.acknowledged);
    if (first && onAcknowledge) onAcknowledge(first);
  };

  return (
    <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, overflow: 'hidden' }}>
      <Box
        component="button"
        type="button"
        onClick={() => setExpanded(!expanded)}
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          width: '100%',
          border: 'none',
          cursor: 'pointer',
          p: 1.5,
          bgcolor: 'background.paper',
          color: 'text.primary',
          textAlign: 'left',
          '&:hover': { bgcolor: 'action.hover' },
        }}
        aria-expanded={expanded}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {unreadCount > 0 ? <NotificationsActiveIcon color="warning" /> : <NotificationsNoneIcon />}
          <Typography variant="subtitle1" fontWeight={600}>
            Alerts
          </Typography>
          {unreadCount > 0 && <Chip label={unreadCount} size="small" color="warning" />}
        </Box>
        {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
      </Box>

      <Collapse in={expanded}>
        <AlertPanel square>
          {!apiReachable ? (
            <Box sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                Alerts load when the API is connected.
              </Typography>
            </Box>
          ) : alerts.length === 0 ? (
            <Box sx={{ p: 3, textAlign: 'center' }}>
              <NotificationsNoneIcon sx={{ fontSize: 40, opacity: 0.35, mb: 1 }} />
              <Typography variant="body2" color="text.secondary">
                No alerts — all clear
              </Typography>
            </Box>
          ) : (
            <>
              {unreadCount > 1 && onAcknowledge && (
                <Box sx={{ px: 2, pt: 1 }}>
                  <Button size="small" onClick={handleAcknowledgeAll}>
                    Acknowledge latest
                  </Button>
                </Box>
              )}
              <List dense sx={{ px: 1, pb: 1 }}>
                {alerts.map((alert) => (
                  <AlertItem key={alert.id || `${alert.timestamp}-${alert.message}`} severity={getSeverity(alert.level)}>
                    <ListItemText
                      primary={
                        <Typography variant="body2" fontWeight={600} component="div">
                          {formatAlertMessage(alert.message, alert.camera_id, cameraNames)}
                        </Typography>
                      }
                      secondaryTypographyProps={{ component: 'div' }}
                      secondary={
                        <>
                          <Typography variant="caption" color="text.secondary" component="span" display="block">
                            {formatRelativeTime(alert.timestamp)} · {resolveCameraName(alert.camera_id, cameraNames)}
                            {alert.acknowledged ? ' · Acknowledged' : ''}
                          </Typography>
                          {alert.data?.snapshot && (
                            <Box sx={{ mt: 0.5 }}>
                              <Button
                                size="small"
                                variant="text"
                                startIcon={<PhotoCameraIcon fontSize="small" />}
                                onClick={() =>
                                  setSnapshotPreview({
                                    url: apiUrl(
                                      `/api/media/file?path=${encodeURIComponent(alert.data.snapshot)}`
                                    ),
                                    title: `Motion ${alert.data.phase === 'last' ? 'ended' : 'started'} — ${resolveCameraName(alert.camera_id, cameraNames)}`,
                                  })
                                }
                                sx={{ p: 0, minWidth: 0 }}
                              >
                                View {alert.data.phase === 'last' ? 'end' : 'start'} snapshot
                              </Button>
                            </Box>
                          )}
                        </>
                      }
                    />
                    {!alert.acknowledged && onAcknowledge && (
                      <IconButton
                        size="small"
                        onClick={() => onAcknowledge(alert)}
                        aria-label="Acknowledge alert"
                        color="success"
                      >
                        <CheckCircleOutlineIcon fontSize="small" />
                      </IconButton>
                    )}
                  </AlertItem>
                ))}
              </List>
            </>
          )}
        </AlertPanel>
      </Collapse>

      <Dialog
        open={Boolean(snapshotPreview)}
        onClose={() => setSnapshotPreview(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', pr: 1 }}>
          <Typography variant="subtitle1" component="span" fontWeight={600}>
            {snapshotPreview?.title || 'Snapshot'}
          </Typography>
          <IconButton aria-label="Close snapshot" onClick={() => setSnapshotPreview(null)} size="small">
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers sx={{ p: 1, bgcolor: 'black' }}>
          {snapshotPreview?.url && (
            <Box
              component="img"
              src={snapshotPreview.url}
              alt={snapshotPreview.title}
              sx={{ width: '100%', height: 'auto', display: 'block', borderRadius: 1 }}
            />
          )}
        </DialogContent>
      </Dialog>
    </Paper>
  );
}
