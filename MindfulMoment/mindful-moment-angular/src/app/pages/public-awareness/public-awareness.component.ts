import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { AuthService } from '../../services/auth.service';
import { DataService } from '../../services/data.service';
import { LocationService, LocationData, LocationInfo } from '../../services/location.service';
import { GpsStatusComponent } from '../../components/gps-status/gps-status.component';
import { User } from '../../models/user.model';

@Component({
  selector: 'app-public-awareness',
  templateUrl: './public-awareness.component.html',
  styleUrls: ['./public-awareness.component.scss'],
  imports: [CommonModule, GpsStatusComponent],
  standalone: true
})
export class PublicAwarenessComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  
  currentUser: User | null = null;
  isInPublicSpace = false;
  currentLocation = 'Unknown';
  publicSessionActive = false;
  currentLocationData: LocationData | null = null;
  currentLocationInfo: LocationInfo | null = null;
  gpsEnabled = false;
  
  // Safety tips
  safetyTips: any[] = [];
  
  // Emergency contacts
  emergencyContacts: any[] = [];

  // Flags to track static values
  hasStaticValues = {
    safetyTips: false,
    emergencyContacts: false
  };
  
  // Public awareness stats
  awarenessStats = {
    totalPublicTime: 0,
    safetyAlerts: 0,
    socialPrompts: 0,
    mindfulScore: 0
  };

  constructor(
    private authService: AuthService,
    private dataService: DataService,
    private router: Router,
    private locationService: LocationService
  ) {}

  ngOnInit() {
    this.loadUserData();
    this.loadAwarenessData();
    this.loadSafetyTips();
    this.loadEmergencyContacts();
    this.detectLocation();
  }

  private loadSafetyTips() {
    this.dataService.getSafetyTips()
      .pipe(takeUntil(this.destroy$))
      .subscribe(tips => {
        if (tips && tips.length > 0) {
          this.safetyTips = tips;
          this.hasStaticValues.safetyTips = false;
        } else {
          // Use static values temporarily
          this.safetyTips = [
            {
              id: 'mrt-safety',
              title: 'MRT Safety',
              icon: 'fas fa-train',
              tips: [
                'Stand behind the yellow line on platforms',
                'Look up from your phone when boarding/alighting',
                'Be aware of platform gaps',
                'Hold handrails on escalators'
              ]
            },
            {
              id: 'crossing-safety',
              title: 'Road Crossing',
              icon: 'fas fa-walking',
              tips: [
                'Look both ways before crossing',
                'Use designated crosswalks',
                'Wait for the green man signal',
                'Avoid using phone while crossing'
              ]
            },
            {
              id: 'crowd-safety',
              title: 'Crowded Areas',
              icon: 'fas fa-users',
              tips: [
                'Be aware of your surroundings',
                'Keep personal belongings secure',
                'Follow crowd flow direction',
                'Stay alert in busy areas'
              ]
            }
          ];
          this.hasStaticValues.safetyTips = true;
        }
      });
  }

  private loadEmergencyContacts() {
    this.dataService.getEmergencyContacts()
      .pipe(takeUntil(this.destroy$))
      .subscribe(contacts => {
        if (contacts && contacts.length > 0) {
          this.emergencyContacts = contacts;
          this.hasStaticValues.emergencyContacts = false;
        } else {
          // Use static values temporarily
          this.emergencyContacts = [
            { name: 'Police', number: '999', icon: 'fas fa-shield-alt', color: '#DC3545' },
            { name: 'Ambulance', number: '995', icon: 'fas fa-ambulance', color: '#28A745' },
            { name: 'Fire Department', number: '995', icon: 'fas fa-fire', color: '#FF9800' },
            { name: 'Non-Emergency', number: '1800-255-0000', icon: 'fas fa-phone', color: '#6C757D' }
          ];
          this.hasStaticValues.emergencyContacts = true;
        }
      });
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private loadUserData() {
    this.authService.currentUser$
      .pipe(takeUntil(this.destroy$))
      .subscribe(user => {
        this.currentUser = user;
      });
  }

  private loadAwarenessData() {
    if (!this.currentUser) return;

    const userId = this.currentUser.id;
    this.dataService.getUserStats(userId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (stats) => {
          if (stats?.publicAwarenessStats) {
            this.awarenessStats = {
              totalPublicTime: stats.publicAwarenessStats.totalPublicTime || 0,
              safetyAlerts: stats.publicAwarenessStats.safetyAlerts || 0,
              socialPrompts: stats.publicAwarenessStats.socialPrompts || 0,
              mindfulScore: stats.publicAwarenessStats.mindfulScore || 0
            };
          }
        },
        error: (error) => {
          console.error('Error loading awareness data:', error);
        }
      });
  }

  private detectLocation() {
    // Get real location using GPS
    this.locationService.getCurrentLocation()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (location) => {
          this.currentLocationData = location;
          this.gpsEnabled = true;
          
          // Get location info (type, name, environment)
          this.locationService.getLocationInfo(location)
            .pipe(takeUntil(this.destroy$))
            .subscribe({
              next: (info) => {
                this.currentLocationInfo = info;
                this.isInPublicSpace = info.type === 'public' || info.type === 'transport';
                this.currentLocation = info.name;
              },
              error: (error) => {
                console.error('Error getting location info:', error);
                this.currentLocation = 'Unknown Location';
              }
            });
        },
        error: (error) => {
          console.error('Error getting location:', error);
          this.gpsEnabled = false;
          this.currentLocation = 'GPS Unavailable';
        }
      });
  }

  startPublicSession() {
    this.publicSessionActive = true;
    // Start monitoring public behavior
  }

  endPublicSession() {
    this.publicSessionActive = false;
    // End monitoring and save data
  }

  callEmergency(number: string) {
    window.open(`tel:${number}`, '_self');
  }

  showSafetyTip(tipId: string) {
    // Show detailed safety tip
    console.log('Showing safety tip:', tipId);
  }

  navigateToHome() {
    this.router.navigate(['/home']);
  }

  navigateToFocus() {
    this.router.navigate(['/focus']);
  }
}
