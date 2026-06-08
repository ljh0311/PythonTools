import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { locationService, GeofenceZone } from './LocationService';

export interface NotificationSettings {
  enabled: boolean;
  mindfulNudges: boolean;
  safetyReminders: boolean;
  focusSessionAlerts: boolean;
  communityUpdates: boolean;
  quietHours: {
    enabled: boolean;
    start: string; // "22:00"
    end: string;   // "07:00"
  };
}

export interface NotificationEvent {
  id: string;
  type: 'mindful_nudge' | 'safety_reminder' | 'focus_session' | 'community';
  title: string;
  body: string;
  timestamp: Date;
  zoneId?: string;
  acknowledged: boolean;
  dismissed: boolean;
}

// Multi-language notification messages
const NOTIFICATION_MESSAGES = {
  en: {
    mindfulNudge: {
      title: 'MindfulMoment',
      body: 'Consider pausing your phone and noticing your surroundings.',
    },
    safetyReminder: {
      title: 'Safety Reminder',
      body: 'Look up and stay alert. Your safety matters.',
    },
    focusSessionStart: {
      title: 'Focus Session Started',
      body: 'Your phone-free time has begun. Stay present!',
    },
    focusSessionEnd: {
      title: 'Focus Session Complete',
      body: 'Great job! You\'ve completed your mindful break.',
    },
    focusSessionReminder: {
      title: 'Focus Session Reminder',
      body: 'Time to take a break from your phone.',
    },
    communityChallenge: {
      title: 'Community Challenge',
      body: 'Your group is making progress! Join the mindful movement.',
    },
  },
  zh: {
    mindfulNudge: {
      title: 'MindfulMoment',
      body: '考虑暂停使用手机，注意周围环境。',
    },
    safetyReminder: {
      title: '安全提醒',
      body: '抬头注意，保持警惕。您的安全很重要。',
    },
    focusSessionStart: {
      title: '专注时段开始',
      body: '您的无手机时间开始了。保持专注！',
    },
    focusSessionEnd: {
      title: '专注时段完成',
      body: '做得好！您已完成专注休息。',
    },
    focusSessionReminder: {
      title: '专注时段提醒',
      body: '是时候放下手机休息一下了。',
    },
    communityChallenge: {
      title: '社区挑战',
      body: '您的小组正在进步！加入正念运动。',
    },
  },
  ms: {
    mindfulNudge: {
      title: 'MindfulMoment',
      body: 'Pertimbangkan untuk berhenti menggunakan telefon dan perhatikan persekitaran anda.',
    },
    safetyReminder: {
      title: 'Peringatan Keselamatan',
      body: 'Angkat kepala dan berwaspada. Keselamatan anda penting.',
    },
    focusSessionStart: {
      title: 'Sesi Fokus Bermula',
      body: 'Masa bebas telefon anda telah bermula. Kekalkan fokus!',
    },
    focusSessionEnd: {
      title: 'Sesi Fokus Selesai',
      body: 'Kerja yang baik! Anda telah menyelesaikan rehat minda.',
    },
    focusSessionReminder: {
      title: 'Peringatan Sesi Fokus',
      body: 'Masa untuk berehat dari telefon anda.',
    },
    communityChallenge: {
      title: 'Cabaran Komuniti',
      body: 'Kumpulan anda sedang membuat kemajuan! Sertai gerakan minda.',
    },
  },
  ta: {
    mindfulNudge: {
      title: 'MindfulMoment',
      body: 'உங்கள் தொலைபேசியை நிறுத்தி சுற்றுப்புறத்தை கவனிக்கவும்.',
    },
    safetyReminder: {
      title: 'பாதுகாப்பு நினைவூட்டல்',
      body: 'தலையை உயர்த்தி எச்சரிக்கையாக இருங்கள். உங்கள் பாதுகாப்பு முக்கியம்.',
    },
    focusSessionStart: {
      title: 'கவனம் செலுத்தும் நேரம் தொடங்கியது',
      body: 'உங்கள் தொலைபேசி இல்லா நேரம் தொடங்கியது. கவனத்துடன் இருங்கள்!',
    },
    focusSessionEnd: {
      title: 'கவனம் செலுத்தும் நேரம் முடிந்தது',
      body: 'நல்ல வேலை! நீங்கள் உங்கள் மனதளவு ஓய்வை முடித்துவிட்டீர்கள்.',
    },
    focusSessionReminder: {
      title: 'கவனம் செலுத்தும் நேர நினைவூட்டல்',
      body: 'உங்கள் தொலைபேசியிலிருந்து ஓய்வெடுக்க வேண்டிய நேரம்.',
    },
    communityChallenge: {
      title: 'சமூக சவால்',
      body: 'உங்கள் குழு முன்னேற்றம் காண்கிறது! மனதளவு இயக்கத்தில் சேரவும்.',
    },
  },
};

