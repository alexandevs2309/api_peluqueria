import { Injectable } from '@angular/core';
import { CanActivate, Router, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { Observable, map } from 'rxjs';
import { AuthService } from '../services/auth/auth.service';
import { MessageService } from 'primeng/api';
import { safeGetItem } from '../utils/storage';

@Injectable({
  providedIn: 'root'
})
export class TenantGuard implements CanActivate {

  constructor(
    private authService: AuthService,
    private router: Router,
    private messageService: MessageService
  ) {}

  canActivate(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<boolean> | boolean {
    return this.authService.currentUser$.pipe(
      map(user => {
        if (!user) {
          this.router.navigate(['/auth/login']);
          return false;
        }

        // SuperAdmin siempre puede acceder
        if (this.authService.isSuperAdmin()) {
          return true;
        }

        // Otros usuarios deben tener un tenant
        const storedTenant = safeGetItem('tenant');
        if (!storedTenant) {
          this.messageService.add({ severity: 'error', summary: 'Acceso Denegado', detail: 'Usuario sin tenant asignado. Contacta al administrador.' });

          this.router.navigate(['/auth/login']);
          return false;
        }

        return true;
      })
    );
  }
}
