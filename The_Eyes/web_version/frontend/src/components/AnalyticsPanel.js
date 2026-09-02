import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Box,
  IconButton,
  Paper,
  Stack,
  Typography,
  useTheme,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { AnalyticsSkeleton } from './skeletons/SurveillanceSkeletons';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { fetchJson } from '../apiConfig';

const HOURS_24 = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`);

function formatHourLabel(hourKey) {
  const [h] = hourKey.split(':');
  const d = new Date();
  d.setHours(Number(h), 0, 0, 0);
  return d.toLocaleTimeString([], { hour: 'numeric' });
}

function ChartCard({ title, subtitle, children, height = 280 }) {
  return (
    <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 2, height }}>
      <Typography variant="subtitle2" fontWeight={600}>
        {title}
      </Typography>
      {subtitle ? (
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.25, mb: 1 }}>
          {subtitle}
        </Typography>
      ) : (
        <Box sx={{ mb: 1 }} />
      )}
      <Box sx={{ height: height - (subtitle ? 72 : 56), minHeight: 188 }}>{children}</Box>
    </Paper>
  );
}

function ChartTooltip({ active, payload, label, valueLabel = 'events' }) {
  if (!active || !payload?.length) return null;
  const count = payload[0]?.value ?? 0;
  return (
    <Paper elevation={3} sx={{ px: 1.25, py: 0.75, borderRadius: 1 }}>
      <Typography variant="caption" fontWeight={600} display="block">
        {label?.includes(':') ? formatHourLabel(label) : label}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {count} {valueLabel}
      </Typography>
    </Paper>
  );
}

export default function AnalyticsPanel({ apiReachable = false }) {
  const theme = useTheme();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [summary, setSummary] = useState(null);

  const loadSummary = useCallback(async () => {
    if (!apiReachable) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchJson('/api/analytics/summary');
      setSummary(data);
    } catch (err) {
      setError(err.message || 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  }, [apiReachable]);

  useEffect(() => {
    loadSummary();
    if (!apiReachable) return undefined;
    const id = setInterval(loadSummary, 15000);
    return () => clearInterval(id);
  }, [apiReachable, loadSummary]);

  const byDay = useMemo(
    () =>
      Object.entries(summary?.motion?.by_day || {})
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([day, count]) => ({
          day: day.slice(5),
          count,
        })),
    [summary]
  );

  const byHour = useMemo(() => {
    const raw = summary?.motion?.by_hour || {};
    const rows = HOURS_24.map((hour) => ({
      hour,
      hourShort: hour.slice(0, 2),
      count: raw[hour] || 0,
    }));
    const peak = rows.reduce(
      (best, row) => (row.count > best.count ? row : best),
      { hour: '—', count: 0 }
    );
    const total = rows.reduce((sum, row) => sum + row.count, 0);
    return { rows, peak, total };
  }, [summary]);

  const hourChartSubtitle = useMemo(() => {
    if (!byHour.total) return 'No motion events yet';
    if (!byHour.peak.count) return `${byHour.total} events across the day`;
    return `Peak ${formatHourLabel(byHour.peak.hour)} · ${byHour.peak.count} events · ${byHour.total} total`;
  }, [byHour]);

  const chartAxisStyle = {
    tick: { fill: theme.palette.text.secondary, fontSize: 11 },
    axisLine: { stroke: theme.palette.divider },
    tickLine: { stroke: theme.palette.divider },
  };

  const gridStroke = theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)';

  const recordingMix = useMemo(() => {
    const recordings = summary?.recordings || {};
    return [
      { name: 'Motion', value: recordings.motion_count || 0 },
      { name: 'Continuous', value: recordings.continuous_count || 0 },
    ];
  }, [summary]);

  return (
    <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
        <Typography variant="subtitle1" fontWeight={600}>
          Analytics
        </Typography>
        <IconButton size="small" onClick={loadSummary} disabled={!apiReachable || loading}>
          <RefreshIcon fontSize="small" />
        </IconButton>
      </Box>

      {!apiReachable ? (
        <Typography variant="body2" color="text.secondary">
          Connect to API to view analytics.
        </Typography>
      ) : loading && !summary ? (
        <AnalyticsSkeleton />
      ) : error ? (
        <Typography variant="body2" color="error">
          {error}
        </Typography>
      ) : (
        <>
          <Stack direction="row" spacing={2} sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
            <Typography variant="caption" color="text.secondary">
              Motion events: {summary?.motion?.total_events || 0}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Avg duration: {summary?.motion?.avg_duration_s || 0}s
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Recordings size: {summary?.recordings?.total_size_mb || 0} MB
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Alerts: {summary?.alerts?.total_count || 0}
            </Typography>
          </Stack>

          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', md: 'repeat(3, minmax(0, 1fr))' },
              gap: 2,
            }}
          >
            <ChartCard title="Events per day">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={byDay} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
                  <CartesianGrid stroke={gridStroke} strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="day" {...chartAxisStyle} />
                  <YAxis allowDecimals={false} {...chartAxisStyle} width={32} />
                  <Tooltip content={<ChartTooltip valueLabel="events" />} />
                  <Bar dataKey="count" fill={theme.palette.primary.main} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Events by hour" subtitle={hourChartSubtitle}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={byHour.rows} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
                  <CartesianGrid stroke={gridStroke} strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="hourShort"
                    {...chartAxisStyle}
                    interval={2}
                    tickFormatter={(h) => formatHourLabel(`${h}:00`)}
                  />
                  <YAxis allowDecimals={false} {...chartAxisStyle} width={32} />
                  <Tooltip
                    content={({ active, payload }) => (
                      <ChartTooltip
                        active={active}
                        payload={payload}
                        label={payload?.[0]?.payload?.hour}
                        valueLabel="events"
                      />
                    )}
                  />
                  <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                    {byHour.rows.map((row) => (
                      <Cell
                        key={row.hour}
                        fill={
                          row.count > 0 && row.hour === byHour.peak.hour
                            ? theme.palette.warning.main
                            : row.count > 0
                              ? theme.palette.warning.light
                              : theme.palette.action.disabledBackground
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Recording mix">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Tooltip content={<ChartTooltip valueLabel="recordings" />} />
                  <Pie
                    data={recordingMix}
                    dataKey="value"
                    nameKey="name"
                    outerRadius={72}
                    fill={theme.palette.success.main}
                    stroke={theme.palette.background.paper}
                    strokeWidth={2}
                  />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>
          </Box>
        </>
      )}
    </Paper>
  );
}
