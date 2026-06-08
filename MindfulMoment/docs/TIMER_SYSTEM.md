# MindfulMoment Timer System

This document explains the comprehensive timer system implemented across both web and React Native applications for focus sessions and breaks.

## 📋 Overview

The timer system provides a complete solution for managing focus sessions, breaks, and time tracking in the MindfulMoment application. It includes:

- **Focus Sessions**: Configurable duration focus periods
- **Break Sessions**: Short and long break periods
- **Session Tracking**: Complete history and statistics
- **Real-time Updates**: Live timer display and progress
- **Settings Integration**: Works with user preferences
- **Event System**: Comprehensive callback system

## 🏗️ Architecture

### Web Application (JavaScript)
```
web-app/
├── js/timer.js                    # Timer class and functionality
└── focus-session-enhanced.php     # Enhanced focus session UI
```

### React Native Application (TypeScript)
```
react-native-app/src/
├── utils/TimerManager.ts          # Timer manager class
└── hooks/useTimer.ts              # React hooks for timer usage
```

## ⚙️ Timer Features

### Core Functionality
- **Start/Stop/Pause/Resume**: Full timer control
- **Configurable Duration**: Custom session lengths
- **Progress Tracking**: Visual progress indicators
- **Session History**: Complete session records
- **Statistics**: Focus time and session analytics
- **Auto-break**: Automatic break after focus sessions
- **Sound Notifications**: Audio alerts on completion

### Session Types
- **Focus Sessions**: Main productivity periods
- **Break Sessions**: Short rest periods
- **Long Break Sessions**: Extended rest periods

## 🌐 Web Application Usage

### Basic Timer Usage

```javascript
// Get timer instance
const timer = window.timer;

// Start a focus session
timer.startFocusSession(25); // 25 minutes

// Start a break session
timer.startBreakSession(5); // 5 minutes

// Control the timer
timer.pause();
timer.resume();
timer.stop();
timer.reset();
```

### Event Handling

```javascript
// Set up event handlers
timer.onTick = function(data) {
    console.log('Time remaining:', data.remaining);
    console.log('Progress:', data.progress + '%');
};

timer.onStart = function(session) {
    console.log('Session started:', session.type);
};

timer.onComplete = function(session) {
    console.log('Session completed:', session.type);
    // Play notification sound
    playNotificationSound();
};

timer.onPause = function(session) {
    console.log('Session paused');
};

timer.onResume = function(session) {
    console.log('Session resumed');
};

timer.onStop = function(session) {
    console.log('Session stopped');
};
```

### Session Management

```javascript
// Get session statistics
const stats = timer.getSessionStats();
console.log('Total focus time:', stats.totalFocusTime + ' minutes');
console.log('Sessions completed:', stats.totalSessions);

// Get today's sessions
const todaySessions = timer.getTodaySessions();

// Get weekly sessions
const weeklySessions = timer.getWeeklySessions();

// Export/Import sessions
const sessionData = timer.exportSessions();
timer.importSessions(sessionData);
```

### Utility Methods

```javascript
// Format time display
const timeString = timer.getFormattedTime(); // "25:00"
const customTime = timer.getFormattedTime(1500); // "25:00"

// Get progress percentage
const progress = timer.getProgress(); // 0-100

// Check timer status
const isActive = timer.isActive();
const isPaused = timer.isPausedState();

// Get time values
const remaining = timer.getRemainingTime(); // seconds
const elapsed = timer.getElapsedTime(); // seconds
```

## 📱 React Native Usage

### Basic Timer Usage

```typescript
import { useTimer } from '../hooks/useTimer';

function FocusScreen() {
  const {
    timerData,
    isRunning,
    isPaused,
    startFocusSession,
    startBreakSession,
    pause,
    resume,
    stop,
    reset
  } = useTimer();

  const handleStartFocus = () => {
    startFocusSession(25); // 25 minutes
  };

  const handleStartBreak = () => {
    startBreakSession(5); // 5 minutes
  };

  return (
    <View>
      <Text>{timerData.formattedTime}</Text>
      <Text>Progress: {timerData.progress}%</Text>
      
      {!isRunning && (
        <Button title="Start Focus" onPress={handleStartFocus} />
      )}
      
      {isRunning && !isPaused && (
        <Button title="Pause" onPress={pause} />
      )}
      
      {isPaused && (
        <Button title="Resume" onPress={resume} />
      )}
    </View>
  );
}
```

### Session Statistics

```typescript
import { useSessionStats } from '../hooks/useTimer';

function StatsScreen() {
  const stats = useSessionStats();

  return (
    <View>
      <Text>Total Sessions: {stats.totalSessions}</Text>
      <Text>Focus Time: {stats.totalFocusTime}m</Text>
      <Text>Break Time: {stats.totalBreakTime}m</Text>
      <Text>Average Focus: {stats.averageFocusTime}m</Text>
    </View>
  );
}
```

### Session History

