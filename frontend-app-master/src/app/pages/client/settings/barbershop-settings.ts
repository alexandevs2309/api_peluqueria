import { Component, DestroyRef, OnInit, inject, signal } from '@angular/core';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { I18nPipe } from '../../../core/pipes/i18n.pipe';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { ToastModule } from 'primeng/toast';
import { FileUploadModule } from 'primeng/fileupload';
import { DialogModule } from 'primeng/dialog';
import { ColorPickerModule } from 'primeng/colorpicker';
import { MessageModule } from 'primeng/message';
import { MessageService, ConfirmationService } from 'primeng/api';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { environment } from '../../../../environments/environment';
import { Router } from '@angular/router';
import { PosService } from '../../../core/services/pos/pos.service';
import { PlanAccessService } from '../../../core/services/plan-access.service';
import { SettingsService } from '../../../core/services/settings/settings.service';
import { OnboardingTourService } from '../../../shared/onboarding/onboarding-tour.service';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { WhatsAppIntegrationComponent } from './components/whatsapp-integration';
import { AuBtn } from '../../../shared/components';

interface BarbershopSettings {
  name: string;
  logo?: string;
  brand_colors?: {
    primary: string;
    secondary: string;
    accent: string;
  };
  currency: string;
  currency_symbol: string;
  currency_locked?: boolean;
  currency_lock_reason?: string;
  business_hours: {
    [key: string]: { open: string; close: string; closed: boolean };
  };
  contact: {
    phone: string;
    email: string;
    address: string;
  };
  pos_config?: {
    business_name: string;
    rnc: string;
    address: string;
    phone: string;
    email: string;
    website: string;
  };
}

@Component({
  selector: 'app-barbershop-settings',
  standalone: true,
  imports: [
    CommonModule, FormsModule, ButtonModule, CardModule,
    InputTextModule, SelectModule, ToastModule, FileUploadModule,
    DialogModule, ColorPickerModule, MessageModule, ConfirmDialogModule,
    TableModule, TagModule, TooltipModule,
    I18nPipe,
    WhatsAppIntegrationComponent,
    AuBtn,
  ],
  providers: [MessageService, ConfirmationService],
  templateUrl: './barbershop-settings.html',
  styles: [`
    .settings-dialog-sm { width: 92vw; max-width: 450px !important; }
    .settings-dialog-md { width: 92vw; max-width: 520px !important; }
    .settings-dialog-lg { width: 92vw; max-width: 600px !important; }
  `]
})
export class BarbershopSettingsComponent implements OnInit {
  protected localeService = inject(LocaleService);
  activeTab = signal('general');

  t(key: string): string {
    return this.localeService.t(key as any);
  }


  private settingsService = inject(SettingsService);
  private planAccessService = inject(PlanAccessService);
  private messageService = inject(MessageService);
  private confirmationService = inject(ConfirmationService);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  private onboardingTourService = inject(OnboardingTourService);
  private posService = inject(PosService);

  // NCF (Comprobante Fiscal)
  ncfSequences = signal<any[]>([]);
  ncfLoading = signal(false);
  showNcfDialog = signal(false);
  editingNcfSequence = signal<any | null>(null);
  ncfForm = signal({
    type: '02',
    prefix: 'B',
    start_sequence: 1,
    end_sequence: 100000,
    current_sequence: 1,
    expiration_date: '',
    is_active: true,
  });

  settings = signal<BarbershopSettings>({
    name: '',
    brand_colors: {
      primary: 'var(--brand)',
      secondary: 'var(--brand)',
      accent: '#059669',
    },
    currency: 'DOP',
    currency_symbol: 'RD$',
    business_hours: {
      monday: { open: '08:00', close: '20:00', closed: false },
      tuesday: { open: '08:00', close: '20:00', closed: false },
      wednesday: { open: '08:00', close: '20:00', closed: false },
      thursday: { open: '08:00', close: '20:00', closed: false },
      friday: { open: '08:00', close: '20:00', closed: false },
      saturday: { open: '08:00', close: '20:00', closed: false },
      sunday: { open: '10:00', close: '20:00', closed: true }
    },
    contact: {
      phone: '',
      email: '',
      address: ''
    },
    pos_config: {
      business_name: '',
      rnc: '',
      address: '',
      phone: '',
      email: '',
      website: ''
    }
  });

