import { Injectable, inject } from '@angular/core';
import { MessageService } from 'primeng/api';
import { Observable, EMPTY } from 'rxjs';
import { FrontendObservabilityService } from './frontend-observability.service';

@Injectable({
  providedIn: 'root'
})
export class ErrorHandlerService {
  private messageService = inject(MessageService);
  private observability = inject(FrontendObservabilityService);

  handleError(operation: string, error: any, fallbackAction?: () => void): Observable<any> {
    const errorMessage = this.getErrorMessage(error);
    this.observability.captureWarn(`Error al ${operation}`, error);
    
    this.messageService.add({
      severity: 'warn',
      summary: 'Conexión limitada',
      detail: `Error al ${operation}. ${errorMessage}`
    });
    
    if (fallbackAction) {
      fallbackAction();
    }
    
    return EMPTY;
  }

  private getErrorMessage(error: any): string {
    if (error.status === 0) {
      return 'Sin conexión al servidor.';
    }
    if (error.status >= 500) {
      return 'Error interno del servidor.';
    }
    if (error.status === 404) {
      return 'Recurso no encontrado.';
    }
    if (error.status === 403) {
      return 'Sin permisos para esta operación.';
    }
    return 'Usando datos locales temporalmente.';
  }

  showSuccess(message: string, detail?: string) {
    this.messageService.add({
      severity: 'success',
      summary: message,
      detail: detail || ''
    });
  }

  showInfo(message: string, detail?: string) {
    this.messageService.add({
      severity: 'info',
      summary: message,
      detail: detail || ''
    });
  }
}
