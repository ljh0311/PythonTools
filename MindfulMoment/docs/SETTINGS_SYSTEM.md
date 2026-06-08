# MindfulMoment Settings System

This document explains how to use the comprehensive settings system implemented across both the web and React Native applications.

## 📋 Overview

The settings system provides a unified way to manage user preferences across the entire MindfulMoment application. It supports:

- **Persistent Storage**: Settings are saved and restored between sessions
- **Type Safety**: Full TypeScript support in React Native
- **Real-time Updates**: UI automatically updates when settings change
- **Import/Export**: Users can backup and restore their settings
- **Default Values**: Sensible defaults for all settings

## 🏗️ Architecture

### Web Application (PHP/JavaScript)
```
web-app/
├── config/settings.php          # PHP settings manager
├── api/settings.php             # REST API endpoint
├── js/settings.js               # JavaScript settings manager
└── settings-page.php            # Settings UI page
```

### React Native Application (TypeScript)
```
react-native-app/src/
├── utils/SettingsManager.ts     # TypeScript settings manager
└── hooks/useSettings.ts         # React hooks for settings
```

## ⚙️ Settings Structure

All settings follow this structure:

```json
{
  "theme": "light",
  "notifications": {
    "enabled": true,
    "reminders": true,
    "sound": true
  },
  "privacy": {
    "tracking": false,
    "shareUsageStats": false,
    "anonymousMode": true
  },
  "focusSession": {
    "defaultDurationMinutes": 25,
    "autoStartBreak": true,
    "breakDurationMinutes": 5
  },
  "insights": {
    "showWeeklySummary": true,
    "showMonthlySummary": true
  },
  "community": {
    "showLeaderboard": true,
    "showChallenges": true,
    "anonymousParticipation": true
  },
  "language": "en",
  "accessibility": {
    "fontSize": "medium",
    "highContrast": false
  }
}
```

## 🌐 Web Application Usage

### PHP Backend

```php
<?php
require_once 'config/settings.php';

// Get a setting
$theme = $settings->get('theme', 'light');
$sessionDuration = $settings->get('focusSession.defaultDurationMinutes', 25);

// Set a setting
$settings->set('theme', 'dark');
$settings->set('notifications.enabled', false);

// Get all settings
$allSettings = $settings->getAll();

// Reset to defaults
$settings->resetToDefaults();
?>
```

### JavaScript Frontend

```javascript
// Get a setting
const theme = window.settingsManager.get('theme', 'light');
const notifications = window.settingsManager.get('notifications.enabled', true);

// Set a setting
await window.settingsManager.set('theme', 'dark');
await window.settingsManager.set('notifications.enabled', false);

// Update multiple settings
await window.settingsManager.updateMultiple({
  theme: 'dark',
  'notifications.enabled': false
});

// Export/Import settings
const json = window.settingsManager.exportSettings();
await window.settingsManager.importSettings(jsonString);

// Reset to defaults
await window.settingsManager.resetToDefaults();
```

### API Endpoints

```javascript
// GET /api/settings.php - Get all settings
fetch('/api/settings.php')

// GET /api/settings.php?key=theme - Get specific setting
fetch('/api/settings.php?key=theme')

// POST /api/settings.php - Update setting
fetch('/api/settings.php', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ key: 'theme', value: 'dark' })
})

// POST /api/settings.php - Update multiple settings
fetch('/api/settings.php', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ 
    settings: { theme: 'dark', 'notifications.enabled': false } 
  })
})

// PUT /api/settings.php - Reset to defaults
fetch('/api/settings.php', { method: 'PUT' })
```

## 📱 React Native Usage

### Basic Usage

```typescript
import { settingsManager } from '../utils/SettingsManager';

// Get a setting
const theme = settingsManager.get('theme');
const sessionDuration = settingsManager.get('focusSession.defaultDurationMinutes', 25);

// Set a setting
await settingsManager.set('theme', 'dark');
await settingsManager.set('notifications.enabled', false);

// Update multiple settings
await settingsManager.updateMultiple({
  theme: 'dark',
  notifications: { enabled: false }
});

// Reset to defaults
await settingsManager.resetToDefaults();
```

### React Hooks

```typescript
import { useSettings, useTheme, useSetting } from '../hooks/useSettings';

function MyComponent() {
  // Get all settings
  const settings = useSettings();
  
  // Get specific setting
  const theme = useTheme();
  const notifications = useSetting('notifications.enabled', true);
  
  // Get focus session duration
  const sessionDuration = useSetting('focusSession.defaultDurationMinutes', 25);
  
  return (
    <View>
      <Text>Current theme: {theme}</Text>
      <Text>Session duration: {sessionDuration} minutes</Text>
    </View>
  );
}
```

### Available Hooks

```typescript
// Basic hooks
useSettings()                    // All settings
useSetting(key, defaultValue)    // Specific setting

// Convenience hooks
useTheme()                       // Theme setting
useNotifications()               // Notification settings
usePrivacy()                     // Privacy settings
useFocusSession()                // Focus session settings
useAccessibility()               // Accessibility settings
useCommunity()                   // Community settings
useInsights()                    // Insights settings
useLanguage()                    // Language setting

// Specific value hooks
useNotificationsEnabled()        // Boolean
useFocusSessionDuration()        // Number
useBreakDuration()               // Number
useTrackingEnabled()             // Boolean
useAnonymousMode()               // Boolean
useFontSize()                    // 'small' | 'medium' | 'large'
useHighContrast()                // Boolean
```

## 🎨 Theme System

