# MindfulMoment - Digital Wellness Mobile App

A modern, privacy-focused mobile application designed to help users build mindful phone habits and stay present in public spaces.

## 🌟 Features

### Core Functionality
- **Focus Sessions**: Set aside phone-free time with customizable durations and categories
- **Smart Nudges**: Location-based gentle reminders to stay present
- **Usage Insights**: Track screen time in public vs private spaces
- **Mindful Minutes**: Earn points for mindful behavior
- **Badges & Rewards**: Gamified progress tracking with redeemable rewards

### Community Features
- **Anonymous Groups**: Join communities using codes (school, workplace, etc.)
- **Leaderboards**: Compete anonymously with others
- **Events**: Discover and RSVP to phone-free community events
- **QR Code Attendance**: Scan codes to log event participation

### Privacy & Settings
- **Privacy-First Design**: All data stored locally on device
- **Permission Controls**: Granular control over location, notifications, and community sharing
- **Dark Mode**: Comfortable viewing in any lighting condition
- **Data Export**: Download your mindful moments data

## 📱 Screens Overview

| Screen | Purpose | Key Features |
|--------|---------|--------------|
| **Onboarding** | First-time setup | Privacy-first messaging, permission requests |
| **Home** | Central dashboard | Current status, quick actions, motivational quotes |
| **Focus Session** | Core feature | Timer, categories, progress tracking |
| **Usage Insights** | Analytics | Weekly summaries, charts, goal setting |
| **Badges & Rewards** | Gamification | Progress tracking, reward redemption |
| **Community** | Social features | Group joining, anonymous leaderboards |
| **Events** | Offline engagement | Event discovery, RSVP, QR scanning |
| **Settings** | User controls | Preferences, privacy, data management |

## 🚀 Getting Started

### Prerequisites
- Node.js (v16 or higher)
- npm or yarn
- Expo CLI
- iOS Simulator or Android Emulator (or physical device)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd mindfulmoment-app
   ```

2. **Install dependencies**
   ```bash
   npm install
   # or
   yarn install
   ```

3. **Start the development server**
   ```bash
   npm start
   # or
   yarn start
   ```

4. **Run on device/simulator**
   - Press `i` for iOS Simulator
   - Press `a` for Android Emulator
   - Scan QR code with Expo Go app on physical device

### Development Commands

```bash
# Start development server
npm start

# Run on iOS
npm run ios

# Run on Android
npm run android

# Run on web
npm run web

# Build for production
expo build:ios
expo build:android
```

## 🏗️ Project Structure

```
mindfulmoment-app/
├── App.tsx                 # Main app component with navigation
├── app.json               # Expo configuration
├── package.json           # Dependencies and scripts
├── src/
│   ├── components/        # Reusable UI components
│   │   ├── Button.tsx
│   │   └── Card.tsx
│   ├── context/          # React Context providers
│   │   ├── AppContext.tsx
│   │   └── ThemeContext.tsx
│   └── screens/          # App screens
│       ├── OnboardingScreen.tsx
│       ├── HomeScreen.tsx
│       ├── FocusSessionScreen.tsx
│       ├── UsageInsightsScreen.tsx
│       ├── BadgesRewardsScreen.tsx
│       ├── CommunityScreen.tsx
│       ├── EventsScreen.tsx
│       └── SettingsScreen.tsx
└── assets/               # Images, icons, and static assets
```

## 🎨 Design System

### Colors
- **Primary**: #4A90E2 (Blue)
- **Secondary**: #7B68EE (Purple)
- **Success**: #28A745 (Green)
- **Warning**: #FFC107 (Yellow)
- **Error**: #DC3545 (Red)
- **Info**: #17A2B8 (Cyan)

### Typography
- **H1**: 32px, Bold
- **H2**: 24px, Semi-bold
- **H3**: 20px, Semi-bold
- **Body**: 16px, Normal
- **Caption**: 14px, Normal

### Spacing
- **XS**: 4px
- **SM**: 8px
- **MD**: 16px
- **LG**: 24px
- **XL**: 32px
- **XXL**: 48px

## 🔧 Technical Stack

- **Framework**: React Native with Expo
- **Navigation**: React Navigation v6
- **State Management**: React Context API
- **Storage**: AsyncStorage for local data
- **Icons**: Expo Vector Icons (Ionicons)
- **Permissions**: Expo Location, Notifications
- **Charts**: React Native Chart Kit (planned)
- **QR Scanning**: Expo Barcode Scanner

## 📋 Permissions Required

- **Location**: For contextual nudges and public/private space detection
- **Notifications**: For gentle reminders and focus session alerts
- **Usage Statistics**: For screen time tracking (Android only)

## 🔒 Privacy Features

- **Local Data Storage**: All user data stored on device
- **Anonymous Community**: No personal information shared in groups
- **Optional Features**: Users can opt out of any feature
- **Data Export**: Users can download their data
- **App Reset**: Complete data deletion option

## 🎯 User Journey

1. **Onboarding**: Privacy-first introduction and permission setup
2. **Daily Use**: Quick focus sessions and mindful moment tracking
3. **Weekly Review**: Usage insights and goal setting
4. **Community**: Join groups and participate in challenges
5. **Events**: Attend phone-free community activities
6. **Rewards**: Redeem points for real-world benefits

## 🚧 Future Enhancements

- **Advanced Analytics**: Detailed usage patterns and insights
- **AI-Powered Nudges**: Smart timing for contextual reminders
- **Integration APIs**: Connect with fitness and wellness apps
- **Offline Events**: Enhanced event discovery and management
- **Multi-language Support**: Internationalization
- **Accessibility**: Screen reader and voice control support

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For support, email support@mindfulmoment.app or create an issue in the repository.

---

**Built with ❤️ for digital wellness and mindful living** 