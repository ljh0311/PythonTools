/**
 * Browser camera stream ownership — keeps MediaStreams alive across React
 * remounts, serializes getUserMedia (Windows exclusive locks), and skips
 * virtual cams that steal the physical device (NVIDIA Broadcast, OBS, etc.).
 */

const VIRTUAL_CAMERA_RE =
  /nvidia\s*broadcast|obs\s*virtual|virtual\s*camera|snap\s*camera|manycam|xsplit|droidcam|iriun|epoccam|ndi\s*video|unity\s*capture|cam\s*link\s*virtual/i;

/** @type {Map<string, MediaStream>} */
const streams = new Map();

/** @type {Map<string, number>} */
const acquireGeneration = new Map();

let acquireChain = Promise.resolve();

export function isVirtualCameraLabel(label = '') {
  return VIRTUAL_CAMERA_RE.test(String(label));
}

export function sameBrowserDeviceList(a = [], b = []) {
  if (a.length !== b.length) return false;
  return a.every((dev, i) => {
    const other = b[i];
    return (
      (dev.canonicalId || dev.deviceId) === (other.canonicalId || other.deviceId) &&
      (dev.originalDeviceId || '') === (other.originalDeviceId || '') &&
      Boolean(dev.isVirtual) === Boolean(other.isVirtual)
    );
  });
}

export function getOwnedStream(cameraId) {
  return streams.get(cameraId) || null;
}

export function hasLiveStream(cameraId) {
  const stream = streams.get(cameraId);
  if (!stream) return false;
  return stream.getTracks().some((t) => t.readyState === 'live');
}

export function attachStreamToVideo(cameraId, videoEl) {
  if (!videoEl) return false;
  const stream = streams.get(cameraId);
  if (!stream) return false;
  if (videoEl.srcObject !== stream) {
    videoEl.srcObject = stream;
  }
  return true;
}

export function releaseStream(cameraId) {
  const stream = streams.get(cameraId);
  if (!stream) return;
  stream.getTracks().forEach((track) => {
    try {
      track.stop();
    } catch {
      /* ignore */
    }
  });
  streams.delete(cameraId);
  acquireGeneration.delete(cameraId);
}

export function releaseAllStreams() {
  [...streams.keys()].forEach(releaseStream);
}

function friendlyAcquireError(err) {
  const name = err?.name || '';
  const message = err?.message || String(err);
  if (name === 'NotReadableError' || /device in use|in use/i.test(message)) {
    return {
      code: 'device_in_use',
      message:
        'Camera is in use by another app (often NVIDIA Broadcast, Zoom, or the desktop GUI). Close that app or turn that virtual camera off.',
    };
  }
  if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
    return { code: 'permission', message: 'Camera permission blocked in the browser.' };
  }
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
    return { code: 'not_found', message: 'No camera found for this device.' };
  }
  if (name === 'OverconstrainedError') {
    return { code: 'overconstrained', message: 'Camera does not support the requested settings.' };
  }
  return { code: 'unknown', message: message || 'Failed to open camera.' };
}

async function openUserMedia(mediaDeviceId) {
  const base = { width: { ideal: 640 }, height: { ideal: 480 } };
  const attempts = [];
  if (mediaDeviceId && !String(mediaDeviceId).startsWith('camera_') && !String(mediaDeviceId).startsWith('webcam_')) {
    attempts.push({ video: { ...base, deviceId: { exact: mediaDeviceId } } });
    attempts.push({ video: { ...base, deviceId: { ideal: mediaDeviceId } } });
  }
  attempts.push({ video: base });

  let lastErr;
  for (const constraints of attempts) {
    try {
      return await navigator.mediaDevices.getUserMedia(constraints);
    } catch (err) {
      lastErr = err;
      if (err?.name === 'NotAllowedError' || err?.name === 'PermissionDeniedError') {
        throw err;
      }
    }
  }
  throw lastErr || new Error('getUserMedia failed');
}

/**
 * Acquire a live MediaStream for a browser camera (serialized).
 * @returns {Promise<{ stream: MediaStream, reused: boolean }>}
 */
export function acquireCameraStream(device, { onTrackEnded } = {}) {
  const cameraId = device.canonicalId || device.deviceId;
  const generation = (acquireGeneration.get(cameraId) || 0) + 1;
  acquireGeneration.set(cameraId, generation);

  const run = async () => {
    if (acquireGeneration.get(cameraId) !== generation) {
      return { stream: streams.get(cameraId), reused: true, cancelled: true };
    }

    if (hasLiveStream(cameraId)) {
      return { stream: streams.get(cameraId), reused: true };
    }

    // Stale dead stream
    if (streams.has(cameraId)) {
      releaseStream(cameraId);
    }

    const mediaDeviceId = device.originalDeviceId || device.deviceId;
    let stream;
    try {
      stream = await openUserMedia(mediaDeviceId);
    } catch (err) {
      const info = friendlyAcquireError(err);
      const wrapped = new Error(info.message);
      wrapped.code = info.code;
      wrapped.cause = err;
      throw wrapped;
    }

    if (acquireGeneration.get(cameraId) !== generation) {
      stream.getTracks().forEach((t) => t.stop());
      return { stream: null, reused: false, cancelled: true };
    }

    stream.getTracks().forEach((track) => {
      track.addEventListener('ended', () => {
        if (streams.get(cameraId) === stream) {
          streams.delete(cameraId);
        }
        onTrackEnded?.(cameraId, device);
      });
    });

    streams.set(cameraId, stream);
    return { stream, reused: false };
  };

  const queued = acquireChain.then(run, run);
  acquireChain = queued.then(
    () => undefined,
    () => undefined
  );
  return queued;
}
