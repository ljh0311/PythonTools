# User Database Integration

## Overview

The MindfulMoment application now uses a JSON-based user database system for storing user details, progress, and settings. This replaces the previous localStorage-only approach with a more robust server-side storage solution.

## Architecture

### 1. User Database Structure (`web-app/data/users/user.json`)

The user database is stored as a JSON file with the following structure:

```json
{
  "users": [
    {
      "id": "user_001",
      "email": "user@example.com",
      "username": "mindfuluser",
      "password": "hashed_password_here",
      "firstName": "John",
      "lastName": "Doe",
      "dateOfBirth": "1990-01-01",
      "phone": "+65 9123 4567",
      "preferences": {
        "language": "en",
        "alertFrequency": "30",
        "primaryGoal": "safety",
        "notifications": true,
        "location": true,
        "screenTime": false,
        "focusMode": false,
        "theme": "light",
        "accessibility": {
          "highContrast": false,
          "largeText": false,
          "screenReader": false
        }
      },
      "community": "singapore",
      "stats": {
        "totalSessions": 15,
        "totalMindfulMinutes": 375,
        "totalSafetyAlerts": 8,
        "totalSocialEngagements": 12,
        "joinDate": "2024-01-15T10:30:00Z",
        "lastActive": "2024-01-20T14:45:00Z",
        "focusSessionStats": {
          "totalPublicFocusTime": 180,
          "totalSocialInteractions": 8,
          "phoneUsageReduction": 240,
          "mindfulMoments": 15
        },
        "publicAwarenessStats": {
          "totalPublicTime": 480,
          "safetyAlerts": 5,
          "socialPrompts": 10,
          "mindfulScore": 85
        }
      },
      "achievements": [...],
      "badges": [...],
      "points": 150,
      "level": 2,
      "homeSettings": {
        "wifiNetworks": ["HomeWiFi", "Home5G"],
        "location": {
          "latitude": 1.3521,
          "longitude": 103.8198,
          "radius": 100
        },
        "isConfigured": true
      },
      "publicAwarenessSettings": {
        "isEnabled": true,
        "alertFrequency": 30,
        "socialPrompts": true,
        "safetyAlerts": true
      }
    }
  ],
  "metadata": {
    "lastUpdated": "2024-01-20T14:45:00Z",
    "version": "1.0",
    "totalUsers": 1
  }
}
```

### 2. PHP API (`web-app/api/user_database.php`)

The PHP API provides the following endpoints:

#### Authentication
- `POST /api/user_database.php?action=login` - User login
- `POST /api/user_database.php?action=register` - User registration

#### User Management
- `GET /api/user_database.php?action=user&id={userId}` - Get user by ID
- `GET /api/user_database.php?action=users` - Get all users
- `PUT /api/user_database.php` - Update user profile

#### Data Updates
- `POST /api/user_database.php?action=update_stats` - Update user statistics
- `POST /api/user_database.php?action=update_settings` - Update user settings
- `POST /api/user_database.php?action=add_achievement` - Add achievement
- `POST /api/user_database.php?action=add_badge` - Add badge

### 3. JavaScript Integration (`web-app/js/account-manager.js`)

The account manager has been updated to use the new API:

#### Key Changes
- **API Integration**: All user operations now use fetch() to communicate with the PHP API
- **Session Persistence**: User sessions are still stored in localStorage for offline access
- **Session Verification**: User sessions are verified against the database on page load
- **Fallback Support**: Graceful fallback to localStorage when API is unavailable

#### New Methods
- `verifyUserSession()` - Verifies user session with database
- `updateUserStats()` - Updates user statistics via API
- `updateUserSettings()` - Updates user settings via API
- `addAchievement()` - Adds achievements via API
- `addBadge()` - Adds badges via API

## Integration Points

### 1. Public Awareness System

The public awareness system now integrates with the user database:

```javascript
// Load home settings from user database
loadHomeSettings() {
    if (window.accountManager && window.accountManager.currentUser) {
        return window.accountManager.currentUser.homeSettings || defaultSettings;
    }
    // Fallback to localStorage
    return localStorage.getItem('mindfulmoment_home_settings') || defaultSettings;
}

// Save home settings to user database
async saveHomeSettings() {
    if (window.accountManager && window.accountManager.currentUser) {
        const result = await window.accountManager.updateUserSettings(
            window.accountManager.currentUser.id, 
            { homeSettings: this.homeSettings }
        );
        if (result.success) {
            window.accountManager.currentUser = result.user;
            window.accountManager.saveCurrentUser();
        }
    } else {
        // Fallback to localStorage
        localStorage.setItem('mindfulmoment_home_settings', JSON.stringify(this.homeSettings));
    }
}
```