```typescript
import { useTodaySessions, useWeeklySessions } from '../hooks/useTimer';

function HistoryScreen() {
  const todaySessions = useTodaySessions();
  const weeklySessions = useWeeklySessions();

  return (
    <View>
      <Text>Today's Sessions: {todaySessions.length}</Text>
      <Text>Weekly Sessions: {weeklySessions.length}</Text>
      
      {todaySessions.map(session => (
        <View key={session.id}>
          <Text>{session.type}: {session.duration}m</Text>
          <Text>Status: {session.completed ? 'Completed' : 'Stopped'}</Text>
        </View>
      ))}
    </View>
  );
}
```

### Individual Timer Hooks

```typescript
import { 
  useFormattedTime, 
  useTimerProgress, 
  useSessionType,
  useTimerActive,
  useTimerPaused 
} from '../hooks/useTimer';

function TimerDisplay() {
  const formattedTime = useFormattedTime();
  const progress = useTimerProgress();
  const sessionType = useSessionType();
  const isActive = useTimerActive();
  const isPaused = useTimerPaused();

  return (
    <View>
      <Text style={{ fontSize: 48 }}>{formattedTime}</Text>
      <Text>Progress: {progress.toFixed(1)}%</Text>
      <Text>Type: {sessionType}</Text>
      <Text>Status: {isActive ? (isPaused ? 'Paused' : 'Running') : 'Stopped'}</Text>
    </View>
  );
}
```

## 🎨 UI Integration

### Web Application UI

The enhanced focus session page includes:

- **Large Timer Display**: Prominent time display with progress bar
- **Control Buttons**: Start, pause, resume, stop, reset
- **Session Configuration**: Duration and break settings
- **Quick Actions**: Pre-configured session lengths
- **Statistics Display**: Today's progress and session counts
- **Session History**: Recent sessions with status
- **Motivational Quotes**: Inspirational content

### React Native UI Components

```typescript
// Timer display component
function TimerDisplay({ time, progress, sessionType }) {
  return (
    <View style={styles.timerContainer}>
      <Text style={styles.timerText}>{time}</Text>
      <Text style={styles.sessionType}>{sessionType}</Text>
      <ProgressBar progress={progress} />
    </View>
  );
}

// Control buttons component
function TimerControls({ isRunning, isPaused, onStart, onPause, onResume, onStop }) {
  return (
    <View style={styles.controls}>
      {!isRunning && <Button title="Start" onPress={onStart} />}
      {isRunning && !isPaused && <Button title="Pause" onPress={onPause} />}
      {isPaused && <Button title="Resume" onPress={onResume} />}
      {isRunning && <Button title="Stop" onPress={onStop} />}
    </View>
  );
}
```

## 🔧 Configuration

### Settings Integration

The timer system integrates with the settings system:

```javascript
// Web - Get settings from settings manager
const sessionDuration = window.settingsManager.getFocusSessionDuration();
const breakDuration = window.settingsManager.getBreakDuration();
const autoStartBreak = window.settingsManager.get('focusSession.autoStartBreak');

// React Native - Use settings hooks
const sessionDuration = useFocusSessionDuration();
const breakDuration = useBreakDuration();
const autoStartBreak = useSetting('focusSession.autoStartBreak', true);
```

### Default Values

- **Focus Session**: 25 minutes (configurable)
- **Break Duration**: 5 minutes (configurable)
- **Auto-start Break**: Enabled (configurable)
- **Sound Notifications**: Enabled (configurable)

## 📊 Session Data Structure

### Session Object

```typescript
interface Session {
  id: number;              // Unique session ID
  type: 'focus' | 'break' | 'longBreak';
  duration: number;        // Duration in minutes
  startTime: Date;         // Session start time
  endTime?: Date;          // Session end time
  completed: boolean;      // Whether session was completed
  paused: boolean;         // Whether session was paused
  pauseTime: number;       // Timestamp when paused
  currentTime?: number;    // Current time in seconds
}
```

### Timer Data Object

```typescript
interface TimerData {
  currentTime: number;     // Current time in seconds
  totalTime: number;       // Total session time in seconds
  remaining: number;       // Remaining time in seconds
  elapsed: number;         // Elapsed time in seconds
  progress: number;        // Progress percentage (0-100)
  sessionType: string;     // Session type
  session: Session | null; // Current session object
}
```

### Session Statistics

```typescript
interface SessionStats {
  totalSessions: number;     // Total completed sessions
  focusSessions: number;     // Number of focus sessions
  breakSessions: number;     // Number of break sessions
  totalFocusTime: number;    // Total focus time in minutes
  totalBreakTime: number;    // Total break time in minutes
  averageFocusTime: number;  // Average focus session length
}
```

## 🔄 Event System

### Web Application Events

```javascript
// Timer events
timer.onTick = (data) => { /* Update UI */ };
timer.onStart = (session) => { /* Session started */ };
timer.onPause = (session) => { /* Session paused */ };
timer.onResume = (session) => { /* Session resumed */ };
timer.onStop = (session) => { /* Session stopped */ };
timer.onComplete = (session) => { /* Session completed */ };
```

