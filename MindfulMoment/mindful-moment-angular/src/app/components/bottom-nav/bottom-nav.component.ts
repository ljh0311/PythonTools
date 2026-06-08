import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-bottom-nav',
  templateUrl: './bottom-nav.component.html',
  styleUrls: ['./bottom-nav.component.scss'],
  imports: [CommonModule],
  standalone: true
})
export class BottomNavComponent implements OnInit {
  currentRoute = '';

  baseNavItems = [
    { route: '/home', icon: 'fas fa-home', label: 'Home' },
    { route: '/focus', icon: 'fas fa-bolt', label: 'Focus' },
    { route: '/community', icon: 'fas fa-users', label: 'Community' },
    { route: '/insights', icon: 'fas fa-chart-line', label: 'Insights' },
    { route: '/bus', icon: 'fas fa-bus', label: 'Bus' },
    { route: '/settings', icon: 'fas fa-cog', label: 'Settings' }
  ];

  get navItems(): { route: string; icon: string; label: string }[] {
    const adminItems = this.authService.isAdmin() || this.authService.isDeveloper()
      ? [
          { route: '/admin/users', icon: 'fas fa-user-cog', label: 'Users' },
          { route: '/admin/insights', icon: 'fas fa-chart-pie', label: 'Summary' }
        ]
      : [];
    return [...this.baseNavItems, ...adminItems];
  }

  constructor(
    private router: Router,
    private authService: AuthService
  ) {}

  ngOnInit() {
    // Track current route
    this.router.events
      .pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd))
      .subscribe(event => {
        this.currentRoute = event.url;
      });
  }

  navigateTo(route: string) {
    this.router.navigate([route]);
  }

  isActive(route: string): boolean {
    return this.currentRoute === route || this.currentRoute.startsWith(route + '/');
  }
}
