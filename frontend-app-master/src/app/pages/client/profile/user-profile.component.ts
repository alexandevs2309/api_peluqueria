import { Component, DestroyRef, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { InputOtpModule } from 'primeng/inputotp';
import { InputTextModule } from 'primeng/inputtext';
import { CardModule } from 'primeng/card';
import { CheckboxModule } from 'primeng/checkbox';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { MessageService, ConfirmationService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';
import { AuthService } from '../../../core/services/auth/auth.service';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { Router } from '@angular/router';
import { SubscriptionService } from '../../../core/services/subscription/subscription.service';
import { TenantService } from '../../../core/services/tenant/tenant.service';
import { PlanAccessService } from '../../../core/services/plan-access.service';
import { getSubscriptionPlanLabel } from '../../../core/utils/subscription-plan-label';
import { getRoleDisplayLabel } from '../../../core/utils/role-normalizer';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { I18nPipe } from '../../../core/pipes/i18n.pipe';
import { AuBtn } from '../../../shared/components';
import { safeGetItem } from '../../../core/utils/storage';

@Component({
    selector: 'app-user-profile',
    standalone: true,
    imports: [CommonModule, FormsModule, AuBtn, ButtonModule, InputTextModule, InputOtpModule, CardModule, CheckboxModule, ConfirmDialogModule, ToastModule, I18nPipe],
    providers: [MessageService, ConfirmationService],
    template: `
        <p-confirmDialog />
        <p-toast />
        <div class="profile-page p-4 md:p-6">
            <section class="profile-hero mb-6">
                <div class="profile-hero__left">
                    <div class="profile-avatar" [class.has-image]="!!getProfileImageUrl()">
                        @if (getProfileImageUrl(); as imageUrl) {
                            <img [src]="imageUrl" [alt]="'profile.profile_photo' | t" />
                        } @else {
                            <span>{{ getInitials(user.full_name || user.email) }}</span>
                        }
                    </div>

                    <div class="profile-identity">
                        <h1 class="display-3 mb-1">{{ 'profile.my_account' | t }}</h1>
                        <p class="profile-name">{{ user.full_name || ('profile.no_name' | t) }}</p>
                        <p class="profile-meta">
                            {{ getRoleDisplayName(user.role) }}
                            <span class="mx-2">•</span>
                            {{ ('profile.member_since' | t).replace('{date}', formatDate(user.date_joined)) }}
                        </p>
                        <div class="mt-3">
                            <input #avatarInput type="file" accept="image/*" class="hidden" (change)="onAvatarSelected($event)" />
                            <button au-btn type="button" variant="secondary" size="sm" [icon]="'pi pi-camera'" (click)="avatarInput.click()" [loading]="uploadingAvatar()">{{ 'profile.change_photo' | t }}</button>
                        </div>
                    </div>
                </div>

                <div class="profile-hero__right">
                    <div class="auron-surface-card stat-chip">
                        <i class="pi pi-verified text-green-500"></i>
                        <div>
                            <p class="stat-label">{{ 'profile.status' | t }}</p>
                            <p class="stat-value">{{ user.is_active === false ? ('profile.inactive' | t) : ('profile.active' | t) }}</p>
                        </div>
                    </div>
                    <div class="auron-surface-card stat-chip">
                        <i class="pi pi-users text-[var(--brand)]"></i>
                        <div>
                            <p class="stat-label">{{ 'profile.roles_assigned' | t }}</p>
                            <p class="stat-value">{{ (user.roles?.length || 0) > 0 ? user.roles.length : 1 }}</p>
                        </div>
                    </div>
                </div>
            </section>

            <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
                <div class="xl:col-span-2">
                    <p-card>
                        <div class="space-y-6">
                            <div>
                                <h2 class="section-title">{{ 'profile.personal_info' | t }}</h2>
                                <p class="section-subtitle">{{ 'profile.personal_info_desc' | t }}</p>
                            </div>

                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label class="block font-medium mb-2">{{ 'profile.full_name' | t }}</label>
                                    <input pInputText [(ngModel)]="user.full_name" class="w-full" />
                                </div>

                                <div>
                                    <label class="block font-medium mb-2">{{ 'profile.email' | t }}</label>
                                    <input pInputText [(ngModel)]="user.email" type="email" class="w-full" />
                                </div>

                                <div>
                                    <label class="block font-medium mb-2">{{ 'profile.phone' | t }}</label>
                                    <input pInputText [(ngModel)]="user.phone" class="w-full" />
                                </div>

                                <div>
                                    <label class="block font-medium mb-2">{{ 'profile.role' | t }}</label>
                                    <input pInputText [value]="getRoleDisplayName(user.role)" [disabled]="true" class="w-full" />
                                </div>
                            </div>

                            <div class="flex justify-end">
                            <button
                                au-btn variant="primary"
                                [icon]="'pi pi-save'"
                                (click)="saveProfile()"
                                [loading]="saving()"
                            >{{ 'profile.save_changes' | t }}</button>
                            </div>
                        </div>
                    </p-card>
                </div>

                <div class="space-y-6">
                    <p-card>
                        <div class="space-y-3">
                            <h3 class="section-title !mb-0">{{ 'profile.summary' | t }}</h3>
                            <div class="summary-row">
                                <span>{{ 'profile.user_id' | t }}</span>
                                <strong>#{{ user.id || 'N/A' }}</strong>
                            </div>
                            <div class="summary-row">
                                <span>{{ 'profile.tenant' | t }}</span>
                                <strong>{{ getTenantDisplay() }}</strong>
                            </div>
                            <div class="summary-row">
                                <span>{{ 'profile.registration_date' | t }}</span>
                                <strong>{{ formatDate(user.date_joined) }}</strong>
                            </div>
                            <div class="summary-row">
                                <span>{{ 'profile.profile_photo' | t }}</span>
                                <strong>{{ getProfileImageUrl() ? ('profile.configured' | t) : ('profile.not_configured' | t) }}</strong>
                            </div>
                            <div class="summary-row">
                                <span>{{ 'profile.mfa' | t }}</span>
                                <strong>{{ user.mfa_enabled ? ('profile.active' | t) : ('profile.not_configured' | t) }}</strong>
                            </div>
                            <div class="summary-row" *ngIf="expiryDate">
                                <span>{{ expiryLabel }}</span>
                                <strong>{{ expiryDate }}</strong>
                            </div>
                        </div>
                    </p-card>

                    <p-card>
                        <div class="space-y-3">
                            <h3 class="section-title !mb-0">{{ 'profile.current_plan' | t }}</h3>
                            <div class="summary-row">
                                <span>{{ 'profile.current_plan' | t }}</span>
                                <strong>{{ getCurrentPlanName() }}</strong>
                            </div>
                            <div class="summary-row">
                                <span>{{ 'profile.plan_status' | t }}</span>
                                <strong>{{ getCurrentPlanStatusText() }}</strong>
                            </div>
                            <div *ngIf="currentSubscription?.is_cancelled" class="cancelled-badge">
                                <i class="pi pi-info-circle"></i>
                                {{ ('profile.cancelled_info' | t).replace('{date}', (currentSubscription.access_until | date:'dd/MM/yyyy') || '') }}
                            </div>
                            <p class="section-subtitle">{{ getCurrentPlanCopy() }}</p>
                            <button au-btn variant="secondary" class="w-full" [icon]="'pi pi-credit-card'" (click)="goToPayment()">{{ 'profile.view_plans' | t }}</button>
                            <button *ngIf="canCancelSubscription() && !currentSubscription?.is_cancelled" au-btn
                                variant="danger" class="w-full"
                                [icon]="'pi pi-times'"
                                (click)="confirmCancel()" [loading]="cancelling">{{ 'profile.cancel_subscription' | t }}
                            </button>
                            <button *ngIf="canCancelSubscription() && currentSubscription?.is_cancelled" au-btn
                                variant="primary" class="w-full"
                                [icon]="'pi pi-refresh'"
                                (click)="reactivate()">{{ 'profile.reactivate_subscription' | t }}
                            </button>
                        </div>
                    </p-card>

                    <p-card>
                        <div class="space-y-4">
                            <div>
                                <h3 class="section-title !mb-0">{{ 'profile.mfa_title' | t }}</h3>
                                <p class="section-subtitle">{{ 'profile.mfa_desc' | t }}</p>
                            </div>

                            @if (user.mfa_enabled) {
                                <div class="mfa-status mfa-status--active">
                                    <i class="pi pi-shield"></i>
                                    <div>
                                        <strong>{{ 'profile.mfa_active_title' | t }}</strong>
                                        <p>{{ 'profile.mfa_active_desc' | t }}</p>
                                    </div>
                                </div>

                                @if (!showDisableMfa) {
                                    <button
                                        au-btn
                                        type="button"
                                        variant="secondary"
                                        class="w-full"
                                        [icon]="'pi pi-lock-open'"
                                        (click)="openDisableMfa()"
                                    >{{ 'profile.mfa_deactivate_btn' | t }}</button>
                                }

                                @if (showDisableMfa) {
                                    <div class="mfa-panel">
                                        <div class="mfa-steps">
                                            <p>{{ 'profile.mfa_step1' | t }}</p>
                                            <p>{{ 'profile.mfa_step2' | t }}</p>
                                        </div>

                                        <div>
                                            <label class="block font-medium mb-2">{{ 'profile.mfa_current_code' | t }}</label>
                                            <p-inputotp [(ngModel)]="disableMfaCode" [length]="6" styleClass="w-full justify-center">
                                                <ng-template #input let-token let-events="events" let-index="index">
                                                    <input
                                                        type="text"
                                                        inputmode="numeric"
                                                        autocomplete="one-time-code"
                                                        [maxLength]="1"
                                                        (input)="events.input($event)"
                                                        (keydown)="events.keydown($event)"
                                                        [attr.value]="token"
                                                        class="mfa-otp-input"
                                                    />
                                                      <div *ngIf="index === 3" class="mfa-otp-separator">
                                                        <i class="pi pi-minus"></i>
                                                      </div>
                                                </ng-template>
                                            </p-inputotp>
                                        </div>

                                        <div class="flex gap-3">
                                            <button
                                                au-btn variant="primary"
                                                class="flex-1"
                                                [icon]="'pi pi-lock-open'"
                                                (click)="disableMfa()"
                                                [loading]="disablingMfa()"
                                                [disabled]="!isValidDisableMfaCode()"
                                            >{{ 'profile.mfa_confirm_deactivate' | t }}</button>
                                            <button
                                                au-btn
                                                type="button"
                                                variant="secondary"
                                                [icon]="'pi pi-times'"
                                                (click)="cancelDisableMfa()"
                                                [disabled]="disablingMfa()"
                                            >{{ 'profile.cancel' | t }}</button>
                                        </div>
                                    </div>
                                }
                            } @else {
                                <div class="mfa-status">
                                    <i class="pi pi-mobile"></i>
                                    <div>
                                        <strong>{{ 'profile.mfa_inactive_title' | t }}</strong>
                                        <p>{{ 'profile.mfa_inactive_desc' | t }}</p>
                                    </div>
                                </div>

                                @if (!mfaQrCode) {
                                    <button
                                        au-btn variant="primary"
                                        class="w-full"
                                        [icon]="'pi pi-qrcode'"
                                        (click)="startMfaSetup()"
                                        [loading]="settingUpMfa()"
                                    >{{ 'profile.mfa_setup_btn' | t }}</button>
                                }

                                @if (mfaQrCode) {
                                    <div class="mfa-panel">
                                        <div class="mfa-steps">
                                            <p>{{ 'profile.mfa_qr_step1' | t }}</p>
                                            <p>{{ 'profile.mfa_qr_step2' | t }}</p>
                                            <p>{{ 'profile.mfa_qr_step3' | t }}</p>
                                        </div>

                                        <div class="mfa-qr-wrap">
                                            <img class="mfa-qr" [src]="'data:image/png;base64,' + mfaQrCode" [alt]="'profile.mfa_title' | t" />
                                        </div>

                                        <div class="mfa-secret-box">
                                            <span>{{ 'profile.mfa_manual_key' | t }}</span>
                                            <div style="display:flex;align-items:center;gap:0.5rem">
                                                <code>{{ showMfaSecret() ? mfaSecret : '••••••••••' }}</code>
                                                <button type="button" au-btn variant="ghost" [icon]="'pi ' + (showMfaSecret() ? 'pi-eye-slash' : 'pi-eye')" (click)="showMfaSecret.set(!showMfaSecret())" style="width:2rem;height:2rem" [iconOnly]="true"></button>
                                            </div>
                                        </div>

                                        <div>
                                            <label class="block font-medium mb-2">{{ 'profile.mfa_code' | t }}</label>
                                            <p-inputotp [(ngModel)]="mfaCode" [length]="6" styleClass="w-full justify-center">
                                                <ng-template #input let-token let-events="events" let-index="index">
                                                    <input
                                                        type="text"
                                                        inputmode="numeric"
                                                        autocomplete="one-time-code"
                                                        [maxLength]="1"
                                                        (input)="events.input($event)"
                                                        (keydown)="events.keydown($event)"
                                                        [attr.value]="token"
                                                        class="mfa-otp-input"
                                                    />
                                                      <div *ngIf="index === 3" class="mfa-otp-separator">
                                                        <i class="pi pi-minus"></i>
                                                      </div>
                                                </ng-template>
                                            </p-inputotp>
                                        </div>

                                        <div class="flex gap-3">
                                            <button
                                                au-btn variant="primary"
                                                class="flex-1"
                                                [icon]="'pi pi-check'"
                                                (click)="confirmMfaSetup()"
                                                [loading]="verifyingMfa()"
                                                [disabled]="!isValidMfaCode()"
                                            >{{ 'profile.confirm' | t }}</button>
                                            <button
                                                au-btn
                                                type="button"
                                                variant="secondary"
                                                [icon]="'pi pi-times'"
                                                (click)="resetMfaSetup()"
                                                [disabled]="verifyingMfa()"
                                            >{{ 'profile.cancel' | t }}</button>
                                        </div>
                                    </div>
                                }
                            }
                        </div>
                    </p-card>

                    <p-card>
                        <div class="space-y-3">
                            <h3 class="section-title !mb-0">{{ 'profile.quick_actions' | t }}</h3>
                            <button au-btn variant="secondary" class="w-full" [icon]="'pi pi-key'" (click)="goToChangePassword()">{{ 'profile.change_password_btn' | t }}</button>
                            <button au-btn variant="secondary" class="w-full" [icon]="'pi pi-question-circle'" (click)="goToHelp()">{{ 'profile.help_center_btn' | t }}</button>
                        </div>
                    </p-card>

                    @if (canAccessWhatsApp) {
                        <p-card>
                            <div class="space-y-3">
                                <h3 class="section-title !mb-0">{{ 'profile.notifications_title' | t }}</h3>
                                <div class="flex items-center gap-3">
                                    <p-checkbox
                                        [(ngModel)]="whatsappEnabled"
                                        [binary]="true"
                                        inputId="whatsapp-toggle"
                                        (onChange)="toggleWhatsApp()"
                                    />
                                    <label for="whatsapp-toggle" class="cursor-pointer font-medium">
                                        {{ 'profile.whatsapp_notifications' | t }}
                                    </label>
                                </div>
                                <p class="text-sm text-surface-500">{{ 'profile.whatsapp_hint' | t }}</p>
                            </div>
                        </p-card>
                    }
                </div>
            </div>
        </div>
    `,
    styles: [`
        .profile-page {
            background: linear-gradient(180deg, rgba(26,86,219,0.06) 0%, rgba(26,86,219,0.02) 35%, transparent 100%);
            min-height: calc(100vh - 7rem);
            border-radius: 1rem;
        }

        .profile-hero {
            border: 1px solid var(--surface-border);
            background: var(--surface-card);
            border-radius: 1rem;
            padding: 1.25rem;
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            flex-wrap: wrap;
        }

        .profile-hero__left {
            display: flex;
            gap: 1rem;
            align-items: center;
        }

        .profile-avatar {
            width: 4.5rem;
            height: 4.5rem;
            border-radius: 999px;
            background: linear-gradient(135deg, var(--brand), var(--brand-400));
            color: #fff;
            display: grid;
            place-items: center;
            font-weight: 700;
            font-size: 1.1rem;
            overflow: hidden;
            flex-shrink: 0;
        }

        .profile-avatar.has-image {
            background: transparent;
        }

        .profile-avatar img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .profile-name {
            font-weight: 600;
            font-size: 1.05rem;
            margin: 0;
            color: var(--text-color);
        }

        .profile-meta {
            margin: 0.25rem 0 0;
            color: var(--text-color-secondary);
            font-size: 0.92rem;
        }

        .profile-hero__right {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.75rem;
            min-width: 280px;
        }

        .stat-chip {
            border: 1px solid var(--surface-border);
            border-radius: 0.75rem;
            padding: 0.75rem;
            display: flex;
            gap: 0.6rem;
            align-items: center;
            background: var(--surface-ground);
        }

        .stat-label {
            margin: 0;
            color: var(--text-color-secondary);
            font-size: 0.78rem;
        }

        .stat-value {
            margin: 0.15rem 0 0;
            color: var(--text-color);
            font-weight: 600;
            font-size: 0.95rem;
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
            font-size: 0.9rem;
        }

        .summary-row {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            align-items: center;
            padding: 0.6rem 0;
            border-bottom: 1px dashed var(--surface-border);
        }

        .summary-row:last-child {
            border-bottom: 0;
            padding-bottom: 0;
        }

        .mfa-status {
            display: flex;
            gap: 0.75rem;
            align-items: flex-start;
            padding: 0.9rem;
            border-radius: 0.9rem;
            border: 1px solid var(--surface-border);
            background: var(--surface-ground);
        }

        .mfa-status i {
            margin-top: 0.15rem;
            color: #0f766e;
        }

        .mfa-status strong,
        .mfa-status p {
            display: block;
            margin: 0;
        }

        .mfa-status p {
            color: var(--text-color-secondary);
            font-size: 0.9rem;
            margin-top: 0.2rem;
        }

        .mfa-status--active {
            border-color: rgba(22, 163, 74, 0.25);
            background: rgba(22, 163, 74, 0.08);
        }

        .mfa-panel {
            display: grid;
            gap: 1rem;
            padding-top: 0.25rem;
        }

        .mfa-steps {
            display: grid;
            gap: 0.35rem;
            color: var(--text-color-secondary);
            font-size: 0.92rem;
        }

        .mfa-steps p {
            margin: 0;
        }

        .mfa-qr-wrap {
            display: flex;
            justify-content: center;
            padding: 1rem;
            border-radius: 1rem;
            background: #ffffff;
            border: 1px solid var(--surface-border);
        }

        .mfa-qr {
            width: 12rem;
            height: 12rem;
            object-fit: contain;
        }

        .mfa-secret-box {
            display: grid;
            gap: 0.35rem;
            padding: 0.85rem 1rem;
            border-radius: 0.9rem;
            border: 1px dashed var(--surface-border);
            background: var(--surface-ground);
        }

        .mfa-secret-box span {
            color: var(--text-color-secondary);
            font-size: 0.85rem;
        }

        .mfa-secret-box code {
            word-break: break-all;
            font-size: 0.92rem;
            color: var(--text-color);
        }

        .mfa-otp-input {
            width: 2.75rem;
            height: 3.25rem;
            text-align: center;
            font-size: 1.15rem;
            font-weight: 700;
            border-radius: 0.9rem;
            border: 1px solid var(--surface-border);
            background: var(--surface-card);
            color: var(--text-color);
            outline: none;
            transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
        }

        .mfa-otp-input:focus {
            border-color: var(--brand);
            box-shadow: 0 0 0 0.2rem color-mix(in srgb, var(--brand) 18%, transparent);
            transform: translateY(-1px);
        }

        .cancelled-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.3rem 0.65rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            background: #fef3c7;
            color: #92400e;
            margin-top: 0.25rem;
        }
        :host-context(.app-dark) .cancelled-badge {
            background: rgba(251, 191, 36, 0.12);
            color: #fbbf24;
        }
        .mfa-otp-separator {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 0 0.5rem;
            color: var(--text-color-secondary);
        }

        @media (max-width: 767px) {
            .profile-hero__right {
                grid-template-columns: 1fr;
                min-width: 100%;
            }
        }
    `]
})
export class UserProfileComponent implements OnInit {
    protected localeService = inject(LocaleService);

    t(key: string): string {
        return this.localeService.t(key as any);
    }

    user: any = {
        id: null,
        full_name: '',
        email: '',
        phone: '',
        role: '',
        is_active: true,
        mfa_enabled: false,
        roles: [],
        tenant_id: null,
        date_joined: null
    };
    saving = signal(false);
    uploadingAvatar = signal(false);
    settingUpMfa = signal(false);
    showMfaSecret = signal(false);
    verifyingMfa = signal(false);
    disablingMfa = signal(false);
    mfaQrCode: string | null = null;
    mfaSecret: string | null = null;
    mfaCode = '';
    showDisableMfa = false;
    disableMfaCode = '';
    subscriptionStatus: any = null;
    currentSubscription: any = null;
    cancelling = false;
    currentTenant: any = null;

    constructor(
        private authService: AuthService,
        private messageService: MessageService,
        private http: HttpClient,
        private router: Router,
        private subscriptionService: SubscriptionService,
        private tenantService: TenantService,
        private confirmationService: ConfirmationService,
        private destroyRef: DestroyRef
    ) {}

    ngOnInit() {
        const currentUser = this.authService.getCurrentUser();
        if (currentUser) {
            this.user = { ...currentUser };
            this.loadFullProfile();
        }
        this.loadSubscriptionStatus();
        this.loadCurrentSubscription();
        this.loadCurrentTenant();
        this.loadNotificationPreferences();
    }

    loadFullProfile(): void {
        if (!this.user?.id) return;

        const url = `${environment.apiUrl}/auth/users/${this.user.id}/`;
        this.http.get<any>(url).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (profile) => {
                this.user = {
                    ...this.user,
                    ...profile,
                    tenant_id: profile?.tenant ?? this.user?.tenant_id ?? null
                };
                this.authService.patchCurrentUser(this.user);
            },
            error: () => {
                // fallback silencioso a datos de sesión
            }
        });
    }

    saveProfile() {
        this.saving.set(true);
        const url = `${environment.apiUrl}/auth/users/${this.user.id}/`;
        
        this.http.patch(url, {
            full_name: this.user.full_name,
            email: this.user.email,
            phone: this.user.phone
        }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (updated: any) => {
                this.user = {
                    ...this.user,
                    ...updated,
                    tenant_id: updated?.tenant ?? this.user?.tenant_id ?? null
                };
                this.authService.patchCurrentUser(this.user);
                this.messageService.add({
                    severity: 'success',
                    summary: this.t('common.success'),
                    detail: this.t('profile.save_success')
                });
                this.saving.set(false);
            },
            error: (err) => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.t('common.error'),
                    detail: err.error?.error || this.t('profile.toast.save_error')
                });
                this.saving.set(false);
            }
        });
    }

    onAvatarSelected(event: Event): void {
        const input = event.target as HTMLInputElement;
        const file = input?.files?.[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('avatar', file);

        this.uploadingAvatar.set(true);
        const url = `${environment.apiUrl}/auth/users/me/avatar/`;
        this.http.post<any>(url, formData).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (response) => {
                this.user = {
                    ...this.user,
                    avatar_url: response?.avatar_url || null
                };
                this.authService.patchCurrentUser(this.user);
                this.messageService.add({
                    severity: 'success',
                    summary: this.t('common.success'),
                    detail: this.t('profile.toast.avatar_success')
                });
                this.uploadingAvatar.set(false);
                input.value = '';
            },
            error: (err) => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.t('common.error'),
                    detail: err?.error?.error || this.t('profile.toast.avatar_error')
                });
                this.uploadingAvatar.set(false);
                input.value = '';
            }
        });
    }

    getInitials(value: string): string {
        if (!value) return 'U';
        const parts = value.trim().split(/\s+/).filter(Boolean);
        if (parts.length === 1) {
            return parts[0].slice(0, 2).toUpperCase();
        }
        return `${parts[0][0] || ''}${parts[1][0] || ''}`.toUpperCase();
    }

    getRoleDisplayName(role: string): string {
        return getRoleDisplayLabel(role);
    }

    get expiryDate(): string | null {
        const status = String(this.subscriptionStatus?.current_status || '').toLowerCase();
        const trialEnd = this.currentTenant?.trial_end_date;
        if ((status === 'trial' || status === 'suspended') && trialEnd) {
            return this.formatDate(trialEnd);
        }
        if (this.currentTenant?.access_until) {
            return this.formatDate(this.currentTenant.access_until);
        }
        return null;
    }

    get expiryLabel(): string {
        const status = String(this.subscriptionStatus?.current_status || '').toLowerCase();
        const trialEnd = this.currentTenant?.trial_end_date;
        if (trialEnd && (status === 'trial' || status === 'suspended')) {
            const now = new Date();
            const trialDate = new Date(trialEnd);
            if (trialDate < now) {
                return this.t('profile.trial_ended');
            }
            return this.t('profile.trial_ends');
        }
        return this.t('profile.access_until');
    }

    getProfileImageUrl(): string | null {
        const rawUrl = this.user?.avatar_url || this.user?.profile_image || this.user?.photo || null;
        if (!rawUrl) return null;
        if (/^https?:\/\//i.test(rawUrl)) return rawUrl;

        const apiOrigin = new URL(environment.apiUrl).origin;
        return rawUrl.startsWith('/') ? `${apiOrigin}${rawUrl}` : `${apiOrigin}/${rawUrl}`;
    }

    getTenantDisplay(): string {
        const tenantName = this.user?.tenant_name;
        if (tenantName) return tenantName;

        const tenantId = this.user?.tenant_id;
        if (tenantId) {
            const localTenantName = (() => {
                try {
                    return JSON.parse(safeGetItem('tenant') || '{}')?.name;
                } catch {
                    return null;
                }
            })();
            return localTenantName || `#${tenantId}`;
        }

        return 'N/A';
    }

    formatDate(value: string | null | undefined): string {
        if (!value) return this.t('profile.date.fallback');
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return this.t('profile.date.fallback');
        return this.localeService.formatDate(date, {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
        });
    }

    goToChangePassword(): void {
        this.router.navigate(['/client/change-password']);
    }

    goToHelp(): void {
        this.router.navigate(['/client/help']);
    }

    goToPayment(): void {
        this.router.navigate(['/client/payment']);
    }

    getCurrentPlanName(): string {
        if (this.currentTenant?.subscription_plan?.display_name || this.currentTenant?.subscription_plan?.name || this.currentTenant?.plan_type) {
            return getSubscriptionPlanLabel(
                this.currentTenant?.subscription_plan?.display_name,
                this.currentTenant?.subscription_plan?.name,
                this.currentTenant?.plan_type
            );
        }

        if (this.subscriptionStatus?.plan_display) {
            return getSubscriptionPlanLabel(this.subscriptionStatus.plan_display);
        }

        try {
            const tenant = JSON.parse(safeGetItem('tenant') || '{}');
            return getSubscriptionPlanLabel(
                tenant?.subscription_plan?.display_name,
                tenant?.subscription_plan?.name,
                tenant?.plan_type,
                this.t('profile.plan.fallback')
            );
        } catch {
            return this.t('profile.plan.fallback');
        }
    }

    getCurrentPlanStatusText(): string {
        const status = String(this.subscriptionStatus?.current_status || '').toLowerCase();
        const graceDays = Number(this.subscriptionStatus?.days_in_grace || 0);

        if (status === 'active') return this.t('profile.plan.active');
        if (graceDays > 0) return this.t('profile.plan.grace').replace('{days}', String(graceDays));
        if (status === 'trial') return this.t('profile.plan.trial');
        if (status) return status;
        return this.t('profile.status.fallback');
    }

    getCurrentPlanCopy(): string {
        const status = String(this.subscriptionStatus?.current_status || '').toLowerCase();
        const graceDays = Number(this.subscriptionStatus?.days_in_grace || 0);

        if (status === 'active') {
            return this.t('profile.plan.copy_active');
        }

        if (graceDays > 0) {
            return this.t('profile.plan.copy_grace').replace('{days}', String(graceDays));
        }

        if (status === 'trial') {
            return this.t('profile.plan.copy_trial');
        }

        return this.t('profile.plan.copy_fallback');
    }

    startMfaSetup(): void {
        this.settingUpMfa.set(true);
        this.authService.setupMfa().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (response) => {
                this.mfaQrCode = response.qr_code;
                this.mfaSecret = response.secret;
                this.mfaCode = '';
                this.showDisableMfa = false;
                this.disableMfaCode = '';
                this.settingUpMfa.set(false);
                this.messageService.add({
                    severity: 'info',
                    summary: this.t('profile.mfa.setup_info'),
                    detail: this.t('profile.mfa.setup_detail')
                });
            },
            error: (err) => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.t('common.error'),
                    detail: err?.error?.error || this.t('profile.mfa.setup_error')
                });
                this.settingUpMfa.set(false);
            }
        });
    }

    confirmMfaSetup(): void {
        if (!this.isValidMfaCode()) return;

        this.verifyingMfa.set(true);
        this.authService.verifyMfa({ code: this.mfaCode.trim() }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: () => {
                this.user = { ...this.user, mfa_enabled: true };
                this.authService.patchCurrentUser({ mfa_enabled: true } as any);
                this.resetMfaSetup();
                this.verifyingMfa.set(false);
                this.messageService.add({
                    severity: 'success',
                    summary: this.t('profile.mfa.activated'),
                    detail: this.t('profile.mfa.activated_detail')
                });
            },
            error: (err) => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.t('profile.mfa.invalid_code'),
                    detail: err?.error?.error || this.t('profile.mfa.invalid_code_detail')
                });
                this.verifyingMfa.set(false);
            }
        });
    }

    resetMfaSetup(): void {
        this.mfaQrCode = null;
        this.mfaSecret = null;
        this.mfaCode = '';
    }

    isValidMfaCode(): boolean {
        return /^\d{6}$/.test(this.mfaCode.trim());
    }

    openDisableMfa(): void {
        this.showDisableMfa = true;
        this.disableMfaCode = '';
    }

    cancelDisableMfa(): void {
        this.showDisableMfa = false;
        this.disableMfaCode = '';
    }

    disableMfa(): void {
        if (!this.isValidDisableMfaCode()) return;

        this.disablingMfa.set(true);
        this.authService.disableMfa({ code: this.disableMfaCode.trim() }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: () => {
                this.user = { ...this.user, mfa_enabled: false };
                this.authService.patchCurrentUser({ mfa_enabled: false } as any);
                this.cancelDisableMfa();
                this.resetMfaSetup();
                this.disablingMfa.set(false);
                this.messageService.add({
                    severity: 'success',
                    summary: this.t('profile.mfa.disabled'),
                    detail: this.t('profile.mfa.disabled_detail')
                });
            },
            error: (err) => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.t('profile.mfa.disable_error_title'),
                    detail: err?.error?.error || this.t('profile.mfa.disable_error')
                });
                this.disablingMfa.set(false);
            }
        });
    }

    isValidDisableMfaCode(): boolean {
        return /^\d{6}$/.test(this.disableMfaCode.trim());
    }

    canCancelSubscription(): boolean {
        const role = this.user?.role || '';
        return ['owner', 'manager'].includes(role);
    }

    private loadCurrentSubscription(): void {
        this.subscriptionService.getUserSubscriptions().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (data: any) => {
                const subs = Array.isArray(data) ? data : (data.results || []);
                if (subs.length > 0) {
                    this.currentSubscription = subs[0];
                }
            },
            error: () => {
                this.currentSubscription = null;
            }
        });
    }

    confirmCancel() {
        this.confirmationService.confirm({
            message: this.t('profile.sub.cancel_confirm'),
            header: this.t('profile.sub.cancel_title'),
            icon: 'pi pi-exclamation-triangle',
            acceptLabel: this.t('profile.sub.cancel_btn_confirm'),
            rejectLabel: this.t('profile.sub.cancel_btn_keep'),
            acceptButtonStyleClass: 'p-button-danger',
            accept: () => this.cancel(),
        });
    }

    cancel() {
        if (!this.currentSubscription?.id || this.cancelling) return;
        this.cancelling = true;
        this.subscriptionService.cancelUserSubscription(this.currentSubscription.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (res: any) => {
                this.messageService.add({
                    severity: 'success',
                    summary: this.t('profile.sub.cancel_success'),
                    detail: res.note || this.t('profile.sub.cancel_success_detail')
                });
                this.currentSubscription.is_cancelled = true;
                this.currentSubscription.access_until = res.access_until;
                this.cancelling = false;
            },
            error: (err: any) => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.t('common.error'),
                    detail: err.error?.detail || this.t('profile.sub.cancel_error')
                });
                this.cancelling = false;
            }
        });
    }

    reactivate() {
        if (!this.currentSubscription?.id) return;
        this.subscriptionService.reactivateUserSubscription(this.currentSubscription.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: () => {
                this.messageService.add({
                    severity: 'success',
                    summary: this.t('profile.sub.reactivate_success'),
                    detail: this.t('profile.sub.reactivate_success_detail')
                });
                this.currentSubscription.is_cancelled = false;
                this.currentSubscription.cancelled_at = null;
            },
            error: (err: any) => {
                this.messageService.add({
                    severity: 'error',
                    summary: this.t('common.error'),
                    detail: err.error?.detail || this.t('profile.sub.reactivate_error')
                });
            }
        });
    }

    private loadSubscriptionStatus(): void {
        this.subscriptionService.getSubscriptionStatus().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (status) => {
                this.subscriptionStatus = status;
            },
            error: () => {
                this.subscriptionStatus = null;
            }
        });
    }

    private loadCurrentTenant(): void {
        this.tenantService.getCurrentTenant().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (tenant) => {
                this.currentTenant = tenant;
            },
            error: () => {
                this.currentTenant = null;
            }
        });
    }

    planAccess = inject(PlanAccessService);
    whatsappEnabled = signal(false);

    get canAccessWhatsApp(): boolean {
        return this.planAccess.canAccessFeature('whatsapp_notifications');
    }

    private loadNotificationPreferences(): void {
        const url = `${environment.apiUrl}/notifications/preferences/`;
        this.http.get<any>(url).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (prefs) => {
                this.whatsappEnabled.set(prefs.whatsapp_enabled ?? false);
            },
            error: () => {
                this.whatsappEnabled.set(false);
            }
        });
    }

    toggleWhatsApp(): void {
        const url = `${environment.apiUrl}/notifications/preferences/`;
        const enabled = this.whatsappEnabled();
        this.http.patch(url, { whatsapp_enabled: enabled }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: () => {
                this.messageService.add({
                    severity: 'success',
                    summary: enabled ? 'WhatsApp activado' : 'WhatsApp desactivado',
                    detail: enabled
                        ? 'Recibirás notificaciones por WhatsApp.'
                        : 'Notificaciones por WhatsApp desactivadas.'
                });
            },
            error: () => {
                this.whatsappEnabled.update(v => !v);
                this.messageService.add({
                    severity: 'error',
                    summary: 'Error',
                    detail: 'No se pudo actualizar la preferencia. Verifica que tu plan incluya WhatsApp.'
                });
            }
        });
    }
}