### React Native Events

Events are handled automatically through the hooks system:

```typescript
// Hooks automatically update when events occur
const { timerData, isRunning, isPaused } = useTimer();
const stats = useSessionStats();
const sessions = useTodaySessions();
```

## 🚀 Best Practices

### 1. Use Hooks in React Native
```typescript
// ✅ Good - Use hooks for automatic updates
const { timerData, startFocusSession } = useTimer();

// ❌ Avoid - Direct timer manager usage
const timer = timerManager;
```

### 2. Handle Timer States
```typescript
// ✅ Good - Check timer state before actions
if (!isRunning) {
  startFocusSession();
} else if (isPaused) {
  resume();
} else {
  pause();
}
```

### 3. Clean Up Event Handlers
```typescript
// ✅ Good - Clean up in useEffect
useEffect(() => {
  timerManager.onTick(updateUI);
  return () => timerManager.removeOnTick();
}, []);
```

### 4. Use Settings Integration
```typescript
// ✅ Good - Use settings for configuration
const duration = useFocusSessionDuration();
startFocusSession(duration);

// ❌ Avoid - Hard-coded values
startFocusSession(25);
```

## 📱 Mobile-Specific Features

### Background Timer Support
The React Native timer continues running in the background and can trigger notifications when sessions complete.

### Haptic Feedback
```typescript
import { Haptics } from 'expo-haptics';

// Trigger haptic feedback on session completion
timerManager.onComplete(() => {
  Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
});
```

### Local Notifications
```typescript
import * as Notifications from 'expo-notifications';

// Schedule notification for session completion
timerManager.onComplete((session) => {
  Notifications.scheduleNotificationAsync({
    content: {
      title: 'Session Complete!',
      body: `${session.type} session finished`,
    },
    trigger: null, // Immediate
  });
});
```

## 🔍 Debugging

### Web Application
```javascript
// Check timer state
console.log('Timer active:', timer.isActive());
console.log('Timer paused:', timer.isPausedState());
console.log('Current time:', timer.getFormattedTime());
console.log('Progress:', timer.getProgress());

// Check sessions
console.log('All sessions:', timer.sessions);
console.log('Today sessions:', timer.getTodaySessions());
console.log('Session stats:', timer.getSessionStats());
```

### React Native
```typescript
// Use React DevTools or console.log
const { timerData, isRunning } = useTimer();
console.log('Timer data:', timerData);
console.log('Is running:', isRunning);

// Check timer manager directly
console.log('Timer active:', timerManager.isActive());
console.log('Current session:', timerManager.getCurrentSession());
```

## 📚 API Reference

### TimerManager Methods (React Native)

#### Control Methods
- `startFocusSession(duration?)` - Start focus session
- `startBreakSession(duration?, type?)` - Start break session
- `pause()` - Pause timer
- `resume()` - Resume timer
- `stop()` - Stop timer
- `reset()` - Reset timer
- `setDuration(seconds)` - Set timer duration

#### Status Methods
- `isActive()` - Check if timer is running
- `isPausedState()` - Check if timer is paused
- `getRemainingTime()` - Get remaining time in seconds
- `getElapsedTime()` - Get elapsed time in seconds
- `getProgress()` - Get progress percentage
- `getFormattedTime(seconds?)` - Get formatted time string

#### Session Methods
- `getCurrentSession()` - Get current session
- `getSessionStats()` - Get session statistics
- `getTodaySessions()` - Get today's sessions
- `getWeeklySessions()` - Get weekly sessions
- `exportSessions()` - Export sessions as JSON
- `importSessions(jsonString)` - Import sessions from JSON
- `clearSessions()` - Clear all sessions

#### Event Methods
- `onTick(callback)` - Set tick callback
- `onStart(callback)` - Set start callback
- `onPause(callback)` - Set pause callback
- `onResume(callback)` - Set resume callback
- `onStop(callback)` - Set stop callback
- `onComplete(callback)` - Set complete callback
- `removeOnTick()` - Remove tick callback
- `removeAllHandlers()` - Remove all callbacks

### React Hooks

#### Main Hook
- `useTimer()` - Main timer hook with all functionality

#### Individual Hooks
- `useSessionStats()` - Session statistics
- `useTodaySessions()` - Today's sessions
- `useWeeklySessions()` - Weekly sessions
- `useCurrentSession()` - Current session
- `useTimerActive()` - Timer active state
- `useTimerPaused()` - Timer paused state
- `useFormattedTime()` - Formatted time string
- `useTimerProgress()` - Timer progress percentage
- `useRemainingTime()` - Remaining time in seconds
- `useElapsedTime()` - Elapsed time in seconds
- `useSessionType()` - Current session type

#### Utility Hooks
- `useExportSessions()` - Export sessions function
- `useImportSessions()` - Import sessions function
- `useClearSessions()` - Clear sessions function 