  loading = signal(false);
  governanceInfo = signal<any>(null);
  showGovernanceDialog = signal(false);
  governanceAcknowledged = signal(false);
  showCriticalDialog = signal(false);
  criticalChanges = signal<any[]>([]);
  pendingData = signal<any>(null);
  customBrandingEnabled = signal(false);

  currencies = [
    { label: 'Peso Colombiano (COP)', value: 'COP', symbol: '$' },
    { label: 'Peso Dominicano (DOP)', value: 'DOP', symbol: 'RD$' },
    { label: 'Dólar Americano (USD)', value: 'USD', symbol: 'USD$' },
    { label: 'Euro (EUR)', value: 'EUR', symbol: '€' },
    { label: 'Peso Mexicano (MXN)', value: 'MXN', symbol: 'MX$' },
    { label: 'Peso Argentino (ARS)', value: 'ARS', symbol: '$' },
    { label: 'Peso Chileno (CLP)', value: 'CLP', symbol: '$' },
    { label: 'Sol Peruano (PEN)', value: 'PEN', symbol: 'S/' },
    { label: 'Bolívar Venezolano (VES)', value: 'VES', symbol: 'Bs.' },
    { label: 'Lempira Hondureño (HNL)', value: 'HNL', symbol: 'L' },
    { label: 'Quetzal Guatemalteco (GTQ)', value: 'GTQ', symbol: 'Q' },
    { label: 'Córdoba Nicaragüense (NIO)', value: 'NIO', symbol: 'C$' },
    { label: 'Colón Costarricense (CRC)', value: 'CRC', symbol: '₡' },
    { label: 'Balboa Panameño (PAB)', value: 'PAB', symbol: 'B/.' },
    { label: 'Real Brasileño (BRL)', value: 'BRL', symbol: 'R$' },
    { label: 'Libra Esterlina (GBP)', value: 'GBP', symbol: '£' }
  ];

  days = [
    { key: 'monday', label: 'Lunes' },
    { key: 'tuesday', label: 'Martes' },
    { key: 'wednesday', label: 'Miércoles' },
    { key: 'thursday', label: 'Jueves' },
    { key: 'friday', label: 'Viernes' },
    { key: 'saturday', label: 'Sábado' },
    { key: 'sunday', label: 'Domingo' }
  ];

  ngOnInit() {
    this.customBrandingEnabled.set(this.planAccessService.canAccessFeature('custom_branding'));
    this.loadSettings();
    this.loadNcfSequences();
  }

