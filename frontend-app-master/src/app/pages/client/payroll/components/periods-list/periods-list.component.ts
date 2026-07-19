import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ButtonModule } from 'primeng/button';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { CardModule } from 'primeng/card';
import { ToastModule } from 'primeng/toast';
import { TooltipModule } from 'primeng/tooltip';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { FormsModule } from '@angular/forms';
import { MessageService, ConfirmationService } from 'primeng/api';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { LocaleService } from '../../../../../core/services/locale/locale.service';
import { I18nPipe } from '../../../../../core/pipes/i18n.pipe';
import { AuBtn } from '../../../../../shared/components';
import { PayrollService } from '../../services/payroll.service';
import { Period } from '../../interfaces/payroll.interface';
import { PaymentConfirmationComponent } from '../payment-confirmation/payment-confirmation.component';
import { firstValueFrom } from 'rxjs';
import { SettingsService } from '../../../../../core/services/settings/settings.service';

@Component({
  selector: 'app-periods-list',
  standalone: true,
  imports: [
    CommonModule, AuBtn, ButtonModule, TableModule, TagModule, CardModule, 
    ToastModule, TooltipModule, PaymentConfirmationComponent, DialogModule,
    InputTextModule, FormsModule, ConfirmDialogModule, I18nPipe
  ],
  providers: [MessageService, ConfirmationService],
  template: `
    <div class="p-6">
      <!-- Header -->
      <div class="flex justify-between items-center mb-6">
        <div>
          <h1 class="text-2xl font-bold" style="color: var(--text-color);">📋 {{ 'payroll.periods' | t }}</h1>
          <p style="color: var(--text-color-secondary);">{{ 'payroll.periods_management_desc' | t }}</p>
        </div>
        <div class="flex gap-2 items-center">
          <button au-btn variant="secondary"
                  (click)="toggleHistory()"
                  [loading]="loading()">{{ showHistory() ? 'Ver pendientes' : 'Ver otros' }}</button>
          <button au-btn variant="secondary" [icon]="'pi pi-refresh'"
                  (click)="loadPeriods()" [loading]="loading()">{{ 'payroll.refresh' | t }}</button>
        </div>
      </div>

      <!-- Tabla de períodos -->
      <p-card id="onb-earnings-periods-table">
        <p-table [value]="periods()" [loading]="loading()" responsiveLayout="scroll">
          <ng-template pTemplate="header">
            <tr>
              <th>{{ 'employees.table.employee' | t }}</th>
              <th>{{ 'payroll.th.period' | t }}</th>
              <th>{{ 'employees.table.status' | t }}</th>
              <th>{{ 'employees.salary' | t }}</th>
              <th>{{ 'payroll.commission' | t }}</th>
              <th>{{ 'payroll.th.gross_total' | t }}</th>
              <th>{{ 'employees.receipt_dialog.deductions' | t }}</th>
              <th>{{ 'payroll.total_net' | t }}</th>
              <th>{{ 'employees.table.actions' | t }}</th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-period>
            <tr [class.status-rejected]="period.status === 'rejected'">
              <td>{{ period.employee_name }}</td>
              <td>{{ period.period_display }}</td>
              <td>
                <p-tag [value]="getStatusLabel(period.status)" 
                       [severity]="getStatusSeverity(period.status)"></p-tag>
              </td>
              <td>{{ formatCurrency(period.base_salary) }}</td>
              <td>{{ formatCurrency(period.commission_earnings) }}</td>
              <td>{{ formatCurrency(period.gross_amount) }}</td>
              <td>{{ formatCurrency(period.deductions_total) }}</td>
              <td class="font-bold">{{ formatCurrency(period.net_amount) }}</td>
              <td>
                <!-- Abierto -->
                <button *ngIf="period.status === 'open'" au-btn variant="primary" size="sm"
                        [icon]="'pi pi-send'"
                        (click)="submitForApproval(period)">{{ 'payroll.btn.submit' | t }}</button>
                
                <!-- Pendiente de Aprobación -->
                <div *ngIf="period.status === 'pending_approval'" class="flex gap-2">
                  <button au-btn variant="primary" size="sm" [icon]="'pi pi-check'"
                          (click)="approvePeriod(period)">{{ 'payroll.btn.approve' | t }}</button>
                  <button au-btn variant="danger" size="sm" [icon]="'pi pi-times'"
                          (click)="openRejectDialog(period)">{{ 'payroll.btn.reject' | t }}</button>
                </div>
                
                <!-- Aprobado -->
                <button *ngIf="period.status === 'approved'" pButton [label]="'payroll.btn.pay' | t" 
                        icon="pi pi-credit-card" class="p-button-sm p-button-success"
                        [disabled]="!period.can_pay"
                        [pTooltip]="period.pay_block_reason || 'Listo para pagar'"
                        tooltipPosition="top"
                        (click)="openPaymentDialog(period)"></button>
                
                <!-- Pagado -->
                <span *ngIf="period.status === 'paid'" 
                      class="font-medium"
                      style="color: var(--success-color-text);">
                  <i class="pi pi-check-circle mr-1"></i>{{ 'payroll.status.paid' | t }}
                </span>
                
                <!-- Rechazado -->
                <span *ngIf="period.status === 'rejected'" 
                      class="font-medium"
                      style="color: var(--danger-color-text);">
                  <i class="pi pi-times-circle mr-1"></i>{{ 'payroll.status.rejected' | t }}
                </span>
              </td>
            </tr>
          </ng-template>
          <ng-template pTemplate="emptymessage">
            <tr>
              <td colspan="9" class="text-center py-8">
                <i class="pi pi-inbox text-4xl mb-4" style="color: var(--text-color-secondary);"></i>
                <p style="color: var(--text-color-secondary);">{{ 'payroll.no_periods_available' | t }}</p>
              </td>
            </tr>
          </ng-template>
        </p-table>
      </p-card>

      <!-- Diálogo de Rechazo -->
      <p-dialog [header]="'payroll.reject_dialog.title' | t" [(visible)]="showRejectDialog" [modal]="true" 
                [style]="{width: '450px'}" [breakpoints]="{'960px':'75vw','640px':'100vw'}">
        <div class="p-4">
          <label class="block font-medium mb-2">{{ 'payroll.reject_dialog.reason' | t }}</label>
          <textarea [(ngModel)]="rejectionReason" rows="4" 
                    class="w-full p-2 border border-gray-300 rounded" 
                    [placeholder]="'payroll.reject_dialog.reason_placeholder' | t"></textarea>
        </div>
        <ng-template pTemplate="footer">
          <button au-btn variant="ghost"
                  (click)="closeRejectDialog()">{{ 'common.cancel' | t }}</button>
          <button au-btn variant="danger" [icon]="'pi pi-times'"
                  [disabled]="!rejectionReason"
                  (click)="confirmReject()">{{ 'payroll.btn.reject' | t }}</button>
        </ng-template>
      </p-dialog>

      <!-- Componente de confirmación de pago -->
      <app-payment-confirmation
        [visible]="showPaymentDialog"
        [period]="selectedPeriod()"
        (confirmed)="onPaymentConfirmed($event)"
        (cancelled)="closePaymentDialog()">
      </app-payment-confirmation>
    </div>

    <p-confirmDialog></p-confirmDialog>
    <p-toast></p-toast>
  `
})
export class PeriodsListComponent implements OnInit {
  private payrollService = inject(PayrollService);
  private localeService = inject(LocaleService);
  private messageService = inject(MessageService);
  private confirmationService = inject(ConfirmationService);
  private settingsService = inject(SettingsService);

