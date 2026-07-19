import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';

/**
 * TenantInterceptor - ELIMINADO
 * 
 * RAZÓN: El tenant_id NUNCA debe ser controlado por el cliente.
 * El backend determina el tenant desde el JWT token.
 * 
 * SEGURIDAD: Previene IDOR - usuario no puede forzar acceso a otro tenant.
 */
@Injectable()
export class TenantInterceptor implements HttpInterceptor {
  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    // ✅ NO HACER NADA - Backend extrae tenant del JWT
    return next.handle(req);
  }
}
