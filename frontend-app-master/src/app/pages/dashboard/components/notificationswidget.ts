import { Component, computed } from '@angular/core';
import { NgClass } from '@angular/common';
import { ButtonModule } from 'primeng/button';
import { MenuModule } from 'primeng/menu';
import { AuBtn } from '../../../shared/components';
import { NotificationService } from '../../../core/services/notification/notification.service';
import { AdminPlatformNotificationService } from '../../../core/services/notification/admin-platform-notification.service';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { AuthService } from '../../../core/services/auth/auth.service';
import { roleKey } from '../../../core/utils/role-normalizer';

@Component({
    standalone: true,
    selector: 'app-notifications-widget',
    imports: [NgClass, AuBtn, ButtonModule, MenuModule],
    template: `
        <div class="card">
            <div class="flex items-center justify-between mb-6">
                <div>
                    <div class="font-semibold text-xl">{{ t('activity.center_title') }}</div>
                    <div class="text-sm mt-1 text-surface-500 dark:text-surface-400">{{ t('activity.widget_subtitle') }}</div>
                </div>
                @if (notifications().length > 0) {
                    <button au-btn type="button" variant="ghost" (click)="markAllAsRead()">{{ t('activity.widget_mark_all') }}</button>
                }
            </div>

            @if (notifications().length > 0) {
                <ul class="p-0 m-0 list-none">
                    @for (notification of notifications(); track notification.id) {
                    <li class="flex items-start py-3 border-b border-surface gap-4">
                        <div class="w-12 h-12 flex items-center justify-center rounded-full shrink-0"
                             [ngClass]="getNotificationStyle(notification.type)">
                            <i [class]="getNotificationIcon(notification.type)"></i>
                        </div>
                        <div class="flex-1">
                            <div class="flex items-start justify-between gap-3">
                                <div>
                                    <span class="text-surface-900 dark:text-surface-0 font-medium block">{{ notification.title }}</span>
                                    <span class="text-surface-600 dark:text-surface-300 text-sm">{{ notification.message }}</span>
                                </div>
                                @if (!notification.is_read) {
                                    <span class="text-[11px] font-semibold uppercase tracking-[0.18em] text-violet-600 dark:text-violet-300">{{ t('activity.widget_new') }}</span>
                                }
                            </div>
                            <div class="flex items-center justify-between mt-2">
                                <div class="text-xs text-surface-500 dark:text-surface-400">{{ getRelativeTime(notification.created_at) }}</div>
                                @if (!notification.is_read) {
                                    <button au-btn type="button" variant="ghost" size="sm" (click)="markAsRead(notification.id)">{{ t('activity.widget_mark_read') }}</button>
                                }
                            </div>
                        </div>
                    </li>
                    }
                </ul>
            } @else {
                <div class="text-center py-6 text-surface-400 dark:text-surface-500">
                    <i class="pi pi-bell-slash text-4xl mb-3 text-surface-300 dark:text-surface-600"></i>
                    <p>{{ t('activity.widget_empty') }}</p>
                </div>
            }
        </div>
    `
})
export class NotificationsWidget {
    notifications = computed(() => {
        const isSuperAdmin = roleKey(this.authService.getCurrentUser()?.role) === 'SUPER_ADMIN';
        return isSuperAdmin
            ? this.adminPlatformNotificationService.notifications().slice(0, 6)
            : this.notificationService.latestNotifications().slice(0, 6);
    });

    constructor(
        private notificationService: NotificationService,
        private localeService: LocaleService,
        private authService: AuthService,
        private adminPlatformNotificationService: AdminPlatformNotificationService
    ) {}

    getNotificationStyle(type: string): string {
        const styles: { [key: string]: string } = {
            sale: 'bg-blue-100 dark:bg-blue-400/10',
            appointment: 'bg-emerald-100 dark:bg-emerald-400/10',
            system: 'bg-slate-100 dark:bg-slate-700',
            warning: 'bg-amber-100 dark:bg-amber-400/10'
        };
        return styles[type] || 'bg-slate-100 dark:bg-slate-700';
    }

    getNotificationIcon(type: string): string {
        const icons: { [key: string]: string } = {
            sale: 'pi pi-dollar text-blue-500',
            appointment: 'pi pi-calendar text-emerald-500',
            system: 'pi pi-cog text-slate-600 dark:text-slate-400',
            warning: 'pi pi-exclamation-triangle text-amber-500'
        };
        return icons[type] || 'pi pi-info-circle text-slate-500';
    }

    getRelativeTime(value: string): string {
        return this.notificationService.getRelativeTime(value);
    }

    markAsRead(notificationId: number) {
        if (roleKey(this.authService.getCurrentUser()?.role) === 'SUPER_ADMIN') {
            this.adminPlatformNotificationService.markAsRead(notificationId);
            return;
        }
        this.notificationService.markAsRead(notificationId).subscribe({ error: () => {} });
    }

    markAllAsRead() {
        if (roleKey(this.authService.getCurrentUser()?.role) === 'SUPER_ADMIN') {
            this.adminPlatformNotificationService.markAllAsRead();
            return;
        }
        this.notificationService.markAllAsRead().subscribe({ error: () => {} });
    }

    t(key: string): string {
        return this.localeService.t(key as any);
    }
}