  // Signal to control showing historical periods
  showHistory = signal(false);

    t(key: string): string {
    return this.localeService.t(key as any);
  }

  loading = signal(false);
  periods = signal<Period[]>([]);
  selectedPeriod = signal<Period | null>(null);
  showPaymentDialog = false;
  showRejectDialog = false;
  rejectionReason = '';

  ngOnInit() {
    this.loadPeriods();
  }

  loadPeriods() {
    this.loading.set(true);
    const serviceCall = this.showHistory() ? this.payrollService.getHistory() : this.payrollService.getPeriods();
    serviceCall.subscribe({
      next: (response) => {
        // Cuando no se muestra el historial, filtrar solo periodos pendientes (no pagados ni cerrados)
        if (!this.showHistory()) {
          const pending = response.periods.filter(p => !['paid', 'closed', 'rejected'].includes(p.status));
          this.periods.set(pending);
        } else {
          this.periods.set(response.periods);
        }
        this.loading.set(false);
      },
      error: (error) => {
        this.messageService.add({
          severity: 'error',
          summary: 'Error',
          detail: this.t('payroll.toast.load_periods_error')
        });
        this.loading.set(false);
      }
    });
  }

  toggleHistory() {
    this.showHistory.set(!this.showHistory());
    this.loadPeriods();
  }

