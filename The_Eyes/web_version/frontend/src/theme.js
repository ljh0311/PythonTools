import { createTheme } from '@mui/material/styles';
import { colors } from './designTokens';

/** Dark monitoring dashboard — high contrast feeds, muted chrome */
export const surveillanceTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: colors.primary },
    secondary: { main: colors.secondary },
    background: {
      default: colors.bgDefault,
      paper: colors.bgPaper,
    },
    text: {
      primary: colors.textPrimary,
      secondary: colors.textSecondary,
    },
    divider: colors.border,
    error: { main: colors.error },
    warning: { main: colors.warning },
    success: { main: colors.success },
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: '"Segoe UI", system-ui, -apple-system, sans-serif',
    h6: { fontWeight: 600, letterSpacing: '0.02em' },
    subtitle2: { fontWeight: 600 },
  },
  components: {
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundImage: `linear-gradient(90deg, ${colors.bgPaper} 0%, ${colors.bgElevated} 100%)`,
          borderBottom: `1px solid ${colors.border}`,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: `linear-gradient(180deg, ${colors.bgElevated} 0%, ${colors.bgPaper} 100%)`,
          border: `1px solid ${colors.borderSubtle}`,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 600 },
      },
    },
    MuiSkeleton: {
      styleOverrides: {
        root: {
          backgroundColor: 'rgba(255,255,255,0.06)',
          '&::after': {
            background: `linear-gradient(90deg, transparent, rgba(79,195,247,0.08), transparent)`,
          },
        },
      },
    },
  },
});
