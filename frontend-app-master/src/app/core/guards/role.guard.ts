import { Injectable } from '@angular/core';
import { CanActivate, Router, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { Observable, map } from 'rxjs';
import { AuthService } from '../services/auth/auth.service';
import { normalizeBusinessRole, normalizeRole, resolveBusinessRole } from '../utils/role-normalizer';
import { MessageService } from 'primeng/api';
import { AccessDeniedDialogService } from '../services/access-denied-dialog.service';

@Injectable({
  providedIn: 'root'
})
export class RoleGuard implements CanActivate {

  constructor(
    private authService: AuthService,
    private router: Router,
    private messageService: MessageService,
    private accessDeniedDialog: AccessDeniedDialogService,
  ) {}

  canActivate(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<boolean> | boolean {
    const requiredRoles = route.data['roles'] as string[];

    if (!requiredRoles || requiredRoles.length === 0) {
      return true;
    }

    return this.authService.currentUser$.pipe(
      map(user => {
        if (!user) {
          this.router.navigate(['/auth/login']);
          return false;
        }

        // Fix RBAC inconsistency: normalize the authenticated role before every raw-role comparison.
        const userRoleKey = normalizeRole(user.role);
        const userBusinessRole = resolveBusinessRole(user.role, user.business_role);
        const hasRequiredRole = requiredRoles.some((requiredRole) => {
          // Fix RBAC inconsistency: normalize route-declared raw roles through the same canonical path.
          const requiredRoleKey = normalizeRole(requiredRole);
          const requiredBusinessRole = normalizeBusinessRole(requiredRole);

          return (requiredRoleKey !== 'UNKNOWN' && requiredRoleKey === userRoleKey) || (!!requiredBusinessRole && requiredBusinessRole === userBusinessRole);
        });

        if (hasRequiredRole) {
          return true;
        } else {
          this.handleUnauthorizedAccess(userRoleKey, userBusinessRole);
          return false;
        }
      })
    );
  }

  private handleUnauthorizedAccess(_userRoleKey: string, _businessRole: string): void {
    const isSuperAdmin = _userRoleKey === 'SUPER_ADMIN';
    const redirectUrl = isSuperAdmin ? '/admin/dashboard' : '/client/dashboard';
    
    this.router.navigate([redirectUrl]).then(() => {
      this.accessDeniedDialog.show({
        title: 'Acceso Restringido',
        message: 'No tienes los permisos requeridos para acceder a esta página. Contacta al administrador si consideras que esto es un error.',
        primaryButtonLabel: 'Entendido',
        icon: 'pi-shield',
        iconColor: 'text-amber-500',
        iconBgColor: 'bg-amber-50 dark:bg-amber-950/20'
      });
    });
  }

}
