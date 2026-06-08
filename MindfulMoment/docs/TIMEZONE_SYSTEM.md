# Timezone System

## Overview

The MindfulMoment timezone system provides automatic timezone detection and management, ensuring that all time-related features display correctly according to the user's local timezone. The system automatically detects the user's timezone from their device and applies it throughout the application.

## Features

### 1. Automatic Timezone Detection
- **Browser Detection**: Uses `Intl.DateTimeFormat().resolvedOptions().timeZone` for automatic detection
- **Device Location**: Detects timezone based on device settings
- **Fallback Support**: Graceful fallback to UTC if detection fails
- **Real-time Updates**: Live time display with current timezone

### 2. Timezone Management
- **Manual Selection**: Users can manually select their timezone
- **Auto-detect Button**: One-click timezone detection and application
- **Comprehensive List**: Support for 200+ timezones worldwide
- **Persistent Settings**: Timezone preferences saved and restored

### 3. Time Display Features
- **Local Time Formatting**: All times displayed in user's local timezone
- **Relative Time**: "2 hours ago", "yesterday", etc.
- **Multiple Formats**: Date, time, datetime, and relative formats
- **Real-time Updates**: Live clock with current local time

### 4. Timezone Conversion
- **Cross-timezone Support**: Convert times between different timezones
- **Session Times**: Focus session times displayed in local timezone
- **Progress Tracking**: All progress data uses local timezone
- **Notifications**: Time-based notifications use local timezone

## Technical Implementation

### Architecture

```
timezone/
├── js/timezone.js          # Main timezone manager
├── css/timezone.css        # Timezone styles
├── config/settings.php     # Settings integration
└── settings.php           # UI integration
```

### Core Components

#### 1. TimezoneManager (JavaScript)
```javascript
class TimezoneManager {
    constructor() {
        this.currentTimezone = null;
        this.detectedTimezone = null;
        this.timezoneList = this.getTimezoneList();
    }
    
    // Core methods
    async init()
    detectTimezone()
    setTimezone(timezone)
    formatTime(timestamp, format)
    getCurrentLocalTime()
}
```

#### 2. Settings Integration (PHP)
```php
class SettingsManager {
    public function get($key, $default = null)
    public function set($key, $value)
    // Timezone is stored as 'timezone' => 'America/New_York'
}
```

### Timezone Detection Process

1. **Browser Detection**: Uses `Intl.DateTimeFormat().resolvedOptions().timeZone`
2. **Validation**: Checks if detected timezone is valid
3. **Application**: Automatically applies detected timezone
4. **Persistence**: Saves timezone preference to settings
5. **Fallback**: Uses UTC if detection fails

## Usage Examples

### Basic Timezone Usage
```javascript
// Get current timezone
const timezone = timezoneManager.getCurrentTimezone();

// Set timezone
await timezoneManager.setTimezone('America/New_York');

// Format time in current timezone
const localTime = timezoneManager.formatTime(timestamp, 'local');
```

### Time Display Elements
```html
<!-- Time with timezone support -->
<span data-timezone data-timestamp="2024-01-15T10:30:00Z" data-format="local">
    10:30 AM
</span>

<!-- Session time -->
<div class="session-time" data-timestamp="2024-01-15T10:30:00Z">
    2 hours ago
</div>
```

### Settings Page Integration
```html
<div class="form-group">
    <label class="form-label">Time Zone</label>
    <div class="timezone-select-container">
        <select class="form-input" id="timezone-select">
            <!-- Populated by JavaScript -->
        </select>
        <button type="button" class="auto-detect-btn" id="auto-detect-timezone">
            <i class="fas fa-crosshairs"></i>
        </button>
    </div>
    <div id="timezone-info"></div>
</div>
```

## Timezone List

### Major Timezones Supported
- **UTC**: Coordinated Universal Time
- **America**: New York, Chicago, Denver, Los Angeles, etc.
- **Europe**: London, Paris, Berlin, Rome, Moscow, etc.
- **Asia**: Tokyo, Beijing, Singapore, Bangkok, Dubai, etc.
- **Australia**: Sydney, Perth, Melbourne, etc.
- **Pacific**: Auckland, Honolulu, etc.

### Timezone Format
```javascript
{
    value: 'America/New_York',
    label: 'UTC-05:00 (Eastern Standard Time)'
}
```

## Time Formatting

### Available Formats
```javascript
// Local date and time
timezoneManager.formatTime(timestamp, 'local')
// Output: "Jan 15, 2024, 10:30 AM"

// Time only
timezoneManager.formatTime(timestamp, 'time')
// Output: "10:30 AM"

// Date only
timezoneManager.formatTime(timestamp, 'date')
// Output: "Jan 15, 2024"

// Relative time
timezoneManager.formatTime(timestamp, 'relative')
// Output: "2 hours ago"
```

### Relative Time Logic
- **Just now**: Less than 1 minute
- **X minutes ago**: Less than 1 hour
- **X hours ago**: Less than 1 day
- **X days ago**: More than 1 day

## Integration with Other Systems

### Focus Sessions
```javascript
// Session start time in local timezone
const sessionStart = timezoneManager.formatTime(session.startTime, 'local');

// Session duration calculation
const duration = timezoneManager.getRelativeTime(session.endTime);
```

### Progress Tracking
```javascript
// Daily stats in local timezone
const dailyStats = progressData.dailyStats.map(stat => ({
    ...stat,
    date: timezoneManager.formatTime(stat.date, 'date'),
    time: timezoneManager.formatTime(stat.time, 'time')
}));
```

### Notifications
```javascript
// Notification time in local timezone
const notificationTime = timezoneManager.formatTime(notification.timestamp, 'local');
```

## Browser Compatibility

