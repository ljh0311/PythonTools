import { Injectable, ErrorHandler, Injector } from '@angular/core';
import { Router } from '@angular/router';
import { LoadingService } from './loading.service';

/**
 * Global Error Handler Service
 * Catches and handles all unhandled errors in the application
 */
@Injectable({
  providedIn: 'root'
})
export class GlobalErrorHandler implements ErrorHandler {
  constructor(
    private injector: Injector
  ) {}

  handleError(error: any): void {
    const router = this.injector.get(Router);
    const loadingService = this.injector.get(LoadingService);

    // Hide any loading overlays
    loadingService.forceHide();

    // Log error to console in development
    if (!this.isProduction()) {
      console.error('Global Error Handler:', error);
    }

    // Extract error message
    const errorMessage = this.extractErrorMessage(error);

    // Handle different types of errors
    if (error.status === 401 || error.status === 403) {
      // Unauthorized - redirect to login
      router.navigate(['/login']);
    } else if (error.status === 404) {
      // Not found - could show 404 page
      console.warn('Resource not found:', errorMessage);
    } else if (error.status >= 500) {
      // Server error - show user-friendly message
      this.showErrorNotification('Server error. Please try again later.');
    } else {
      // Other errors - show generic message
      this.showErrorNotification('An unexpected error occurred. Please try again.');
    }

    // In production, you might want to send error to logging service
    if (this.isProduction()) {
      this.logErrorToService(error);
    }
  }

  private extractErrorMessage(error: any): string {
    if (error?.error?.message) {
      return error.error.message;
    }
    if (error?.message) {
      return error.message;
    }
    if (typeof error === 'string') {
      return error;
    }
    return 'An unknown error occurred';
  }

  private isProduction(): boolean {
    return false; // TODO: Use environment variable
  }

  private showErrorNotification(message: string): void {
    // You can integrate with toast service here
    console.error('Error:', message);
    // Example: this.toastService.showError(message);
  }

  private logErrorToService(error: any): void {
    // TODO: Send error to logging service (e.g., Sentry, LogRocket)
    // Example:
    // this.loggingService.logError({
    //   message: error.message,
    //   stack: error.stack,
    //   url: window.location.href,
    //   timestamp: new Date().toISOString()
    // });
  }
}