class NotificationService {
  private settings: NotificationSettings;
  private notificationEvents: NotificationEvent[] = [];
  private isInitialized = false;
  private currentLanguage = 'en';

  constructor() {
    this.settings = {
      enabled: true,
      mindfulNudges: true,
      safetyReminders: true,
      focusSessionAlerts: true,
      communityUpdates: true,
      quietHours: {
        enabled: false,
        start: '22:00',
        end: '07:00',
      },
    };
  }

  async initialize(): Promise<void> {
    if (this.isInitialized) return;

    try {
      // Configure notification behavior
      Notifications.setNotificationHandler({
        handleNotification: async () => ({
          shouldShowAlert: true,
          shouldPlaySound: true,
          shouldSetBadge: false,
        }),
      });

      // Request permissions
      const { status } = await Notifications.requestPermissionsAsync();
      if (status !== 'granted') {
        console.log('Notification permissions not granted');
        return;
      }

      // Load settings and events
      await this.loadSettings();
      await this.loadNotificationEvents();

      this.isInitialized = true;
      console.log('NotificationService initialized');
    } catch (error) {
      console.error('Error initializing NotificationService:', error);
    }
  }

  async setLanguage(language: string): Promise<void> {
    this.currentLanguage = language;
    await this.saveSettings();
  }

  async updateSettings(newSettings: Partial<NotificationSettings>): Promise<void> {
    this.settings = { ...this.settings, ...newSettings };
    await this.saveSettings();
  }

  getSettings(): NotificationSettings {
    return this.settings;
  }

  async sendMindfulNudge(zone?: GeofenceZone): Promise<void> {
    if (!this.settings.enabled || !this.settings.mindfulNudges || this.isInQuietHours()) {
      return;
    }

    const messages = NOTIFICATION_MESSAGES[this.currentLanguage as keyof typeof NOTIFICATION_MESSAGES] || NOTIFICATION_MESSAGES.en;
    
    const notification: NotificationEvent = {
      id: `mindful_${Date.now()}`,
      type: 'mindful_nudge',
      title: messages.mindfulNudge.title,
      body: messages.mindfulNudge.body,
      timestamp: new Date(),
      zoneId: zone?.id,
      acknowledged: false,
      dismissed: false,
    };

    await this.sendNotification(notification);
  }

  async sendSafetyReminder(zone?: GeofenceZone): Promise<void> {
    if (!this.settings.enabled || !this.settings.safetyReminders || this.isInQuietHours()) {
      return;
    }

    const messages = NOTIFICATION_MESSAGES[this.currentLanguage as keyof typeof NOTIFICATION_MESSAGES] || NOTIFICATION_MESSAGES.en;
    
    const notification: NotificationEvent = {
      id: `safety_${Date.now()}`,
      type: 'safety_reminder',
      title: messages.safetyReminder.title,
      body: messages.safetyReminder.body,
      timestamp: new Date(),
      zoneId: zone?.id,
      acknowledged: false,
      dismissed: false,
    };

    await this.sendNotification(notification);
  }

  async sendFocusSessionStart(duration: number): Promise<void> {
    if (!this.settings.enabled || !this.settings.focusSessionAlerts || this.isInQuietHours()) {
      return;
    }

    const messages = NOTIFICATION_MESSAGES[this.currentLanguage as keyof typeof NOTIFICATION_MESSAGES] || NOTIFICATION_MESSAGES.en;
    
    const notification: NotificationEvent = {
      id: `focus_start_${Date.now()}`,
      type: 'focus_session',
      title: messages.focusSessionStart.title,
      body: messages.focusSessionStart.body,
      timestamp: new Date(),
      acknowledged: false,
      dismissed: false,
    };

    await this.sendNotification(notification);
  }

  async sendFocusSessionEnd(mindfulMinutes: number): Promise<void> {
    if (!this.settings.enabled || !this.settings.focusSessionAlerts || this.isInQuietHours()) {
      return;
    }

    const messages = NOTIFICATION_MESSAGES[this.currentLanguage as keyof typeof NOTIFICATION_MESSAGES] || NOTIFICATION_MESSAGES.en;
    
    const notification: NotificationEvent = {
      id: `focus_end_${Date.now()}`,
      type: 'focus_session',
      title: messages.focusSessionEnd.title,
      body: `${messages.focusSessionEnd.body} You earned ${mindfulMinutes} mindful minutes!`,
      timestamp: new Date(),
      acknowledged: false,
      dismissed: false,
    };

    await this.sendNotification(notification);
  }

  async sendFocusSessionReminder(): Promise<void> {
    if (!this.settings.enabled || !this.settings.focusSessionAlerts || this.isInQuietHours()) {
      return;
    }

    const messages = NOTIFICATION_MESSAGES[this.currentLanguage as keyof typeof NOTIFICATION_MESSAGES] || NOTIFICATION_MESSAGES.en;
    
    const notification: NotificationEvent = {
      id: `focus_reminder_${Date.now()}`,
      type: 'focus_session',
      title: messages.focusSessionReminder.title,
      body: messages.focusSessionReminder.body,
      timestamp: new Date(),
      acknowledged: false,
      dismissed: false,
    };

    await this.sendNotification(notification);
  }

