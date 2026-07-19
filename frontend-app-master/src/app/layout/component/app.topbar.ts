import { Component, OnInit, OnDestroy, ViewChild, HostListener } from '@angular/core';
import { MenuItem } from 'primeng/api';
import { RouterModule, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { StyleClassModule } from 'primeng/styleclass';
import { MenuModule } from 'primeng/menu';
import { Menu } from 'primeng/menu';
import { BadgeModule } from 'primeng/badge';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ConfirmationService } from 'primeng/api';
import { LayoutService } from '../service/layout.service';
import { AuthService } from '../../core/services/auth/auth.service';
import { MessageService } from 'primeng/api';
import { AppConfigService } from '../../core/services/app-config.service';
import { NotificationService } from '../../core/services/notification/notification.service';
import { NotificationBadgeService } from '../../core/services/notification/notification-badge.service';
import { LocaleService } from '../../core/services/locale/locale.service';
import { Subscription } from 'rxjs';
import { OnboardingTourService } from '../../shared/onboarding/onboarding-tour.service';
import { environment } from '../../../environments/environment';
import { roleKey } from '../../core/utils/role-normalizer';
import { BarbershopSettingsService } from '../../shared/services/barbershop-settings.service';
import { FormsModule } from '@angular/forms';
import { SelectModule } from 'primeng/select';
import { BranchService, Branch } from '../../core/services/branch/branch.service';
import { PlanAccessService } from '../../core/services/plan-access.service';

