import { BehaviorSubject, Observable } from 'rxjs';
import { NoAuthGuard } from './no-auth.guard';
import { AuthService } from '../services/auth/auth.service';

describe('NoAuthGuard', () => {
    let guard: NoAuthGuard;
    let routerSpy: { navigate: jasmine.Spy };
    let isAuthenticatedSubject: BehaviorSubject<boolean>;
    let authServiceStub: Partial<AuthService>;
    let currentRole: string | null;

    beforeEach(() => {
        routerSpy = { navigate: jasmine.createSpy('navigate') };
        isAuthenticatedSubject = new BehaviorSubject<boolean>(false);
        currentRole = null;

        authServiceStub = {
            isAuthenticated$: isAuthenticatedSubject.asObservable(),
            getCurrentUserRole: () => currentRole,
            getCurrentUser: () => currentRole ? ({ role: currentRole } as any) : null
        };

        guard = new NoAuthGuard(authServiceStub as AuthService, routerSpy as any);
    });

    it('should allow access when the user is not authenticated', (done) => {
        (guard.canActivate() as Observable<boolean>).subscribe(result => {
            expect(result).toBeTrue();
            expect(routerSpy.navigate).not.toHaveBeenCalled();
            done();
        });
    });

    it('should redirect super admins away from auth pages', (done) => {
        currentRole = 'SUPER_ADMIN';
        isAuthenticatedSubject.next(true);

        (guard.canActivate() as Observable<boolean>).subscribe(result => {
            expect(result).toBeFalse();
            expect(routerSpy.navigate).toHaveBeenCalledWith(['/admin/dashboard']);
            done();
        });
    });

    it('should redirect tenant users away from auth pages', (done) => {
        currentRole = 'CLIENT_ADMIN';
        isAuthenticatedSubject.next(true);

        (guard.canActivate() as Observable<boolean>).subscribe(result => {
            expect(result).toBeFalse();
            expect(routerSpy.navigate).toHaveBeenCalledWith(['/client/dashboard']);
            done();
        });
    });
});
