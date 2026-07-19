import { Injectable, inject } from '@angular/core';
import { Observable, throwError, of } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';
import { EmployeeService, CreateEmployeeRequest } from './employee.service';
import { AuthService, CreateUserRequest, CreateUserResponse } from '../auth/auth.service';

export interface CreateEmployeeWithUserRequest {
  // Datos del usuario
  email: string;
  full_name: string;
  password: string;
  user_phone?: string;
  
  // Datos del empleado
  profession?: string;
  phone?: string;
  hire_date?: string;
  is_active: boolean;
}

export interface EmployeeCreationResult {
  success: boolean;
  user?: CreateUserResponse;
  employee?: any;
  error?: string;
  userCreated?: boolean;
  employeeCreated?: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class EmployeeManagementService {
  private authService = inject(AuthService);
  private employeeService = inject(EmployeeService);

  /**
   * Crea un empleado completo (usuario + empleado) con manejo de errores y rollback
   */
  createEmployeeWithUser(data: CreateEmployeeWithUserRequest): Observable<EmployeeCreationResult> {
    let createdUser: CreateUserResponse | null = null;
    
    // Paso 1: Crear usuario
    const userData: CreateUserRequest = {
      email: data.email,
      full_name: data.full_name,
      password: data.password,
      phone: data.user_phone || ''
    };

    return this.authService.createUser(userData).pipe(
      switchMap((user: CreateUserResponse) => {
        createdUser = user;
        
        // Paso 2: Crear empleado
        const employeeData: CreateEmployeeRequest = {
          user_id: user.id,
          profession: data.profession || '',
          phone: data.phone || '',
          hire_date: data.hire_date || new Date().toISOString().split('T')[0],
          is_active: data.is_active
        };

        return this.employeeService.createEmployee(employeeData).pipe(
          switchMap((employee) => {
            // Éxito completo
            return of({
              success: true,
              user: createdUser!,
              employee,
              userCreated: true,
              employeeCreated: true
            });
          }),
          catchError((employeeError) => {
            // Falló la creación del empleado, intentar rollback del usuario
            
            
            return this.authService.deleteUser(createdUser!.id).pipe(
              switchMap(() => {
                // Rollback exitoso
                return throwError(() => ({
                  success: false,
                  error: this.getEmployeeErrorMessage(employeeError),
                  userCreated: true,
                  employeeCreated: false,
                  rollbackSuccessful: true
                }));
              }),
              catchError((rollbackError) => {
                // Rollback falló - situación crítica
                
                return throwError(() => ({
                  success: false,
                  error: `Error creando empleado: ${this.getEmployeeErrorMessage(employeeError)}. ATENCIÓN: Se creó el usuario pero no se pudo eliminar. Contacte al administrador.`,
                  userCreated: true,
                  employeeCreated: false,
                  rollbackSuccessful: false,
                  criticalError: true
                }));
              })
            );
          })
        );
      }),
      catchError((userError) => {
        // Falló la creación del usuario
        
        return throwError(() => ({
          success: false,
          error: this.getUserErrorMessage(userError),
          userCreated: false,
          employeeCreated: false
        }));
      })
    );
  }

  /**
   * Valida si un email está disponible
   */
  validateEmailAvailability(email: string): Observable<boolean> {
    return this.authService.checkEmailAvailability(email).pipe(
      switchMap((response) => of(response?.available !== false)),
      catchError(() => of(false)) // En caso de error, asumir que NO está disponible
    );
  }

  /**
   * Obtiene usuarios disponibles para ser empleados
   */
  getAvailableUsers(): Observable<any[]> {
    return this.authService.getUsersAvailableForEmployee().pipe(
      catchError((error) => {
        
        return of([]);
      })
    );
  }

  /**
   * Valida los límites de empleados según el plan
   */
  validateEmployeeLimit(): Observable<{ canCreate: boolean; message?: string }> {
    return this.employeeService.getEmployees().pipe(
      switchMap((response) => {
        // Esta validación se hace en el backend, pero podemos hacer una pre-validación
        const currentCount = response?.results?.length || 0;
        
        // Por ahora retornamos true, el backend manejará los límites
        return of({ canCreate: true });
      }),
      catchError((error) => {
        if (error.status === 403 && error.error?.error?.includes('límite')) {
          return of({ 
            canCreate: false, 
            message: error.error.error 
          });
        }
        return of({ canCreate: true });
      })
    );
  }

  private getUserErrorMessage(error: any): string {
    if (error.status === 400) {
      if (error.error?.email) {
        return 'El email ya está registrado en el sistema';
      }
      if (error.error?.full_name) {
        return 'El nombre completo es inválido';
      }
      if (error.error?.password) {
        return 'La contraseña no cumple con los requisitos mínimos';
      }
      return 'Datos de usuario inválidos';
    }
    
    if (error.status === 403) {
      return 'Sin permisos para crear usuarios';
    }
    
    if (error.status === 0) {
      return 'Error de conexión al crear usuario';
    }
    
    return 'Error inesperado al crear usuario';
  }

  private getEmployeeErrorMessage(error: any): string {
    if (error.status === 400) {
      if (error.error?.user_id) {
        return 'Usuario inválido para empleado';
      }
      if (error.error?.error?.includes('límite')) {
        return error.error.error;
      }
      return 'Datos de empleado inválidos';
    }
    
    if (error.status === 403) {
      return 'Sin permisos para crear empleados';
    }
    
    if (error.status === 0) {
      return 'Error de conexión al crear empleado';
    }
    
    return 'Error inesperado al crear empleado';
  }
}
