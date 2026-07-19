import { CommonModule } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';
import { NotificationBadgeService } from '../../../core/services/notification/notification-badge.service';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { AppointmentsDataService } from './appointments-data.service';
import { AppointmentsUiService } from './appointments-ui.service';
import { AuBtn, AuSkeleton } from '../../../shared/components';

type AppointmentTab = 'calendar' | 'list';

@Component({
    selector: 'app-appointments-main',
    standalone: true,
    imports: [CommonModule, RouterLink, RouterLinkActive, RouterOutlet, AuBtn, AuSkeleton],
    template: `
        <div class="appts-shell">
            <header class="appts-header">
                <div class="appts-header__left">
                    <div class="appts-status">
                        <span class="appts-status__dot"></span>
                        {{ t('appointments.active_agenda') }}
                    </div>
                    <div class="appts-header__title">
                        <strong>{{ t('appointments.manage_day') }}</strong>
                        <span>{{ getHeaderNarrative() }}</span>
                    </div>
                    <div class="appts-header__counts" *ngIf="!appointmentsDataService.loading(); else statsSkeleton">
                        <span><strong>{{ stats().todayCount }}</strong> {{ t('appointments.today') }}</span>
                        <span class="appts-header__sep">·</span>
                        <span [class.appts-header__overdue]="stats().overdueCount > 0"><strong>{{ stats().overdueCount }}</strong> {{ t('appointments.overdue') }}</span>
                        <span class="appts-header__sep">·</span>
                        <span><strong>{{ stats().statusCounts.scheduled }}</strong> {{ t('appointments.scheduled_f') }}</span>
                    </div>
                    <ng-template #statsSkeleton>
                        <div class="appts-header__counts">
                            <span><au-skeleton width="60px" height="16px" /></span>
                        </div>
                    </ng-template>
                </div>
                <div class="appts-header__right">
                    <a routerLink="calendar" routerLinkActive="is-active" class="appts-tab">
                        <i class="pi pi-calendar"></i> {{ t('appointments.calendar') }}
                    </a>
                    <a routerLink="list" routerLinkActive="is-active" class="appts-tab">
                        <i class="pi pi-list"></i> {{ t('appointments.list') }}
                    </a>
                    <button au-btn variant="primary" [icon]="'pi pi-plus'" (click)="crearCita()" class="appts-cta">{{ t('appointments.new_appointment') }}</button>
                </div>
            </header>

            <div class="appts-next" *ngIf="stats().nextAppointment as next; else noNextAppointment">
                <span class="appts-next__label">{{ t('appointments.next') }}</span>
                <strong>{{ next.client_name || (t('appointments.client_hash') + next.client) }}</strong>
                <span>{{ next.stylist_name || (t('appointments.employee_hash') + next.stylist) }}</span>
                <span class="appts-next__time">{{ next.date_time | date: 'dd/MM HH:mm' }}</span>
            </div>
            <ng-template #noNextAppointment>
                <div class="appts-next">
                    <span class="appts-next__label">{{ t('appointments.status') }}</span>
                    <strong>{{ t('appointments.no_next_appointment') }}</strong>
                    <span>{{ stats().statusCounts.scheduled > 0 ? t('appointments.pending_in_list') : t('appointments.agenda_clean') }}</span>
                </div>
            </ng-template>

            <router-outlet></router-outlet>
        </div>

        <style>
        .appts-shell { display: flex; flex-direction: column; gap: 0; }

        .appts-header {
            display: flex; align-items: center; justify-content: space-between;
            flex-wrap: wrap; gap: 0.75rem;
            padding: 0.85rem 1rem;
            border: 1px solid var(--surface-border);
            background: var(--surface-card);
            border-radius: 0.85rem;
            margin-bottom: 0.75rem;
        }

        .appts-header__left, .appts-header__right { display: flex; align-items: center; gap: 0.65rem; flex-wrap: wrap; }

        .appts-header__title {
            display: flex;
            flex-direction: column;
            gap: 0.12rem;
            margin-left: 0.25rem;
        }

        .appts-header__title strong {
            font-size: 1rem;
            color: var(--text-color);
        }

        .appts-header__title span {
            font-size: 0.82rem;
            color: var(--text-color-secondary);
        }

        .appts-status {
            display: inline-flex; align-items: center; gap: 0.4rem;
            font-size: 0.78rem; font-weight: 700; text-transform: uppercase;
            letter-spacing: 0.1em; color: var(--text-color-secondary);
        }

        .appts-status__dot {
            width: 0.5rem; height: 0.5rem; border-radius: 999px; background: #10b981;
        }

        .appts-header__counts { display: flex; align-items: center; gap: 0.5rem; font-size: 0.9rem; color: var(--text-color); }
        .appts-header__sep { color: var(--text-color-secondary); }
        .appts-header__overdue strong { color: #d97706; }

        .appts-tab {
            display: inline-flex; align-items: center; gap: 0.4rem;
            padding: 0.45rem 0.9rem; border-radius: 6px;
            font-size: 0.88rem; font-weight: 600;
            border: 1px solid var(--surface-border);
            color: var(--text-color-secondary);
            text-decoration: none; transition: all 120ms;
        }

        .appts-tab.is-active {
            background: var(--brand); color: var(--p-primary-contrast-color); border-color: var(--brand);
        }

        .appts-cta { height: 2.25rem; font-size: 0.88rem; }

        .appts-next {
            display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;
            padding: 0.65rem 1rem;
            border: 1px solid var(--surface-border);
            background: var(--surface-ground);
            border-radius: 0.65rem;
            font-size: 0.88rem;
            margin-bottom: 0.75rem;
        }

        .appts-next__label {
            font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
            letter-spacing: 0.1em; color: var(--text-color-secondary);
        }

        .appts-next strong { color: var(--text-color); font-weight: 700; }
        .appts-next span { color: var(--text-color-secondary); }

        .appts-next__time {
            margin-left: auto; font-weight: 700;
            color: var(--brand);
        }
        </style>
    `
})
export class AppointmentsMain implements OnInit {
    private readonly notificationService = inject(NotificationBadgeService);
    private readonly appointmentsUiService = inject(AppointmentsUiService);
    readonly appointmentsDataService = inject(AppointmentsDataService);
    private readonly localeService = inject(LocaleService);
    private readonly destroyRef = inject(DestroyRef);
    private readonly router = inject(Router);

