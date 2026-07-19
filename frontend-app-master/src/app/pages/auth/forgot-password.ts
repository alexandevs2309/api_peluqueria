import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { AuBtn } from '../../shared/components';
import { ToastModule } from 'primeng/toast';
import { MessageService } from 'primeng/api';
import { AuthService } from '../../core/services/auth/auth.service';
import { AppConfigService } from '../../core/services/app-config.service';
import { LocaleService } from '../../core/services/locale/locale.service';
import { getHttpErrorMessage } from '../../core/utils/http-error-message';
import { safeGetItem } from '../../core/utils/storage';

@Component({
    selector: 'app-forgot-password',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, RouterModule, ButtonModule, InputTextModule, ToastModule, AuBtn],
    providers: [MessageService],
    templateUrl: './forgot-password.component.html'
})
export class ForgotPassword {
    forgotForm: FormGroup;
    isLoading = signal(false);
    emailSent = signal(false);
    tenantRequired = signal(false);

    constructor(
        private fb: FormBuilder,
        private authService: AuthService,
        public appConfig: AppConfigService,
        private messageService: MessageService,
        private router: Router,
        private localeService: LocaleService
    ) {
        this.forgotForm = this.fb.group({
            email: ['', [Validators.required, Validators.email]],
            tenant_subdomain: ['']
        });
    }

    get email() {
        return this.forgotForm.get('email')!;
    }

    get tenantSubdomain() {
        return this.forgotForm.get('tenant_subdomain')!;
    }

    onSubmit() {
        if (this.forgotForm.invalid) return;

        this.isLoading.set(true);
        const { email, tenant_subdomain } = this.forgotForm.value;

        const storedTenant = JSON.parse(safeGetItem('tenant') || 'null');
        const resolvedSubdomain = (tenant_subdomain || '').trim() || storedTenant?.subdomain || undefined;

        this.authService.requestPasswordReset(email, resolvedSubdomain).subscribe({
            next: () => {
                this.emailSent.set(true);
                this.tenantRequired.set(false);
                this.messageService.add({
                    severity: 'success',
                    summary: this.t('auth.forgot.email_sent'),
                    detail: this.t('auth.forgot.check_inbox')
                });
            },
            error: (error) => {
                if (error?.error?.code === 'tenant_required') {
                    this.tenantRequired.set(true);
                    this.forgotForm.get('tenant_subdomain')?.setValidators([Validators.required]);
                    this.forgotForm.get('tenant_subdomain')?.updateValueAndValidity();
                    this.messageService.add({
                        severity: 'warn',
                        summary: 'Tenant requerido',
                        detail: 'Tu correo está asociado a varias cuentas. Ingresa el subdominio de tu negocio.'
                    });
                } else {
                    this.messageService.add({
                        severity: 'error',
                        summary: this.t('common.error'),
                        detail: getHttpErrorMessage(error, this.t('auth.forgot.could_not_send'))
                    });
                }
                this.isLoading.set(false);
            },
            complete: () => this.isLoading.set(false)
        });
    }

    backToLogin() {
        this.router.navigate(['/auth/login']);
    }

    t(key: string): string {
        return this.localeService.t(key as any);
    }
}
