import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { Subject, of } from 'rxjs';
import { takeUntil, debounceTime, distinctUntilChanged, switchMap, finalize, catchError } from 'rxjs/operators';
import { DataService } from '../../services/data.service';
import { PageBackBarComponent } from '../../components/page-back-bar/page-back-bar.component';
import {
  BusArrivalResponse,
  BusArrivalNextBus,
  BusStopLookup
} from '../../models/bus-arrival.model';

@Component({
  selector: 'app-bus-arrivals',
  templateUrl: './bus-arrivals.component.html',
  styleUrls: ['./bus-arrivals.component.scss'],
  imports: [CommonModule, FormsModule, PageBackBarComponent],
  standalone: true
})
export class BusArrivalsComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  private readonly searchTerms$ = new Subject<string>();

  busStopCode = '';
  stopSearchInput = '';
  stopMatches: BusStopLookup[] = [];
  stopSearchLoading = false;
  stopSearchError: string | null = null;
  selectedStopSummary: string | null = null;
  /** When set, manual edits to `busStopCode` that still match this code keep the selection hint. */
  private selectedStopCode: string | null = null;

  serviceNo = '';
  loading = false;
  error: string | null = null;
  result: BusArrivalResponse | null = null;

  constructor(private dataService: DataService) {}

  ngOnInit(): void {
    this.searchTerms$
      .pipe(
        takeUntil(this.destroy$),
        debounceTime(350),
        distinctUntilChanged((a, b) => a.trim() === b.trim()),
        switchMap((raw) => {
          this.stopSearchError = null;
          const q = raw.trim();
          if (q.length < 2) {
            this.stopMatches = [];
            this.stopSearchLoading = false;
            return of({ matches: [] as BusStopLookup[] });
          }
          this.stopSearchLoading = true;
          return this.dataService.searchBusStops(q).pipe(
            catchError((err: unknown) => {
              this.stopSearchError = this.describeStopSearchError(err);
              return of({ matches: [] as BusStopLookup[] });
            }),
            finalize(() => {
              this.stopSearchLoading = false;
            })
          );
        })
      )
      .subscribe((res) => {
        this.stopMatches = res.matches || [];
      });
  }

  private describeStopSearchError(err: unknown): string {
    if (err instanceof HttpErrorResponse) {
      if (err.status === 404) {
        return 'Stop search is not available (404). Restart or update the backend so it exposes GET /api/bus/stops/search.';
      }
      if (err.status === 503) {
        const body = err.error as { error?: string } | null;
        return body?.error || 'Bus stop search not configured. Set LTA_ACCOUNT_KEY in backend .env.';
      }
      if (err.error && typeof err.error === 'object' && 'error' in err.error) {
        return String((err.error as { error: string }).error);
      }
      if (err.status === 0) {
        return 'Cannot reach the API. Start the backend (e.g. port 3001) and use ng serve with proxy to /api.';
      }
      return err.message || `Stop search failed (${err.status})`;
    }
    if (err instanceof Error) {
      return err.message;
    }
    return 'Stop search failed';
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  onStopSearchInput(value: string): void {
    this.stopSearchError = null;
    if (this.selectedStopSummary != null && value.trim() !== this.selectedStopSummary.trim()) {
      this.selectedStopSummary = null;
      this.selectedStopCode = null;
      this.busStopCode = '';
    }
    this.searchTerms$.next(value);
    if (value.trim().length < 2) {
      this.stopMatches = [];
    }
  }

  onBusStopCodeInput(): void {
    const trimmed = this.busStopCode?.trim() ?? '';
    if (this.selectedStopCode != null && trimmed === this.selectedStopCode.trim()) {
      return;
    }
    this.selectedStopSummary = null;
    this.selectedStopCode = null;
    this.stopSearchInput = '';
    this.stopMatches = [];
  }

  selectStop(stop: BusStopLookup): void {
    this.selectedStopCode = stop.BusStopCode;
    this.busStopCode = stop.BusStopCode;
    this.selectedStopSummary = `${stop.Description} — ${stop.RoadName} (${stop.BusStopCode})`;
    this.stopSearchInput = this.selectedStopSummary;
    this.stopMatches = [];
  }

  loadArrivals(): void {
    const code = this.busStopCode?.trim();
    if (!code) {
      this.error = 'Select a stop from search or enter a bus stop code';
      return;
    }
    this.error = null;
    this.result = null;
    this.loading = true;
    const serviceNoOpt = this.serviceNo?.trim() || undefined;
    this.dataService
      .getBusArrivals(code, serviceNoOpt)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data) => {
          this.result = data;
          this.loading = false;
        },
        error: (err) => {
          this.loading = false;
          const status = err?.status;
          const body = err?.error;
          if (status === 503 || (body && body.error === 'Bus arrivals not configured')) {
            this.error = 'Bus arrivals not configured';
          } else {
            this.error = body?.error || err?.message || 'Unable to load bus arrivals';
          }
        }
      });
  }

  formatEta(eta: BusArrivalNextBus | undefined): string {
    if (!eta?.EstimatedArrival) return '--';
    try {
      const date = new Date(eta.EstimatedArrival);
      const now = new Date();
      const diffMs = date.getTime() - now.getTime();
      const diffMin = Math.round(diffMs / 60000);
      if (diffMin < 0) return 'Arriving';
      if (diffMin < 1) return '1 min';
      return `${diffMin} min`;
    } catch {
      return eta.EstimatedArrival;
    }
  }
}
