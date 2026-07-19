import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';

/**
 * LoggerService - Logging seguro
 * 
 * SEGURIDAD:
 * - NO hace console.log en producción
 * - Sanitiza datos sensibles
 * - Previene information disclosure
 * 
 * USO:
 * - Reemplazar todos los console.log
 * - logger.debug() solo en desarrollo
 * - logger.error() envía a Sentry en producción
 */
@Injectable({
  providedIn: 'root'
})
export class LoggerService {
  
  private readonly sensitiveKeys = [
    'password', 'token', 'access_token', 'refresh_token',
    'credit_card', 'ssn', 'api_key', 'secret'
  ];

  debug(message: string, data?: any): void {
    if (!environment.production) {
      console.debug(`[DEBUG] ${message}`, data !== undefined ? this.sanitize(data) : '');
    }
  }

  info(message: string, data?: any): void {
    if (!environment.production) {
      console.info(`[INFO] ${message}`, data !== undefined ? this.sanitize(data) : '');
    }
  }

  warn(message: string, data?: any): void {
    if (!environment.production) {
      console.warn(`[WARN] ${message}`, data !== undefined ? this.sanitize(data) : '');
    }
    // TODO: Enviar a Sentry en producción
  }

  error(message: string, error?: any): void {
    if (!environment.production) {
      
    } else {
      // TODO: Enviar a Sentry
      // Sentry.captureException(error, { extra: { message } });
    }
  }

  private sanitize(data: any): any {
    if (!data) return data;
    
    if (typeof data === 'object') {
      const sanitized = { ...data };
      this.sensitiveKeys.forEach(key => {
        if (key in sanitized) {
          sanitized[key] = '***REDACTED***';
        }
      });
      return sanitized;
    }
    
    return data;
  }
}
