import React, { useCallback, useRef, useState } from 'react';
import { Box } from '@mui/material';
import { colors } from '../designTokens';

const ZONE_COLOR = colors.zoneStroke;
const ZONE_FILL = colors.zoneFill;
const DRAFT_COLOR = colors.zoneDraft;

function clamp01(value) {
  return Math.max(0, Math.min(1, value));
}

function normalizeRect(x1, y1, x2, y2, width, height) {
  const left = Math.min(x1, x2);
  const top = Math.min(y1, y2);
  const right = Math.max(x1, x2);
  const bottom = Math.max(y1, y2);
  if (right - left < 4 || bottom - top < 4) return null;
  return [
    clamp01(left / width),
    clamp01(top / height),
    clamp01((right - left) / width),
    clamp01((bottom - top) / height),
  ];
}

export default function ZoneEditor({
  zones = [],
  editable = false,
  showOutlines = true,
  onChange,
  onSelectZone,
}) {
  const containerRef = useRef(null);
  const [draft, setDraft] = useState(null);
  const [dragStart, setDragStart] = useState(null);

  const getLocalPoint = useCallback((event) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return null;
    return {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
      width: rect.width,
      height: rect.height,
    };
  }, []);

  const handlePointerDown = (event) => {
    if (!editable) return;
    event.preventDefault();
    const pt = getLocalPoint(event);
    if (!pt) return;
    setDragStart(pt);
    setDraft({ x1: pt.x, y1: pt.y, x2: pt.x, y2: pt.y });
  };

  const handlePointerMove = (event) => {
    if (!editable || !dragStart) return;
    const pt = getLocalPoint(event);
    if (!pt) return;
    setDraft({ x1: dragStart.x, y1: dragStart.y, x2: pt.x, y2: pt.y });
  };

  const finishDraw = useCallback(() => {
    if (!editable || !draft || !containerRef.current) {
      setDragStart(null);
      setDraft(null);
      return;
    }
    const rect = containerRef.current.getBoundingClientRect();
    const normalized = normalizeRect(
      draft.x1,
      draft.y1,
      draft.x2,
      draft.y2,
      rect.width,
      rect.height
    );
    if (normalized) {
      onChange?.([...zones, normalized]);
    }
    setDragStart(null);
    setDraft(null);
  }, [draft, editable, onChange, zones]);

  const handlePointerUp = () => {
    finishDraw();
  };

  const handleZoneClick = (event, index) => {
    event.stopPropagation();
    onSelectZone?.(index);
  };

  if (!showOutlines && !editable) return null;

  return (
    <Box
      ref={containerRef}
      sx={{
        position: 'absolute',
        inset: 0,
        zIndex: 4,
        cursor: editable ? 'crosshair' : 'default',
        touchAction: 'none',
      }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerLeave={handlePointerUp}
    >
      {showOutlines &&
        zones.map((zone, index) => {
          const [x, y, w, h] = zone;
          return (
            <Box
              key={`zone-${index}`}
              onClick={(e) => handleZoneClick(e, index)}
              sx={{
                position: 'absolute',
                left: `${x * 100}%`,
                top: `${y * 100}%`,
                width: `${w * 100}%`,
                height: `${h * 100}%`,
                border: `2px solid ${ZONE_COLOR}`,
                bgcolor: ZONE_FILL,
                pointerEvents: editable ? 'auto' : 'none',
                boxSizing: 'border-box',
              }}
            />
          );
        })}

      {editable && draft && (
        <Box
          sx={{
            position: 'absolute',
            left: Math.min(draft.x1, draft.x2),
            top: Math.min(draft.y1, draft.y2),
            width: Math.abs(draft.x2 - draft.x1),
            height: Math.abs(draft.y2 - draft.y1),
            border: `2px dashed ${DRAFT_COLOR}`,
            bgcolor: colors.zoneDraftFill,
            pointerEvents: 'none',
          }}
        />
      )}
    </Box>
  );
}
