import { Component, OnInit, OnDestroy, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { MessageModule } from 'primeng/message';
import { TagModule } from 'primeng/tag';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ToastModule } from 'primeng/toast';
import { MessageService, ConfirmationService } from 'primeng/api';
import { Router } from '@angular/router';
import { Subscription, interval } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';
import { LocaleService } from '../../../../core/services/locale/locale.service';
import { I18nPipe } from '../../../../core/pipes/i18n.pipe';
import { SettingsService } from '../../../../core/services/settings/settings.service';
import { PlanAccessService } from '../../../../core/services/plan-access.service';
import { AuBtn } from '../../../../shared/components';

@Component({
  selector: 'app-whatsapp-integration',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ButtonModule,
    CardModule,
    MessageModule,
    TagModule,
    ConfirmDialogModule,
    ToastModule,
    I18nPipe,
    AuBtn,
  ],
  providers: [MessageService, ConfirmationService],
  template: `
    <div class="space-y-6">
      <!-- CONTROL DE ACCESO / UPGRADE REQUIRED -->
      <div *ngIf="!hasPermission()" class="rounded-3xl border border-amber-200 bg-amber-50/50 p-6 shadow-sm dark:border-amber-800 dark:bg-amber-900/10">
        <div class="flex items-start gap-4">
          <div class="rounded-2xl bg-amber-100 p-3 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400">
            <i class="pi pi-star text-2xl"></i>
          </div>
          <div class="flex-1">
            <h4 class="text-lg font-bold text-amber-900 dark:text-amber-100">{{ 'settings.whatsapp.upgrade_title' | t }}</h4>
            <p class="mt-2 text-sm leading-6 text-amber-800 dark:text-amber-200">
              {{ 'settings.whatsapp.upgrade_desc' | t }}
            </p>
            <button au-btn 
                    variant="primary" 
                    icon="pi pi-bolt" 
                    class="mt-4" 
                    (click)="goToPlans()">
              {{ 'settings.whatsapp.upgrade_btn' | t }}
            </button>
          </div>
        </div>
      </div>

      <!-- INTEGRACIÓN ACTIVA -->
      <div *ngIf="hasPermission()">
        <!-- SPINNER INICIAL -->
        <div *ngIf="loading()" class="flex flex-col items-center justify-center p-12 bg-white dark:bg-surface-900 rounded-[1.6rem] border border-surface-200 dark:border-surface-800 shadow-[var(--shadow-overlay)] min-h-[300px]">
          <i class="pi pi-spin pi-spinner text-4xl text-primary"></i>
          <span class="mt-4 text-sm text-surface-600 dark:text-surface-400 font-medium">{{ 'settings.whatsapp.loading_status' | t }}</span>
        </div>

        <div *ngIf="!loading()">
          <!-- ESTADO: DESCONECTADO -->
          <div *ngIf="status() === 'disconnected'" class="bg-white dark:bg-surface-900 rounded-[1.6rem] border border-surface-200 dark:border-surface-800 p-8 shadow-[var(--shadow-overlay)]">
            <div class="max-w-2xl">
              <div class="flex items-center gap-3 mb-4">
                <div class="p-3 bg-green-500 rounded-2xl shadow-md text-white">
                  <i class="pi pi-whatsapp text-3xl"></i>
                </div>
                <div>
                  <div class="inline-flex rounded-full bg-surface-100 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.24em] text-surface-600 dark:bg-surface-800 dark:text-surface-300">
                    {{ 'settings.whatsapp.tab_title' | t }}
                  </div>
                  <h3 class="text-2xl font-black text-surface-900 dark:text-white mt-1">{{ 'settings.whatsapp.disconnected_title' | t }}</h3>
                </div>
              </div>

              <p class="text-surface-600 dark:text-surface-400 leading-7 text-base">
                {{ 'settings.whatsapp.disconnected_desc' | t }}
              </p>

              <div class="grid md:grid-cols-3 gap-4 my-6">
                <div class="p-4 rounded-2xl bg-surface-50 dark:bg-surface-800/50 border border-surface-100 dark:border-surface-800">
                  <i class="pi pi-qrcode text-xl text-primary mb-2"></i>
                  <div class="font-bold text-sm text-surface-900 dark:text-white">{{ 'settings.whatsapp.step1_title' | t }}</div>
                  <div class="text-xs text-surface-600 dark:text-surface-400 mt-1">{{ 'settings.whatsapp.step1_desc' | t }}</div>
                </div>
                <div class="p-4 rounded-2xl bg-surface-50 dark:bg-surface-800/50 border border-surface-100 dark:border-surface-800">
                  <i class="pi pi-mobile text-xl text-[var(--brand)] mb-2"></i>
                  <div class="font-bold text-sm text-surface-900 dark:text-white">{{ 'settings.whatsapp.step2_title' | t }}</div>
                  <div class="text-xs text-surface-600 dark:text-surface-400 mt-1">{{ 'settings.whatsapp.step2_desc' | t }}</div>
                </div>
                <div class="p-4 rounded-2xl bg-surface-50 dark:bg-surface-800/50 border border-surface-100 dark:border-surface-800">
                  <i class="pi pi-bell text-xl text-emerald-500 mb-2"></i>
                  <div class="font-bold text-sm text-surface-900 dark:text-white">{{ 'settings.whatsapp.step3_title' | t }}</div>
                  <div class="text-xs text-surface-600 dark:text-surface-400 mt-1">{{ 'settings.whatsapp.step3_desc' | t }}</div>
                </div>
              </div>

              <div class="rounded-2xl bg-[rgba(26,86,219,0.06)] border border-[rgba(26,86,219,0.15)] p-4 dark:bg-[rgba(26,86,219,0.08)] dark:border-[rgba(26,86,219,0.20)] mb-6">
                <div class="flex gap-3">
                  <i class="pi pi-info-circle text-[var(--brand)] dark:text-[var(--brand-400)] text-lg mt-0.5"></i>
                  <p class="text-xs text-[var(--brand)] dark:text-[var(--brand-400)] leading-5">
                    {{ 'settings.whatsapp.disconnected_note' | t }}
                  </p>
                </div>
              </div>

              <button au-btn 
                      variant="primary" 
                      size="lg"
                      icon="pi pi-qrcode" 
                      class="shadow-md" 
                      (click)="connect()"
                      [loading]="actionLoading()">
                {{ 'settings.whatsapp.btn_connect' | t }}
              </button>
            </div>
          </div>

          <!-- ESTADO: CONECTANDO / MOSTRANDO QR -->
          <div *ngIf="status() === 'connecting'" class="bg-white dark:bg-surface-900 rounded-[1.6rem] border border-surface-200 dark:border-surface-800 p-8 shadow-[var(--shadow-overlay)]">
            <div class="grid md:grid-cols-2 gap-8 items-center">
              <div>
                <div class="flex items-center gap-3 mb-4">
                  <div class="p-2 bg-[var(--brand)] rounded-xl text-white shadow-sm">
                    <i class="pi pi-qrcode text-2xl"></i>
                  </div>
                  <h3 class="text-xl font-bold text-surface-900 dark:text-white">{{ 'settings.whatsapp.scan_title' | t }}</h3>
                </div>
                <ol class="space-y-4 text-surface-700 dark:text-surface-300 text-sm leading-6">
                  <li class="flex items-start gap-3">
                    <span class="flex items-center justify-center bg-primary text-white rounded-full h-6 w-6 text-xs font-bold mt-0.5">1</span>
                    <span>{{ 'settings.whatsapp.scan_step1' | t }}</span>
                  </li>
                  <li class="flex items-start gap-3">
                    <span class="flex items-center justify-center bg-primary text-white rounded-full h-6 w-6 text-xs font-bold mt-0.5">2</span>
                    <span>{{ 'settings.whatsapp.scan_step2' | t }}</span>
                  </li>
                  <li class="flex items-start gap-3">
                    <span class="flex items-center justify-center bg-primary text-white rounded-full h-6 w-6 text-xs font-bold mt-0.5">3</span>
                    <span>{{ 'settings.whatsapp.scan_step3' | t }}</span>
                  </li>
                  <li class="flex items-start gap-3">
                    <span class="flex items-center justify-center bg-primary text-white rounded-full h-6 w-6 text-xs font-bold mt-0.5">4</span>
                    <span>{{ 'settings.whatsapp.scan_step4' | t }}</span>
                  </li>
                </ol>

                <div class="mt-6 flex flex-wrap gap-3">
                  <button au-btn 
                          variant="secondary" 
                          size="sm"
                          icon="pi pi-refresh" 
                          (click)="connect()"
                          [loading]="actionLoading()">
                    {{ 'settings.whatsapp.btn_refresh' | t }}
                  </button>
                  <button au-btn 
                          variant="danger" 
                          size="sm"
                          icon="pi pi-times" 
                          (click)="disconnect()"
                          [loading]="actionLoading()">
                    {{ 'settings.whatsapp.btn_cancel' | t }}
                  </button>
                </div>
              </div>

              <div class="flex flex-col items-center justify-center bg-surface-50 dark:bg-surface-950 p-8 rounded-[1.6rem] border border-surface-200 dark:border-surface-800 min-h-[320px]">
                <div *ngIf="actionLoading()" class="flex flex-col items-center justify-center">
                  <i class="pi pi-spin pi-spinner text-3xl text-primary"></i>
                  <span class="mt-3 text-xs text-surface-500">{{ 'settings.whatsapp.generating_qr' | t }}</span>
                </div>

                <div *ngIf="!actionLoading()" class="text-center">
                  <div *ngIf="qrCodeBase64()" class="inline-block p-4 bg-white rounded-2xl shadow-md border border-surface-200 mb-4">
                    <img [src]="getQrCodeSrc()" alt="WhatsApp QR Code" class="w-48 h-48" />
                  </div>
                  <div *ngIf="!qrCodeBase64()" class="text-surface-400 p-8 text-center text-sm">
                    <i class="pi pi-qrcode text-4xl mb-2"></i>
                    <div>{{ 'settings.whatsapp.qr_missing' | t }}</div>
                  </div>
                  <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[rgba(26,86,219,0.08)] border border-[rgba(26,86,219,0.2)] text-[var(--brand)] text-xs font-semibold dark:bg-[rgba(26,86,219,0.15)] dark:border-[rgba(26,86,219,0.25)] dark:text-[var(--brand-400)]">
                    <i class="pi pi-spin pi-sync text-[10px]"></i>
                    {{ 'settings.whatsapp.waiting_scan' | t }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- ESTADO: CONECTADO -->
          <div *ngIf="status() === 'connected'" class="bg-white dark:bg-surface-900 rounded-[1.6rem] border border-surface-200 dark:border-surface-800 p-8 shadow-[var(--shadow-overlay)]">
            <div class="max-w-2xl">
              <div class="flex items-center gap-4 mb-6">
                <div class="p-3 bg-emerald-500 rounded-2xl text-white shadow-md">
                  <i class="pi pi-whatsapp text-3xl"></i>
                </div>
                <div>
                  <div class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400">
                    <span class="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-ping"></span>
                    {{ 'settings.whatsapp.status_connected' | t }}
                  </div>
                  <h3 class="text-2xl font-black text-surface-900 dark:text-white mt-1">{{ 'settings.whatsapp.connected_title' | t }}</h3>
                </div>
              </div>

              <div class="grid md:grid-cols-2 gap-4 mb-6">
                <div class="p-4 rounded-2xl bg-surface-50 dark:bg-surface-800/50 border border-surface-100 dark:border-surface-800">
                  <div class="text-xs text-surface-500">{{ 'settings.whatsapp.connected_phone' | t }}</div>
                  <div class="text-base font-bold text-surface-900 dark:text-white mt-1">
                    {{ phone() ? '+' + phone() : ('settings.whatsapp.phone_unknown' | t) }}
                  </div>
                </div>
                <div class="p-4 rounded-2xl bg-surface-50 dark:bg-surface-800/50 border border-surface-100 dark:border-surface-800">
                  <div class="text-xs text-surface-500">{{ 'settings.whatsapp.instance_name' | t }}</div>
                  <div class="text-base font-mono font-bold text-surface-900 dark:text-white mt-1">
                    {{ instanceName() }}
                  </div>
                </div>
              </div>

              <p class="text-sm text-surface-600 dark:text-surface-400 leading-6 mb-6">
                {{ 'settings.whatsapp.connected_desc' | t }}
              </p>

              <button au-btn 
                      variant="danger" 
                      icon="pi pi-power-off" 
                      (click)="confirmDisconnect()"
                      [loading]="actionLoading()">
                {{ 'settings.whatsapp.btn_disconnect' | t }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <p-confirmDialog [style]="{width: '450px'}"></p-confirmDialog>
  `,
  styles: [`
    ol {
      counter-reset: step;
    }
  `]
})
export class WhatsAppIntegrationComponent implements OnInit, OnDestroy {
  protected localeService = inject(LocaleService);
  private settingsService = inject(SettingsService);
  private planAccessService = inject(PlanAccessService);
  private messageService = inject(MessageService);
  private confirmationService = inject(ConfirmationService);
  private router = inject(Router);

