import { BehaviorSubject } from 'rxjs';
import { MessageService } from 'primeng/api';
import { RoleGuard } from './role.guard';
import { AuthService, User } from '../services/auth/auth.service';
import { AccessDeniedDialogService } from '../services/access-denied-dialog.service';

describe('RoleGuard', () => {
    let guard: RoleGuard;
    let routerSpy: { navigate: jasmine.Spy };
    let messageServiceSpy: jasmine.SpyObj<MessageService>;
    let accessDeniedDialogSpy: jasmine.SpyObj<AccessDeniedDialogService>;
    let currentUserSubject: BehaviorSubject<User | null>;
    let authServiceStub: Partial<AuthService>;

    beforeEach(() => {
        routerSpy = { navigate: jasmine.createSpy('navigate').and.returnValue(Promise.resolve(true)) };
        messageServiceSpy = jasmine.createSpyObj<MessageService>('MessageService', ['add']);
        accessDeniedDialogSpy = jasmine.createSpyObj<AccessDeniedDialogService>('AccessDeniedDialogService', ['show', 'dismiss']);
        currentUserSubject = new BehaviorSubject<User | null>(null);
        authServiceStub = {
            currentUser$: currentUserSubject.asObservable()
        };

        guard = new RoleGuard(authServiceStub as AuthService, routerSpy as any, messageServiceSpy, accessDeniedDialogSpy);
    });

    it('should allow access when no roles are required', () => {
        const result = guard.canActivate({ data: {} } as any, {} as any);
        expect(result).toBeTrue();
    });

    it('should redirect to login when the user is missing', (done) => {
        const result = guard.canActivate({ data: { roles: ['CLIENT_ADMIN'] } } as any, {} as any);

        (result as any).subscribe((allowed: boolean) => {
            expect(allowed).toBeFalse();
            expect(routerSpy.navigate).toHaveBeenCalledWith(['/auth/login']);
            done();
        });
    });

    it('should allow access when the user role matches', (done) => {
        currentUserSubject.next({
            id: 1,
            email: 'admin@test.com',
            full_name: 'Admin',
            role: 'CLIENT_ADMIN',
            roles: []
        });

        const result = guard.canActivate({ data: { roles: ['CLIENT_ADMIN'] } } as any, {} as any);

        (result as any).subscribe((allowed: boolean) => {
            expect(allowed).toBeTrue();
            expect(routerSpy.navigate).not.toHaveBeenCalled();
            done();
        });
    });

    it('should deny access and redirect client roles to client dashboard', (done) => {
        currentUserSubject.next({
            id: 2,
            email: 'staff@test.com',
            full_name: 'Staff',
            role: 'CLIENT_STAFF',
            roles: []
        });

        const result = guard.canActivate({ data: { roles: ['SUPER_ADMIN'] } } as any, {} as any);

        (result as any).subscribe((allowed: boolean) => {
            expect(allowed).toBeFalse();
            expect(routerSpy.navigate).toHaveBeenCalledWith(['/client/dashboard']);
            setTimeout(() => {
                expect(accessDeniedDialogSpy.show).toHaveBeenCalled();
                done();
            });
        });
    });
});