@Component({
    selector: 'app-topbar',
    standalone: true,
    imports: [RouterModule, CommonModule, StyleClassModule, MenuModule, BadgeModule, ConfirmDialogModule, FormsModule, SelectModule],
    providers: [ConfirmationService],
    template: `<div class="layout-topbar">
        <div class="layout-topbar-logo-container">
            <button class="layout-menu-button layout-topbar-action" (click)="layoutService.onMenuToggle()">
                <i class="pi pi-bars"></i>
            </button>
            <a class="layout-topbar-logo" [routerLink]="getDashboardRoute()" style="cursor: pointer;">
                <span class="topbar-brand-mark">
                    <img [src]="tenantLogoUrl" [alt]="tenantLabel">
                </span>
                <div class="topbar-brand-copy">
                    <strong>{{ tenantLabel }}</strong>
                    <small>{{ getWorkspaceLabel() }}</small>
                </div>
            </a>
        </div>

        <button type="button" class="layout-topbar-search" (click)="openCommandBar($event)">
            <i class="pi pi-search"></i>
            <span>{{ t('common.search') }}, navegar o ejecutar</span>
            <kbd>Ctrl K</kbd>
        </button>

        @if (showBranchSelector) {
            <div class="branch-selector-container">
                <p-select 
                    [options]="branchService.branches()" 
                    [(ngModel)]="selectedBranch" 
                    optionLabel="name" 
                    placeholder="Seleccionar sucursal"
                    [style]="{'min-width': '180px', 'background': 'rgba(255,255,255,0.05)', 'border-color': 'rgba(255,255,255,0.1)', 'backdrop-filter': 'blur(10px)'}"
                    class="branch-dropdown-glass">
                </p-select>
            </div>
        }

        <p-menu #quickSearchMenu [model]="quickSearchItems" [popup]="true" [style]="{'width': '320px'}"></p-menu>

        <div class="layout-topbar-actions">
            <div class="activity-center">
                <button type="button" class="layout-topbar-action p-overlay-badge" (click)="toggleActivityCenter($event)">
                    <i class="pi pi-bell"></i>
                    @if (activityCount() > 0) {
                        <p-badge [value]="activityCount().toString()" severity="danger"></p-badge>
                    }
                </button>

                @if (activityPanelOpen) {
                    <div class="activity-center-panel">
                        <div class="activity-center-panel__header">
                            <div>
                                <div class="activity-center-panel__eyebrow">{{ t('activity.center_title') }}</div>
                                <div class="activity-center-panel__title">{{ t('activity.center_subtitle') }}</div>
                            </div>
                            @if (notificationService.saleCount() > 0) {
                                <button type="button" class="activity-center-panel__link" (click)="markAllAsRead()">{{ t('activity.mark_sales_read') }}</button>
                            }
                        </div>

                        <div class="activity-center-panel__summary">
                            <div class="activity-center-summary-card">
                                <span class="activity-center-summary-card__label">{{ t('activity.summary_appointments_today') }}</span>
                                <strong>{{ appointmentBadgeService.todayAppointments().length }}</strong>
                            </div>
                            <div class="activity-center-summary-card">
                                <span class="activity-center-summary-card__label">{{ t('activity.summary_pending') }}</span>
                                <strong>{{ appointmentBadgeService.overdueAppointments().length }}</strong>
                            </div>
                            <div class="activity-center-summary-card">
                                <span class="activity-center-summary-card__label">{{ t('activity.summary_new_sales') }}</span>
                                <strong>{{ notificationService.saleCount() }}</strong>
                            </div>
                        </div>

                        <div class="activity-center-section">
                            <div class="activity-center-section__head">
                                <span>{{ t('activity.section_appointments') }}</span>
                                <button type="button" class="activity-center-panel__link" (click)="goToAppointments()">{{ t('activity.open_agenda') }}</button>
                            </div>

                            @if (activityAppointments().length > 0) {
                                <div class="activity-center-list">
                                    @for (appointment of activityAppointments(); track appointment.id) {
                                        <button type="button" class="activity-center-item" (click)="goToAppointments()">
                                            <div class="activity-center-item__icon appointment">
                                                <i class="pi" [ngClass]="appointment.kind === 'overdue' ? 'pi-clock' : 'pi-calendar'"></i>
                                            </div>
                                            <div class="activity-center-item__body">
                                                <div class="activity-center-item__title">{{ appointment.client }}</div>
                                                <div class="activity-center-item__meta">{{ appointment.time }} · {{ appointment.service }}</div>
                                            </div>
                                            <span class="activity-center-item__tag" [class.urgent]="appointment.kind === 'overdue'">
                                                {{ appointment.kind === 'overdue' ? t('activity.tag_urgent') : appointment.kind === 'upcoming' ? t('activity.tag_upcoming') : t('activity.tag_today') }}
                                            </span>
                                        </button>
                                    }
                                </div>
                            } @else {
                                <div class="activity-center-empty">{{ t('activity.no_appointments') }}</div>
                            }
                        </div>

                        <div class="activity-center-section">
                            <div class="activity-center-section__head">
                                <span>{{ t('activity.section_sales') }}</span>
                            </div>

                            @if (recentSales().length > 0) {
                                <div class="activity-center-list">
                                    @for (sale of recentSales(); track sale.id) {
                                        <button type="button" class="activity-center-item" (click)="markSaleAsRead(sale.id)">
                                            <div class="activity-center-item__icon sale">
                                                <i class="pi pi-dollar"></i>
                                            </div>
                                            <div class="activity-center-item__body">
                                                <div class="activity-center-item__title">{{ sale.title }}</div>
                                                <div class="activity-center-item__meta">{{ sale.message }}</div>
                                            </div>
                                            <span class="activity-center-item__time">{{ notificationService.getRelativeTime(sale.created_at) }}</span>
                                        </button>
                                    }
                                </div>
                            } @else {
                                <div class="activity-center-empty">{{ t('activity.no_sales') }}</div>
                            }
                        </div>
                    </div>
                }
            </div>

            <div class="layout-config-menu">
                <button type="button" class="layout-topbar-action" (click)="startOnboardingTour()" title="Recorrido guiado">
                    <i class="pi pi-compass"></i>
                </button>
                <button type="button" class="layout-topbar-action" (click)="toggleDarkMode()">
                    <i [ngClass]="{ 'pi': true, 'pi-moon': layoutService.isDarkTheme(), 'pi-sun': !layoutService.isDarkTheme() }"></i>
                </button>

                <div class="language-center">
                    <button type="button" class="layout-topbar-action language-toggle" (click)="toggleLanguagePanel($event)" [title]="localeService.getLanguageLabel()">
                        <i class="pi pi-language language-toggle__icon"></i>
                    </button>
 
                    @if (languagePanelOpen) {
                        <div class="language-panel" (click)="$event.stopPropagation()">
                            <div class="language-panel__header">
                                <div>
                                    <div class="language-panel__eyebrow">{{ t('language.panel_eyebrow') }}</div>
                                    <div class="language-panel__title">{{ t('language.panel_title') }}</div>
                                </div>
                                <span class="language-panel__current">{{ localeService.getCurrentLanguageOption().shortLabel }}</span>
                            </div>
 
                            <div class="language-panel__list">
                                @for (language of localeService.getLanguageOptions(); track language.code) {
                                    <button
                                        type="button"
                                        class="language-option"
                                        [class.active]="localeService.getCurrentLanguage() === language.code"
                                        (click)="changeLanguage(language.code)"
                                    >
                                        <div class="language-option__icon">{{ language.icon }}</div>
                                        <div class="language-option__body">
                                            <div class="language-option__title">{{ language.nativeLabel }}</div>
                                            <div class="language-option__meta">{{ language.label }} · {{ language.region }}</div>
                                        </div>
                                        @if (localeService.getCurrentLanguage() === language.code) {
                                            <i class="pi pi-check language-option__check"></i>
                                        } @else {
                                            <span class="language-option__code">{{ language.shortLabel }}</span>
                                        }
                                    </button>
                                }
                            </div>
                        </div>
                    }
                </div>
            </div>

            <button class="layout-topbar-menu-button layout-topbar-action" pStyleClass="@next" enterFromClass="hidden" enterActiveClass="animate-scalein" leaveToClass="hidden" leaveActiveClass="animate-fadeout" [hideOnOutsideClick]="true">
                <i class="pi pi-ellipsis-v"></i>
            </button>

            <div class="layout-topbar-menu hidden lg:block">
                <button type="button" class="layout-topbar-action layout-topbar-user" (click)="userMenu.toggle($event)" [title]="getUserDisplayName()">
                    <div class="topbar-user-avatar" [class.has-image]="!!getUserAvatarUrl()">
                        @if (getUserAvatarUrl(); as avatarUrl) {
                            <img [src]="avatarUrl" alt="Avatar de usuario" />
                        } @else {
                            <strong>{{ getUserInitials() }}</strong>
                        }
                    </div>
                    <span>{{ localeService.t('topbar.profile') }}</span>
                </button>
                <p-menu #userMenu [model]="userMenuItems" [popup]="true"></p-menu>
            </div>
        </div>
        <p-confirmDialog [closable]="false" [closeOnEscape]="false" [dismissableMask]="false"></p-confirmDialog>
    </div>`,
    styles: [`
        .layout-topbar-user {
            overflow: hidden;
        }

        .activity-center {
            position: relative;
        }

        .language-center {
            position: relative;
        }

        .activity-center-panel {
            position: absolute;
            top: calc(100% + 0.9rem);
            right: 0;
            width: min(30rem, calc(100vw - 2rem));
            border-radius: 1.5rem;
            border: 1px solid var(--surface-border);
            background: color-mix(in srgb, var(--surface-card) 94%, transparent);
            box-shadow: 0 24px 70px color-mix(in srgb, var(--surface-900) 18%, transparent);
            backdrop-filter: blur(18px);
            padding: 1rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
            z-index: 40;
        }

        :host-context(.app-dark) .activity-center-panel {
            background: var(--surface-card);
            backdrop-filter: none;
            box-shadow: 0 24px 70px rgba(0, 0, 0, 0.5);
        }

        .activity-center-panel__header {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            align-items: flex-start;
        }

        .activity-center-panel__eyebrow {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--text-color-secondary);
            font-weight: 700;
            margin-bottom: 0.2rem;
        }

        .activity-center-panel__title {
            font-size: 1rem;
            font-weight: 700;
            color: var(--text-color);
        }

        .activity-center-panel__link {
            border: 0;
            background: transparent;
            color: var(--brand);
            font-size: 0.82rem;
            font-weight: 700;
            cursor: pointer;
            padding: 0;
        }

        .activity-center-panel__summary {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.75rem;
        }

        .activity-center-summary-card {
            padding: 0.85rem 0.9rem;
            border-radius: 1rem;
            background: color-mix(in srgb, var(--surface-100) 82%, transparent);
            border: 1px solid color-mix(in srgb, var(--surface-border) 72%, transparent);
            display: flex;
            flex-direction: column;
            gap: 0.28rem;
        }

        :host-context(.app-dark) .activity-center-summary-card {
            background: var(--surface-800);
            border-color: var(--surface-700);
        }

        .activity-center-summary-card__label {
            font-size: 0.75rem;
            color: var(--text-color-secondary);
        }

        .activity-center-summary-card strong {
            font-size: 1.2rem;
            color: var(--text-color);
            font-weight: 800;
        }

        .activity-center-section {
            display: flex;
            flex-direction: column;
            gap: 0.7rem;
        }

        .activity-center-section__head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.86rem;
            font-weight: 700;
            color: var(--text-color);
        }

        .activity-center-list {
            display: flex;
            flex-direction: column;
            gap: 0.55rem;
        }

        .activity-center-item {
            display: flex;
            align-items: center;
            gap: 0.85rem;
            width: 100%;
            border: 1px solid color-mix(in srgb, var(--surface-border) 72%, transparent);
            background: color-mix(in srgb, var(--surface-50) 76%, transparent);
            border-radius: 1rem;
            padding: 0.8rem;
            cursor: pointer;
            transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
            text-align: left;
        }

        :host-context(.app-dark) .activity-center-item {
            background: var(--surface-800);
            border-color: var(--surface-700);
        }

        .activity-center-item:hover {
            transform: translateY(-1px);
            border-color: color-mix(in srgb, var(--brand) 28%, var(--surface-border));
            background: color-mix(in srgb, var(--surface-100) 76%, transparent);
        }

        :host-context(.app-dark) .activity-center-item:hover {
            background: var(--surface-700);
            border-color: var(--brand);
        }

        .activity-center-item__icon {
            width: 2.5rem;
            height: 2.5rem;
            border-radius: 0.9rem;
            display: grid;
            place-items: center;
            flex-shrink: 0;
        }

        .activity-center-item__icon.appointment {
            background: rgba(14, 165, 233, 0.12);
            color: #0284c7;
        }

        .activity-center-item__icon.sale {
            background: rgba(16, 185, 129, 0.12);
            color: #059669;
        }

        .activity-center-item__body {
            flex: 1;
            min-width: 0;
        }

        .activity-center-item__title {
            font-size: 0.9rem;
            font-weight: 700;
            color: var(--text-color);
            margin-bottom: 0.12rem;
        }

        .activity-center-item__meta {
            font-size: 0.78rem;
            color: var(--text-color-secondary);
            line-height: 1.45;
        }

        .activity-center-item__tag,
        .activity-center-item__time {
            font-size: 0.72rem;
            font-weight: 700;
            color: var(--text-color-secondary);
            flex-shrink: 0;
        }

        .activity-center-item__tag.urgent {
            color: #dc2626;
        }

        .activity-center-empty {
            border-radius: 1rem;
            border: 1px dashed color-mix(in srgb, var(--surface-border) 75%, transparent);
            padding: 0.9rem 1rem;
            font-size: 0.84rem;
            color: var(--text-color-secondary);
            background: color-mix(in srgb, var(--surface-50) 70%, transparent);
        }

        :host-context(.app-dark) .activity-center-empty {
            background: var(--surface-800);
            border-color: var(--surface-700);
        }

        .language-toggle__icon {
            font-size: 0.95rem;
            line-height: 1;
            color: inherit;
        }

        .language-panel {
            position: absolute;
            top: calc(100% + 0.9rem);
            right: 0;
            width: min(22rem, calc(100vw - 2rem));
            border-radius: 1.5rem;
            border: 1px solid var(--surface-border);
            background: color-mix(in srgb, var(--surface-card) 95%, transparent);
            box-shadow: 0 24px 70px color-mix(in srgb, var(--surface-900) 18%, transparent);
            backdrop-filter: blur(18px);
            padding: 1rem;
            z-index: 40;
            display: flex;
            flex-direction: column;
            gap: 0.9rem;
        }

        .language-panel__header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 0.8rem;
        }

        .language-panel__eyebrow {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--text-color-secondary);
            font-weight: 700;
            margin-bottom: 0.2rem;
        }

        .language-panel__title {
            font-size: 1rem;
            font-weight: 700;
            color: var(--text-color);
        }

        .language-panel__current {
            min-width: 2.4rem;
            height: 2.4rem;
            display: grid;
            place-items: center;
            border-radius: 0.95rem;
            background: color-mix(in srgb, var(--brand) 12%, var(--surface-100));
            color: var(--brand);
            font-size: 0.74rem;
            font-weight: 800;
            letter-spacing: 0.08em;
        }

        .language-panel__list {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .language-option {
            width: 100%;
            display: flex;
            align-items: center;
            gap: 0.8rem;
            padding: 0.8rem 0.85rem;
            border-radius: 1rem;
            border: 1px solid color-mix(in srgb, var(--surface-border) 74%, transparent);
            background: color-mix(in srgb, var(--surface-50) 70%, transparent);
            text-align: left;
            transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
        }

        .language-option:hover {
            transform: translateY(-1px);
            border-color: color-mix(in srgb, var(--brand) 28%, var(--surface-border));
            background: color-mix(in srgb, var(--surface-100) 76%, transparent);
        }

        .language-option.active {
            border-color: color-mix(in srgb, var(--brand) 34%, var(--surface-border));
            background: color-mix(in srgb, var(--brand) 10%, var(--surface-50));
        }

        :host-context(.app-dark) .language-panel {
            box-shadow: 0 24px 70px rgba(2, 6, 23, 0.5);
        }

        :host-context(.app-dark) .language-panel__current {
            background: color-mix(in srgb, var(--brand) 16%, var(--surface-800));
        }

        :host-context(.app-dark) .language-option {
            background: color-mix(in srgb, var(--surface-800) 70%, transparent);
            border-color: color-mix(in srgb, var(--surface-700) 74%, transparent);
        }

        :host-context(.app-dark) .language-option:hover {
            background: color-mix(in srgb, var(--surface-700) 76%, transparent);
            border-color: color-mix(in srgb, var(--brand) 28%, var(--surface-700));
        }

        :host-context(.app-dark) .language-option.active {
            background: color-mix(in srgb, var(--brand) 12%, var(--surface-800));
            border-color: color-mix(in srgb, var(--brand) 34%, var(--surface-700));
        }

        :host-context(.app-dark) .language-option__icon {
            background: color-mix(in srgb, var(--surface-700) 82%, transparent);
        }

        .language-option__icon {
            width: 2.45rem;
            height: 2.45rem;
            border-radius: 0.95rem;
            display: grid;
            place-items: center;
            background: color-mix(in srgb, var(--surface-100) 82%, transparent);
            font-size: 1.05rem;
            flex-shrink: 0;
        }

        .language-option__body {
            flex: 1;
            min-width: 0;
        }

        .language-option__title {
            font-size: 0.9rem;
            font-weight: 700;
            color: var(--text-color);
            margin-bottom: 0.1rem;
        }

        .language-option__meta {
            font-size: 0.78rem;
            color: var(--text-color-secondary);
        }

        .language-option__code,
        .language-option__check {
            color: var(--text-color-secondary);
            font-size: 0.75rem;
            font-weight: 800;
            flex-shrink: 0;
        }

        .language-option__check {
            color: var(--brand);
            font-size: 0.88rem;
        }

        .topbar-brand-mark {
            width: 2.25rem;
            height: 2.25rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 0.9rem;
            background: var(--shell-brand-mark-bg);
            overflow: hidden;
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.12);
        }

        .topbar-brand-mark img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .topbar-brand-copy {
            display: flex;
            flex-direction: column;
            line-height: 1.1;
        }

        .topbar-brand-copy strong {
            font-size: 0.98rem;
            color: var(--text-color);
            font-weight: 700;
        }

        .topbar-brand-copy small {
            font-size: 0.72rem;
            color: var(--text-color-secondary);
            letter-spacing: 0.02em;
        }

        .layout-topbar-search {
            min-width: min(38rem, 42vw);
            height: 2.85rem;
            border-radius: 999px;
            border: 1px solid var(--shell-search-border);
            background: var(--shell-search-bg);
            display: inline-flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0 1rem;
            color: var(--text-color-secondary);
            box-shadow: var(--shell-search-shadow);
            transition: all 180ms ease;
        }

        .layout-topbar-search:hover {
            border-color: var(--shell-search-border-hover);
            color: var(--text-color);
            transform: translateY(-1px);
        }

        .layout-topbar-search span {
            flex: 1;
            text-align: left;
            font-size: 0.92rem;
        }

        .layout-topbar-search kbd {
            border-radius: 999px;
            border: 1px solid var(--shell-search-kbd-border);
            padding: 0.2rem 0.55rem;
            font-size: 0.72rem;
            background: var(--shell-search-kbd-bg);
            color: var(--text-color-secondary);
        }

        .topbar-user-avatar {
            width: 2rem;
            height: 2rem;
            border-radius: 999px;
            display: grid;
            place-items: center;
            background: linear-gradient(135deg, var(--accent-600), var(--accent-500));
            color: #fff;
            font-size: 0.75rem;
            font-weight: 700;
            line-height: 1;
            overflow: hidden;
            flex-shrink: 0;
        }

        .topbar-user-avatar.has-image {
            background: transparent;
        }

        .topbar-user-avatar img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        @media (max-width: 991px) {
            .layout-topbar-search {
                display: none;
            }

            .activity-center-panel {
                right: -0.5rem;
                width: min(28rem, calc(100vw - 1.25rem));
            }
        }

        .branch-selector-container {
            display: inline-flex;
            align-items: center;
            margin-left: 0.5rem;
        }
        
        .branch-dropdown-glass {
            backdrop-filter: blur(10px);
            border-radius: 12px;
            font-size: 0.9rem;
            color: var(--text-color);
        }

        @media (max-width: 991px) {
            .topbar-brand-copy {
                display: none;
            }

            .branch-dropdown-glass {
                min-width: 140px !important;
            }
        }

        @media (max-width: 768px) {
            .layout-topbar-action {
                width: 2.25rem;
                height: 2.25rem;
            }

            .layout-topbar-action i {
                font-size: 1.1rem;
            }

            .layout-topbar-actions {
                gap: 0.5rem !important;
            }

            .branch-dropdown-glass {
                min-width: 120px !important;
            }
        }

        @media (max-width: 460px) {
            .branch-dropdown-glass {
                min-width: 90px !important;
            }

            .layout-config-menu {
                display: none !important;
            }

            .layout-topbar-actions {
                gap: 0.35rem !important;
            }
        }
    `]
})
export class AppTopbar implements OnInit, OnDestroy {
    @ViewChild('quickSearchMenu') quickSearchMenu!: Menu;
    