  // States
  hasPermission = signal(false);
  loading = signal(true);
  actionLoading = signal(false);
  status = signal<'disconnected' | 'connecting' | 'connected'>('disconnected');
  qrCodeBase64 = signal<string | null>(null);
  qrCode = signal<string | null>(null);
  phone = signal<string | null>(null);
  instanceName = signal<string>('');

  private pollingSub?: Subscription;

  t(key: string): string {
    return this.localeService.t(key as any);
  }

  getQrCodeSrc(): string {
    const qr = this.qrCodeBase64();
    if (!qr) return '';
    return qr.startsWith('data:') ? qr : 'data:image/png;base64,' + qr;
  }

  ngOnInit(): void {
    const hasFeature = this.planAccessService.canAccessFeature('whatsapp_notifications');
    this.hasPermission.set(hasFeature);

    if (hasFeature) {
      this.checkStatus();
    } else {
      this.loading.set(false);
    }
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  goToPlans(): void {
    this.router.navigate(['/client/payment'], {
      state: { recommendedPlanName: 'Premium' }
    });
  }

  checkStatus(): void {
    this.settingsService.getWhatsAppStatus().subscribe({
      next: (data) => {
        this.status.set(data.whatsapp_status || 'disconnected');
        this.phone.set(data.whatsapp_phone || null);
        this.instanceName.set(data.whatsapp_instance_name || '');
        
        if (this.status() === 'connecting') {
          this.startPolling();
        } else {
          this.stopPolling();
        }
        
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.messageService.add({
          severity: 'error',
          summary: this.t('common.error'),
          detail: this.t('settings.whatsapp.status_error')
        });
      }
    });
  }

  connect(): void {
    this.actionLoading.set(true);
    this.settingsService.connectWhatsApp().subscribe({
      next: (data) => {
        this.actionLoading.set(false);
        if (data.success) {
          this.qrCodeBase64.set(data.qrcode_base64 || null);
          this.qrCode.set(data.qrcode_code || null);
          this.status.set('connecting');
          this.startPolling();
          
          this.messageService.add({
            severity: 'info',
            summary: this.t('settings.whatsapp.tab_title'),
            detail: this.t('settings.whatsapp.qr_generated')
          });
        } else {
          this.messageService.add({
            severity: 'error',
            summary: this.t('common.error'),
            detail: data.error || this.t('settings.whatsapp.connect_error')
          });
        }
      },
      error: (err) => {
        this.actionLoading.set(false);
        const detail = err?.error?.error || this.t('settings.whatsapp.connect_error');
        this.messageService.add({
          severity: 'error',
          summary: this.t('common.error'),
          detail
        });
      }
    });
  }

  confirmDisconnect(): void {
    this.confirmationService.confirm({
      message: this.t('settings.whatsapp.disconnect_confirm_msg'),
      header: this.t('settings.whatsapp.disconnect_confirm_title'),
      icon: 'pi pi-exclamation-triangle',
      acceptLabel: this.t('common.yes'),
      rejectLabel: this.t('common.no'),
      accept: () => {
        this.disconnect();
      }
    });
  }

  disconnect(): void {
    this.actionLoading.set(true);
    this.settingsService.disconnectWhatsApp().subscribe({
      next: () => {
        this.actionLoading.set(false);
        this.status.set('disconnected');
        this.qrCodeBase64.set(null);
        this.qrCode.set(null);
        this.phone.set(null);
        this.stopPolling();
        
        this.messageService.add({
          severity: 'success',
          summary: this.t('common.success'),
          detail: this.t('settings.whatsapp.disconnect_success')
        });
      },
      error: () => {
        this.actionLoading.set(false);
        this.messageService.add({
          severity: 'error',
          summary: this.t('common.error'),
          detail: this.t('settings.whatsapp.disconnect_error')
        });
      }
    });
  }

  private startPolling(): void {
    if (this.pollingSub) return;

    this.pollingSub = interval(5000)
      .pipe(
        switchMap(() => this.settingsService.getWhatsAppStatus()),
        takeWhile((data) => data.whatsapp_status === 'connecting', true)
      )
      .subscribe({
        next: (data) => {
          if (data.whatsapp_status === 'connected') {
            this.status.set('connected');
            this.phone.set(data.whatsapp_phone);
            this.instanceName.set(data.whatsapp_instance_name);
            this.stopPolling();
            
            this.messageService.add({
              severity: 'success',
              summary: this.t('common.success'),
              detail: this.t('settings.whatsapp.connect_success')
            });
          } else if (data.whatsapp_status === 'disconnected') {
            this.status.set('disconnected');
            this.stopPolling();
          }
        },
        error: () => {
          this.stopPolling();
        }
      });
  }

  private stopPolling(): void {
    if (this.pollingSub) {
      this.pollingSub.unsubscribe();
      this.pollingSub = undefined;
    }
  }
}
