# Accessibility System

## Overview

The MindfulMoment accessibility system provides comprehensive support for users with various accessibility needs, ensuring the application is usable by everyone regardless of their abilities or disabilities.

## Features

### 1. Visual Accessibility
- **High Contrast Mode**: Increases contrast for better visibility
- **Large Text Mode**: Increases text size throughout the application
- **Font Size Control**: Adjustable base font size (small, medium, large, xlarge)
- **Color Blindness Support**: Filters for different types of color blindness
- **Focus Indicators**: Clear visual indicators for keyboard navigation

### 2. Motion & Animation
- **Reduce Motion**: Disables or reduces animations and transitions
- **Smooth Transitions**: Respects user's motion preferences
- **Animation Control**: Configurable animation durations

### 3. Screen Reader Support
- **ARIA Labels**: Comprehensive ARIA attributes for screen readers
- **Semantic HTML**: Proper heading structure and landmarks
- **Live Regions**: Dynamic content announcements
- **Skip Links**: Quick navigation to main content

### 4. Keyboard Navigation
- **Full Keyboard Support**: All functionality accessible via keyboard
- **Focus Management**: Proper focus trapping and management
- **Tab Navigation**: Logical tab order throughout the application
- **Keyboard Shortcuts**: Common shortcuts for frequent actions

### 5. Cognitive Accessibility
- **Clear Language**: Simple, concise text
- **Consistent Layout**: Predictable interface patterns
- **Error Prevention**: Clear error messages and validation
- **Help Text**: Contextual help and guidance

## Technical Implementation

### Architecture

```
accessibility/
├── js/accessibility.js          # Main accessibility manager
├── css/accessibility.css        # Accessibility styles
├── api/accessibility.php        # Accessibility API
└── config/settings.php          # Settings integration
```

### Core Components

#### 1. AccessibilityManager (JavaScript)
```javascript
class AccessibilityManager {
    constructor() {
        this.settings = {};
        this.apiUrl = 'api/accessibility.php';
    }
    
    // Core methods
    async init()
    async loadSettings()
    applyAccessibilitySettings()
    updateSetting(key, value)
    setupKeyboardNavigation()
    setupScreenReaderSupport()
}
```

#### 2. Settings Integration (PHP)
```php
class SettingsManager {
    public function getAccessibilitySettings()
    public function updateAccessibilitySettings($settings)
    public function getAccessibilityClasses()
}
```

#### 3. API Endpoints
- `GET /api/accessibility.php` - Retrieve settings
- `POST /api/accessibility.php` - Update settings
- `PUT /api/accessibility.php` - Update specific setting
- `DELETE /api/accessibility.php` - Reset to defaults

### CSS Classes

#### Font Size Classes
```css
.font-size-small    { --font-size-base: 0.875rem; }
.font-size-medium   { --font-size-base: 1rem; }
.font-size-large    { --font-size-base: 1.125rem; }
.font-size-xlarge   { --font-size-base: 1.25rem; }
```

#### High Contrast Mode
```css
.high-contrast {
    --text-color: #000000 !important;
    --bg-color: #FFFFFF !important;
    --primary-color: #0000FF !important;
}
```

#### Color Blindness Support
```css
.color-blindness-protanopia { filter: url(#protanopia-filter); }
.color-blindness-deuteranopia { filter: url(#deuteranopia-filter); }
.color-blindness-tritanopia { filter: url(#tritanopia-filter); }
```

#### Motion Reduction
```css
.reduce-motion * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
}
```

## Usage Examples

### Basic Implementation
```html
<!-- Include accessibility files -->
<link rel="stylesheet" href="css/accessibility.css">
<script src="js/accessibility.js"></script>

<!-- Apply accessibility classes -->
<body class="<?php echo $settings->getAccessibilityClasses(); ?>">
```

### JavaScript Usage
```javascript
// Initialize accessibility manager
const accessibility = new AccessibilityManager();

// Update a setting
accessibility.updateSetting('highContrast', true);

// Get current settings
const settings = accessibility.getSettings();

// Reset to defaults
accessibility.resetToDefaults();
```

### Settings Page Integration
```html
<div class="form-group">
    <label class="checkbox-label">
        <input type="checkbox" id="high-contrast-toggle">
        <span class="checkmark"></span>
        High contrast mode
    </label>
    <small class="form-help">Increases contrast for better visibility</small>
</div>
```

## Accessibility Standards Compliance

### WCAG 2.1 AA Compliance
- **1.4.3 Contrast (Minimum)**: High contrast mode ensures 4.5:1 ratio
- **1.4.4 Resize Text**: Font size controls allow 200% zoom
- **2.1.1 Keyboard**: Full keyboard navigation support
- **2.1.2 No Keyboard Trap**: Proper focus management
- **2.4.1 Bypass Blocks**: Skip links to main content
- **2.4.3 Focus Order**: Logical tab order
- **2.4.7 Focus Visible**: Clear focus indicators
- **3.2.1 On Focus**: Predictable behavior on focus
- **3.2.2 On Input**: Predictable behavior on input
- **4.1.2 Name, Role, Value**: Proper ARIA attributes

### Section 508 Compliance
- **1194.21(a)**: Software applications and operating systems
- **1194.21(b)**: Applications shall not disrupt accessibility features
- **1194.21(c)**: A well-defined on-screen indication of current focus
- **1194.21(d)**: Sufficient information about user interface elements
- **1194.21(e)**: Application shall not override user selected contrast
- **1194.21(f)**: Animation shall be displayable in at least one mode
- **1194.21(g)**: Color coding shall not be used as the only means
- **1194.21(h)**: When a product permits a user to adjust color
- **1194.21(i)**: When animation is displayed, the information shall be
- **1194.21(j)**: Color and contrast information can be programmatically