  openPaymentDialog(period: Period) {
    if (period.status !== 'approved' || !period.can_pay) {
      this.messageService.add({
        severity: 'warn',
        summary: 'Pago bloqueado',
        detail: period.pay_block_reason || 'El período debe estar aprobado y listo para pago.'
      });
      return;
    }
    this.selectedPeriod.set(period);
    this.showPaymentDialog = true;
  }

  closePaymentDialog() {
    this.showPaymentDialog = false;
    this.selectedPeriod.set(null);
  }

  onPaymentConfirmed(response: any) {
    this.messageService.add({
      severity: 'success',
      summary: 'Pago Registrado',
      detail: `Pago de ${this.formatCurrency(response.amount_paid)} registrado exitosamente`
    });
    this.closePaymentDialog();
    this.loadPeriods();

    // Mostrar recibo automáticamente usando ventana abierta por gesto de usuario
    this.verReciboDirecto(response.payment_id, response.printWindow);
  }

  getStatusLabel(status: string): string {
    const labels = {
      'open': this.t('payroll.status.open'),
      'pending_approval': this.t('payroll.status.pending_approval'),
      'approved': this.t('payroll.status.approved'),
      'paid': this.t('payroll.status.paid'),
      'rejected': this.t('payroll.status.rejected')
    };
    return labels[status as keyof typeof labels] || status;
  }

  getStatusSeverity(status: string): 'info' | 'success' | 'warn' | 'danger' {
    const severities = {
      'open': 'info' as const,
      'pending_approval': 'warn' as const,
      'approved': 'success' as const,
      'paid': 'success' as const,
      'rejected': 'danger' as const
    };
    return severities[status as keyof typeof severities] || 'info';
  }

  formatCurrency(amount: number): string {
    const symbol = this.settingsService.getCurrencySymbol() || '$';
    return `${symbol}${amount?.toFixed(2) || '0.00'}`;
  }

