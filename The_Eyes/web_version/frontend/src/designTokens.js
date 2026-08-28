/** Shared surveillance UI tokens — keep in sync with src/gui/theme.py */
export const colors = {
  bgDefault: '#0d1117',
  bgPaper: '#161b22',
  bgElevated: '#1c2128',
  bgSidebar: '#12161c',
  primary: '#4fc3f7',
  secondary: '#81c784',
  error: '#f85149',
  warning: '#d29922',
  success: '#3fb950',
  textPrimary: '#e6edf3',
  textSecondary: '#8b949e',
  border: 'rgba(255,255,255,0.08)',
  borderSubtle: 'rgba(255,255,255,0.06)',
  zoneStroke: 'rgba(79, 195, 247, 0.85)',
  zoneFill: 'rgba(79, 195, 247, 0.12)',
  zoneDraft: 'rgba(210, 153, 34, 0.9)',
  zoneDraftFill: 'rgba(210, 153, 34, 0.1)',
};

export const layout = {
  sidebarWidth: 248,
  sidebarCollapsed: 72,
  sectionGap: 3,
  panelPadding: 2,
  contentMaxWidth: 'xl',
};

export const navSections = [
  { id: 'live', label: 'Live view', group: 'monitor' },
  { id: 'alerts', label: 'Alerts & recording', group: 'monitor' },
  { id: 'analytics', label: 'Analytics', group: 'insights' },
  { id: 'people', label: 'Known people', group: 'insights' },
  { id: 'media', label: 'Media library', group: 'data' },
];
