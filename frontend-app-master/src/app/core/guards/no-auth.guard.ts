import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { Observable, of } from 'rxjs';
import { AuthService } from '../services/auth/auth.service';
import { roleKey } from '../utils/role-normalizer';

@Injectable({
  providedIn: 'root'
})
export class NoAuthGuard implements CanActivate {

  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  canActivate(): Observable<boolean> | boolean {
    // Check synchronous state first to avoid race condition with isAuthenticated$
    if (this.authService.getCurrentUser()) {
      const userRole = this.authService.getCurrentUserRole();
      this.redirectToDashboard(userRole);
      return of(false);
    }
    return of(true);
  }


  private redirectToDashboard(role: string | null): void {
    switch (roleKey(role)) {
      case 'SUPER_ADMIN':
        this.router.navigate(['/admin/dashboard']);
        break;
      case 'CLIENT_ADMIN':
      case 'CLIENT_STAFF':
      case 'CAJERA':
      case 'ESTILISTA':
      case 'MANAGER':
        this.router.navigate(['/client/dashboard']);
        break;
      default:
        this.router.navigate(['/landing']);
    }
  }
}