### Supported Browsers
- **Chrome**: Full support
- **Firefox**: Full support
- **Safari**: Full support
- **Edge**: Full support
- **Internet Explorer**: Limited support (fallback to UTC)

### Feature Detection
```javascript
function isTimezoneDetectionSupported() {
    return typeof Intl !== 'undefined' && 
           typeof Intl.DateTimeFormat !== 'undefined' && 
           typeof Intl.DateTimeFormat().resolvedOptions === 'function';
}
```

## Error Handling

### Detection Failures
```javascript
try {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (timezone) {
        // Use detected timezone
    } else {
        // Fallback to UTC
    }
} catch (error) {
    console.error('Timezone detection failed:', error);
    // Fallback to UTC
}
```

### Invalid Timezones
```javascript
function validateTimezone(timezone) {
    try {
        new Date().toLocaleString('en-US', { timeZone: timezone });
        return true;
    } catch (error) {
        return false;
    }
}
```

## Performance Considerations

### Optimization Strategies
1. **Caching**: Cache timezone detection results
2. **Lazy Loading**: Load timezone data only when needed
3. **Efficient Updates**: Update time displays efficiently
4. **Memory Management**: Cleanup of intervals and listeners

### Update Intervals
```javascript
// Update time display every second
setInterval(() => {
    timezoneManager.updateTimezoneDisplay();
}, 1000);

// Update session times every minute
setInterval(() => {
    timezoneManager.updateSessionTimes();
}, 60000);
```

## Security Considerations

### Privacy
- **No Location Data**: Only uses browser timezone, not GPS location
- **Local Processing**: All timezone calculations done client-side
- **No External APIs**: No calls to external timezone services

### Data Validation
```javascript
function sanitizeTimezone(timezone) {
    // Only allow valid timezone identifiers
    const validTimezones = timezoneManager.getTimezoneList();
    return validTimezones.find(tz => tz.value === timezone) ? timezone : 'UTC';
}
```

## Testing

### Manual Testing Checklist
- [ ] Timezone detection works on different devices
- [ ] Manual timezone selection works correctly
- [ ] Time displays update in real-time
- [ ] Session times show in local timezone
- [ ] Progress data uses correct timezone
- [ ] Notifications display correct times
- [ ] Fallback to UTC works when detection fails

### Automated Testing
```javascript
function testTimezoneSystem() {
    // Test timezone detection
    const detected = timezoneManager.getDetectedTimezone();
    assert(detected !== null);
    
    // Test timezone setting
    await timezoneManager.setTimezone('America/New_York');
    assert(timezoneManager.getCurrentTimezone() === 'America/New_York');
    
    // Test time formatting
    const formatted = timezoneManager.formatTime(new Date(), 'local');
    assert(typeof formatted === 'string');
}
```

## Troubleshooting

### Common Issues

#### Timezone Not Detected
- Check browser compatibility
- Verify JavaScript is enabled
- Check for browser extensions blocking timezone detection
- Try manual timezone selection

#### Times Displaying Incorrectly
- Verify timezone is set correctly
- Check for daylight saving time issues
- Ensure timestamps are in UTC format
- Clear browser cache and reload

#### Auto-detect Not Working
- Check browser permissions
- Verify network connectivity
- Try refreshing the page
- Check browser console for errors

### Debug Mode
```javascript
// Enable debug logging
localStorage.setItem('timezone_debug', 'true');

// Check timezone status
console.log(timezoneManager.getDetectionStatus());
console.log(timezoneManager.getCurrentTimezone());
console.log(timezoneManager.getDetectedTimezone());
```

## Best Practices

### Development Guidelines
1. **Always Use UTC**: Store all timestamps in UTC
2. **Convert for Display**: Convert to local timezone only for display
3. **Handle DST**: Account for daylight saving time changes
4. **Validate Input**: Always validate timezone inputs
5. **Provide Fallbacks**: Always have fallback options

### User Experience
1. **Automatic Detection**: Detect timezone automatically when possible
2. **Manual Override**: Allow users to manually set timezone
3. **Clear Display**: Show current timezone clearly
4. **Real-time Updates**: Update time displays in real-time
5. **Helpful Messages**: Provide clear error messages

### Performance
1. **Efficient Updates**: Update displays efficiently
2. **Cache Results**: Cache timezone detection results
3. **Minimize API Calls**: Avoid unnecessary server calls
4. **Optimize Calculations**: Use efficient time calculations

## Future Enhancements

### Planned Features
1. **Location-based Detection**: Use GPS for more accurate detection
2. **Multiple Timezones**: Support for multiple timezones per user
3. **Timezone Groups**: Group timezones by region
4. **Custom Formats**: User-defined time display formats
5. **Timezone Alerts**: Notifications for timezone changes

### Technical Improvements
1. **Service Workers**: Offline timezone support
2. **Web Components**: Reusable timezone components
3. **Progressive Enhancement**: Better fallback support
4. **Performance Monitoring**: Timezone performance metrics
5. **A/B Testing**: Timezone feature testing

## Support & Resources

### Documentation
- [MDN Intl.DateTimeFormat](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DateTimeFormat)
- [IANA Timezone Database](https://www.iana.org/time-zones)
- [Moment.js Timezone](https://momentjs.com/timezone/)

### Testing Tools
- [Timezone Converter](https://www.timeanddate.com/worldclock/converter.html)
- [Browser Timezone Test](https://www.w3schools.com/js/js_date_methods.asp)
- [Timezone Validator](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

### Community Resources
- [Stack Overflow Timezone](https://stackoverflow.com/questions/tagged/timezone)
- [GitHub Timezone Issues](https://github.com/topics/timezone)
- [Timezone Best Practices](https://www.timeanddate.com/time/timezone-best-practices.html) 