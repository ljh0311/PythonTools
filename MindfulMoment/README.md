# MindfulMoment - Multi-Platform Application Suite

A comprehensive suite of applications for promoting mindful behavior in public spaces, fostering face-to-face engagement, and improving safety. Available as both a **Progressive Web App (Angular)** and **Native Mobile App (React Native)**.

## 🎯 Overview

MindfulMoment addresses excessive smartphone usage in public environments through:

- **Safety**: Reduce distracted walking and situational unawareness
- **Social Connection**: Encourage face-to-face interactions in public spaces
- **Mindfulness**: Promote present-moment awareness and gratitude
- **Community**: Build supportive networks for mindful public behavior
- **Privacy**: Maintain user privacy while enabling community features
- **Accessibility**: Multi-language support for Singapore's diverse population
- **Cross-Platform**: Available on web browsers and mobile devices

## 🚀 Key Features

### Privacy-First Design

- All raw usage logs and location data stay on-device
- Only anonymized summary events are shared (with user consent)
- Users can fully opt out of data sharing while using local features
- Clear privacy explanations during onboarding

### Context-Aware In-The-Moment Nudges

- **Geofencing**: Detects entry into predefined public areas (MRT stations, busy crossings)
- **Smart Alerts**: Gentle notifications when screen usage persists in public spaces
- **Safety Reminders**: Concise alerts near high-risk points (platform edges, intersections)
- **Multi-language Support**: English, Chinese, Malay, and Tamil

### Focus Sessions for Self-Regulation

- **Manual Control**: Users start sessions before or during public activities
- **App Blocking**: Select which app categories to block (social media, games, etc.)
- **Notification Silencing**: Mute non-urgent notifications during sessions
- **Mindful Minutes**: Track and reward phone-free time
- **Location Context**: Sessions automatically tagged with location data

### Usage Dashboard & Reflective Insights

- **Weekly Summaries**: Screen time in public vs. private zones
- **Progress Tracking**: Nudges acknowledged, focus sessions completed
- **Mindful Minutes Chart**: Visual progress over time
- **Reflection Prompts**: Periodic questions about mood and focus changes
- **Goal Setting**: Modest, achievable targets based on usage patterns

### Gamification & Community Motivation

- **Points System**: Earn points for mindful behavior
- **Badges**: "Safe Commuter," "Park Explorer," "Streak Master"
- **Anonymous Groups**: Join via group codes (school, workplace, neighborhood)
- **Community Challenges**: Collective goals like "500 Mindful Minutes this week"
- **Rewards**: Redeem points for local business vouchers and discounts

### Safety Emphasis

- **Timely Alerts**: "Look up for safety" near high-risk locations
- **Distraction Prevention**: Based on international safety studies
- **Aggregated Insights**: Anonymous data to inform safety campaigns
- **LTA Integration**: Reinforces public transport etiquette

## 📱 Technical Implementation

### Architecture Overview

The MindfulMoment suite consists of two main applications:

#### 🌐 Angular Web Application (`mindful-moment-angular/`)

- **Angular 17**: Modern web framework with TypeScript
- **Progressive Web App (PWA)**: Installable, offline-capable
- **Angular Material**: Modern UI components
- **Service Workers**: Offline functionality and caching
- **Mobile-First Design**: Optimized for mobile browsers
- **Responsive Layout**: Works on all screen sizes

#### 📱 React Native Mobile App (`react-native-app/`)

- **React Native + Expo**: Cross-platform mobile development
- **TypeScript**: Type-safe development
- **Context API**: State management
- **AsyncStorage**: Local data persistence
- **Native APIs**: Location, notifications, device info

### Core Services

#### LocationService

- Geofencing for Singapore MRT stations and public areas
- Real-time location tracking with privacy controls
- Zone-based screen time monitoring
- Safety level assessment for different areas

#### NotificationService

- Context-aware nudges and safety reminders
- Multi-language notification messages
- Quiet hours support
- Notification acknowledgment tracking

#### FocusSessionService

- Session management with app blocking
- Timer functionality with pause/resume
- Category-based session types
- Integration with location and community services

#### CommunityService

- Anonymous group management
- Badge and reward systems
- Progress tracking and gamification
- Local business partnerships

### Data Privacy

- **On-Device Storage**: All personal data stored locally
- **Anonymized Sharing**: Only summary statistics shared (optional)
- **User Control**: Granular privacy settings
- **PDPA Compliance**: Singapore data protection standards

## 🗺️ Singapore-Specific Features

### MRT Station Coverage

- Major stations: Raffles Place, City Hall, Orchard, Somerset, Dhoby Ghaut
- Marina Bay, Bugis, Lavender, Kallang, Aljunied
- Platform edge detection for safety alerts

### Public Spaces