    userMenuItems: MenuItem[] = [];
    quickSearchItems: MenuItem[] = [];
    activityPanelOpen = false;
    languagePanelOpen = false;
    private subscription = new Subscription();
    private refreshIntervalId: ReturnType<typeof setInterval> | null = null;
    private dueAlertIntervalId: ReturnType<typeof setInterval> | null = null;
    private dueAlertActive = false;
    private cycleAlertActive = false;
    private cycleAlertSoundPlayed = false;

    constructor(
        public layoutService: LayoutService,
        public appConfig: AppConfigService,
        public notificationService: NotificationService,
        public appointmentBadgeService: NotificationBadgeService,
        public localeService: LocaleService,
        private authService: AuthService,
        private router: Router,
        private messageService: MessageService,
        private barbershopSettings: BarbershopSettingsService,
        private onboardingTourService: OnboardingTourService,
        private confirmationService: ConfirmationService,
        public branchService: BranchService,
        private planAccessService: PlanAccessService
    ) {
        this.initUserMenu();
        this.initQuickSearchMenu();
    }

    ngOnInit() {
        this.appointmentBadgeService.loadAppointments();
        
        const user = this.authService.getCurrentUser();
        const isSuperAdmin = roleKey(user?.role) === 'SUPER_ADMIN';
        if (!isSuperAdmin && this.planAccessService.canAccessFeature('multi_location')) {
            this.branchService.loadBranches().subscribe();
        }

        this.checkDueAppointmentAlerts();
        this.checkCycleCompletedAlerts();
        this.refreshIntervalId = setInterval(() => {
            this.appointmentBadgeService.refresh();
            this.checkDueAppointmentAlerts();
            this.checkCycleCompletedAlerts();
        }, 2 * 60000);

        this.dueAlertIntervalId = setInterval(() => {
            this.checkDueAppointmentAlerts();
            this.checkCycleCompletedAlerts();
        }, 30 * 1000);

        this.subscription.add(
            this.localeService.languageChanged$.subscribe(() => {
                this.initUserMenu();
                this.initQuickSearchMenu();
            })
        );
    }

