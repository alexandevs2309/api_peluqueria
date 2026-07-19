import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { PasswordModule } from 'primeng/password';
import { CardModule } from 'primeng/card';
import { MessageService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';
import { AuthService } from '../../../core/services/auth/auth.service';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { I18nPipe } from '../../../core/pipes/i18n.pipe';
import { AuBtn } from '../../../shared/components';

@Component({
    selector: 'app-change-password',
    standalone: true,
    imports: [CommonModule, FormsModule, AuBtn, ButtonModule, PasswordModule, CardModule, ToastModule, I18nPipe],
    providers: [MessageService],
    template: `
        <p-toast />
        <div class="password-page p-4 md:p-6">
            <section class="password-hero mb-6">
                <div class="flex items-center gap-4">
                    <div class="hero-icon">
                        <i class="pi pi-shield text-white text-2xl"></i>
                    </div>
                    <div>
                        <h1 class="display-3 mb-1">{{ 'password.title' | t }}</h1>
                        <p class="hero-subtitle">{{ userName }} • {{ 'password.subtitle' | t }}</p>
                    </div>
                </div>
            </section>

            <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
                <div class="xl:col-span-2">
                    <p-card>
                        <div class="space-y-5">
                            <div>
                                <h2 class="section-title">{{ 'password.section_title' | t }}</h2>
                                <p class="section-subtitle">{{ 'password.section_subtitle' | t }}</p>
                            </div>

                            <div>
                                <label class="block font-medium mb-2">{{ 'password.current' | t }}</label>
                                <p-password
                                    [(ngModel)]="currentPassword"
                                    [feedback]="false"
                                    [toggleMask]="true"
                                    styleClass="w-full"
                                    inputStyleClass="w-full"
                                ></p-password>
                            </div>

                            <div>
                                <label class="block font-medium mb-2">{{ 'password.new' | t }}</label>
                                <p-password
                                    [(ngModel)]="newPassword"
                                    [toggleMask]="true"
                                    styleClass="w-full"
                                    inputStyleClass="w-full"
                                ></p-password>
                            </div>

                            <div>
                                <label class="block font-medium mb-2">{{ 'password.confirm' | t }}</label>
                                <p-password
                                    [(ngModel)]="confirmPassword"
                                    [feedback]="false"
                                    [toggleMask]="true"
                                    styleClass="w-full"
                                    inputStyleClass="w-full"
                                ></p-password>
                                @if (confirmPassword.length > 0 && newPassword !== confirmPassword) {
                                    <small class="text-red-500 mt-2 block">{{ 'password.mismatch' | t }}</small>
                                }
                            </div>

                            <div class="flex justify-end">
                            <button
                                au-btn variant="primary"
                                [icon]="'pi pi-key'"
                                (click)="changePassword()"
                                [loading]="saving()"
                                [disabled]="!isValid()"
                            >{{ 'password.title' | t }}</button>
                            </div>
                        </div>
                    </p-card>
                </div>

                <div class="space-y-6">
                    <p-card>
                        <div class="space-y-3">
                            <h3 class="section-title !mb-0">{{ 'password.checklist_title' | t }}</h3>
                            <div class="check-row" [class.ok]="newPassword.length >= 8">
                                <i class="pi" [ngClass]="newPassword.length >= 8 ? 'pi-check-circle' : 'pi-circle'"></i>
                                <span>{{ 'password.checklist_min_len' | t }}</span>
                            </div>
                            <div class="check-row" [class.ok]="hasUppercase()">
                                <i class="pi" [ngClass]="hasUppercase() ? 'pi-check-circle' : 'pi-circle'"></i>
                                <span>{{ 'password.checklist_uppercase' | t }}</span>
                            </div>
                            <div class="check-row" [class.ok]="hasNumber()">
                                <i class="pi" [ngClass]="hasNumber() ? 'pi-check-circle' : 'pi-circle'"></i>
                                <span>{{ 'password.checklist_number' | t }}</span>
                            </div>
                            <div class="check-row" [class.ok]="newPassword === confirmPassword && confirmPassword.length > 0">
                                <i class="pi" [ngClass]="newPassword === confirmPassword && confirmPassword.length > 0 ? 'pi-check-circle' : 'pi-circle'"></i>
                                <span>{{ 'password.checklist_match' | t }}</span>
                            </div>
                        </div>
                    </p-card>

                    <p-card>
                        <div class="space-y-2">
                            <h3 class="section-title !mb-0">{{ 'password.recommendation_title' | t }}</h3>
                            <p class="section-subtitle">{{ 'password.recommendation_desc' | t }}</p>
                        </div>
                    </p-card>
                </div>
            </div>
        </div>
    `,
    styles: [`
        .password-page {
            background: linear-gradient(180deg, rgba(26,86,219,0.08) 0%, rgba(26,86,219,0.02) 35%, transparent 100%);
            min-height: calc(100vh - 7rem);
            border-radius: 1rem;
        }

        .password-hero {
            border: 1px solid var(--surface-border);
            background: var(--surface-card);
            border-radius: 1rem;
            padding: 1.25rem;
        }

        .hero-icon {
            width: 3rem;
            height: 3rem;
            border-radius: 0.75rem;
            background: linear-gradient(135deg, var(--brand), var(--brand-400));
            display: grid;
            place-items: center;
        }

        .hero-subtitle {
            margin: 0;
            color: var(--text-color-secondary);
        }

        .section-title {
            margin: 0 0 0.25rem;
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text-color);
        }

        .section-subtitle {
            margin: 0;
            color: var(--text-color-secondary);
            font-size: 0.92rem;
        }

        .check-row {
            display: flex;
            gap: 0.55rem;
            align-items: center;
            color: var(--text-color-secondary);
            font-size: 0.92rem;
        }

        .check-row.ok {
            color: #16a34a;
        }
    `]
})
export class ChangePasswordComponent implements OnInit {
    protected localeService = inject(LocaleService);

    t(key: string): string {
        return this.localeService.t(key as any);
    }

    currentPassword = '';
    newPassword = '';
    confirmPassword = '';
    saving = signal(false);
    userName = '';

    constructor(
        private messageService: MessageService,
        private authService: AuthService
    ) {}

    ngOnInit(): void {
        const user = this.authService.getCurrentUser();
        this.userName = user?.full_name || user?.email || this.t('profile.no_name');
    }

    isValid(): boolean {
        return this.currentPassword.length > 0 &&
               this.newPassword.length >= 8 &&
               this.hasUppercase() &&
               this.hasNumber() &&
               this.newPassword === this.confirmPassword;
    }

    hasUppercase(): boolean {
        return /[A-Z]/.test(this.newPassword);
    }

    hasNumber(): boolean {
        return /\d/.test(this.newPassword);
    }

    changePassword() {
        if (!this.isValid()) return;

        this.saving.set(true);
        this.authService.changePassword({
            old_password: this.currentPassword,
            new_password: this.newPassword
        }).subscribe({
            next: () => {
                this.messageService.add({
                    severity: 'success',
                    summary: this.t('common.success'),
                    detail: this.t('password.toast.success')
                });
                this.currentPassword = '';
                this.newPassword = '';
                this.confirmPassword = '';
                this.saving.set(false);
            },
            error: (err) => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.t('common.error'),
                    detail: err.error?.old_password?.[0] || err.error?.detail || this.t('password.toast.error')
                });
                this.saving.set(false);
            }
        });
    }
}
