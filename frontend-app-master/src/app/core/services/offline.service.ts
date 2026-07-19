import { Injectable, signal } from '@angular/core';

@Injectable({
    providedIn: 'root'
})
export class OfflineService {
    private readonly offlineSignal = signal<boolean>(!navigator.onLine);
    isOffline = this.offlineSignal.asReadonly();

    constructor() {
        window.addEventListener('online', () => this.offlineSignal.set(false));
        window.addEventListener('offline', () => this.offlineSignal.set(true));
    }
}