    get showBranchSelector(): boolean {
        const user = this.authService.getCurrentUser();
        const isSuperAdmin = roleKey(user?.role) === 'SUPER_ADMIN';
        if (isSuperAdmin) return false;

        const isClientAdmin = roleKey(user?.role) === 'CLIENT_ADMIN';
        if (!isClientAdmin) return false;
        
        return this.planAccessService.canAccessFeature('multi_location') && this.branchService.branches().length > 1;
    }

    get selectedBranch(): Branch | null {
        return this.branchService.activeBranch();
    }

    set selectedBranch(val: Branch | null) {
        if (val?.id === this.branchService.activeBranchId()) return;
        this.branchService.selectBranch(val);
        window.location.reload();
    }

    ngOnDestroy() {
        this.subscription.unsubscribe();
        if (this.refreshIntervalId) {
            clearInterval(this.refreshIntervalId);
            this.refreshIntervalId = null;
        }
        if (this.dueAlertIntervalId) {
            clearInterval(this.dueAlertIntervalId);
            this.dueAlertIntervalId = null;
        }
    }

    getDashboardRoute(): string {
        const user = this.authService.getCurrentUser();
        if (roleKey(user?.role) === 'SUPER_ADMIN') {
            return '/admin/dashboard';
        }
        return '/client/dashboard';
    }

