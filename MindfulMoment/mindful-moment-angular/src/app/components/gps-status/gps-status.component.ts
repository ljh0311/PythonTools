import { Component, OnInit, OnDestroy, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LocationService, LocationData } from '../../services/location.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-gps-status',
  templateUrl: './gps-status.component.html',
  styleUrls: ['./gps-status.component.scss'],
  imports: [CommonModule],
  standalone: true
})
export class GpsStatusComponent implements OnInit, OnDestroy {
  @Input() showDetails: boolean = false;
  
  signalQuality: 'excellent' | 'good' | 'fair' | 'poor' | 'none' = 'none';
  accuracy: number = 0;
  isLoading: boolean = false;
  lastUpdated: Date | null = null;
  private locationSubscription?: Subscription;

  constructor(private locationService: LocationService) {}

  ngOnInit(): void {
    this.locationSubscription = this.locationService.currentLocation$.subscribe(location => {
      if (location) {
        this.accuracy = Math.round(location.accuracy || 0);
        this.signalQuality = this.locationService.getSignalQuality(location.accuracy);
        this.isLoading = false;
        this.lastUpdated = new Date();
      } else {
        this.isLoading = true;
      }
    });
  }

  ngOnDestroy(): void {
    if (this.locationSubscription) {
      this.locationSubscription.unsubscribe();
    }
  }

  getStatusColor(): string {
    switch (this.signalQuality) {
      case 'excellent': return '#28A745';
      case 'good': return '#5CB85C';
      case 'fair': return '#FFC107';
      case 'poor': return '#FF9800';
      case 'none': return '#DC3545';
      default: return '#6C757D';
    }
  }

  getStatusIcon(): string {
    switch (this.signalQuality) {
      case 'excellent':
      case 'good':
        return 'location_on';
      case 'fair':
        return 'location_searching';
      case 'poor':
      case 'none':
        return 'location_disabled';
      default:
        return 'location_off';
    }
  }

  getStatusText(): string {
    if (this.isLoading) return 'Locating...';
    return `GPS: ${this.signalQuality} (${this.accuracy}m)`;
  }
}
