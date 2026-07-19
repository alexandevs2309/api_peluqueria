import { TestBed } from '@angular/core/testing';
import { OfflineService } from './offline.service';

describe('OfflineService', () => {
    let service: OfflineService;

    beforeEach(() => {
        TestBed.configureTestingModule({});
        service = TestBed.inject(OfflineService);
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    it('should initialize with current navigator.onLine status', () => {
        expect(service.isOffline()).toBe(!navigator.onLine);
    });

    it('should update isOffline to false on online event', () => {
        window.dispatchEvent(new Event('online'));
        expect(service.isOffline()).toBeFalse();
    });

    it('should update isOffline to true on offline event', () => {
        window.dispatchEvent(new Event('offline'));
        expect(service.isOffline()).toBeTrue();
    });
});
