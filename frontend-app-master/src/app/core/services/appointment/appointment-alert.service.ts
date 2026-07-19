import { Injectable, signal, inject } from '@angular/core';
import { LocaleService } from '../locale/locale.service';

/**
 * Datos de una cita con detalles para mostrar en la alerta
 */
export interface AppointmentAlert {
  id: number;
  clientName: string;
  clientPhone?: string;
  stylistName: string;
  serviceName?: string;
  status: 'completed' | 'cancelled' | 'no_show' | 'cycle_completed';
  dateTime: Date;
  description?: string;
}

/**
 * Servicio singleton que gestiona alertas modales persistentes
 * para cambios de estado de citas (completada, cancelada, no asistió)
 *
 * Uso:
 * ```
 * this.alertService.showAlert({
 *   id: 123,
 *   clientName: 'Juan Pérez',
 *   stylistName: 'Carlos García',
 *   serviceName: 'Corte de cabello',
 *   status: 'completed',
 *   dateTime: new Date()
 * });
 * ```
 */
@Injectable({
  providedIn: 'root'
})
export class AppointmentAlertService {
  // Alerta actualmente mostrada (null si no hay alerta)
  readonly activeAlert = signal<AppointmentAlert | null>(null);

  // Controla visibilidad del modal
  readonly alertVisible = signal<boolean>(false);

  private readonly localeService = inject(LocaleService);

  constructor() {}

  /**
   * Muestra una alerta modal persistente
   * Solo una alerta puede estar activa a la vez
   * La alerta no se cierra automáticamente
   * @param alert Datos de la alerta a mostrar
   */
  showAlert(alert: AppointmentAlert): void {
    this.activeAlert.set(alert);
    this.alertVisible.set(true);
  }

  /**
   * Cierra la alerta modal actual
   */
  closeAlert(): void {
    this.alertVisible.set(false);
    // Esperar a que termine la animación de cierre antes de limpiar datos
    setTimeout(() => {
      this.activeAlert.set(null);
    }, 300);
  }

  /**
   * Obtiene el icono según el estado de la cita
   */
  getStatusIcon(status: 'completed' | 'cancelled' | 'no_show' | 'cycle_completed'): string {
    switch (status) {
      case 'completed':
        return 'pi-check-circle';
      case 'cancelled':
        return 'pi-times-circle';
      case 'no_show':
        return 'pi-exclamation-circle';
      case 'cycle_completed':
        return 'pi-clock';
      default:
        return 'pi-info-circle';
    }
  }

  getStatusColor(status: 'completed' | 'cancelled' | 'no_show' | 'cycle_completed'): string {
    switch (status) {
      case 'completed':
        return '#10b981'; // verde
      case 'cancelled':
        return '#ef4444'; // rojo
      case 'no_show':
        return '#f59e0b'; // naranja
      case 'cycle_completed':
        return '#8B5CF6'; // violet
      default:
        return '#8B5CF6';
    }
  }

  getStatusMessage(status: 'completed' | 'cancelled' | 'no_show' | 'cycle_completed'): string {
    switch (status) {
      case 'completed':
        return this.localeService.t('appointments.alert.completed');
      case 'cancelled':
        return this.localeService.t('appointments.alert.cancelled');
      case 'no_show':
        return this.localeService.t('appointments.alert.no_show');
      case 'cycle_completed':
        return this.localeService.t('appointments.alert.cycle_completed');
      default:
        return this.localeService.t('appointments.alert.status_change');
    }
  }
}