    getWorkspaceLabel(): string {
        const user = this.authService.getCurrentUser();
        return roleKey(user?.role) === 'SUPER_ADMIN' ? 'Control Center' : (user?.tenant_name || 'Workspace');
    }

    get tenantLabel(): string {
        return this.barbershopSettings.settings().name || this.appConfig.platformName();
    }

    get tenantLogoUrl(): string {
        return this.barbershopSettings.settings().logo || 'assets/logos/logo-final.png';
    }

    initUserMenu() {
        this.userMenuItems = [
            {
                label: 'Mi Cuenta',
                icon: 'pi pi-user',
                command: () => this.goToProfile()
            },
            {
                label: 'Cambiar Contraseña',
                icon: 'pi pi-key',
                command: () => this.goToChangePassword()
            },
            {
                label: 'Ayuda',
                icon: 'pi pi-question-circle',
                command: () => this.goToHelp()
            },
            {
                separator: true
            },
            {
                label: this.localeService.t('topbar.logout'),
                icon: 'pi pi-sign-out',
                command: () => this.logout()
            }
        ];
    }

    initQuickSearchMenu() {
        const isSuperAdmin = roleKey(this.authService.getCurrentUser()?.role) === 'SUPER_ADMIN';

        this.quickSearchItems = isSuperAdmin
            ? [
                {
                    label: 'Ir al dashboard admin',
                    icon: 'pi pi-home',
                    command: () => this.router.navigate(['/admin/dashboard'])
                },
                {
                    label: 'Tenants',
                    icon: 'pi pi-building',
                    command: () => this.router.navigate(['/admin/tenants'])
                },
                {
                    label: 'Usuarios',
                    icon: 'pi pi-users',
                    command: () => this.router.navigate(['/admin/users'])
                },
                {
                    label: 'Facturacion',
                    icon: 'pi pi-credit-card',
                    command: () => this.router.navigate(['/admin/billing'])
                },
                {
                    label: 'Soporte',
                    icon: 'pi pi-life-ring',
                    command: () => this.router.navigate(['/admin/support'])
                }
            ]
            : [
                {
                    label: 'Dashboard',
                    icon: 'pi pi-home',
                    command: () => this.router.navigate(['/client/dashboard'])
                },
                {
                    label: 'Agenda',
                    icon: 'pi pi-calendar',
                    command: () => this.router.navigate(['/client/appointments'])
                },
                {
                    label: 'POS',
                    icon: 'pi pi-shopping-cart',
                    command: () => this.router.navigate(['/client/pos'])
                },
                {
                    label: 'Clientes',
                    icon: 'pi pi-users',
                    command: () => this.router.navigate(['/client/clients'])
                },
                {
                    label: 'Reportes',
                    icon: 'pi pi-chart-line',
                    command: () => this.router.navigate(['/client/reports'])
                }
            ];
    }

