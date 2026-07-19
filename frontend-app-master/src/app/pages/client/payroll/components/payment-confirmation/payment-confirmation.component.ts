import { Component, Input, Output, EventEmitter, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DialogModule } from 'primeng/dialog';
import { ButtonModule } from 'primeng/button';
import { SelectModule } from 'primeng/select';
import { InputTextModule } from 'primeng/inputtext';
import { FormsModule } from '@angular/forms';
import { PayrollService } from '../../services/payroll.service';
import { LocaleService } from '../../../../../core/services/locale/locale.service';
import { I18nPipe } from '../../../../../core/pipes/i18n.pipe';
import { AuBtn } from '../../../../../shared/components';
import { Period, PaymentRequest } from '../../interfaces/payroll.interface';
import { SettingsService } from '../../../../../core/services/settings/settings.service';

@Component({
  selector: 'app-payment-confirmation',
  standalone: true,
  imports: [
    CommonModule, AuBtn, DialogModule, ButtonModule, SelectModule, 
    InputTextModule, FormsModule, I18nPipe
  ],
  template: `
    <p-dialog [(visible)]="visible" [header]="'payroll.confirm_payment_dialog.title' | t" 
              [modal]="true" [style]="{width: '500px'}" [breakpoints]="{'960px':'75vw','640px':'100vw'}" [closable]="false">
      
      <div *ngIf="period" class="space-y-4">
        <!-- Información del período -->
        <div class="p-4 rounded" style="background-color: var(--surface-100);">
          <h4 class="font-medium" style="color: var(--text-color);">{{ period.employee_name }}</h4>
          <p class="text-sm" style="color: var(--text-color-secondary);">{{ period.period_display }}</p>
        </div>

        <!-- Desglose de montos -->
        <div class="p-4 rounded border" style="background-color: color-mix(in srgb, var(--brand) 10%, transparent); border-color: color-mix(in srgb, var(--brand) 30%, transparent);">
          <div class="space-y-2 text-sm">
            <div class="flex justify-between">
              <span style="color: var(--text-color-secondary);">{{ 'employees.salary' | t }}:</span>
              <span>{{ formatCurrency(period.base_salary) }}</span>
            </div>
            <div class="flex justify-between">
              <span style="color: var(--text-color-secondary);">{{ 'payroll.commission' | t }}:</span>
              <span>{{ formatCurrency(period.commission_earnings) }}</span>
            </div>
            <hr style="border-color: color-mix(in srgb, var(--brand) 30%, transparent);">
            <div class="flex justify-between">
              <span style="color: var(--text-color-secondary);">{{ 'payroll.th.gross_total' | t }}:</span>
              <span class="font-medium">{{ formatCurrency(period.gross_amount) }}</span>
            </div>
            <div class="flex justify-between" style="color: var(--danger-color-text);">
              <span>{{ 'employees.receipt_dialog.deductions' | t }}:</span>
              <span>-{{ formatCurrency(period.deductions_total) }}</span>
            </div>
            <hr style="border-color: color-mix(in srgb, var(--brand) 30%, transparent);">
            <div class="flex justify-between text-lg font-bold" style="color: var(--brand);">
              <span>{{ 'payroll.total_net' | t }}:</span>
              <span>{{ formatCurrency(period.net_amount) }}</span>
            </div>
          </div>
        </div>

        <!-- Método de pago -->
        <div>
          <label class="block text-sm font-medium mb-2">{{ 'employees.receipt_dialog.method' | t }}</label>
          <p-select [(ngModel)]="paymentMethod" [options]="paymentMethods" appendTo="body"
                      optionLabel="label" optionValue="value" 
                    [placeholder]="'payroll.confirm_payment_dialog.select_method_placeholder' | t" class="w-full"></p-select>
        </div>

        <!-- Referencia -->
        <div>
          <label class="block text-sm font-medium mb-2">{{ 'employees.receipt_dialog.reference' | t }} ({{ 'common.optional' | t | lowercase }})</label>
          <input pInputText [(ngModel)]="paymentReference" 
                 [placeholder]="'payroll.confirm_payment_dialog.reference_placeholder' | t" class="w-full">
        </div>
      </div>

      <ng-template pTemplate="footer">
        <button au-btn variant="secondary"
                (click)="cancel()" [disabled]="processing()">{{ 'common.cancel' | t }}</button>
        <button au-btn variant="primary"
                [loading]="processing()" (click)="confirmPayment()"
                [disabled]="!paymentMethod || processing()">{{ 'payroll.confirm_payment_dialog.confirm_btn' | t }}</button>
      </ng-template>
    </p-dialog>
  `
})
export class PaymentConfirmationComponent {
  @Input() visible = false;
  @Input() period: Period | null = null;
  @Output() confirmed = new EventEmitter<any>();
  @Output() cancelled = new EventEmitter<void>();

  private payrollService = inject(PayrollService);
  private localeService = inject(LocaleService);
  private settingsService = inject(SettingsService);
  
    t(key: string): string {
    return this.localeService.t(key as any);
  }

  processing = signal(false);
  paymentMethod = 'cash';
  paymentReference = '';

  get paymentMethods() {
    return [
      { label: this.t('payroll.payment_method.cash'), value: 'cash' },
      { label: this.t('payroll.payment_method.transfer'), value: 'transfer' }
    ];
  }

  confirmPayment() {
    if (!this.period || !this.paymentMethod) return;

    this.processing.set(true);
    // Abrir ventana desde gesto de usuario para evitar bloqueo de popup
    const printWindow = window.open('', '_blank', 'width=800,height=600');

    const paymentData: PaymentRequest = {
      period_id: this.period.id,
      payment_method: this.paymentMethod as 'cash' | 'transfer',
      payment_reference: this.paymentReference || undefined
    };

    this.payrollService.registerPayment(paymentData).subscribe({
      next: (response) => {
        this.confirmed.emit({ ...response, printWindow });
        this.resetForm();
        this.processing.set(false);
      },
      error: (error) => {
        if (printWindow && !printWindow.closed) {
          printWindow.close();
        }
        
        // El error se maneja en el componente padre
        this.processing.set(false);
      }
    });
  }

  cancel() {
    this.cancelled.emit();
    this.resetForm();
  }

  private resetForm() {
    this.paymentMethod = 'cash';
    this.paymentReference = '';
  }

  formatCurrency(amount: number): string {
    const symbol = this.settingsService.getCurrencySymbol() || '$';
    return `${symbol}${amount?.toFixed(2) || '0.00'}`;
  }
}