  async sendCommunityUpdate(message: string): Promise<void> {
    if (!this.settings.enabled || !this.settings.communityUpdates || this.isInQuietHours()) {
      return;
    }

    const messages = NOTIFICATION_MESSAGES[this.currentLanguage as keyof typeof NOTIFICATION_MESSAGES] || NOTIFICATION_MESSAGES.en;
    
    const notification: NotificationEvent = {
      id: `community_${Date.now()}`,
      type: 'community',
      title: messages.communityChallenge.title,
      body: message,
      timestamp: new Date(),
      acknowledged: false,
      dismissed: false,
    };

    await this.sendNotification(notification);
  }

  private async sendNotification(notification: NotificationEvent): Promise<void> {
    try {
      // Schedule the notification
      await Notifications.scheduleNotificationAsync({
        content: {
          title: notification.title,
          body: notification.body,
          data: { notificationId: notification.id },
        },
        trigger: null, // Send immediately
      });

      // Store the notification event
      this.notificationEvents.push(notification);
      await this.saveNotificationEvents();

      console.log(`Notification sent: ${notification.type}`);
    } catch (error) {
      console.error('Error sending notification:', error);
    }
  }

  async acknowledgeNotification(notificationId: string): Promise<void> {
    const notification = this.notificationEvents.find(n => n.id === notificationId);
    if (notification) {
      notification.acknowledged = true;
      await this.saveNotificationEvents();
    }
  }

  async dismissNotification(notificationId: string): Promise<void> {
    const notification = this.notificationEvents.find(n => n.id === notificationId);
    if (notification) {
      notification.dismissed = true;
      await this.saveNotificationEvents();
    }
  }

  getNotificationEvents(): NotificationEvent[] {
    return this.notificationEvents;
  }

  getTodayNotifications(): NotificationEvent[] {
    const today = new Date().toISOString().split('T')[0];
    return this.notificationEvents.filter(event => 
      event.timestamp.toISOString().startsWith(today)
    );
  }

  getNotificationStats(): {
    total: number;
    acknowledged: number;
    dismissed: number;
    mindfulNudges: number;
    safetyReminders: number;
  } {
    const todayNotifications = this.getTodayNotifications();
    
    return {
      total: todayNotifications.length,
      acknowledged: todayNotifications.filter(n => n.acknowledged).length,
      dismissed: todayNotifications.filter(n => n.dismissed).length,
      mindfulNudges: todayNotifications.filter(n => n.type === 'mindful_nudge').length,
      safetyReminders: todayNotifications.filter(n => n.type === 'safety_reminder').length,
    };
  }

  private isInQuietHours(): boolean {
    if (!this.settings.quietHours.enabled) return false;

    const now = new Date();
    const currentTime = now.getHours() * 60 + now.getMinutes();
    
    const [startHour, startMinute] = this.settings.quietHours.start.split(':').map(Number);
    const [endHour, endMinute] = this.settings.quietHours.end.split(':').map(Number);
    
    const startTime = startHour * 60 + startMinute;
    const endTime = endHour * 60 + endMinute;

    if (startTime <= endTime) {
      // Same day (e.g., 09:00 to 17:00)
      return currentTime >= startTime && currentTime <= endTime;
    } else {
      // Overnight (e.g., 22:00 to 07:00)
      return currentTime >= startTime || currentTime <= endTime;
    }
  }

  private async loadSettings(): Promise<void> {
    try {
      const settingsData = await AsyncStorage.getItem('notificationSettings');
      if (settingsData) {
        this.settings = { ...this.settings, ...JSON.parse(settingsData) };
      }
    } catch (error) {
      console.error('Error loading notification settings:', error);
    }
  }

  private async saveSettings(): Promise<void> {
    try {
      await AsyncStorage.setItem('notificationSettings', JSON.stringify(this.settings));
    } catch (error) {
      console.error('Error saving notification settings:', error);
    }
  }

  private async loadNotificationEvents(): Promise<void> {
    try {
      const eventsData = await AsyncStorage.getItem('notificationEvents');
      if (eventsData) {
        this.notificationEvents = JSON.parse(eventsData).map((event: any) => ({
          ...event,
          timestamp: new Date(event.timestamp),
        }));
      }
    } catch (error) {
      console.error('Error loading notification events:', error);
    }
  }

  private async saveNotificationEvents(): Promise<void> {
    try {
      await AsyncStorage.setItem('notificationEvents', JSON.stringify(this.notificationEvents));
    } catch (error) {
      console.error('Error saving notification events:', error);
    }
  }

  async clearNotificationData(): Promise<void> {
    this.notificationEvents = [];
    await AsyncStorage.removeItem('notificationEvents');
  }
}

export const notificationService = new NotificationService(); 