    changeLanguage(lang: 'es' | 'en' | 'fr' | 'pt' | 'de') {
        this.localeService.setLanguage(lang);
        this.languagePanelOpen = false;
        
        const langKeys: Record<string, string> = {
            es: 'language.changed_to_es',
            en: 'language.changed_to_en',
            fr: 'language.changed_to_fr',
            pt: 'language.changed_to_pt',
            de: 'language.changed_to_de'
        };
        
        this.messageService.add({ 
            severity: 'success', 
            summary: this.localeService.t('language.changed'), 
            detail: this.localeService.t(langKeys[lang] as any)
        });
    }

    toggleDarkMode() {
        this.layoutService.layoutConfig.update((state) => ({ ...state, darkTheme: !state.darkTheme }));
    }

    toggleLanguagePanel(event: Event) {
        event.stopPropagation();
        this.languagePanelOpen = !this.languagePanelOpen;
        if (this.languagePanelOpen) {
            this.activityPanelOpen = false;
        }
    }

    openCommandBar(event: Event) {
        this.quickSearchMenu.toggle(event);
    }

    goToProfile() {
        this.router.navigate(['/client/profile']);
    }

    goToChangePassword() {
        this.router.navigate(['/client/change-password']);
    }

    goToHelp() {
        this.router.navigate(['/client/help']);
    }