- Marina Bay Sands, Gardens by the Bay
- Merlion Park, Clarke Quay
- Busy crossings and intersections

### Local Partnerships

- Coffee shops near MRT stations
- Gardens by the Bay discounts
- National Museum passes
- LTA transit credits

## 🛠️ Installation & Setup

### Prerequisites

- Node.js 18+
- Angular CLI 17+
- Expo CLI (for React Native app)
- Android Studio (for Android development)
- Xcode (for iOS development, macOS only)

### Quick Start

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd mindfulmoment-app
   ```

#### 🌐 Angular Web Application

1. **Navigate to Angular app and install dependencies**

   ```bash
   cd mindful-moment-angular
   npm install
   ```

2. **Start the development server**

   ```bash
   npm start
   # or
   ng serve
   ```

3. **Open in browser**
   Navigate to `http://localhost:4200`

#### 📱 React Native Mobile App

1. **Navigate to React Native app and install dependencies**

   ```bash
   cd react-native-app
   npm install
   ```

2. **Start the development server**

   ```bash
   npx expo start
   ```

3. **Run on device/simulator**

   ```bash
   # Android
   npx expo run:android
   
   # iOS
   npx expo run:ios
   ```

## 📁 Project Structure

```
mindfulmoment-app/
├── docs/                          # Documentation files
│   ├── ACCESSIBILITY_SYSTEM.md
│   ├── CHALLENGE_SYSTEM.md
│   ├── ENHANCED_HOME_DETECTION_SYSTEM.md
│   └── ...
├── mindful-moment-angular/        # Angular Web Application
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/        # Shared components
│   │   │   ├── pages/            # Feature pages
│   │   │   ├── services/         # Business logic
│   │   │   ├── models/           # TypeScript interfaces
│   │   │   └── guards/           # Route guards
│   │   ├── index.html
│   │   ├── manifest.json         # PWA manifest
│   │   └── styles.scss
│   ├── angular.json
│   ├── package.json
│   └── README.md
├── react-native-app/             # React Native Mobile App
│   ├── src/
│   │   ├── components/           # Reusable components
│   │   ├── screens/             # App screens
│   │   ├── context/             # State management
│   │   ├── hooks/               # Custom hooks
│   │   └── utils/               # Utility services
│   ├── App.tsx
│   ├── app.json
│   └── package.json
└── README.md                     # This file
```

### Environment Configuration

1. **Location Services**
   - Configure Google Maps API key (optional, for better accuracy)
   - Update geofence coordinates as needed

2. **Notifications**
   - Configure push notification certificates
   - Set up quiet hours preferences

3. **Community Features**
   - Configure backend endpoints (if using remote features)
   - Set up local business partnerships

## 📊 Usage Analytics

### Privacy-Preserving Metrics

- **Aggregated Data**: Only summary statistics shared
- **Anonymized Events**: "Completed Focus Session in MRT zone"
- **Opt-in Sharing**: Users control data contribution
- **Local Processing**: All analysis done on-device

### Key Metrics Tracked

- Screen time in public vs. private zones
- Focus session completion rates
- Safety reminder effectiveness
- Community challenge participation
- Badge and reward redemption rates

## 🤝 Community Integration

### School Programs

- Digital Wellness curriculum integration
- Class-based group challenges
- Character and Citizenship Education alignment

### Workplace Initiatives

- Corporate wellness programs
- Team-based mindful challenges
- Productivity improvement tracking

### Public Awareness

- HPB/MCI campaign alignment
- Transit digital screen integration
- Community center event coordination

## 🔒 Privacy & Security

### Data Protection

- **Local Storage**: All personal data on device
- **Encryption**: Sensitive data encrypted at rest
- **Minimal Permissions**: Only essential permissions requested
- **User Consent**: Explicit opt-in for data sharing

### Compliance

- **PDPA**: Singapore Personal Data Protection Act
- **GDPR**: European data protection standards
- **COPPA**: Children's online privacy protection

## 🚀 Future Enhancements

### Planned Features

- **AI-Powered Insights**: Personalized recommendations
- **Advanced Geofencing**: More precise location detection
- **Social Features**: Anonymous community interactions
- **Integration APIs**: Third-party app connections
- **Offline Mode**: Full functionality without internet

### Research Integration

- **Behavioral Studies**: Academic research partnerships
- **Safety Impact**: Distraction reduction measurement
- **Community Health**: Public space engagement metrics

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## 📞 Support

For support and questions:

- Email: <support@mindfulmoment.sg>
- Community Forum: [community.mindfulmoment.sg](https://community.mindfulmoment.sg)
- Documentation: [docs.mindfulmoment.sg](https://docs.mindfulmoment.sg)

---

**MindfulMoment** - Building a more mindful, connected, and safe Singapore, one moment at a time. 🌱