### 2. Focus Session Integration

Focus session progress is now stored in the user database:

```javascript
// Update focus session progress
async updateFocusSessionProgress(sessionData) {
    if (!sessionData) return;

    // Update focus session stats
    this.focusSessionStats.totalPublicFocusTime += sessionData.duration || 0;
    
    // Add points based on session completion
    const pointsEarned = Math.floor((sessionData.duration || 0) / 60) * 10;
    
    // Update user points if logged in
    if (window.accountManager && window.accountManager.currentUser) {
        const newPoints = (window.accountManager.currentUser.points || 0) + pointsEarned;
        await window.accountManager.updateProfile({ points: newPoints });
    }

    // Save updated stats
    await this.saveFocusSessionStats();
}
```

### 3. Navbar Integration

The navbar now properly displays user information from the database:

```javascript
// Update navbar user information
function updateNavbarUser() {
    if (window.accountManager && window.accountManager.isAuthenticated && window.accountManager.currentUser) {
        const user = window.accountManager.currentUser;
        const displayName = user.firstName || user.username || user.email;
        usernameElement.textContent = displayName;
        // Show logout button, hide login button
    } else {
        usernameElement.textContent = 'Guest';
        // Show login button, hide logout button
    }
}
```

## Security Features

### 1. Password Hashing
- Passwords are hashed using SHA-256 with a salt
- In production, use `password_hash()` and `password_verify()`

### 2. Session Management
- User sessions are verified against the database
- Automatic logout on invalid sessions
- Session persistence in localStorage for offline access

### 3. Data Validation
- Input validation on all API endpoints
- Error handling for malformed requests
- Graceful fallbacks for network issues

## Benefits

### 1. Data Persistence
- User data persists across devices and sessions
- No data loss when clearing browser storage
- Centralized data management

### 2. Multi-User Support
- Support for multiple user accounts
- User-specific settings and progress
- Admin capabilities for user management

### 3. Enhanced Features
- Achievement and badge system
- Points and leveling system
- Comprehensive statistics tracking
- Home/private space detection settings

### 4. Scalability
- Easy to migrate to a proper database (MySQL, PostgreSQL)
- API-based architecture for future expansion
- Modular design for additional features

## Usage Instructions

### 1. User Registration
1. Click the login button in the navbar
2. Click "Register" to create a new account
3. Fill in the required information
4. Submit the form to create your account

### 2. User Login
1. Click the login button in the navbar
2. Enter your email and password
3. Submit to log in to your account

### 3. Profile Management
1. Click on your username in the navbar
2. Update your profile information
3. Save changes to update your profile

### 4. Data Synchronization
- User data automatically syncs with the database
- Offline changes are saved locally and synced when online
- Session verification ensures data integrity

## Future Enhancements

### 1. Database Migration
- Migrate from JSON to MySQL/PostgreSQL
- Implement proper database indexing
- Add database backup and recovery

### 2. Advanced Security
- Implement JWT tokens for authentication
- Add rate limiting for API endpoints
- Implement proper password reset functionality

### 3. Additional Features
- User roles and permissions
- Social features (friends, groups)
- Advanced analytics and reporting
- Mobile app integration

## Troubleshooting

### 1. API Connection Issues
- Check if the PHP server is running
- Verify file permissions for the user.json file
- Check browser console for error messages

### 2. User Session Issues
- Clear browser localStorage and re-login
- Check if user exists in the database
- Verify API endpoint accessibility

### 3. Data Synchronization Issues
- Check network connectivity
- Verify API response format
- Check browser console for error messages

## File Structure

```
web-app/
├── api/
│   └── user_database.php          # User database API
├── data/
│   └── users/
│       └── user.json              # User database file
├── js/
│   ├── account-manager.js         # Updated account manager
│   └── public-awareness.js        # Updated public awareness
└── docs/
    └── USER_DATABASE_INTEGRATION.md # This documentation
```

This integration provides a robust foundation for user management and data persistence in the MindfulMoment application. 