  async verReciboDirecto(paymentId: string, targetWindow?: Window | null) {
    try {
      const response = await firstValueFrom(this.payrollService.getPaymentReceipt(paymentId));
      // Abrir recibo en nueva ventana para imprimir
      this.abrirReciboEnVentana(response, targetWindow);
    } catch {
      if (targetWindow && !targetWindow.closed) {
        targetWindow.close();
      }
      this.messageService.add({
        severity: 'warn',
        summary: 'Recibo no disponible',
        detail: 'El pago se registró, pero no se pudo abrir el recibo automáticamente.'
      });
    }
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  private escape(value: any): string {
    if (value === null || value === undefined) return '';
    return this.escapeHtml(String(value));
  }

  abrirReciboEnVentana(recibo: any, existingWindow?: Window | null) {
    const reciboHtml = this.generarHtmlRecibo(recibo);
    const ventana = existingWindow || window.open('', '_blank', 'width=800,height=600');
    if (ventana) {
      ventana.document.write(reciboHtml);
      ventana.document.close();
      ventana.focus();
      setTimeout(() => ventana.print(), 300);
    } else {
      this.messageService.add({
        severity: 'warn',
        summary: 'Popup bloqueado',
        detail: 'Permite ventanas emergentes para imprimir el recibo automáticamente.'
      });
    }
  }

  generarHtmlRecibo(recibo: any): string {
    const e = (v: any) => this.escape(v);
    const symbol = this.settingsService.getCurrencySymbol() || '$';
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Recibo de Pago</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; }
          .header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; }
          .section { margin: 20px 0; }
          .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
          .amount { font-size: 18px; font-weight: bold; color: #059669; }
          @media print { body { margin: 0; } }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>${e(recibo.company?.name)}</h1>
          <p>${e(recibo.company?.address)}</p>
          <h2>RECIBO DE PAGO</h2>
        </div>
        
        <div class="section grid">
          <div>
            <h3>Empleado:</h3>
            <p><strong>${e(recibo.employee?.name)}</strong></p>
            <p>${e(recibo.employee?.email)}</p>
          </div>
          <div>
            <h3>Período:</h3>
            <p><strong>${e(recibo.period?.display)}</strong></p>
            <p>${new Date(recibo.period?.start_date).toLocaleDateString()} - ${new Date(recibo.period?.end_date).toLocaleDateString()}</p>
          </div>
        </div>
        
        <div class="section">
          <h3>Detalle de Pago:</h3>
          <p><strong>Tipo de pago:</strong> ${e(recibo.employee?.payment_type)}</p>
          <p>Sueldo Base: ${symbol}${recibo.amounts?.base_salary?.toFixed(2)}</p>
          <p>Comisión: ${symbol}${recibo.amounts?.commission_earnings?.toFixed(2)}</p>
          <p>Monto Bruto: ${symbol}${recibo.amounts?.gross_amount?.toFixed(2)}</p>
          <p>Total Descuentos: -${symbol}${recibo.amounts?.deductions?.total?.toFixed(2)}</p>
          <p class="amount">Monto Neto: ${symbol}${recibo.amounts?.net_amount?.toFixed(2)}</p>
        </div>
        
        <div class="section grid">
          <div>
            <h3>Información del Pago:</h3>
            <p>Método: ${e(recibo.payment_info?.method)}</p>
            <p>Referencia: ${e(recibo.payment_info?.reference)}</p>
          </div>
          <div>
            <h3>Fecha:</h3>
            <p>${new Date(recibo.payment_info?.paid_at).toLocaleString()}</p>
            <p>Pagado por: ${e(recibo.payment_info?.paid_by)}</p>
          </div>
        </div>
        
        <div style="text-align: center; margin-top: 40px; font-size: 12px; color: #666;">
          <p>Recibo ID: ${e(recibo.payment_id)}</p>
        </div>
      </body>
      </html>
    `;
  }

  submitForApproval(period: Period) {
    if (period.status !== 'open') {
      this.messageService.add({
        severity: 'warn',
        summary: 'Envío bloqueado',
        detail: 'Solo se pueden enviar períodos abiertos.'
      });
      return;
    }

    this.confirmationService.confirm({
      message: this.t('payroll.confirm_send_msg').replace('{name}', period.employee_name), // wait we can define it or replace
      header: this.t('payroll.confirm_send_title'),
      icon: 'pi pi-send',
      accept: () => {
        this.payrollService.submitForApproval(period.id).subscribe({
          next: () => {
            this.messageService.add({
              severity: 'success',
              summary: 'Enviado',
              detail: 'Período enviado para aprobación'
            });
            this.loadPeriods();
          },
          error: (error) => {
            this.messageService.add({
              severity: 'error',
              summary: 'Error',
              detail: error.error?.error || 'No se pudo enviar el período'
            });
          }
        });
      }
    });
  }

  approvePeriod(period: Period) {
    if (period.status !== 'pending_approval') {
      this.messageService.add({
        severity: 'warn',
        summary: 'Aprobación bloqueada',
        detail: 'Solo se pueden aprobar períodos en estado pendiente.'
      });
      return;
    }

    if (period.net_amount <= 0) {
      this.messageService.add({
        severity: 'warn',
        summary: 'Aprobación bloqueada',
        detail: 'No se puede aprobar un período con monto neto cero o negativo.'
      });
      return;
    }

    this.confirmationService.confirm({
      message: this.t('payroll.confirm_approve_msg').replace('{name}', period.employee_name).replace('{amount}', this.formatCurrency(period.net_amount)),
      header: this.t('payroll.confirm_approve_title'),
      icon: 'pi pi-check',
      accept: () => {
        this.payrollService.approvePeriod(period.id).subscribe({
          next: () => {
            this.messageService.add({
              severity: 'success',
              summary: 'Aprobado',
              detail: 'Período aprobado exitosamente'
            });
            this.loadPeriods();
          },
          error: (error) => {
            this.messageService.add({
              severity: 'error',
              summary: 'Error',
              detail: error.error?.error || 'No se pudo aprobar el período'
            });
          }
        });
      }
    });
  }

  openRejectDialog(period: Period) {
    this.selectedPeriod.set(period);
    this.rejectionReason = '';
    this.showRejectDialog = true;
  }

  closeRejectDialog() {
    this.showRejectDialog = false;
    this.selectedPeriod.set(null);
    this.rejectionReason = '';
  }

  confirmReject() {
    const period = this.selectedPeriod();
    if (!period || !this.rejectionReason) return;
    if (period.status !== 'pending_approval') {
      this.messageService.add({
        severity: 'warn',
        summary: 'Rechazo bloqueado',
        detail: 'Solo se pueden rechazar períodos pendientes.'
      });
      this.closeRejectDialog();
      return;
    }

    this.payrollService.rejectPeriod(period.id, this.rejectionReason).subscribe({
      next: () => {
        this.messageService.add({
          severity: 'warn',
          summary: 'Rechazado',
          detail: 'Período rechazado'
        });
        this.closeRejectDialog();
        this.loadPeriods();
      },
      error: (error) => {
        this.messageService.add({
          severity: 'error',
          summary: 'Error',
          detail: error.error?.error || 'No se pudo rechazar el período'
        });
      }
    });
  }
}
