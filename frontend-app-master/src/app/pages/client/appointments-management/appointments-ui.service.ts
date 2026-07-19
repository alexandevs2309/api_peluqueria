import { Injectable } from '@angular/core';
import { Observable, Subject } from 'rxjs';

export type AppointmentCreateTarget = 'calendar' | 'list';

@Injectable({ providedIn: 'root' })
export class AppointmentsUiService {
    private readonly refreshSubject = new Subject<void>();
    private readonly createSubject = new Subject<AppointmentCreateTarget>();

    get refresh$(): Observable<void> {
        return this.refreshSubject.asObservable();
    }

    get create$(): Observable<AppointmentCreateTarget> {
        return this.createSubject.asObservable();
    }

    requestRefresh(): void {
        this.refreshSubject.next();
    }

    requestCreate(target: AppointmentCreateTarget): void {
        this.createSubject.next(target);
    }
}
