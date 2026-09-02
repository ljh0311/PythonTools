import React from 'react';
import { Box, Card, CardContent, Grid, Paper, Skeleton, Stack } from '@mui/material';

/** Shimmering placeholder matching a live camera tile */
export function CameraFeedSkeleton() {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1, gap: 1 }}>
          <Skeleton variant="text" width="45%" height={24} />
          <Stack direction="row" spacing={0.75}>
            <Skeleton variant="rounded" width={36} height={22} />
            <Skeleton variant="rounded" width={64} height={22} />
          </Stack>
        </Box>
        <Skeleton
          variant="rounded"
          sx={{ width: '100%', aspectRatio: '16 / 9', borderRadius: 2 }}
          animation="wave"
        />
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 0.5, mt: 1 }}>
          <Skeleton variant="circular" width={28} height={28} />
          <Skeleton variant="circular" width={28} height={28} />
          <Skeleton variant="circular" width={28} height={28} />
        </Box>
      </CardContent>
    </Card>
  );
}

/** Grid of camera skeletons for first paint / detecting cameras */
export function LiveViewSkeleton({ count = 2, cols = 2 }) {
  return (
    <Box>
      <Skeleton variant="rounded" height={52} sx={{ mb: 2, borderRadius: 2 }} animation="wave" />
      <Skeleton variant="rounded" height={64} sx={{ mb: 2, borderRadius: 2 }} animation="wave" />
      <Grid container spacing={2}>
        {Array.from({ length: count }).map((_, i) => (
          <Grid item xs={12} sm={6} md={12 / cols} key={`cam-skel-${i}`}>
            <CameraFeedSkeleton />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}

export function AnalyticsSkeleton() {
  return (
    <Box>
      <Stack direction="row" spacing={2} sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
        {[90, 110, 120, 70].map((w) => (
          <Skeleton key={w} variant="text" width={w} height={18} />
        ))}
      </Stack>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', md: 'repeat(3, minmax(0, 1fr))' },
          gap: 2,
        }}
      >
        {[1, 2, 3].map((i) => (
          <Box key={i} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 1.5 }}>
            <Skeleton variant="text" width="50%" height={20} sx={{ mb: 1 }} />
            <Skeleton variant="rounded" height={160} animation="wave" />
          </Box>
        ))}
      </Box>
    </Box>
  );
}

export function KnownPeopleSkeleton() {
  return (
    <Box>
      <Box
        sx={{
          display: 'grid',
          gap: 1.5,
          gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
          mb: 2,
        }}
      >
        <Skeleton variant="rounded" height={40} />
        <Skeleton variant="rounded" height={40} />
      </Box>
      <Stack direction="row" spacing={1.5} sx={{ mb: 2 }}>
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} variant="rounded" width={72} height={72} />
        ))}
      </Stack>
      <Skeleton variant="rounded" height={120} animation="wave" />
    </Box>
  );
}

export function MediaLibrarySkeleton({ cards = 6 }) {
  return (
    <Box>
      <Stack direction="row" spacing={1} sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
        <Skeleton variant="rounded" width={120} height={36} />
        <Skeleton variant="rounded" width={140} height={36} />
        <Skeleton variant="rounded" width={100} height={36} />
      </Stack>
      <Grid container spacing={2}>
        {Array.from({ length: cards }).map((_, i) => (
          <Grid item xs={12} sm={6} md={4} key={`media-skel-${i}`}>
            <Skeleton variant="rounded" sx={{ width: '100%', aspectRatio: '16 / 10' }} animation="wave" />
            <Skeleton variant="text" width="70%" sx={{ mt: 1 }} />
            <Skeleton variant="text" width="40%" />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}

export function AlertsPanelSkeleton() {
  return (
    <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2 }}>
      <Skeleton variant="text" width={160} height={28} sx={{ mb: 2 }} />
      {[1, 2, 3].map((i) => (
        <Skeleton key={i} variant="rounded" height={56} sx={{ mb: 1 }} animation="wave" />
      ))}
    </Paper>
  );
}

export function RecordingControlsSkeleton() {
  return (
    <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2 }}>
      <Skeleton variant="text" width={180} height={28} sx={{ mb: 1 }} />
      <Skeleton variant="text" width="90%" height={18} sx={{ mb: 2 }} />
      <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap" useFlexGap>
        <Skeleton variant="rounded" width={120} height={36} />
        <Skeleton variant="rounded" width={160} height={32} />
        <Skeleton variant="rounded" width={180} height={32} />
      </Stack>
    </Paper>
  );
}
