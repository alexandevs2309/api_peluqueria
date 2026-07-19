import { ErrorHandler, Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { FrontendObservabilityService } from './frontend-observability.service';
import { ErrorDialogService } from './error-dialog.service';

@Injectable()
export class GlobalErrorHandlerService implements ErrorHandler {
  private readonly observability = inject(FrontendObservabilityService);
  private readonly router = inject(Router);
  private readonly errorDialog = inject(ErrorDialogService);

  handleError(error: any): void {
    const normalized = this.normalizeError(error);

    this.observability.captureError(normalized.message, normalized.context);

    try {
      this.errorDialog.show({
        message: 'La aplicación encontró un error inesperado. El evento fue registrado.',
        retryLabel: 'Recargar página',
        retry: () => window.location.reload(),
      });
    } catch {
      this.router.navigate(['/auth/error'], { queryParams: { message: 'La aplicación encontró un error inesperado. El evento fue registrado.' } });
    }
  }

  private normalizeError(error: any): { message: string; context: unknown } {
    if (error?.rejection) {
      return this.normalizeError(error.rejection);
    }

    if (error instanceof Error) {
      return {
        message: error.message,
        context: {
          name: error.name,
          stack: error.stack
        }
      };
    }

    return {
      message: 'Unhandled frontend error',
      context: error
    };
  }
}
