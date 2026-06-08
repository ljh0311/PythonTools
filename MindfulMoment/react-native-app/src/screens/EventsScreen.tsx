import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../context/ThemeContext';
import { useApp } from '../context/AppContext';
import { Button } from '../components/Button';
import { Card } from '../components/Card';

const mockEvents = [
  {
    id: '1',
    title: 'Mindful Morning Walk',
    description: 'Join us for a peaceful morning walk in the park. Leave your phone behind and connect with nature.',
    date: '2024-01-15',
    time: '07:00',
    duration: '60',
    location: 'Central Park',
    distance: '0.5 km',
    attendees: 12,
    maxAttendees: 20,
    isRSVPd: true,
    category: 'Nature',
    icon: 'leaf-outline',
    color: '#28A745',
  },
  {
    id: '2',
    title: 'Digital Detox Meetup',
    description: 'A casual meetup to discuss digital wellness and share tips for mindful technology use.',
    date: '2024-01-18',
    time: '19:00',
    duration: '90',
    location: 'Community Center',
    distance: '1.2 km',
    attendees: 8,
    maxAttendees: 15,
    isRSVPd: false,
    category: 'Discussion',
    icon: 'people-outline',
    color: '#4A90E2',
  },
  {
    id: '3',
    title: 'Yoga in the Park',
    description: 'Outdoor yoga session focused on mindfulness and presence. No phones allowed.',
    date: '2024-01-20',
    time: '08:30',
    duration: '75',
    location: 'Riverside Park',
    distance: '2.1 km',
    attendees: 15,
    maxAttendees: 25,
    isRSVPd: false,
    category: 'Fitness',
    icon: 'fitness-outline',
    color: '#FF6B6B',
  },
  {
    id: '4',
    title: 'Reading Circle',
    description: 'Bring a book and join our reading circle. We\'ll discuss mindful reading habits.',
    date: '2024-01-22',
    time: '18:00',
    duration: '120',
    location: 'Local Library',
    distance: '0.8 km',
    attendees: 6,
    maxAttendees: 12,
    isRSVPd: true,
    category: 'Education',
    icon: 'library-outline',
    color: '#7B68EE',
  },
];

