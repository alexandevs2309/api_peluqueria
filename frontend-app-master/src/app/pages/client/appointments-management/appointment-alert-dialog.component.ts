import { CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { DialogModule } from 'primeng/dialog';
import { AppointmentAlert, AppointmentAlertService } from '../../../core/services/appointment/appointment-alert.service';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { AuBtn } from '../../../shared/components';

@Component({
  selector: 'app-appointment-alert-dialog',
  standalone: true,
  imports: [CommonModule, DialogModule, AuBtn],
  template: `
    <p-dialog
      [(visible)]="alertService.alertVisible"
      [modal]="true"
      [closable]="false"
      [showHeader]="false"
      [blockScroll]="true"
      styleClass="appointment-alert-dialog"
      [style]="{ 'max-width': '32rem', 'width': '90vw' }"
      (onHide)="onDialogHide()"
    >
      <div class="alert-content" *ngIf="alertService.activeAlert() as alert">
        <!-- Efecto de pulso de fondo -->
        <div class="alert-pulse-ring"></div>

        <!-- Contenedor principal -->
        <div class="alert-card">
          <!-- Icono animado -->
          <div class="alert-icon-wrapper">
            <div class="alert-icon" [style.color]="alertService.getStatusColor(alert.status)">
              <i [class]="'pi ' + alertService.getStatusIcon(alert.status)"></i>
            </div>
          </div>

          <!-- Mensaje principal -->
          <div class="alert-message">
            <h2 class="alert-title">
              {{ alertService.getStatusMessage(alert.status) }}
            </h2>

            <!-- Detalles de la cita -->
            <div class="alert-details">
              <!-- Cliente -->
              <div class="detail-item">
                <span class="detail-label">{{ t('appointments.alert.client') }}</span>
                <span class="detail-value">{{ alert.clientName }}</span>
                <span *ngIf="alert.clientPhone" class="detail-phone">{{ alert.clientPhone }}</span>
              </div>

              <!-- Empleado -->
              <div class="detail-item">
                <span class="detail-label">{{ t('appointments.alert.employee') }}</span>
                <span class="detail-value">{{ alert.stylistName }}</span>
              </div>

              <!-- Servicio (si existe) -->
              <div class="detail-item" *ngIf="alert.serviceName">
                <span class="detail-label">{{ t('appointments.alert.service') }}</span>
                <span class="detail-value">{{ alert.serviceName }}</span>
              </div>

              <!-- Fecha y Hora -->
              <div class="detail-item">
                <span class="detail-label">{{ t('appointments.alert.date_time') }}</span>
                <span class="detail-value">
                  {{ alert.dateTime | date: 'dd/MM/yyyy HH:mm' }}
                </span>
              </div>

              <!-- Descripción (si existe) -->
              <div class="detail-item" *ngIf="alert.description">
                <span class="detail-label">{{ t('appointments.alert.notes') }}</span>
                <span class="detail-value detail-description">{{ alert.description }}</span>
              </div>
            </div>

            <!-- Botón de cierre -->
            <button
              au-btn
              variant="primary"
              [icon]="'pi pi-check'"
              (click)="alertService.closeAlert()"
              class="alert-button"
              [style]="{ 'background-color': alertService.getStatusColor(alert.status) }"
            >{{ t('appointments.alert.entendido') }}</button>
          </div>
        </div>
      </div>
    </p-dialog>

    <style>
      /* Variables de color dinámico */
      :host {
        --alert-color: #10b981;
        --alert-color-light: rgba(16, 185, 129, 0.1);
      }

      ::ng-deep .appointment-alert-dialog {
        /* Modal persistente - no se cierra con overlay click */
        .p-dialog {
          animation: slideInCenter 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
        }

        .p-dialog-mask {
          backdrop-filter: blur(4px);
          background: rgba(15, 23, 42, 0.6);
          animation: maskFlash 1.5s ease-in-out infinite;
        }
      }

      @keyframes maskFlash {
        0%, 100% { background: rgba(15, 23, 42, 0.6); }
        50% { background: rgba(15, 23, 42, 0.75); }
      }

      @keyframes slideInCenter {
        from {
          opacity: 0;
          transform: scale(0.85) translateY(-20px);
        }
        to {
          opacity: 1;
          transform: scale(1) translateY(0);
        }
      }

      @keyframes fadeOut {
        from {
          opacity: 1;
          transform: scale(1);
        }
        to {
          opacity: 0;
          transform: scale(0.9);
        }
      }

      @keyframes pulse {
        0% {
          box-shadow: 0 0 0 0 var(--alert-color);
          transform: scale(1);
          opacity: 0.5;
        }
        25% {
          opacity: 0.9;
        }
        50% {
          box-shadow: 0 0 0 25px rgba(16, 185, 129, 0);
          transform: scale(1.05);
          opacity: 0.2;
        }
        75% {
          opacity: 0.9;
        }
        100% {
          box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
          transform: scale(1);
          opacity: 0.5;
        }
      }

      @keyframes blinkBorder {
        0%, 100% { border-color: var(--alert-color); }
        50% { border-color: transparent; }
      }

      @keyframes shake {
        0%, 100% { transform: translateX(0); }
        10%, 30%, 50%, 70%, 90% { transform: translateX(-2px); }
        20%, 40%, 60%, 80% { transform: translateX(2px); }
      }

      @keyframes scaleUp {
        from {
          transform: scale(0);
          opacity: 0;
        }
        to {
          transform: scale(1);
          opacity: 1;
        }
      }

      /* Contenedor principal */
      .alert-content {
        position: relative;
        padding: 0;
      }

      /* Anillo de pulso de fondo */
      .alert-pulse-ring {
        position: absolute;
        width: 120%;
        height: 120%;
        top: -10%;
        left: -10%;
        border: 3px solid var(--alert-color);
        border-radius: 50%;
        pointer-events: none;
        animation: pulse 1.2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
      }

      /* Tarjeta principal */
      .alert-card {
        position: relative;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1.5rem;
        padding: 2rem;
        border-radius: 1.5rem;
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 3px solid var(--alert-color);
        animation: blinkBorder 1.2s ease-in-out infinite;
        box-shadow:
          0 20px 25px -5px rgba(0, 0, 0, 0.1),
          0 10px 10px -5px rgba(0, 0, 0, 0.04),
          inset 0 1px 0 0 rgba(255, 255, 255, 0.6);
        z-index: 2;
      }

      /* Wrapper del icono */
      .alert-icon-wrapper {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        margin-top: 0.5rem;
      }

      /* Icono principal */
      .alert-icon {
        position: relative;
        width: 80px;
        height: 80px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 3.5rem;
        background: var(--alert-color-light);
        border-radius: 50%;
        animation: scaleUp 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
        box-shadow: 0 4px 20px rgba(16, 185, 129, 0.25);

        i {
          animation: bounce 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) 0.2s forwards;
        }
      }

      @keyframes bounce {
        0%, 100% {
          transform: translateY(0);
        }
        50% {
          transform: translateY(-10px);
        }
      }

      /* Contenedor de mensaje */
      .alert-message {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        width: 100%;
        text-align: center;
        z-index: 3;
      }

      /* Título */
      .alert-title {
        margin: 0;
        font-size: 1.75rem;
        font-weight: 700;
        line-height: 1.2;
        color: #0f172a;
        letter-spacing: -0.5px;
      }

      /* Sección de detalles */
      .alert-details {
        display: flex;
        flex-direction: column;
        gap: 0.85rem;
        padding: 1.25rem;
        background: var(--alert-color-light);
        border-radius: 1rem;
        border: 1px solid rgba(16, 185, 129, 0.2);
        text-align: left;
      }

      /* Item de detalle */
      .detail-item {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
      }

      /* Etiqueta de detalle */
      .detail-label {
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: rgba(16, 185, 129, 0.7);
      }

      /* Valor de detalle */
      .detail-value {
        font-size: 0.95rem;
        font-weight: 600;
        color: #0f172a;
        word-break: break-word;
      }

      /* Teléfono especial */
      .detail-phone {
        font-size: 0.82rem;
        color: #64748b;
        font-weight: 400;
      }

      /* Descripción */
      .detail-description {
        font-size: 0.85rem;
        font-weight: 400;
        color: #475569;
        line-height: 1.5;
        max-height: 80px;
        overflow-y: auto;
      }

      /* Botón de acción */
      .alert-button {
        padding: 0.9rem 1.8rem;
        font-size: 0.95rem;
        font-weight: 600;
        border: none;
        border-radius: 0.75rem;
        color: white;
        cursor: pointer;
        animation: blinkBorder 1.2s ease-in-out infinite;
        transition:
          all 0.3s cubic-bezier(0.4, 0, 0.2, 1),
          box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
        width: 100%;

        &:hover {
          animation: none;
          transform: translateY(-2px);
          box-shadow: 0 8px 25px rgba(16, 185, 129, 0.4);
        }

        &:active {
          transform: translateY(0);
          box-shadow: 0 2px 10px rgba(16, 185, 129, 0.3);
        }
      }

      /* Responsive */
      @media (max-width: 640px) {
        .alert-card {
          padding: 1.5rem;
          gap: 1rem;
        }

        .alert-icon {
          width: 70px;
          height: 70px;
          font-size: 3rem;
        }

        .alert-title {
          font-size: 1.5rem;
        }

        .alert-details {
          padding: 1rem;
          gap: 0.75rem;
        }

        .detail-value {
          font-size: 0.9rem;
        }
      }

      /* Dark mode */
      :host-context(.app-dark) {
        .alert-card {
          background: linear-gradient(135deg, var(--surface-card) 0%, var(--surface-ground) 100%);
          border-color: color-mix(in srgb, var(--success-color) 40%, transparent);
        }

        .alert-title {
          color: var(--text-color);
        }

        .alert-details {
          background: color-mix(in srgb, var(--success-color) 8%, transparent);
          border-color: color-mix(in srgb, var(--success-color) 20%, transparent);
        }

        .detail-label {
          color: color-mix(in srgb, var(--success-color) 60%, transparent);
        }

        .detail-value {
          color: var(--text-color);
        }

        .detail-phone {
          color: var(--text-color-secondary);
        }

        .detail-description {
          color: var(--text-color-secondary);
        }
      }
    </style>
  `,
  styles: []
})
export class AppointmentAlertDialogComponent implements OnInit {
  private readonly localeService = inject(LocaleService);
  readonly alertService = inject(AppointmentAlertService);

  t(key: string): string {
    return this.localeService.t(key as any);
  }

  ngOnInit(): void {
    // El componente se suscribe automáticamente a través de las señales
  }

  /**
   * Se ejecuta cuando el usuario hace click en "Entendido" o cierra el modal
   */
  onDialogHide(): void {
    // Si el diálogo se cierra por cualquier razón, asegurar que limpiar la alerta
    if (this.alertService.activeAlert()) {
      this.alertService.closeAlert();
    }
  }
}
