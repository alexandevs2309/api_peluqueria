import { Injectable, inject } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { LocaleService } from '../services/locale/locale.service';

/**
 * AuthInterceptor - httpOnly Cookies + Accept-Language
 * 
 * SEGURIDAD:
 * - NO inyecta Authorization header manualmente
 * - Cookies httpOnly son enviadas automáticamente por el navegador
 * - Tokens NO accesibles desde JavaScript (previene XSS)
 * - withCredentials: true permite envío de cookies cross-origin
 * 
 * MULTIIDIOMA:
 * - Inyecta header Accept-Language según preferencia del usuario
 * 
 * PERFORMANCE:
 * - Skip para rutas públicas (landing, legal, register)
 */
@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  private localeService = inject(LocaleService);

  private readonly publicPaths = [
    '/landing',
    '/terms',
    '/privacy',
    '/cookies',
    '/about',
    '/register',
    '/settings/public-branding/',
    '/auth/login',
    '/auth/register',
    '/auth/reset-password'
  ];

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    // Determinar pathname de la URL de la request (robusto frente a URLs absolutas/relativas)
    let pathname = req.url;
    try {
      pathname = new URL(req.url).pathname;
    } catch (e) {
      try {
        if (typeof window !== 'undefined') {
          pathname = new URL(req.url, window.location.origin).pathname;
        }
      } catch (e2) {
        pathname = req.url;
      }
    }

    // ✅ Skip interceptor para rutas públicas (comparación estricta de pathname)
    if (this.isPublicRoute(pathname)) {
      return next.handle(req);
    }

    // ✅ Solo para requests al backend API autenticado
    if (req.url.startsWith(environment.apiUrl)) {
      const authReq = req.clone({
        withCredentials: true, // Envía cookies httpOnly automáticamente
        setHeaders: {
          'Accept-Language': this.localeService.getCurrentLanguage(),
          'X-Requested-With': 'XMLHttpRequest' // Protección CSRF
        }
      });
      return next.handle(authReq);
    }

    return next.handle(req);
  }

  private isPublicRoute(pathname: string): boolean {
    return this.publicPaths.some((p) => {
      const normalizedP = p.endsWith('/') ? p.slice(0, -1) : p;
      const normalizedPath = pathname.endsWith('/') ? pathname.slice(0, -1) : pathname;
      return normalizedPath === normalizedP || normalizedPath.startsWith(normalizedP + '/') || normalizedPath.startsWith('/' + normalizedP + '/');
    });
  }
}
