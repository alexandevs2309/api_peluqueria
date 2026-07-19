import { Injectable, inject } from '@angular/core';
import { environment } from '../../../environments/environment';
import { CanActivate, Router } from '@angular/router';
import { Observable, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { AuthService } from '../services/auth/auth.service';
import { MessageService } from 'primeng/api';

@Injectable({
  providedIn: 'root'
})
export class EmployeeManagementGuard implements CanActivate {
  private authService = inject(AuthService);
  private router = inject(Router);
  private messageService = inject(MessageService);

  canActivate(): Observable<boolean> {
    const user = this.authService.getCurrentUser();
    
    if (!user) {
      this.router.navigate(['/auth/login']);
      return of(false);
    }

    // SuperAdmin siempre puede acceder
    if (this.authService.isSuperAdmin()) {
      return of(true);
    }

    // ClientAdmin puede gestionar empleados
    if (this.authService.isClientAdmin()) {
      return this.validateTenantAndSubscription();
    }

    // ClientStaff no puede gestionar empleados
    this.messageService.add({
      severity: 'warn',
      summary: 'Acceso Denegado',
      detail: 'No tiene permisos para gestionar empleados'
    });
    
    this.router.navigate(['/client/dashboard']);
    return of(false);
  }

  private validateTenantAndSubscription(): Observable<boolean> {
    const user = this.authService.getCurrentUser();
    
    if (!user?.tenant_id) {
      this.messageService.add({
        severity: 'error',
        summary: 'Error de Configuración',
        detail: 'Usuario sin tenant asignado. Contacte al administrador.'
      });
      
      this.router.navigate(['/client/dashboard']);
      return of(false);
    }

    // Validar permisos específicos del usuario
    return this.authService.getUserPermissions().pipe(
      map((permissions) => {
        const canManageEmployees = permissions?.employees?.create || 
                                 permissions?.employees?.update || 
                                 permissions?.employees?.delete;
        
        if (!canManageEmployees) {
          this.messageService.add({
            severity: 'warn',
            summary: 'Permisos Insuficientes',
            detail: 'Su plan actual no incluye gestión de empleados'
          });
          
          this.router.navigate(['/client/dashboard']);
          return false;
        }
        
        return true;
      }),
      catchError((error) => {
        if (!environment.production) console.error('[EmployeeManagementGuard] Error validando permisos:', error);
        this.router.navigate(['/client/dashboard']);
        return of(false);
      })
    );
  }
}
