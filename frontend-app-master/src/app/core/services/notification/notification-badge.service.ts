import { Injectable, signal, computed, inject, effect, untracked } from '@angular/core';
import { AppointmentService } from '../appointment/appointment.service';
import { BranchService } from '../branch/branch.service';
import { LoggerService } from '../logger.service';

@Injectable({
  providedIn: 'root'
})
export class NotificationBadgeService {
  private appointmentService = inject(AppointmentService);
  private branchService = inject(BranchService);
  private logger = inject(LoggerService);
  private appointments = signal<any[]>([]);
  private readonly overdueWindowMs = 24 * 60 * 60 * 1000; // 24 horas
  private readonly dueAlertWindowMs = 30 * 60 * 1000; // 30 min desde el inicio
  private dismissedDueAlerts = new Set<number>();
  private dismissedCycleAlerts = new Set<number>();

  todayAppointments = computed(() => {
    const now = new Date();
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    return this.appointments().filter(apt => {
      const aptDate = new Date(apt.date_time);
      return aptDate >= now && aptDate < tomorrow && apt.status === 'scheduled';
    });
  });

  upcomingAppointments = computed(() => {
    const now = new Date();
    const in30min = new Date(now.getTime() + 30 * 60000);

    return this.appointments().filter(apt => {
      const aptDate = new Date(apt.date_time);
      return aptDate >= now && aptDate <= in30min && apt.status === 'scheduled';
    });
  });

  overdueAppointments = computed(() => {
    const now = new Date();
    const windowStart = new Date(now.getTime() - this.overdueWindowMs);
    return this.appointments().filter(apt => {
      const aptDate = new Date(apt.date_time);
      return aptDate < now && aptDate >= windowStart && apt.status === 'scheduled';
    });
  });

  badgeCount = computed(() => this.todayAppointments().length);

  dueNowAppointments = computed(() => {
    const now = new Date();
    const alertWindowStart = new Date(now.getTime() - this.dueAlertWindowMs);
    return this.appointments().filter(apt => {
      const aptDate = new Date(apt.date_time);
      return apt.status === 'scheduled' && aptDate <= now && aptDate >= alertWindowStart;
    });
  });

  cycleCompletedAppointments = computed(() => {
    const now = new Date().getTime();
    return this.appointments().filter(apt => {
      if (apt.status !== 'scheduled') return false;
      const startTime = new Date(apt.date_time).getTime();
      const durationMs = (apt.service_duration || 30) * 60 * 1000;
      return now >= startTime + durationMs;
    });
  });

  constructor() {
    effect(() => {
      const _branchId = this.branchService.activeBranchId();
      untracked(() => this.loadAppointments());
    });
  }

  loadAppointments() {
    const branchId = this.branchService.activeBranchId();
    const params = branchId ? { branch: branchId } : {};
    this.appointmentService.getAppointments(params).subscribe({
      next: (response: any) => {
        const data = response?.results || response || [];
        this.appointments.set(data);
      },
      error: (err) => {
        this.logger.error('Failed to load appointments for badge', err);
        this.appointments.set([]);
      }
    });
  }

  refresh() {
    this.loadAppointments();
  }

  getPendingDueAlerts(): any[] {
    return this.dueNowAppointments().filter(apt => !this.dismissedDueAlerts.has(apt.id));
  }

  dismissDueAlert(appointmentId: number): void {
    this.dismissedDueAlerts.add(appointmentId);
  }

  getPendingCycleAlerts(): any[] {
    return this.cycleCompletedAppointments().filter(apt => !this.dismissedCycleAlerts.has(apt.id));
  }

  dismissCycleAlert(appointmentId: number): void {
    this.dismissedCycleAlerts.add(appointmentId);
  }
}
