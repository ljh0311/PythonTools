# MindfulMoment React Native Application

This directory contains the React Native mobile application for MindfulMoment digital wellness.

## 🚀 Quick Start

1. **Prerequisites**: Node.js, npm, and Expo CLI installed
2. **Install Dependencies**: `npm install`
3. **Start Development Server**: `npx expo start`
4. **Run on Device**: Use Expo Go app or run on simulator/emulator

## 📁 File Structure

```
react-native-app/
├── App.tsx              # Main application component
├── app.json             # Expo configuration
├── package.json         # Dependencies and scripts
├── tsconfig.json        # TypeScript configuration
├── babel.config.js      # Babel configuration
├── metro.config.js      # Metro bundler configuration
├── src/                 # Source code
│   ├── components/      # Reusable components
│   ├── context/         # React context providers
│   └── screens/         # Screen components
├── assets/              # Images and static assets
├── .expo/               # Expo configuration
└── node_modules/        # Dependencies
```

## 🔧 Key Files

- **`App.tsx`**: Main application component and navigation setup
- **`app.json`**: Expo configuration and app metadata
- **`package.json`**: Project dependencies and scripts
- **`src/`**: Application source code
- **`assets/`**: Images, icons, and other static assets

## 📱 Features

- **Cross-Platform**: Works on iOS and Android
- **TypeScript**: Type-safe development
- **Expo**: Easy development and deployment
- **Modern React**: Uses latest React patterns and hooks
- **Responsive Design**: Adapts to different screen sizes

## 🔧 Development Commands

```bash
# Install dependencies
npm install

# Start development server
npx expo start

# Run on iOS simulator
npx expo run:ios

# Run on Android emulator
npx expo run:android

# Build for production
npx expo build
```

## 📖 Project Structure

The app follows a modular structure:

- **Components**: Reusable UI components
- **Screens**: Individual page components
- **Context**: Global state management
- **Assets**: Static resources

## 🎯 Features

- **Digital Wellness Tracking**: Monitor screen time and mindful moments
- **Focus Sessions**: Timer-based focus periods
- **Community Features**: Anonymous group challenges
- **Privacy-First**: All data stored locally on device
- **Smart Nudges**: Location-based gentle reminders

## 🔧 Technologies Used

- **React Native**: Cross-platform mobile development
- **TypeScript**: Type-safe JavaScript
- **Expo**: Development platform and tools
- **React Navigation**: Screen navigation
- **React Context**: State management

## 📱 Platform Support

- **iOS**: 12.0 and later
- **Android**: API level 21 and later
- **Web**: React Native Web support

## 🚀 Deployment

The app can be deployed using Expo's build service:

1. Configure app.json with your app details
2. Run `npx expo build:ios` or `npx expo build:android`
3. Submit to App Store or Google Play Store
