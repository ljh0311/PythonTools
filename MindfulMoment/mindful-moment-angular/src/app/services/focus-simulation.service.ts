import { Injectable } from '@angular/core';
import { Subject, Observable } from 'rxjs';
import { DistractionType } from '../models/focus-session.model';

export type SimulationEvent =
  | { type: 'distraction'; distractionType?: DistractionType; description?: string }
  | { type: 'notification' };

@Injectable({
  providedIn: 'root'
})
export class FocusSimulationService {
  private simulationEventsSubject = new Subject<SimulationEvent>();
  public simulationEvents$: Observable<SimulationEvent> = this.simulationEventsSubject.asObservable();

  simulateDistraction(type: DistractionType = DistractionType.PHONE, description?: string): void {
    this.simulationEventsSubject.next({
      type: 'distraction',
      distractionType: type,
      description: description ?? `Simulated ${type} distraction`
    });
  }

  simulateNotification(): void {
    this.simulationEventsSubject.next({ type: 'notification' });
  }
}
