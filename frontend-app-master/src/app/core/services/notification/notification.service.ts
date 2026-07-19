import { Injectable, computed, inject, signal, OnDestroy } from '@angular/core';
import { Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { MessageService } from 'primeng/api';
import { BaseApiService } from '../base-api.service';
import { LocaleService } from '../locale/locale.service';
import { API_CONFIG } from '../../config/api.config';

export interface InAppNotification {
  id: number;
  type: 'appointment' | 'sale' | 'system' | 'warning' | 'support_reply';
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface NotificationResponse {
  count: number;
  results: InAppNotification[];
}

@Injectable({
  providedIn: 'root'
})
export class NotificationService extends BaseApiService implements OnDestroy {
  private messageService = inject(MessageService);
  private localeService = inject(LocaleService);
  private notificationsSignal = signal<InAppNotification[]>([]);
  private seenNotificationIds = new Set<number>();
  private eventSource: EventSource | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private sseRetryCount = 0;
  private isPolling = false;
  private pollingTimer: any = null;

  public unreadCount = computed(() =>
    this.notificationsSignal().filter((n) => !n.is_read).length
  );

  public appointmentNotifications = computed(() =>
    this.notificationsSignal().filter((n) => n.type === 'appointment')
  );

  public appointmentCount = computed(() =>
    this.appointmentNotifications().filter((n) => !n.is_read).length
  );

  public saleNotifications = computed(() =>
    this.notificationsSignal().filter((n) => n.type === 'sale')
  );

  public saleCount = computed(() =>
    this.saleNotifications().filter((n) => !n.is_read).length
  );

  public latestNotifications = computed(() =>
    [...this.notificationsSignal()].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  );

  constructor() {
    super();
    this.initSSE();
  }

  ngOnDestroy(): void {
    this.disconnectSSE();
  }

  private initSSE(): void {
    this.sseRetryCount = 0;
    this.disconnectSSE();
    this.connectSSE();
  }

  private connectSSE(): void {
    // If polling is active, we don't start SSE unless reset
    if (this.isPolling) return;

    // Limpiar proactivamente cualquier residuo legacy en localStorage
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    
    const url = `${API_CONFIG.BASE_URL}/notifications/stream/`;
    this.eventSource = new EventSource(url, { withCredentials: true });

    this.eventSource.addEventListener('init', (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        if (data.notifications) {
          this.notificationsSignal.set(data.notifications);
          data.notifications.forEach((item: InAppNotification) => this.seenNotificationIds.add(item.id));
        }
      } catch { /* ignore parse errors */ }
    });

    this.eventSource.addEventListener('notification', (event: MessageEvent) => {
      try {
        const notification: InAppNotification = JSON.parse(event.data);
        this.notificationsSignal.update((current) => [notification, ...current]);
        this.seenNotificationIds.add(notification.id);

        if (notification.type === 'appointment' && !notification.is_read) {
          this.messageService.add({
            severity: 'info',
            summary: 'Nueva cita',
            detail: notification.title || notification.message,
            life: 5000
          });
        }

        if (notification.type === 'sale' && !notification.is_read) {
          this.messageService.add({
            severity: 'success',
            summary: 'Nueva venta',
            detail: notification.title || notification.message,
            life: 4500
          });
        }

        if (notification.type === 'support_reply' && !notification.is_read) {
          this.messageService.add({
            severity: 'info',
            summary: '🎧 Soporte respondió',
            detail: notification.message,
            life: 8000,
          });
        }
      } catch { /* ignore parse errors */ }
    });

    this.eventSource.onerror = () => {
      this.disconnectSSE();
      this.sseRetryCount++;
      if (this.sseRetryCount >= 3) {
        console.warn('SSE notification stream failed 3 times. Falling back to HTTP polling.');
        this.startPolling();
      } else {
        this.reconnectTimer = setTimeout(() => this.connectSSE(), 5000);
      }
    };
  }

  private startPolling(): void {
    if (this.isPolling) return;
    this.isPolling = true;
    this.disconnectSSE();
    this.refresh();
    this.pollingTimer = setInterval(() => {
      this.refresh();
    }, 30000);
  }

  private disconnectSSE(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.pollingTimer) {
      clearInterval(this.pollingTimer);
      this.pollingTimer = null;
    }
    this.isPolling = false;
  }

  public refresh(): void {
    this.fetchNotifications().subscribe({
      next: (response) => {
        this.notificationsSignal.set(response.results);
        response.results.forEach((item) => this.seenNotificationIds.add(item.id));
      }
    });
  }

  private fetchNotifications(): Observable<NotificationResponse> {
    return this.get<NotificationResponse>('/notifications/').pipe(
      catchError(() => of({ count: 0, results: [] }))
    );
  }

  markAsRead(notificationId: number): Observable<any> {
    const current = this.notificationsSignal();
    this.notificationsSignal.set(
      current.map((n) => n.id === notificationId ? { ...n, is_read: true } : n)
    );

    return this.patch(`/notifications/${notificationId}/`, { is_read: true }).pipe(
      catchError((err) => {
        this.refresh();
        return of(err);
      })
    );
  }

  markAllAsRead(): Observable<any> {
    const current = this.notificationsSignal();
    this.notificationsSignal.set(current.map((n) => ({ ...n, is_read: true })));

    return this.post('/notifications/mark-all-read/', {}).pipe(
      catchError((err) => {
        this.refresh();
        return of(err);
      })
    );
  }

  deleteNotification(notificationId: number): Observable<any> {
    const current = this.notificationsSignal();
    this.notificationsSignal.set(current.filter((n) => n.id !== notificationId));

    return this.delete(`/notifications/${notificationId}/`).pipe(
      catchError((err) => {
        this.refresh();
        return of(err);
      })
    );
  }

  getRelativeTime(value: string): string {
    return this.localeService.formatRelativeTime(value);
  }
}
