import React, { useState } from 'react';
import {
  Box,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Toolbar,
  AppBar,
  IconButton,
  Tooltip,
  Badge,
  Divider,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import RefreshIcon from '@mui/icons-material/Refresh';
import VisibilityIcon from '@mui/icons-material/Visibility';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import InsightsIcon from '@mui/icons-material/Insights';
import FaceIcon from '@mui/icons-material/Face';
import PermMediaIcon from '@mui/icons-material/PermMedia';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import { colors, layout, navSections } from '../designTokens';

const SECTION_ICONS = {
  live: VisibilityIcon,
  alerts: NotificationsActiveIcon,
  analytics: InsightsIcon,
  people: FaceIcon,
  media: PermMediaIcon,
};

const GROUP_LABELS = {
  monitor: 'Monitoring',
  insights: 'Insights',
  data: 'Library',
};

export default function DashboardLayout({
  activeSection,
  onSectionChange,
  sectionBadges = {},
  hiddenSections = [],
  onRefresh,
  children,
}) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const drawerWidth = collapsed && !isMobile ? layout.sidebarCollapsed : layout.sidebarWidth;
  const visibleSections = navSections.filter((s) => !hiddenSections.includes(s.id));

  const renderNavItems = () => {
    let lastGroup = null;
    return visibleSections.map((section) => {
      const Icon = SECTION_ICONS[section.id];
      const badge = sectionBadges[section.id];
      const items = [];
      if (section.group !== lastGroup) {
        lastGroup = section.group;
        if (!collapsed || isMobile) {
          items.push(
            <Typography
              key={`group-${section.group}`}
              variant="overline"
              sx={{
                px: 2.5,
                pt: lastGroup === 'monitor' ? 1 : 2,
                pb: 0.5,
                display: 'block',
                color: colors.textSecondary,
                letterSpacing: '0.12em',
                fontSize: '0.65rem',
              }}
            >
              {GROUP_LABELS[section.group]}
            </Typography>
          );
        } else {
          items.push(<Divider key={`div-${section.group}`} sx={{ my: 1, borderColor: colors.border }} />);
        }
      }
      const selected = activeSection === section.id;
      items.push(
        <ListItemButton
          key={section.id}
          selected={selected}
          onClick={() => {
            onSectionChange(section.id);
            if (isMobile) setMobileOpen(false);
          }}
          sx={{
            mx: 1,
            mb: 0.5,
            borderRadius: 2,
            minHeight: 44,
            justifyContent: collapsed && !isMobile ? 'center' : 'flex-start',
            px: collapsed && !isMobile ? 1 : 2,
            '&.Mui-selected': {
              bgcolor: 'rgba(79, 195, 247, 0.12)',
              borderLeft: `3px solid ${colors.primary}`,
              '&:hover': { bgcolor: 'rgba(79, 195, 247, 0.18)' },
            },
          }}
        >
          <ListItemIcon
            sx={{
              minWidth: collapsed && !isMobile ? 0 : 40,
              color: selected ? colors.primary : colors.textSecondary,
              justifyContent: 'center',
            }}
          >
            <Badge badgeContent={badge} color="error" max={99} invisible={!badge}>
              <Icon fontSize="small" />
            </Badge>
          </ListItemIcon>
          {(!collapsed || isMobile) && (
            <ListItemText
              primary={section.label}
              primaryTypographyProps={{
                fontSize: '0.875rem',
                fontWeight: selected ? 600 : 500,
                color: selected ? colors.textPrimary : colors.textSecondary,
              }}
            />
          )}
        </ListItemButton>
      );
      return items;
    });
  };

  const drawer = (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: colors.bgSidebar,
        borderRight: `1px solid ${colors.border}`,
      }}
    >
      <Toolbar
        sx={{
          minHeight: { xs: 56, sm: 64 },
          px: collapsed && !isMobile ? 1 : 2,
          justifyContent: collapsed && !isMobile ? 'center' : 'space-between',
        }}
      >
        {(!collapsed || isMobile) && (
          <Box>
            <Typography variant="subtitle1" fontWeight={700} letterSpacing="0.04em">
              The Eyes
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Surveillance
            </Typography>
          </Box>
        )}
        {!isMobile && (
          <IconButton size="small" onClick={() => setCollapsed((v) => !v)} aria-label="Toggle sidebar">
            {collapsed ? <ChevronRightIcon fontSize="small" /> : <ChevronLeftIcon fontSize="small" />}
          </IconButton>
        )}
      </Toolbar>
      <Divider sx={{ borderColor: colors.border }} />
      <List sx={{ flex: 1, py: 1 }}>{renderNavItems()}</List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: colors.bgDefault }}>
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          width: { md: `calc(100% - ${drawerWidth}px)` },
          ml: { md: `${drawerWidth}px` },
          transition: theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
        }}
      >
        <Toolbar>
          {isMobile && (
            <IconButton color="inherit" edge="start" onClick={() => setMobileOpen(true)} sx={{ mr: 1 }}>
              <MenuIcon />
            </IconButton>
          )}
          <Typography variant="h6" component="h1" sx={{ flexGrow: 1, fontSize: { xs: '1rem', sm: '1.15rem' } }}>
            {visibleSections.find((s) => s.id === activeSection)?.label || 'Dashboard'}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ mr: 2, display: { xs: 'none', sm: 'block' } }}>
            {new Date().toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}
          </Typography>
          <Tooltip title="Refresh API status">
            <IconButton color="inherit" onClick={onRefresh} aria-label="Refresh status">
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}>
        {isMobile ? (
          <Drawer
            variant="temporary"
            open={mobileOpen}
            onClose={() => setMobileOpen(false)}
            ModalProps={{ keepMounted: true }}
            sx={{
              '& .MuiDrawer-paper': { width: layout.sidebarWidth, boxSizing: 'border-box' },
            }}
          >
            {drawer}
          </Drawer>
        ) : (
          <Drawer
            variant="permanent"
            sx={{
              '& .MuiDrawer-paper': {
                width: drawerWidth,
                boxSizing: 'border-box',
                transition: theme.transitions.create('width', {
                  easing: theme.transitions.easing.sharp,
                  duration: theme.transitions.duration.enteringScreen,
                }),
                overflowX: 'hidden',
              },
            }}
            open
          >
            {drawer}
          </Drawer>
        )}
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: { md: `calc(100% - ${drawerWidth}px)` },
          minHeight: '100vh',
        }}
      >
        <Toolbar />
        <Box sx={{ px: { xs: 2, sm: 3 }, py: 3, maxWidth: 1600, mx: 'auto' }}>{children}</Box>
      </Box>
    </Box>
  );
}
