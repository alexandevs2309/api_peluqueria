import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent, HttpErrorResponse, HttpBackend, HttpClient } from '@angular/common/http';
import { Observable, of, ReplaySubject, throwError } from 'rxjs';
import { catchError, delay, retry, switchMap, take, tap } from 'rxjs/operators';
import { Router } from '@angular/router';
import { MessageService } from 'primeng/api';
import { environment } from '../../../environments/environment';
import { extractErrorDetail, getHttpErrorMessage } from '../utils/http-error-message';
import { ErrorDialogService } from '../services/error-dialog.service';

@Injectable()
export class ErrorInterceptor implements HttpInterceptor {
  private httpWithoutInterceptors: HttpClient;
  private refreshInProgress = false;
  private refreshCompleted$ = new ReplaySubject<boolean>(1);
  private errorDialog: ErrorDialogService;

  constructor(
    private router: Router,
    private messageService: MessageService,
    httpBackend: HttpBackend,
    errorDialog: ErrorDialogService
  ) {
    this.httpWithoutInterceptors = new HttpClient(httpBackend);
    this.errorDialog = errorDialog;
  }

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    return next.handle(req).pipe(
      retry({
        count: 1,
        delay: (error) => {
          if (error.status >= 500 && error.status < 600) {
            return of(null).pipe(delay(2000));
          }
          return throwError(() => error);
        }
      }),
      catchError((error: HttpErrorResponse) => {
        if (error.status === 401 && this.shouldAttemptRefresh(req.url)) {
          return this.tryRefreshAndRetry(req, next, error);
        }

        this.handleError(error);
        return throwError(() => error);
      })
    );
  }

  private shouldAttemptRefresh(url: string): boolean {
    return !url.includes('/auth/cookie-refresh/') && !url.includes('/auth/cookie-login/');
  }

  private tryRefreshAndRetry(req: HttpRequest<any>, next: HttpHandler, originalError: HttpErrorResponse): Observable<HttpEvent<any>> {
    if (this.refreshInProgress) {
      return this.refreshCompleted$.pipe(
        take(1),
        switchMap((refreshSucceeded) => {
          if (!refreshSucceeded) {
            this.handle401Error();
            return throwError(() => originalError);
          }

          const retryReq = req.clone({ withCredentials: true });
          return next.handle(retryReq);
        })
      );
    }

    this.refreshInProgress = true;

    return this.httpWithoutInterceptors
      .post(`${environment.apiUrl}/auth/cookie-refresh/`, {}, { withCredentials: true })
      .pipe(
        tap(() => {
          this.refreshInProgress = false;
          this.refreshCompleted$.next(true);
          this.refreshCompleted$.complete();
          this.refreshCompleted$ = new ReplaySubject<boolean>(1);
        }),
        switchMap(() => {
          const retryReq = req.clone({ withCredentials: true });
          return next.handle(retryReq);
        }),
        catchError(() => {
          this.refreshInProgress = false;
          this.refreshCompleted$.next(false);
          this.refreshCompleted$.complete();
          this.refreshCompleted$ = new ReplaySubject<boolean>(1);
          this.handle401Error();
          return throwError(() => originalError);
        })
      );
  }

  private handleError(error: HttpErrorResponse): void {
    if (error.status === 0) {
      if (!environment.production) console.warn('[ErrorInterceptor] Network error (status 0):', error.url || error.message)
      return
    }
    switch (error.status) {
      case 400:
        this.handle400Error(error);
        break;
      case 401:
        this.handle401Error();
        break;
      case 402:
        this.handle402Error(error);
        break;
      case 403:
        this.handle403Error(error);
        break;
      case 404:
        this.handle404Error();
        break;
      case 500:
        this.handle500Error();
        break;
      case 503:
        break;
      default:
        this.handleGenericError(error);
    }
  }

  private handle400Error(error: HttpErrorResponse): void {
    if (!this.router.url.startsWith('/auth/')) {
      const detail = extractErrorDetail(error);
      if (detail) {
        this.messageService.add({
          severity: 'warn',
          summary: 'Datos inválidos',
          detail: detail,
          life: 6000
        });
      }
    }
  }

  private handle401Error(): void {
    // ✅ SEGURO - Cookies httpOnly manejadas por navegador
    const currentUrl = this.router.url;
    const publicPages = ['/landing', '/auth', '/maintenance', '/tutorials'];
    const isPublicPage = publicPages.some(page => currentUrl.startsWith(page));
    
    if (!isPublicPage) {
      // Limpiar solo datos locales (no tokens)
      localStorage.removeItem('user');
      localStorage.removeItem('tenant');
      
      this.router.navigate(['/auth/login']);
      this.messageService.add({ 
        severity: 'error', 
        summary: 'Sesión expirada', 
        detail: 'Por favor, inicia sesión nuevamente.', 
        life: 3000 
      });
    }
  }

  private handle402Error(error: HttpErrorResponse): void {
    const errorData = error.error;
    const code = errorData?.code;
    
    if (code === 'TRIAL_EXPIRED') {
      this.messageService.add({ 
        severity: 'warn', 
        summary: 'Período de prueba expirado', 
        detail: 'Tu período de prueba ha expirado. Selecciona un plan para continuar.', 
        life: 5000 
      });
      this.router.navigate(['/client/payment']);
    } else if (code === 'SUBSCRIPTION_EXPIRED') {
      this.messageService.add({ 
        severity: 'warn', 
        summary: 'Suscripción expirada', 
        detail: 'Tu suscripción ha expirado. Renueva para continuar.', 
        life: 5000 
      });
      this.router.navigate(['/client/payment']);
    } else {
      this.messageService.add({ 
        severity: 'warn', 
        summary: 'Pago requerido', 
        detail: errorData?.error || 'Se requiere un plan activo para continuar.', 
        life: 5000 
      });
      this.router.navigate(['/client/payment']);
    }
  }

  private handle403Error(error: HttpErrorResponse): void {
    if (this.router.url.startsWith('/auth/')) return;

    const code = error.error?.code;
    if (code === 'TENANT_ARCHIVED') {
      this.messageService.add({
        severity: 'error',
        summary: 'Cuenta archivada',
        detail: 'Esta cuenta empresarial ha sido archivada. Contacta a soporte.',
        sticky: true
      });
      this.router.navigate(['/auth/login']);
      return;
    }
    if (code === 'NO_TENANT') {
      this.messageService.add({
        severity: 'error',
        summary: 'Sin tenant asignado',
        detail: 'Tu usuario no tiene una empresa asignada. Contacta a soporte.',
        sticky: true
      });
      this.router.navigate(['/auth/login']);
      return;
    }
    if (code === 'TENANT_INACTIVE') {
      this.messageService.add({
        severity: 'error',
        summary: 'Empresa suspendida',
        detail: error.error?.message || 'Esta cuenta empresarial está suspendida. Contacta a soporte.',
        sticky: true
      });
      this.router.navigate(['/client/payment']);
      return;
    }
    this.messageService.add({
      severity: 'warn',
      summary: 'Permiso denegado',
      detail: getHttpErrorMessage(error, 'No tienes permiso para realizar esta acción.'),
      sticky: true
    });
  }

  private handle404Error(): void {
    this.messageService.add({ severity: 'error', summary: 'Error', detail: 'Recurso no encontrado.' });
  }

  private handle500Error(): void {
    if (!this.router.url.startsWith('/auth/')) {
      this.messageService.add({
        severity: 'warn',
        summary: 'Error de conexión',
        detail: 'Error temporal del servidor. Los datos se cargarán cuando se restablezca la conexión.',
        life: 5000
      });
    }
  }

  private handleGenericError(error: HttpErrorResponse): void {
    if (!this.router.url.startsWith('/auth/')) {
      this.messageService.add({
        severity: 'warn',
        summary: 'Error de conexión',
        detail: getHttpErrorMessage(error, 'Error temporal. Los datos se cargarán cuando se restablezca la conexión.'),
        life: 5000
      });
    }
  }
}
