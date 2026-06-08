import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class LoadingService {
  private loadingSubject = new BehaviorSubject<boolean>(false);
  // Debounce loading state changes to prevent flickering (only debounce rapid changes)
  public isLoading$ = this.loadingSubject.asObservable().pipe(
    debounceTime(150),
    distinctUntilChanged()
  );

  private loadingMessageSubject = new BehaviorSubject<string>('Loading...');
  public loadingMessage$ = this.loadingMessageSubject.asObservable();

  private loadingCount = 0;
  private minDisplayTime = 300; // Minimum time to show loading (ms)
  private showTime: number | null = null;
  private hideTimeout: any = null;

  show(message: string = 'Loading...'): void {
    // Clear any pending hide
    if (this.hideTimeout) {
      clearTimeout(this.hideTimeout);
      this.hideTimeout = null;
    }

    this.loadingCount++;
    this.loadingMessageSubject.next(message);
    
    // Only update if not already showing
    if (!this.loadingSubject.value) {
      this.showTime = Date.now();
      this.loadingSubject.next(true);
    }
  }

  hide(): void {
    this.loadingCount = Math.max(0, this.loadingCount - 1);
    
    if (this.loadingCount === 0 && this.loadingSubject.value) {
      // Calculate how long loading has been shown
      const displayTime = this.showTime ? Date.now() - this.showTime : 0;
      const remainingTime = Math.max(0, this.minDisplayTime - displayTime);

      if (remainingTime > 0) {
        // Wait for minimum display time before hiding
        this.hideTimeout = setTimeout(() => {
          this.loadingSubject.next(false);
          this.showTime = null;
          this.hideTimeout = null;
        }, remainingTime);
      } else {
        // Hide immediately if minimum time has passed
        this.loadingSubject.next(false);
        this.showTime = null;
      }
    }
  }

  forceHide(): void {
    if (this.hideTimeout) {
      clearTimeout(this.hideTimeout);
      this.hideTimeout = null;
    }
    this.loadingCount = 0;
    this.loadingSubject.next(false);
    this.showTime = null;
  }

  setMessage(message: string): void {
    this.loadingMessageSubject.next(message);
  }
}
