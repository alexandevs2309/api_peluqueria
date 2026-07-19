import { Injectable } from '@angular/core';
import { PreloadingStrategy, Route } from '@angular/router';
import { Observable, EMPTY, timer } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { AuthService } from './auth/auth.service';

@Injectable({
    providedIn: 'root'
})
export class RoleBasedPreloadingStrategy implements PreloadingStrategy {
    constructor(private authService: AuthService) {}

    preload(route: Route, load: () => Observable<unknown>): Observable<unknown> {
        if (!route.data?.['preload']) {
            return EMPTY;
        }

        if (route.data['preloadAfterAuth'] && !this.authService.getCurrentUser()) {
            return EMPTY;
        }

        const allowedRoles = route.data['preloadFor'] as string[] | undefined;
        if (allowedRoles?.length) {
            const currentRole = this.authService.getCurrentUserRole();
            if (!currentRole || !allowedRoles.includes(currentRole)) {
                return EMPTY;
            }
        }

        const delayMs = Number(route.data['preloadDelayMs'] ?? 1200);
        return timer(delayMs).pipe(switchMap(() => load()));
    }
}
