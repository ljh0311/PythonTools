# Mobile (iOS/Android) strategy for SmartCam

The SmartCam desktop application is built with Python and tkinter. **Tkinter does not run on iOS or Android.** To deliver SmartCam on mobile, you need a separate approach. This document outlines the main options.

## Using a phone as the camera (without a native SmartCam mobile app)

Until a packaged mobile client exists, the practical pattern is: **run SmartCam on a laptop or mini PC**, and make the phone appear as a **standard webcam / capture device** to the OS (then SmartCam uses OpenCV like any other camera). Examples users often combine:

- **Apple Continuity Camera** (iPhone as Mac webcam) — see Apple’s Mac Help: *Use your iPhone as a webcam* (`https://support.apple.com/guide/mac-help/use-iphone-as-a-webcam-mchl77879b8f/mac`).
- **Third-party “phone as webcam” apps** (USB or Wi‑Fi). Prefer **wired USB** when you need predictable latency for road-trip mounting.

Document latency, resolution, and power expectations in any user-facing trip guide; Wi‑Fi preview can be usable for framing but is weaker for continuous AI preview.

## Options

### A. Python on mobile: Kivy or BeeWare

- **Idea**: Keep Python for camera/ML logic and build a new UI layer that runs on iOS/Android.
- **Kivy**: Mature Python UI framework with multi-touch, runs on desktop and mobile. You would share or port core logic (e.g. OpenCV, detection) and implement a Kivy-based UI. Build with [buildozer](https://buildozer.readthedocs.io/) for Android and [kivy-ios](https://github.com/kivy/kivy-ios) for iOS.
- **BeeWare**: Write the app in Python and use the [Briefcase](https://briefcase.readthedocs.io/) toolchain to package for iOS and Android. UI is typically Toga (native-looking widgets).
- **Effort**: High (new UI, build/packaging, store submission).
- **Pros**: Single language (Python), potential to share some logic with the desktop app.
- **Cons**: Different UI codebase; some desktop dependencies (e.g. heavy ML stacks) may need adaptation or lighter alternatives on device.

### B. Web app + PWA

- **Idea**: Build a web front-end (e.g. React, Vue) that talks to a backend (Flask/FastAPI). Camera/ML runs on the server or via browser APIs (e.g. WebRTC, MediaDevices). Users can “Add to Home Screen” for a PWA-like experience on mobile.
- **Effort**: High (backend API, responsive web UI, hosting, optional native wrapper).
- **Pros**: One web codebase for desktop and mobile browsers; no app store required for the web version.
- **Cons**: Camera/ML either server-side (latency, cost) or limited by browser APIs; full native feel may require a thin native wrapper.

### C. Native mobile app + SmartCam backend

- **Idea**: Build a native app (React Native, Flutter, or Swift/Kotlin) that uses SmartCam as a local or cloud API. The existing Python app (or a headless service) handles camera and ML; the mobile app is the UI and control surface.
- **Effort**: High (separate mobile project, API design, deployment).
- **Pros**: Native UX and store distribution; clear separation between backend (SmartCam) and client.
- **Cons**: Two codebases; need to define and maintain the API.

## Recommended next step

1. **Choose one path** (A, B, or C) based on your priorities: maximum Python reuse (A), broad reach and one codebase (B), or best native mobile UX (C).
2. **Document the choice** in this file (e.g. “We are pursuing Option A with Kivy”) and add a short roadmap (e.g. prototype, packaging, store).
3. **Implement** in a separate repo or subfolder (e.g. `SmartCamMobile/` or `smartcam-web/`) so the main tkinter app stays unchanged until the chosen path is ready.

Until then, the main SmartCam app remains desktop- and Raspberry Pi–oriented (touch and DPAD), with mobile strategy handled via one of the options above.