The settings system includes a comprehensive theme system:

### Web Application

```php
// PHP
$themeClass = $settings->getThemeClass(); // "theme-light", "theme-dark", etc.
$accessibilityClasses = $settings->getAccessibilityClasses(); // "font-size-medium high-contrast"
```

```javascript
// JavaScript
const themeClass = window.settingsManager.getThemeClass();
const accessibilityClasses = window.settingsManager.getAccessibilityClasses();
```

### React Native

```typescript
import { useTheme, useAccessibility } from '../hooks/useSettings';

function MyComponent() {
  const theme = useTheme();
  const accessibility = useAccessibility();
  
  const styles = {
    backgroundColor: theme === 'dark' ? '#000' : '#fff',
    fontSize: accessibility.fontSize === 'large' ? 18 : 14,
  };
  
  return <View style={styles}>...</View>;
}
```

## 🔄 Settings Change Events

### Web Application

```javascript
// Listen for settings changes
window.addEventListener('settingsChanged', (event) => {
  const { settings } = event.detail;
  console.log('Settings updated:', settings);
});
```

### React Native

```typescript
import { settingsManager } from '../utils/SettingsManager';

// Add listener
const unsubscribe = settingsManager.addListener((settings) => {
  console.log('Settings updated:', settings);
});

// Remove listener
unsubscribe();
```

## 💾 Storage

### Web Application
- **File-based**: Settings stored in `user_settings.json`
- **Server-side**: PHP manages file I/O
- **Client-side**: JavaScript communicates via API

### React Native
- **AsyncStorage**: Settings stored in device storage
- **Key**: `@MindfulMoment:settings`
- **Automatic**: Settings persist between app launches

## 🔧 Configuration

### Default Settings

Default settings are defined in:
- **Web**: `web-app/config/settings.php` (PHP array)
- **React Native**: `react-native-app/src/utils/SettingsManager.ts` (TypeScript object)

### Validation

The system includes validation for:
- **Type checking**: TypeScript ensures type safety
- **Range validation**: Numeric values have min/max limits
- **Enum validation**: Theme, font size, etc. have specific allowed values

## 🚀 Best Practices

### 1. Use Hooks in React Native
```typescript
// ✅ Good
const theme = useTheme();
const notifications = useNotificationsEnabled();

// ❌ Avoid
const theme = settingsManager.get('theme');
```

### 2. Provide Default Values
```typescript
// ✅ Good
const duration = useSetting('focusSession.defaultDurationMinutes', 25);

// ❌ Avoid
const duration = useSetting('focusSession.defaultDurationMinutes');
```

### 3. Batch Updates
```typescript
// ✅ Good - Single update
await settingsManager.updateMultiple({
  theme: 'dark',
  'notifications.enabled': false
});

// ❌ Avoid - Multiple updates
await settingsManager.set('theme', 'dark');
await settingsManager.set('notifications.enabled', false);
```

### 4. Error Handling
```typescript
// ✅ Good
try {
  await settingsManager.set('theme', 'dark');
} catch (error) {
  console.error('Failed to update theme:', error);
}

// ✅ Good - Check return value
const success = await settingsManager.set('theme', 'dark');
if (!success) {
  console.error('Failed to update theme');
}
```

## 📝 Migration Guide

### From Old Settings System

If you have an existing settings system:

1. **Export old settings** to JSON format
2. **Map to new structure** using the settings interface
3. **Import using the new system**:

```typescript
// React Native
await settingsManager.importSettings(oldSettingsJson);

// Web
await window.settingsManager.importSettings(oldSettingsJson);
```

## 🔍 Debugging

### Web Application
```javascript
// Check current settings
console.log(window.settingsManager.getAll());

// Check specific setting
console.log(window.settingsManager.get('theme'));

// Export for inspection
console.log(window.settingsManager.exportSettings());
```

### React Native
```typescript
// Check current settings
console.log(settingsManager.getAll());

// Check specific setting
console.log(settingsManager.get('theme'));

// Export for inspection
console.log(settingsManager.exportSettings());
```

## 📚 API Reference

### SettingsManager Methods

#### Web (JavaScript)
- `get(key, defaultValue)` - Get setting value
- `set(key, value)` - Set setting value
- `updateMultiple(settingsObject)` - Update multiple settings
- `resetToDefaults()` - Reset to default values
- `exportSettings()` - Export as JSON string
- `importSettings(jsonString)` - Import from JSON string
- `getAll()` - Get all settings
- `getThemeClass()` - Get theme CSS class
- `getAccessibilityClasses()` - Get accessibility CSS classes

#### React Native (TypeScript)
- `get<K>(key, defaultValue?)` - Get setting value
- `set<K>(key, value)` - Set setting value
- `updateMultiple(updates)` - Update multiple settings
- `resetToDefaults()` - Reset to default values
- `exportSettings()` - Export as JSON string
- `importSettings(jsonString)` - Import from JSON string
- `getAll()` - Get all settings
- `addListener(listener)` - Add change listener
- `getTheme()` - Get theme setting
- `setTheme(theme)` - Set theme setting

### React Hooks
- `useSettings()` - All settings
- `useSetting<T>(key, defaultValue?)` - Specific setting
- `useTheme()` - Theme setting
- `useNotifications()` - Notification settings
- `usePrivacy()` - Privacy settings
- `useFocusSession()` - Focus session settings
- `useAccessibility()` - Accessibility settings
- `useCommunity()` - Community settings
- `useInsights()` - Insights settings
- `useLanguage()` - Language setting 