## Testing & Validation

### Automated Testing
```javascript
// Test accessibility features
function testAccessibility() {
    // Test keyboard navigation
    testKeyboardNavigation();
    
    // Test screen reader compatibility
    testScreenReaderSupport();
    
    // Test color contrast
    testColorContrast();
    
    // Test focus management
    testFocusManagement();
}
```

### Manual Testing Checklist
- [ ] All functionality accessible via keyboard
- [ ] Screen reader announces content correctly
- [ ] High contrast mode works properly
- [ ] Font size changes apply correctly
- [ ] Color blindness filters work
- [ ] Motion reduction respected
- [ ] Focus indicators visible
- [ ] Skip links functional
- [ ] Error messages clear and helpful

### Tools for Testing
- **Screen Readers**: NVDA, JAWS, VoiceOver, TalkBack
- **Color Contrast**: WebAIM Contrast Checker
- **Keyboard Navigation**: Manual testing with Tab, Shift+Tab, Enter, Escape
- **Automated Testing**: axe-core, WAVE, Lighthouse

## Performance Considerations

### Optimization Strategies
1. **Lazy Loading**: Load accessibility features only when needed
2. **CSS Optimization**: Efficient selectors and minimal repaints
3. **JavaScript Performance**: Debounced settings updates
4. **Memory Management**: Cleanup of event listeners

### Browser Support
- **Modern Browsers**: Full support for all features
- **Legacy Browsers**: Graceful degradation
- **Mobile Browsers**: Touch-friendly accessibility controls
- **Screen Readers**: Compatible with major screen readers

## Configuration Options

### Default Settings
```javascript
const defaultSettings = {
    fontSize: 'medium',
    highContrast: false,
    largeText: false,
    screenReader: false,
    reduceMotion: true,
    colorBlindness: 'none',
    focusIndicators: true,
    keyboardNavigation: true,
    audioDescriptions: false,
    captions: false
};
```

### Customization
```javascript
// Custom accessibility settings
const customSettings = {
    fontSize: 'large',
    highContrast: true,
    reduceMotion: false,
    colorBlindness: 'protanopia'
};

accessibilityManager.updateSettings(customSettings);
```

## Integration with Other Systems

### Settings System
- Integrates with main settings manager
- Persists accessibility preferences
- Syncs across user sessions

### Theme System
- Works with light/dark themes
- Respects user theme preferences
- Maintains accessibility in all themes

### Progress Tracking
- Accessible progress indicators
- Screen reader announcements
- Keyboard navigation for progress features

## Future Enhancements

### Planned Features
1. **Voice Control**: Voice commands for navigation
2. **Gesture Support**: Touch gestures for accessibility
3. **Customizable Shortcuts**: User-defined keyboard shortcuts
4. **Advanced Color Themes**: More color blindness options
5. **Audio Descriptions**: Spoken descriptions of content
6. **Haptic Feedback**: Vibration feedback for mobile

### Technical Improvements
1. **Web Components**: Reusable accessibility components
2. **Service Workers**: Offline accessibility support
3. **Progressive Enhancement**: Better fallback support
4. **Performance Monitoring**: Accessibility performance metrics
5. **A/B Testing**: Accessibility feature testing

## Troubleshooting

### Common Issues

#### Settings Not Applying
- Check if accessibility manager is initialized
- Verify CSS classes are being applied
- Check browser console for errors

#### Keyboard Navigation Issues
- Ensure focus indicators are enabled
- Check tab order in HTML
- Verify event listeners are attached

#### Screen Reader Problems
- Check ARIA attributes are present
- Verify semantic HTML structure
- Test with multiple screen readers

### Debug Mode
```javascript
// Enable debug logging
localStorage.setItem('accessibility_debug', 'true');

// Check accessibility status
console.log(accessibilityManager.getSettings());
console.log(document.body.className);
```

## Best Practices

### Development Guidelines
1. **Semantic HTML**: Use proper HTML elements
2. **ARIA Attributes**: Add appropriate ARIA labels
3. **Keyboard Support**: Test all interactions with keyboard
4. **Color Independence**: Don't rely solely on color
5. **Text Alternatives**: Provide alt text for images
6. **Focus Management**: Maintain logical focus order

### Content Guidelines
1. **Clear Language**: Use simple, concise text
2. **Consistent Terminology**: Use consistent terms throughout
3. **Error Messages**: Provide clear, helpful error messages
4. **Instructions**: Give clear instructions for tasks
5. **Feedback**: Provide immediate feedback for actions

### Design Guidelines
1. **High Contrast**: Ensure sufficient color contrast
2. **Readable Fonts**: Use readable font families
3. **Adequate Spacing**: Provide sufficient spacing between elements
4. **Touch Targets**: Make touch targets large enough
5. **Visual Hierarchy**: Use clear visual hierarchy

## Support & Resources

### Documentation
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/TR/wai-aria-practices/)
- [Web Accessibility Initiative](https://www.w3.org/WAI/)

### Testing Tools
- [axe-core](https://github.com/dequelabs/axe-core)
- [WAVE](https://wave.webaim.org/)
- [Lighthouse](https://developers.google.com/web/tools/lighthouse)

### Community Resources
- [WebAIM](https://webaim.org/)
- [A11Y Project](https://www.a11yproject.com/)
- [Inclusive Design Principles](https://inclusivedesignprinciples.org/) 