export default function EventsScreen() {
  const { theme } = useTheme();
  const { user } = useApp();
  const [selectedTab, setSelectedTab] = useState<'upcoming' | 'my-events'>('upcoming');

  const upcomingEvents = mockEvents.filter(event => !event.isRSVPd);
  const myEvents = mockEvents.filter(event => event.isRSVPd);

  const handleRSVP = (event: typeof mockEvents[0]) => {
    if (event.attendees >= event.maxAttendees) {
      Alert.alert('Event Full', 'This event has reached maximum capacity.');
      return;
    }

    Alert.alert(
      'RSVP to Event',
      `Would you like to RSVP to "${event.title}"?`,
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'RSVP', 
          onPress: () => {
            Alert.alert('Success!', `You've RSVP'd to ${event.title}. Check your email for details.`);
          }
        },
      ]
    );
  };

  const handleCancelRSVP = (event: typeof mockEvents[0]) => {
    Alert.alert(
      'Cancel RSVP',
      `Are you sure you want to cancel your RSVP for "${event.title}"?`,
      [
        { text: 'Keep RSVP', style: 'cancel' },
        { 
          text: 'Cancel RSVP', 
          style: 'destructive',
          onPress: () => {
            Alert.alert('Cancelled', `Your RSVP for ${event.title} has been cancelled.`);
          }
        },
      ]
    );
  };

  const handleScanQR = () => {
    Alert.alert(
      'QR Code Scanner',
      'This would open the camera to scan event QR codes for attendance.',
      [{ text: 'OK' }]
    );
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      weekday: 'short', 
      month: 'short', 
      day: 'numeric' 
    });
  };

  const renderEventCard = (event: typeof mockEvents[0]) => (
    <Card key={event.id} style={styles.eventCard}>
      <View style={styles.eventHeader}>
        <View style={[styles.eventIcon, { backgroundColor: event.color + '20' }]}>
          <Ionicons name={event.icon as any} size={24} color={event.color} />
        </View>
        <View style={styles.eventInfo}>
          <Text style={[styles.eventTitle, { color: theme.colors.text }]}>
            {event.title}
          </Text>
          <Text style={[styles.eventCategory, { color: event.color }]}>
            {event.category}
          </Text>
        </View>
        <View style={styles.eventStatus}>
          {event.isRSVPd && (
            <View style={[styles.rsvpBadge, { backgroundColor: theme.colors.success }]}>
              <Text style={styles.rsvpText}>RSVP'd</Text>
            </View>
          )}
        </View>
      </View>

      <Text style={[styles.eventDescription, { color: theme.colors.textSecondary }]}>
        {event.description}
      </Text>

      <View style={styles.eventDetails}>
        <View style={styles.detailItem}>
          <Ionicons name="calendar-outline" size={16} color={theme.colors.textSecondary} />
          <Text style={[styles.detailText, { color: theme.colors.textSecondary }]}>
            {formatDate(event.date)} at {event.time}
          </Text>
        </View>
        
        <View style={styles.detailItem}>
          <Ionicons name="time-outline" size={16} color={theme.colors.textSecondary} />
          <Text style={[styles.detailText, { color: theme.colors.textSecondary }]}>
            {event.duration} minutes
          </Text>
        </View>
        
        <View style={styles.detailItem}>
          <Ionicons name="location-outline" size={16} color={theme.colors.textSecondary} />
          <Text style={[styles.detailText, { color: theme.colors.textSecondary }]}>
            {event.location} ({event.distance})
          </Text>
        </View>
        
        <View style={styles.detailItem}>
          <Ionicons name="people-outline" size={16} color={theme.colors.textSecondary} />
          <Text style={[styles.detailText, { color: theme.colors.textSecondary }]}>
            {event.attendees}/{event.maxAttendees} attendees
          </Text>
        </View>
      </View>

      <View style={styles.eventActions}>
        {event.isRSVPd ? (
          <Button
            title="Cancel RSVP"
            onPress={() => handleCancelRSVP(event)}
            variant="outline"
            size="small"
            style={styles.actionButton}
          />
        ) : (
          <Button
            title={event.attendees >= event.maxAttendees ? "Event Full" : "RSVP"}
            onPress={() => handleRSVP(event)}
            variant="primary"
            size="small"
            disabled={event.attendees >= event.maxAttendees}
            style={styles.actionButton}
          />
        )}
      </View>
    </Card>
  );

  const renderUpcomingEvents = () => (
    <View style={styles.eventsContainer}>
      {upcomingEvents.length > 0 ? (
        upcomingEvents.map(renderEventCard)
      ) : (
        <Card style={styles.emptyCard}>
          <Ionicons name="calendar-outline" size={48} color={theme.colors.textSecondary} />
          <Text style={[styles.emptyTitle, { color: theme.colors.text }]}>
            No Upcoming Events
          </Text>
          <Text style={[styles.emptyDescription, { color: theme.colors.textSecondary }]}>
            Check back later for new events in your area
          </Text>
        </Card>
      )}
    </View>
  );

  const renderMyEvents = () => (
    <View style={styles.eventsContainer}>
      {myEvents.length > 0 ? (
        myEvents.map(renderEventCard)
      ) : (
        <Card style={styles.emptyCard}>
          <Ionicons name="calendar-checkmark-outline" size={48} color={theme.colors.textSecondary} />
          <Text style={[styles.emptyTitle, { color: theme.colors.text }]}>
            No Events RSVP'd
          </Text>
          <Text style={[styles.emptyDescription, { color: theme.colors.textSecondary }]}>
            RSVP to events to see them here
          </Text>
        </Card>
      )}
    </View>
  );

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <View style={styles.header}>
        <Text style={[styles.title, { color: theme.colors.text }]}>
          Events & Activities
        </Text>
        <Button
          title="Scan QR"
          onPress={handleScanQR}
          variant="outline"
          size="small"
          icon={<Ionicons name="qr-code-outline" size={16} color={theme.colors.primary} />}
        />
      </View>

      {/* Tab Selector */}
      <View style={styles.tabContainer}>
        <Button
          title="Upcoming"
          onPress={() => setSelectedTab('upcoming')}
          variant={selectedTab === 'upcoming' ? 'primary' : 'outline'}
          size="medium"
          style={styles.tabButton}
        />
        <Button
          title="My Events"
          onPress={() => setSelectedTab('my-events')}
          variant={selectedTab === 'my-events' ? 'primary' : 'outline'}
          size="medium"
          style={styles.tabButton}
        />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {selectedTab === 'upcoming' ? renderUpcomingEvents() : renderMyEvents()}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    paddingBottom: 0,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
  },
  tabContainer: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    marginBottom: 20,
  },
  tabButton: {
    flex: 1,
    marginHorizontal: 4,
  },
  scrollContent: {
    padding: 20,
    paddingTop: 0,
  },
  eventsContainer: {
    marginBottom: 20,
  },
  eventCard: {
    marginBottom: 16,
  },
  eventHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  eventIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  eventInfo: {
    flex: 1,
  },
  eventTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  eventCategory: {
    fontSize: 12,
    fontWeight: '500',
  },
  eventStatus: {
    alignItems: 'flex-end',
  },
  rsvpBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  rsvpText: {
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: '600',
  },
  eventDescription: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 16,
  },
  eventDetails: {
    marginBottom: 16,
  },
  detailItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  detailText: {
    fontSize: 14,
    marginLeft: 8,
  },
  eventActions: {
    alignItems: 'flex-start',
  },
  actionButton: {
    minWidth: 100,
  },
  emptyCard: {
    alignItems: 'center',
    padding: 40,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginTop: 16,
    marginBottom: 8,
  },
  emptyDescription: {
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 20,
  },
}); 