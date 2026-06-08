# MindfulMoment - Angular Web Application

A comprehensive Angular-based web application for promoting mindful behavior in public spaces, designed with mobile-first approach and Progressive Web App (PWA) capabilities.

## 🚀 Features

### Core Functionality
- **Performance Dashboard** - Comprehensive user performance tracking and insights
- **Focus Sessions** - Mindful focus session management with location tracking
- **Community Groups** - Join and participate in mindfulness communities
- **Public Awareness** - Safety tips and emergency contacts
- **Achievement System** - Gamified progress tracking with badges and rewards
- **Real-time Insights** - Performance analytics and trend analysis

### Technical Features
- **Mobile-First Design** - Responsive UI optimized for mobile devices
- **Progressive Web App** - Installable with offline capabilities
- **Angular Material** - Modern, accessible UI components
- **TypeScript** - Type-safe development
- **Service Workers** - Offline functionality and caching
- **Responsive Design** - Works seamlessly across all device sizes

## 📱 Mobile Compatibility

The application is specifically designed for mobile phones with:
- Touch-optimized interface
- Bottom navigation for easy thumb access
- Swipe gestures support
- Mobile-specific layouts and interactions
- PWA installation prompts
- Offline functionality

## 🛠️ Technology Stack

- **Angular 17** - Frontend framework
- **Angular Material** - UI component library
- **TypeScript** - Programming language
- **SCSS** - Styling
- **RxJS** - Reactive programming
- **Chart.js** - Data visualization
- **Service Workers** - PWA capabilities

## 📦 Installation

### Prerequisites
- Node.js (v18 or higher)
- npm (v9 or higher)
- Angular CLI (v17 or higher)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd mindful-moment-angular
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Install Angular CLI globally** (if not already installed)
   ```bash
   npm install -g @angular/cli
   ```

4. **Start development server**
   ```bash
   npm start
   ```

5. **Open in browser**
   Navigate to `http://localhost:4200`

## 🏗️ Build and Deployment

### Development Build
```bash
npm run build
```

### Production Build
```bash
npm run build:prod
```

### Serve Production Build
```bash
npm run serve:prod
```

## 📁 Project Structure

```
src/
├── app/
│   ├── components/          # Shared components
│   │   ├── header/         # Navigation header
│   │   ├── bottom-nav/     # Mobile bottom navigation
│   │   ├── loading-overlay/ # Loading indicators
│   │   └── toast-container/ # Notifications
│   ├── pages/              # Feature pages
│   │   ├── home/           # Dashboard page
│   │   ├── focus/          # Focus sessions
│   │   ├── community/      # Community features
│   │   ├── insights/       # Performance insights
│   │   ├── public-awareness/ # Safety features
│   │   ├── profile/        # User profile
│   │   └── settings/       # App settings
│   ├── services/           # Business logic
│   │   ├── auth.service.ts # Authentication
│   │   ├── data.service.ts # Data management
│   │   └── loading.service.ts # Loading states
│   ├── models/             # TypeScript interfaces
│   │   ├── user.model.ts   # User data structure
│   │   ├── focus-session.model.ts # Focus session data
│   │   ├── community-group.model.ts # Community data
│   │   └── achievement.model.ts # Achievement data
│   ├── guards/             # Route guards
│   │   └── auth.guard.ts   # Authentication guard
│   ├── app.component.*     # Root component
│   ├── app.module.ts       # Root module
│   └── app-routing.module.ts # Routing configuration
├── assets/                 # Static assets
├── styles.scss            # Global styles
├── index.html             # Main HTML file
└── manifest.json          # PWA manifest
```

## 🎨 Design System

### Color Palette
- **Primary**: #4A90E2 (Blue)
- **Secondary**: #28A745 (Green)
- **Accent**: #FF9800 (Orange)
- **Warning**: #FFC107 (Yellow)
- **Danger**: #DC3545 (Red)

### Typography
- **Font Family**: Roboto
- **Weights**: 300, 400, 500, 600, 700

### Spacing
- **XS**: 0.25rem
- **SM**: 0.5rem
- **MD**: 1rem
- **LG**: 1.5rem
- **XL**: 2rem

## 📱 Mobile Features

### Responsive Breakpoints
- **Mobile**: < 768px
- **Tablet**: 768px - 1024px
- **Desktop**: > 1024px

### Mobile-Specific Components
- Bottom navigation bar
- Touch-optimized buttons
- Swipe gestures
- Mobile-first layouts
- PWA installation

## 🔧 Configuration

### Environment Variables
Create `src/environments/environment.ts`:
```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost:3000/api',
  appName: 'MindfulMoment'
};
```

### PWA Configuration
The app includes:
- Service worker for offline functionality
- App manifest for installation
- Caching strategies for performance
- Push notification support (ready for implementation)

## 🧪 Testing

### Unit Tests
```bash
npm test
```

### E2E Tests
```bash
npm run e2e
```

### Linting
```bash
npm run lint
```

## 🚀 Deployment

### Build for Production
```bash
npm run build:prod
```

### Deploy to Static Hosting
The built files in `dist/mindful-moment-angular/` can be deployed to:
- Netlify
- Vercel
- GitHub Pages
- Firebase Hosting
- AWS S3 + CloudFront

### Docker Deployment
```dockerfile
FROM nginx:alpine
COPY dist/mindful-moment-angular /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 📊 Performance

### Optimization Features
- Lazy loading modules
- OnPush change detection
- Service worker caching
- Image optimization
- Bundle splitting
- Tree shaking

### Performance Metrics
- First Contentful Paint: < 1.5s
- Largest Contentful Paint: < 2.5s
- Cumulative Layout Shift: < 0.1
- First Input Delay: < 100ms

## 🔒 Security

### Security Features
- Content Security Policy
- XSS Protection
- CSRF Protection
- Secure headers
- Input validation
- Authentication guards

## 🌐 Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+
- Mobile browsers (iOS Safari, Chrome Mobile)

## 📈 Analytics

The app is ready for analytics integration:
- Google Analytics
- Firebase Analytics
- Custom event tracking
- Performance monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

## 🔄 Migration from PHP

This Angular application replaces the original PHP-based MindfulMoment application while maintaining all core functionality:

### Migrated Features
- ✅ User authentication and management
- ✅ Performance dashboard
- ✅ Focus session tracking
- ✅ Community features
- ✅ Achievement system
- ✅ Public awareness features
- ✅ Mobile responsiveness
- ✅ PWA capabilities

### New Features
- 🆕 Modern Angular architecture
- 🆕 TypeScript type safety
- 🆕 Enhanced mobile experience
- 🆕 Offline functionality
- 🆕 Better performance
- 🆕 Improved accessibility

---

**MindfulMoment** - Promoting mindful behavior in public spaces for a safer, more connected Singapore.