    goToAppointments() {
        this.router.navigate(['/client/appointments']);
    }

    activityCount(): number {
        return this.notificationService.saleCount() + this.appointmentBadgeService.badgeCount();
    }

    toggleActivityCenter(event: Event) {
        event.stopPropagation();
        this.activityPanelOpen = !this.activityPanelOpen;
        if (this.activityPanelOpen) {
            this.languagePanelOpen = false;
        }
    }

    activityAppointments() {
        const overdue = this.appointmentBadgeService.overdueAppointments().slice(0, 2).map((apt: any) => this.mapAppointmentToActivity(apt, 'overdue'));
        const upcoming = this.appointmentBadgeService.upcomingAppointments().slice(0, 2).map((apt: any) => this.mapAppointmentToActivity(apt, 'upcoming'));
        const today = this.appointmentBadgeService.todayAppointments().slice(0, 2).map((apt: any) => this.mapAppointmentToActivity(apt, 'today'));
        return [...overdue, ...upcoming, ...today].slice(0, 5);
    }

    recentSales() {
        return this.notificationService.latestNotifications().filter((item) => item.type === 'sale').slice(0, 5);
    }

    markAllAsRead() {
        this.notificationService.markAllAsRead().subscribe(() => {
            this.messageService.add({ 
                severity: 'success', 
                summary: this.localeService.t('common.success'), 
                detail: this.localeService.t('topbar.mark_all_read') 
            });
        });
    }

    markSaleAsRead(notificationId: number) {
        this.notificationService.markAsRead(notificationId).subscribe({ error: () => {} });
    }

    async startOnboardingTour() {
        const started = await this.onboardingTourService.startManualTour();
        if (!started) {
            this.messageService.add({
                severity: 'info',
                summary: this.t('onboarding.overlay.kicker'),
                detail: 'Este módulo no tiene recorrido guiado por ahora.'
            });
        }
    }

