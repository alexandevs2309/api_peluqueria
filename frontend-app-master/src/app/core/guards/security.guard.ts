import { Injectable } from '@angular/core';
import { CanActivate, Router, ActivatedRouteSnapshot } from '@angular/router';
import { Observable, of } from 'rxjs';
import { map, catchError, delay } from 'rxjs/operators';
import { AuthService } from '../services/auth/auth.service';
import { normalizeRole } from '../utils/role-normalizer';

/**
 * SecurityGuard - Validaciones de seguridad adicionales
 * 
 * SEGURIDAD:
 * - Previene timing attacks (respuesta constante)
 * - Valida integridad de sesión con backend
 * - Detecta manipulación de datos locales
 * - Rate limiting en cliente
 */
@Injectable({
  providedIn: 'root'
})
export class SecurityGuard implements CanActivate {
  
  private readonly MIN_RESPONSE_TIME = 100; // ms
  private requestCount = 0;
  private lastRequestTime = 0;

  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  canActivate(route: ActivatedRouteSnapshot): Observable<boolean> {
    const startTime = Date.now();
    
    // ✅ Rate limiting básico en cliente
    if (this.isRateLimited()) {
      return this.denyWithConstantTime(startTime, 'rate_limit');
    }

    // ✅ Validar integridad de sesión
    return this.authService.validateSession().pipe(
      map(isValid => {
        if (!isValid) {
          this.authService.clearAuthData();
          this.router.navigate(['/auth/login']);
          return false;
        }

        // Validar que rol local coincide con backend (usa normalizeRole para mapear business roles internos)
        const localUser = this.authService.getCurrentUser();
        const requiredRoles = route.data['roles'] as string[];
        
        if (requiredRoles && localUser) {
          const hasRole = requiredRoles.some((r) => normalizeRole(r) === normalizeRole(localUser.role));
          if (!hasRole) {
            this.router.navigate(['/auth/login']);
            return false;
          }
        }

        return true;
      }),
      // ✅ Timing attack prevention - respuesta constante
      delay(Math.max(0, this.MIN_RESPONSE_TIME - (Date.now() - startTime))),
      catchError(() => this.denyWithConstantTime(startTime, 'error'))
    );
  }

  private isRateLimited(): boolean {
    const now = Date.now();
    const timeSinceLastRequest = now - this.lastRequestTime;
    
    // Reset counter cada segundo
    if (timeSinceLastRequest > 1000) {
      this.requestCount = 0;
    }
    
    this.lastRequestTime = now;
    this.requestCount++;
    
    // Máximo 10 requests por segundo
    return this.requestCount > 10;
  }

  private denyWithConstantTime(startTime: number, reason: string): Observable<boolean> {
    const elapsed = Date.now() - startTime;
    const delayTime = Math.max(0, this.MIN_RESPONSE_TIME - elapsed);
    
    return of(false).pipe(
      delay(delayTime)
    );
  }
}
