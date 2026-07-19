import { TestBed } from '@angular/core/testing';
import { Access } from './access';
import { AppConfigService } from '../../core/services/app-config.service';
import { AuthService } from '../../core/services/auth/auth.service';
import { LocaleService } from '../../core/services/locale/locale.service';
import { Router } from '@angular/router';

describe('Access', () => {
    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [
                { provide: AppConfigService, useValue: { supportEmail: () => 'test@test.com' } },
                { provide: AuthService, useValue: { getCurrentUser: () => null } },
                { provide: LocaleService, useValue: { t: (key: string) => key } },
                { provide: Router, useValue: { navigate: jasmine.createSpy('navigate') } }
            ]
        });
    });

    it('uses default message when no query param', () => {
        const route = { snapshot: { queryParams: {} } } as any;
        TestBed.runInInjectionContext(() => {
            const component = new Access(route);
            expect(component['message']).toBe('auth.access.default_message');
        });
    });

    it('uses custom message from query param', () => {
        const route = { snapshot: { queryParams: { message: 'Custom access message' } } } as any;
        TestBed.runInInjectionContext(() => {
            const component = new Access(route);
            expect(component['message']).toBe('Custom access message');
        });
    });
});