    t(key: string): string {
        return this.localeService.t(key as any);
    }

    activeTab: AppointmentTab = 'calendar';
    stats = this.appointmentsDataService.stats;

    summaryCards = [
        { key: 'scheduled', labelKey: 'appointments.scheduled_f', accent: 'border-l-blue-500 text-blue-700 dark:text-blue-300' },
        { key: 'completed', labelKey: 'appointments.completed_f', accent: 'border-l-emerald-500 text-emerald-700 dark:text-emerald-300' },
        { key: 'cancelled', labelKey: 'appointments.cancelled_f', accent: 'border-l-rose-500 text-rose-700 dark:text-rose-300' },
        { key: 'no_show', labelKey: 'appointments.no_show_f', accent: 'border-l-amber-500 text-amber-700 dark:text-amber-300' }
    ] as const;

    ngOnInit(): void {
        this.appointmentsDataService.load(true);
        this.appointmentsUiService.refresh$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
            this.notificationService.refresh();
        });
        this.setActiveTabFromUrl(this.router.url);
        this.router.events.pipe(
            filter((event): event is NavigationEnd => event instanceof NavigationEnd),
            takeUntilDestroyed(this.destroyRef)
        ).subscribe((event) => {
            this.setActiveTabFromUrl(event.urlAfterRedirects);
        });
    }

    crearCita(): void {
        this.appointmentsUiService.requestCreate(this.activeTab);
    }

    getHeaderNarrative(): string {
        if (this.activeTab === 'list') {
            return this.t('appointments.list_narrative');
        }

        return this.t('appointments.calendar_narrative');
    }

    private setActiveTabFromUrl(url: string): void {
        this.activeTab = url.includes('/appointments/list') ? 'list' : 'calendar';
    }
}