    logout() {
        this.authService.logout().subscribe({
            next: () => {
                this.messageService.add({ 
                    severity: 'success', 
                    summary: this.localeService.t('common.success'), 
                    detail: this.localeService.t('auth.logout_success') 
                });
                this.router.navigate(['/auth/login']);
            },
            error: () => {
                this.authService.clearAuthData();
                this.messageService.add({ 
                    severity: 'success', 
                    summary: this.localeService.t('common.success'), 
                    detail: this.localeService.t('auth.logout_success') 
                });
                this.router.navigate(['/auth/login']);
            }
        });
    }

    getUserAvatarUrl(): string | null {
        const user: any = this.authService.getCurrentUser();
        const rawUrl = user?.avatar_url || user?.profile_image || user?.photo || null;
        if (!rawUrl) return null;
        if (/^https?:\/\//i.test(rawUrl)) return rawUrl;

        const apiOrigin = new URL(environment.apiUrl).origin;
        return rawUrl.startsWith('/') ? `${apiOrigin}${rawUrl}` : `${apiOrigin}/${rawUrl}`;
    }

    getUserDisplayName(): string {
        const user: any = this.authService.getCurrentUser();
        return user?.full_name || user?.email || this.localeService.t('topbar.profile');
    }

    t(key: string): string {
        return this.localeService.t(key as any);
    }

    getUserInitials(): string {
        const raw = this.getUserDisplayName();
        if (!raw) return 'U';
        const parts = raw.trim().split(/\s+/).filter(Boolean);
        if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
        return `${parts[0][0] || ''}${parts[1][0] || ''}`.toUpperCase();
    }

    private mapAppointmentToActivity(apt: any, kind: 'overdue' | 'upcoming' | 'today') {
        const time = this.localeService.formatTime(apt.date_time);
        const client = apt.client_name || `Cliente #${apt.client}`;
        const service = apt.service_name || 'Servicio';
        return {
            id: apt.id,
            client,
            service,
            time,
            kind
        };
    }

    @HostListener('document:click')
    closeActivityPanel() {
        this.activityPanelOpen = false;
        this.languagePanelOpen = false;
    }

    private checkDueAppointmentAlerts(): void {
        if (this.dueAlertActive) return;
        const pending = this.appointmentBadgeService.getPendingDueAlerts();
        if (!pending.length) return;

        const apt = pending[0];
        const time = new Date(apt.date_time).toLocaleTimeString('es-DO', { hour: '2-digit', minute: '2-digit' });
        const client = apt.client_name || `Cliente #${apt.client}`;
        const service = apt.service_name || 'Servicio no especificado';

        this.dueAlertActive = true;
        this.playDueAlertSound();

        this.confirmationService.confirm({
            header: 'Cita en curso',
            message: `${time} · ${client} · ${service}\n¿Qué deseas hacer?`,
            icon: 'pi pi-exclamation-triangle',
            acceptLabel: 'Confirmar',
            rejectLabel: 'Descartar',
            accept: () => {
                this.appointmentBadgeService.dismissDueAlert(apt.id);
                this.dueAlertActive = false;
                this.goToAppointments();
            },
            reject: () => {
                this.appointmentBadgeService.dismissDueAlert(apt.id);
                this.dueAlertActive = false;
            }
        });
    }

    private checkCycleCompletedAlerts(): void {
        const pending = this.appointmentBadgeService.getPendingCycleAlerts();
        if (!pending.length) return;

        const apt = pending[0];
        const time = new Date(apt.date_time).toLocaleTimeString('es-DO', { hour: '2-digit', minute: '2-digit' });
        const client = apt.client_name || `Cliente #${apt.client}`;
        const service = apt.service_name || 'Servicio no especificado';

        // Beep intermitente cada tick (30s) hasta que el usuario cierre
        this.playDueAlertSound();

        // Solo mostrar el diálogo si no hay uno ya abierto
        if (this.cycleAlertActive) return;
        this.cycleAlertActive = true;

        this.confirmationService.confirm({
            header: '⏰ Ciclo de cita completado',
            message: `${time} · ${client} · ${service}\nEl tiempo del servicio ha finalizado.\n¿Qué deseas hacer?`,
            icon: 'pi pi-clock',
            acceptLabel: 'Confirmar',
            rejectLabel: 'Descartar',
            accept: () => {
                this.appointmentBadgeService.dismissCycleAlert(apt.id);
                this.cycleAlertActive = false;
                this.goToAppointments();
            },
            reject: () => {
                this.appointmentBadgeService.dismissCycleAlert(apt.id);
                this.cycleAlertActive = false;
            }
        });
    }

    private playDueAlertSound(): void {
        try {
            const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.type = 'square';
            oscillator.frequency.setValueAtTime(990, audioContext.currentTime);
            gainNode.gain.setValueAtTime(0.09, audioContext.currentTime);

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            oscillator.start();
            oscillator.stop(audioContext.currentTime + 0.25);
        } catch {
        }
    }
}
