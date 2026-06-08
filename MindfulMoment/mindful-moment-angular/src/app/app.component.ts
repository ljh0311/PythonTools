import { Component, OnInit, OnDestroy, HostListener } from '@angular/core';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Router, NavigationEnd } from '@angular/router';
import { Observable, Subject } from 'rxjs';
import { map, filter, takeUntil, take } from 'rxjs/operators';
import { LoadingService } from './services/loading.service';
import { AuthService } from './services/auth.service';
import { environment } from '../environments/environment';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit, OnDestroy {
  title = 'MindfulMoment';
  isMobile = false;
  isLoading$: Observable<boolean>;
  isHandset$!: Observable<boolean>;
  showHeader = false;
  showDevSidebar = false;
  isDevMode = !environment.production;
  private destroy$ = new Subject<void>();

  toggleDevSidebar(): void {
    this.showDevSidebar = !this.showDevSidebar;
  }

  closeDevSidebar(): void {
    this.showDevSidebar = false;
  }

  constructor(
    private breakpointObserver: BreakpointObserver,
    private loadingService: LoadingService,
    private authService: AuthService,
    private router: Router
  ) {
    // Use the debounced loading observable directly
    this.isLoading$ = this.loadingService.isLoading$;
  }

  ngOnInit() {
    // Force clear any stuck loading states on app initialization
    this.loadingService.forceHide();
    
    this.isHandset$ = this.breakpointObserver
      .observe(Breakpoints.Handset)
      .pipe(map((result) => result.matches));
    
    // Safety timeout: if loading is on for more than 30 seconds, force hide it
    this.isLoading$
      .pipe(
        filter(loading => loading === true),
        takeUntil(this.destroy$)
      )
      .subscribe(() => {
        setTimeout(() => {
          if (this.loadingService.isLoading$) {
            this.loadingService.isLoading$
              .pipe(take(1))
              .subscribe(isLoading => {
                if (isLoading) {
                  console.warn('Loading overlay was active for more than 30 seconds, forcing hide');
                  this.loadingService.forceHide();
                }
              });
          }
        }, 30000);
      });

    // Check if mobile on init
    this.checkMobile();

    // Update header visibility based on route and auth status
    this.updateHeaderVisibility();
    
    // Subscribe to route changes to update header visibility
    this.router.events
      .pipe(filter(event => event instanceof NavigationEnd))
      .subscribe(() => {
        this.updateHeaderVisibility();
      });
    
    // Subscribe to auth state changes
    this.authService.currentUser$.subscribe(() => {
      this.updateHeaderVisibility();
    });
  }

  private updateHeaderVisibility() {
    const url = this.router.url;
    const isAuthPage = url === '/login' || url === '/register' || url.startsWith('/login') || url.startsWith('/register');
    const isAuthenticated = this.authService.isAuthenticated();
    
    // Show header only if authenticated and not on auth pages
    this.showHeader = isAuthenticated && !isAuthPage;
  }

  @HostListener('window:resize', ['$event'])
  onResize(event: any) {
    this.checkMobile();
  }

  private checkMobile() {
    this.isMobile = window.innerWidth <= 768;
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
