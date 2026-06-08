import { Component, OnInit } from '@angular/core';
import { BreakpointObserver } from '@angular/cdk/layout';
import { Router } from '@angular/router';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { AuthService } from '../../services/auth.service';
import { User } from '../../models/user.model';

@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.scss']
})
export class HeaderComponent implements OnInit {
  /** Viewports at or below this width use the collapsible nav (CDK Handset is too narrow). */
  private static readonly COMPACT_HEADER_MAX_PX = 1100;

  isCompactHeader$!: Observable<boolean>;

  currentUser: User | null = null;
  isMenuOpen = false;

  constructor(
    private breakpointObserver: BreakpointObserver,
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit() {
    const mq = `(max-width: ${HeaderComponent.COMPACT_HEADER_MAX_PX}px)`;
    this.isCompactHeader$ = this.breakpointObserver
      .observe(mq)
      .pipe(map(result => result.matches));
    this.authService.currentUser$.subscribe(user => {
      this.currentUser = user;
    });
  }

  toggleMenu() {
    this.isMenuOpen = !this.isMenuOpen;
  }

  closeMenu() {
    this.isMenuOpen = false;
  }

  logout() {
    this.authService.logout().subscribe(() => {
      this.closeMenu();
      this.router.navigate(['/login']);
    });
  }

  getGreeting(): string {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  }

  getUserDisplayName(): string {
    if (!this.currentUser) return '';
    return this.currentUser.firstName || this.currentUser.username || 'User';
  }

  get showAdminNav(): boolean {
    return this.authService.isAdmin() || this.authService.isDeveloper();
  }
}
