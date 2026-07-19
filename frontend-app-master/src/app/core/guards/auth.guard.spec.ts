import { AuthGuard } from './auth.guard';
import { AuthService } from '../services/auth/auth.service';

describe('AuthGuard', () => {
    let guard: AuthGuard;
    let authServiceSpy: jasmine.SpyObj<AuthService>;
    let routerSpy: { navigate: jasmine.Spy };

    beforeEach(() => {
        authServiceSpy = jasmine.createSpyObj<AuthService>('AuthService', [
            'getCurrentUser',
            'validateSession',
            'clearAuthData'
        ]);
        routerSpy = {
            navigate: jasmine.createSpy('navigate')
        };

        guard = new AuthGuard(authServiceSpy, routerSpy as any);
    });

    it('should redirect to login when there is no current user', () => {
        authServiceSpy.getCurrentUser.and.returnValue(null);

        const result = guard.canActivate({} as any, { url: '/client/dashboard' } as any);
        expect(result).toBeFalse();
        expect(routerSpy.navigate).toHaveBeenCalledWith(['/auth/login'], {
            queryParams: { returnUrl: '/client/dashboard' }
        });
    });

    it('should allow access when session validation succeeds', () => {
        authServiceSpy.getCurrentUser.and.returnValue({ id: 1 } as any);

        const result = guard.canActivate({} as any, { url: '/client/dashboard' } as any);
        expect(result).toBeTrue();
        expect(authServiceSpy.clearAuthData).not.toHaveBeenCalled();
        expect(routerSpy.navigate).not.toHaveBeenCalled();
    });
});
