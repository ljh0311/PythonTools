import { useCallback, useRef, useState } from 'react';

/**
 * Optimistic UI helper — apply local state immediately, rollback on failure.
 * Keeps the dashboard feeling responsive while API calls settle.
 */
export function useOptimisticToggle(value, setValue) {
  const [pending, setPending] = useState(false);
  const rollbackRef = useRef(value);

  const run = useCallback(
    async (nextValue, request) => {
      rollbackRef.current = value;
      setValue(nextValue);
      setPending(true);
      try {
        await request(nextValue);
        return true;
      } catch (err) {
        setValue(rollbackRef.current);
        throw err;
      } finally {
        setPending(false);
      }
    },
    [setValue, value]
  );

  return { pending, run };
}

/**
 * Optimistically patch a keyed map (e.g. recordingStatus[cameraId]).
 * Returns { apply, revert, settle }.
 */
export function optimisticMapPatch(setMap, key, nextValue) {
  let previous;
  setMap((prev) => {
    previous = prev[key];
    return { ...prev, [key]: nextValue };
  });
  return {
    revert: () => setMap((prev) => ({ ...prev, [key]: previous })),
    settle: (confirmed) => {
      if (confirmed !== undefined) {
        setMap((prev) => ({ ...prev, [key]: confirmed }));
      }
    },
  };
}

/**
 * Optimistically patch an array item by id (e.g. alerts).
 */
export function optimisticListPatch(setList, id, patch) {
  let snapshot;
  setList((prev) => {
    snapshot = prev;
    return prev.map((item) => (item.id === id ? { ...item, ...patch } : item));
  });
  return {
    revert: () => setList(snapshot),
  };
}