  loadSettings() {
    this.loading.set(true);
    this.settingsService.getBarbershopAdminSettings()
      .pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (data) => {
          const posConfigData = (data.pos_config as BarbershopSettings['pos_config']) || {
            business_name: '',
            rnc: '',
            address: '',
            phone: '',
            email: '',
            website: ''
          };
          const normalizedData: BarbershopSettings = {
            name: data.name || posConfigData.business_name || '',
            logo: data.logo ? this.toAbsoluteUrl(data.logo) : undefined,
            brand_colors: data.brand_colors || {
              primary: 'var(--brand)',
              secondary: 'var(--brand)',
              accent: '#059669',
            },
            currency: data.currency || 'DOP',
            currency_symbol: data.currency_symbol || 'RD$',
            currency_locked: data.currency_locked ?? false,
            currency_lock_reason: data.currency_lock_reason || '',
            business_hours: data.business_hours && Object.keys(data.business_hours).length > 0 ? data.business_hours : {
              monday: { open: '08:00', close: '20:00', closed: false },
              tuesday: { open: '08:00', close: '20:00', closed: false },
              wednesday: { open: '08:00', close: '20:00', closed: false },
              thursday: { open: '08:00', close: '20:00', closed: false },
              friday: { open: '08:00', close: '20:00', closed: false },
              saturday: { open: '08:00', close: '20:00', closed: false },
              sunday: { open: '10:00', close: '20:00', closed: true }
            },
            contact: data.contact || {
              phone: '',
              email: '',
              address: ''
            },
            pos_config: posConfigData
          };
          this.settings.set(normalizedData);
          this.loading.set(false);
        },
        error: () => {
          this.loading.set(false);
          this.messageService.add({
            severity: 'warn',
            summary: this.t('settings.title'),
            detail: this.t('settings.toast.load_default_warning')
          });
        }
      });
  }

  loadGovernanceInfo() {
    // Endpoint governance_info no disponible - usando configuración por defecto
  }

  // NCF (Comprobante Fiscal) Methods
  loadNcfSequences() {
    this.ncfLoading.set(true);
    this.posService.getNcfSequences()
      .pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (data) => {
          this.ncfSequences.set(data.results || data);
          this.ncfLoading.set(false);
        },
        error: () => {
          this.ncfLoading.set(false);
        }
      });
  }

  openNcfDialog(sequence: any | null = null) {
    if (sequence) {
      this.editingNcfSequence.set(sequence);
      this.ncfForm.set({
        type: sequence.type,
        prefix: sequence.prefix,
        start_sequence: sequence.start_sequence,
        end_sequence: sequence.end_sequence,
        current_sequence: sequence.current_sequence,
        expiration_date: sequence.expiration_date,
        is_active: sequence.is_active,
      });
    } else {
      this.editingNcfSequence.set(null);
      this.ncfForm.set({
        type: '02',
        prefix: 'B',
        start_sequence: 1,
        end_sequence: 100000,
        current_sequence: 1,
        expiration_date: '',
        is_active: true,
      });
    }
    this.showNcfDialog.set(true);
  }

  saveNcfSequence() {
    const form = this.ncfForm();
    const isEdit = this.editingNcfSequence() !== null;
    const data = {
      type: form.type,
      prefix: form.prefix,
      start_sequence: form.start_sequence,
      end_sequence: form.end_sequence,
      current_sequence: form.current_sequence,
      expiration_date: form.expiration_date,
      is_active: form.is_active,
    };

    this.ncfLoading.set(true);
    const request = isEdit
      ? this.posService.updateNcfSequence(this.editingNcfSequence()!.id, data)
      : this.posService.createNcfSequence(data);

    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.messageService.add({
          severity: 'success',
          summary: this.t('common.success'),
          detail: isEdit ? this.t('settings.ncf.updated') : this.t('settings.ncf.created'),
        });
        this.ncfLoading.set(false);
        this.showNcfDialog.set(false);
        this.loadNcfSequences();
      },
      error: (err) => {
        this.ncfLoading.set(false);
        const detail = err?.error?.detail || this.t('settings.ncf.save_error');
        this.messageService.add({
          severity: 'error',
          summary: this.t('common.error'),
          detail,
        });
      }
    });
  }

  deleteNcfSequence(sequence: any) {
    this.confirmationService.confirm({
      message: this.t('settings.ncf.delete_confirm').replace('{name}', sequence.prefix + sequence.type),
      header: this.t('settings.ncf.delete_title'),
      icon: 'pi pi-exclamation-triangle',
      acceptLabel: this.t('common.yes'),
      rejectLabel: this.t('common.no'),
      accept: () => {
        this.ncfLoading.set(true);
        this.posService.deleteNcfSequence(sequence.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
          next: () => {
            this.messageService.add({
              severity: 'success',
              summary: this.t('common.success'),
              detail: this.t('settings.ncf.deleted'),
            });
            this.ncfLoading.set(false);
            this.loadNcfSequences();
          },
          error: () => {
            this.ncfLoading.set(false);
            this.messageService.add({
              severity: 'error',
              summary: this.t('common.error'),
              detail: this.t('settings.ncf.delete_error'),
            });
          }
        });
      }
    });
  }

  saveSettings() {
    const validationErrors = this.validateSettings();
    if (validationErrors.length > 0) {
      this.messageService.add({
        severity: 'warn',
        summary: this.t('settings.toast.review_config_warning'),
        detail: validationErrors[0]
      });
      return;
    }

    this.pendingSettings = this.settings();
    if (!this.governanceAcknowledged()) {
      this.showGovernanceDialog.set(true);
      return;
    }
    this.proceedSave();
  }

  private pendingSettings: any = null;

  private proceedSave() {
    if (!this.pendingSettings) return;
    const current = this.pendingSettings;

    this.loading.set(true);
    const payload: Record<string, unknown> = {
      name: current.name || current.pos_config?.business_name || '',
      currency: current.currency,
      currency_symbol: current.currency_symbol,
      business_hours: current.business_hours,
      contact: current.contact,
      pos_config: current.pos_config
    };
    if (current.brand_colors) {
      payload.primary_color = current.brand_colors.primary;
      payload.secondary_color = current.brand_colors.secondary;
      payload.accent_color = current.brand_colors.accent;
    }

    this.settingsService.updateBarbershopSettings(payload)
      .pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (response: any) => {
          this.loading.set(false);
          
          if (response.requires_confirmation) {
            this.criticalChanges.set(response.critical_changes);
            this.pendingData.set(current);
            this.showCriticalDialog.set(true);
            return;
          }
          
          this.messageService.add({
            severity: 'success',
            summary: this.t('common.success'),
            detail: this.t('settings.toast.save_success_detail')
          });
          this.loadSettings();
        },
        error: (error) => {
          this.loading.set(false);
          const backendDetail =
            error?.error?.details ||
            error?.error?.error ||
            error?.error?.message ||
            this.t('settings.toast.save_error_detail');
          this.messageService.add({
            severity: 'error',
            summary: this.t('common.error'),
            detail: backendDetail
          });
        }
      });
  }

  confirmCriticalChanges() {
    if (!this.pendingData()) return;
    
    this.loading.set(true);
    const dataWithConfirmation = {
      ...this.pendingData(),
      confirmed_critical: true
    };
    
    this.settingsService.updateBarbershopSettings(dataWithConfirmation)
      .pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (response: any) => {
          this.loading.set(false);
          this.showCriticalDialog.set(false);
          this.criticalChanges.set([]);
          this.pendingData.set(null);
          
          this.messageService.add({
            severity: 'success',
            summary: this.t('common.success'),
            detail: this.t('settings.toast.critical_save_success_detail')
          });
          this.loadSettings();
        },
        error: () => {
          this.loading.set(false);
          this.messageService.add({
            severity: 'error',
            summary: this.t('common.error'),
            detail: this.t('settings.toast.save_error_detail')
          });
        }
      });
  }

  acknowledgeGovernance() {
    this.governanceAcknowledged.set(true);
    this.showGovernanceDialog.set(false);
    this.proceedSave();
  }

  dismissGovernance() {
    this.showGovernanceDialog.set(false);
    this.criticalChanges.set([]);
    this.pendingData.set(null);
    this.pendingSettings = null;
    this.messageService.add({
      severity: 'info',
      summary: this.t('settings.governance_title'),
      detail: this.t('settings.toast.governance_cancel')
    });
  }

  cancelCriticalChanges() {
    this.showCriticalDialog.set(false);
    this.criticalChanges.set([]);
    this.pendingData.set(null);
    
    this.messageService.add({
      severity: 'info',
      summary: this.t('settings.critical_dialog_cancel'),
      detail: this.t('settings.toast.cancel_critical_info')
    });
  }

  onCurrencyChange(currency: any) {
    if (this.settings().currency_locked) {
      return;
    }
    const selected = this.currencies.find(c => c.value === currency);
    if (selected) {
      this.settings.update(s => ({
        ...s,
        currency: selected.value,
        currency_symbol: selected.symbol
      }));
    }
  }

  onLogoUpload(event: any) {
    if (!this.customBrandingEnabled()) {
      const recommendation = this.planAccessService.getFeatureUpgradeRecommendation('custom_branding');
      this.messageService.add({
        severity: 'warn',
        summary: this.t('settings.toast.upgrade_branding_warning'),
        detail: recommendation ? `${recommendation.reason} ${recommendation.detail}` : 'Esta funcionalidad requiere Premium.'
      });
      return;
    }

    const file = event.files[0];
    if (file) {
      const formData = new FormData();
      formData.append('logo', file);

      this.settingsService.uploadBarbershopLogo(formData)
        .pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
          next: (response: any) => {
            this.settings.update(s => ({ ...s, logo: this.toAbsoluteUrl(response.logo_url) }));
            this.messageService.add({
              severity: 'success',
              summary: this.t('settings.logo_label'),
              detail: this.t('settings.toast.logo_upload_success')
            });
          },
          error: () => {
            this.messageService.add({
              severity: 'error',
              summary: this.t('common.error'),
              detail: this.t('settings.toast.logo_upload_error')
            });
          }
        });
    }
  }

  updatePosConfig(field: keyof NonNullable<BarbershopSettings['pos_config']>, value: string) {
    this.settings.update(s => ({
      ...s,
      pos_config: { ...s.pos_config!, [field]: value }
    }));
  }

  updateContact(field: keyof BarbershopSettings['contact'], value: string) {
    this.settings.update(s => ({
      ...s,
      contact: { ...s.contact, [field]: value }
    }));
  }

  updateName(value: string) {
    this.settings.update(s => ({ ...s, name: value }));
  }

  updateBusinessHour(day: string, field: 'open' | 'close' | 'closed', value: any) {
    this.settings.update(s => ({
      ...s,
      business_hours: {
        ...s.business_hours,
        [day]: {
          ...s.business_hours[day],
          [field]: value
        }
      }
    }));
  }

  getBusinessHour(day: string, field: 'open' | 'close' | 'closed'): any {
    return this.settings().business_hours[day]?.[field];
  }

  isBusinessNameInvalid(): boolean {
    return !this.settings().name?.trim();
  }

  isContactEmailInvalid(): boolean {
    const email = this.settings().contact?.email;
    return Boolean(email && !this.isValidEmail(email));
  }

  isPosEmailInvalid(): boolean {
    const email = this.settings().pos_config?.email;
    return Boolean(email && !this.isValidEmail(email));
  }

  isPosWebsiteInvalid(): boolean {
    const website = this.settings().pos_config?.website;
    return Boolean(website && !this.isValidUrl(website));
  }

  isDayScheduleInvalid(day: string): boolean {
    const schedule = this.settings().business_hours?.[day];
    if (!schedule || schedule.closed) {
      return false;
    }

    return !schedule.open || !schedule.close || schedule.open >= schedule.close;
  }

  getTicketPreviewBusinessName(): string {
    return this.settings().pos_config?.business_name?.trim() || this.settings().name?.trim() || 'Mi Peluqueria';
  }

  getTicketPreviewAddress(): string {
    return this.settings().pos_config?.address?.trim() || this.settings().contact?.address?.trim() || 'Direccion no configurada';
  }

  getTicketPreviewRnc(): string {
    return this.settings().pos_config?.rnc?.trim() || 'RNC no configurado';
  }

  getTicketPreviewPhone(): string {
    return this.settings().pos_config?.phone?.trim() || this.settings().contact?.phone?.trim() || 'Telefono no configurado';
  }

  getTicketPreviewEmail(): string {
    return this.settings().pos_config?.email?.trim() || this.settings().contact?.email?.trim() || 'Email no configurado';
  }

  getTicketPreviewWebsite(): string {
    return this.settings().pos_config?.website?.trim() || 'www.tunegocio.com';
  }

  getTicketPreviewCurrency(): string {
    return this.settings().currency_symbol || '$';
  }

  getConfiguredContactCount(): number {
    const contact = this.settings().contact;
    return [contact?.phone, contact?.email, contact?.address].filter((value) => String(value || '').trim()).length;
  }

  hasFiscalIdentity(): boolean {
    return Boolean(this.settings().pos_config?.business_name?.trim() && this.settings().pos_config?.rnc?.trim());
  }

  getOperationalReadinessMessage(): string {
    if (!this.settings().name?.trim()) {
      return this.t('settings.readiness.name_missing');
    }

    if (!this.hasFiscalIdentity()) {
      return this.t('settings.readiness.fiscal_missing');
    }

    if (this.getConfiguredContactCount() < 2) {
      return this.t('settings.readiness.contact_missing');
    }

    return this.t('settings.readiness.ready');
  }

  copyMondayScheduleToOpenDays() {
    const monday = this.settings().business_hours['monday'];
    if (!monday) {
      return;
    }

    this.settings.update(s => {
      const updatedHours = { ...s.business_hours };
      Object.keys(updatedHours).forEach((dayKey) => {
        if (dayKey === 'monday') return;
        if (!updatedHours[dayKey].closed) {
          updatedHours[dayKey] = {
            ...updatedHours[dayKey],
            open: monday.open,
            close: monday.close
          };
        }
      });

      return {
        ...s,
        business_hours: updatedHours
      };
    });

    this.saveSettings();
  }

  getSettingType(settingName: string): 'critical' | 'sensitive' | 'cosmetic' {
    const governance = this.governanceInfo();
    if (!governance) return 'cosmetic';
    
    if (governance.critical && governance.critical[settingName]) return 'critical';
    if (governance.sensitive && governance.sensitive[settingName]) return 'sensitive';
    return 'cosmetic';
  }

  getSettingIcon(settingName: string): string {
    const type = this.getSettingType(settingName);
    switch (type) {
      case 'critical': return 'pi pi-exclamation-triangle';
      case 'sensitive': return 'pi pi-info-circle';
      default: return 'pi pi-cog';
    }
  }

  getSettingColor(settingName: string): string {
    const type = this.getSettingType(settingName);
    switch (type) {
      case 'critical': return 'text-red-600';
      case 'sensitive': return 'text-orange-600';
      default: return 'text-surface-600';
    }
  }

  goToPlans() {
    this.router.navigate(['/client/payment'], {
      state: { recommendedPlanName: 'Premium' }
    });
  }

  private toAbsoluteUrl(url?: string): string {
    if (!url) return '';
    if (/^https?:\/\//i.test(url)) return url;
    const apiOrigin = new URL(environment.apiUrl).origin;
    return url.startsWith('/') ? `${apiOrigin}${url}` : `${apiOrigin}/${url}`;
  }

  private validateSettings(): string[] {
    const current = this.settings();
    const errors: string[] = [];

    if (!current.name?.trim() && !current.pos_config?.business_name?.trim()) {
      errors.push(this.t('settings.business_name_required'));
    }

    if (current.contact?.email && !this.isValidEmail(current.contact.email)) {
      errors.push(this.t('settings.contact_email_invalid'));
    }

    if (current.pos_config?.email && !this.isValidEmail(current.pos_config.email)) {
      errors.push(this.t('settings.pos_config_email_invalid'));
    }

    if (current.pos_config?.website && !this.isValidUrl(current.pos_config.website)) {
      errors.push(this.t('settings.pos_config_website_invalid'));
    }

    for (const day of Object.keys(current.business_hours || {})) {
      const schedule = current.business_hours[day];
      if (!schedule || schedule.closed) {
        continue;
      }

      const dayLabel = this.t('common.days.' + day);
      if (!schedule.open || !schedule.close) {
        errors.push(this.t('settings.business_hours_required').replace('{day}', dayLabel));
        continue;
      }

      if (schedule.open >= schedule.close) {
        errors.push(this.t('settings.business_hours_invalid_range').replace('{day}', dayLabel));
      }
    }

    return errors;
  }

  private isValidEmail(value: string): boolean {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
  }

  private isValidUrl(value: string): boolean {
    const normalized = value.startsWith('http://') || value.startsWith('https://')
      ? value
      : `https://${value}`;

    try {
      const url = new URL(normalized);
      return Boolean(url.hostname);
    } catch {
      return false;
    }
  }

  restartTour(): void {
    this.onboardingTourService.startManualTour();
  }

  onBrandColorChange(): void {
    const colors = this.settings().brand_colors;
    if (colors) {
      const root = document.documentElement;
      root.style.setProperty('--brand-primary', colors.primary);
      root.style.setProperty('--brand-secondary', colors.secondary);
      root.style.setProperty('--brand-accent', colors.accent);
    }
  }
}


