import { Component, OnInit, OnDestroy, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { firstValueFrom } from 'rxjs';
import { EmployeeService } from '../../../../core/services/employee/employee.service';
import { AuthService } from '../../../../core/services/auth/auth.service';
import { LocaleService } from '../../../../core/services/locale/locale.service';
import { I18nPipe } from '../../../../core/pipes/i18n.pipe';

@Component({
  selector: 'app-employee-clock-widget',
  standalone: true,
  imports: [CommonModule, I18nPipe],
  template: `
    <div class="overflow-hidden rounded-3xl border border-surface-200 bg-white shadow-lg dark:border-surface-800 dark:bg-surface-900 transition-all duration-300 hover:shadow-xl">
      <div class="relative overflow-hidden p-6 md:p-8">
        <!-- Fondo de gradiente premium -->
        <div class="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-teal-500/5 dark:from-primary/10"></div>
        
        <div class="relative flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div class="space-y-2">
            <div class="inline-flex items-center gap-1.5 rounded-full border border-surface-200 bg-surface-50/90 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-surface-600 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-300">
              <span class="h-2 w-2 rounded-full" [ngClass]="statusColorClass()"></span>
              {{ statusLabel() }}
            </div>
            <h3 class="text-2xl font-bold text-surface-900 dark:text-white">
              {{ greeting() }}, {{ employeeName() }}
            </h3>
            <p class="text-sm text-surface-500 dark:text-surface-400">
              {{ todayLabel() }} • {{ shiftLabel() }}
            </p>
          </div>

          <div class="flex flex-col items-center md:items-end gap-3 min-w-[200px]">
            <!-- Timer / Hora Actual -->
            <div class="text-center md:text-right">
              @if (isWorking()) {
                <div class="text-[11px] font-semibold uppercase tracking-wider text-surface-400">{{ 'schedules.worked_time_today' | t }}</div>
                <div class="text-3xl font-black font-mono tracking-tight text-primary dark:text-teal-400">
                  {{ workedTime() }}
                </div>
              } @else {
                <div class="text-[11px] font-semibold uppercase tracking-wider text-surface-400">{{ 'schedules.server_time' | t }}</div>
                <div class="text-3xl font-bold font-mono tracking-tight text-surface-900 dark:text-white">
                  {{ currentTime() }}
                </div>
              }
            </div>

            <!-- Botones de Acción -->
            <div class="w-full flex gap-2 justify-center md:justify-end">
              @if (state() === 'not_started') {
                <button (click)="checkIn()" 
                        [disabled]="loading()" 
                        class="w-full md:w-auto px-6 py-3 rounded-2xl text-white font-semibold shadow-md transition-all duration-200 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 hover:shadow-lg disabled:opacity-50">
                  <i class="pi pi-sign-in mr-2"></i> {{ 'schedules.mark_check_in' | t }}
                </button>
              } @else if (state() === 'working') {
                <button (click)="checkOut()" 
                        [disabled]="loading()" 
                        class="w-full md:w-auto px-6 py-3 rounded-2xl text-white font-semibold shadow-md transition-all duration-200 bg-gradient-to-r from-orange-500 to-red-600 hover:from-orange-600 hover:to-red-700 hover:shadow-lg disabled:opacity-50">
                  <i class="pi pi-sign-out mr-2"></i> {{ 'schedules.mark_check_out' | t }}
                </button>
              } @else if (state() === 'completed') {
                <div class="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-semibold bg-emerald-50 dark:bg-emerald-950/30 px-4 py-2.5 rounded-2xl text-sm">
                  <i class="pi pi-check-circle text-base"></i> {{ 'schedules.jornada_completada' | t }}
                </div>
              }
            </div>
          </div>
        </div>

        @if (errorMessage()) {
          <div class="mt-4 p-3 rounded-xl border border-red-200 bg-red-50 text-xs text-red-600 dark:border-red-900/50 dark:bg-red-950/20 dark:text-red-400">
            <i class="pi pi-exclamation-circle mr-1"></i> {{ errorMessage() }}
          </div>
        }

        @if (delayAlert()) {
          <div class="mt-4 p-3 rounded-xl border border-amber-200 bg-amber-50 text-xs text-amber-700 dark:border-amber-900/50 dark:bg-amber-950/20 dark:text-amber-400">
            <i class="pi pi-clock mr-1"></i> {{ delayAlert() }}
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }
  `]
})
export class EmployeeClockWidget implements OnInit, OnDestroy {
  private readonly employeeService = inject(EmployeeService);
  private readonly authService = inject(AuthService);
  private readonly localeService = inject(LocaleService);

  t(key: string): string {
    return this.localeService.t(key as any);
  }

  loading = signal(false);
  errorMessage = signal('');
  delayAlert = signal('');
  employeeName = signal('');
  employeeId = signal<number | null>(null);
  
  // Estados: 'loading', 'not_started', 'working', 'completed', 'off_duty'
  state = signal<'loading' | 'not_started' | 'working' | 'completed' | 'off_duty'>('loading');
  
  workedTime = signal('00:00:00');
  currentTime = signal('00:00:00');
  shiftLabel = signal('');

  private timerInterval: any;
  private clockInterval: any;
  private checkInTime: Date | null = null;

  ngOnInit(): void {
    const user = this.authService.getCurrentUser();
    if (user) {
      this.employeeName.set(user.full_name || user.email);
    } else {
      this.employeeName.set(this.t('schedules.colaborador'));
    }
    this.shiftLabel.set(this.t('schedules.no_shift_today'));
    
    this.startServerClock();
    this.loadTodayStatus();
  }

  ngOnDestroy(): void {
    this.clearIntervals();
  }

  private clearIntervals(): void {
    if (this.timerInterval) clearInterval(this.timerInterval);
    if (this.clockInterval) clearInterval(this.clockInterval);
  }

  private startServerClock(): void {
    const updateClock = () => {
      const now = new Date();
      this.currentTime.set(now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }));
    };
    updateClock();
    this.clockInterval = setInterval(updateClock, 1000);
  }

  private async loadTodayStatus(): Promise<void> {
    this.loading.set(true);
    this.errorMessage.set('');
    try {
      const user = this.authService.getCurrentUser();
      if (!user) return;

      // 1. Obtener perfil de empleado
      const employee = await firstValueFrom(this.employeeService.getEmployeeByUserId(user.id));
      if (!employee) {
        this.state.set('off_duty');
        this.shiftLabel.set(this.t('schedules.not_registered_as_employee'));
        return;
      }
      this.employeeId.set(employee.id);

      // 2. Obtener asistencia de hoy
      const attendanceResponse = await firstValueFrom(this.employeeService.getAttendance({ employee_id: employee.id }));
      const attendanceRecords = Array.isArray(attendanceResponse) ? attendanceResponse : (attendanceResponse?.results || []);
      
      const todayStr = new Date().toISOString().split('T')[0];
      const todayRecord = attendanceRecords.find((r: any) => r.work_date === todayStr);

      // 3. Obtener turno programado de hoy
      const days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
      const todayName = days[new Date().getDay()];
      
      const scheduleResponse = await firstValueFrom(this.employeeService.getSchedules({ employee_id: employee.id }));
      const schedules = Array.isArray(scheduleResponse) ? scheduleResponse : (scheduleResponse?.results || []);
      const todaySchedule = schedules.find((s: any) => s.employee === employee.id && s.day_of_week === todayName);

      if (todaySchedule) {
        this.shiftLabel.set(
          this.t('schedules.todays_shift_label')
            .replace('{start}', todaySchedule.start_time.slice(0, 5))
            .replace('{end}', todaySchedule.end_time.slice(0, 5))
        );
      } else {
        this.shiftLabel.set(this.t('schedules.no_shift_scheduled'));
      }

      // 4. Evaluar estado
      if (todayRecord) {
        if (todayRecord.check_out_at) {
          this.state.set('completed');
          this.clearIntervals();
          this.startServerClock();
        } else if (todayRecord.check_in_at) {
          this.state.set('working');
          this.checkInTime = new Date(todayRecord.check_in_at);
          this.startWorkedTimer();
        }
      } else {
        this.state.set('not_started');
        
        // Evaluar si ya va tarde
        if (todaySchedule) {
          const [shour, smin] = todaySchedule.start_time.split(':').map(Number);
          const now = new Date();
          const target = new Date();
          target.setHours(shour, smin, 0, 0);
          
          if (now > target) {
            const diffMs = now.getTime() - target.getTime();
            const diffMins = Math.floor(diffMs / 60000);
            this.delayAlert.set(
              this.t('schedules.delay_warning_label')
                .replace('{start}', todaySchedule.start_time.slice(0, 5))
                .replace('{mins}', String(diffMins))
            );
          }
        }
      }
    } catch (err: any) {
      this.errorMessage.set(this.t('schedules.error_load_status'));
      this.state.set('not_started');
    } finally {
      this.loading.set(false);
    }
  }

  private startWorkedTimer(): void {
    if (this.timerInterval) clearInterval(this.timerInterval);
    
    const updateTimer = () => {
      if (!this.checkInTime) return;
      const now = new Date();
      const diffMs = now.getTime() - this.checkInTime.getTime();
      
      const hours = Math.floor(diffMs / 3600000);
      const minutes = Math.floor((diffMs % 3600000) / 60000);
      const seconds = Math.floor((diffMs % 60000) / 1000);
      
      const pad = (n: number) => n.toString().padStart(2, '0');
      this.workedTime.set(`${pad(hours)}:${pad(minutes)}:${pad(seconds)}`);
    };
    
    updateTimer();
    this.timerInterval = setInterval(updateTimer, 1000);
  }

  async checkIn(): Promise<void> {
    this.loading.set(true);
    this.errorMessage.set('');
    try {
      // Llamada segura: si se envía sin ID de empleado, el backend deduce la sesión
      const res = await firstValueFrom(this.employeeService.checkIn());
      this.checkInTime = new Date(res.check_in_at || new Date());
      this.state.set('working');
      this.delayAlert.set('');
      this.startWorkedTimer();
    } catch (err: any) {
      this.errorMessage.set(err?.error?.detail || err?.error?.error || this.t('schedules.error_check_in'));
    } finally {
      this.loading.set(false);
    }
  }

  async checkOut(): Promise<void> {
    this.loading.set(true);
    this.errorMessage.set('');
    try {
      await firstValueFrom(this.employeeService.checkOut());
      this.state.set('completed');
      if (this.timerInterval) clearInterval(this.timerInterval);
      this.startServerClock();
    } catch (err: any) {
      this.errorMessage.set(err?.error?.detail || err?.error?.error || this.t('schedules.error_check_out'));
    } finally {
      this.loading.set(false);
    }
  }

  // Helpers visuales
  greeting(): string {
    const hrs = new Date().getHours();
    if (hrs < 12) return this.t('schedules.good_morning');
    if (hrs < 19) return this.t('schedules.good_afternoon');
    return this.t('schedules.good_evening');
  }

  todayLabel(): string {
    const options: Intl.DateTimeFormatOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    const locale = this.localeService.getCurrentLanguage() === 'en' ? 'en-US' : 'es-DO';
    return new Date().toLocaleDateString(locale, options);
  }

  isWorking(): boolean {
    return this.state() === 'working';
  }

  statusLabel(): string {
    const map = {
      loading: this.t('schedules.clock_status_loading'),
      not_started: this.t('schedules.clock_status_not_started'),
      working: this.t('schedules.clock_status_working'),
      completed: this.t('schedules.clock_status_completed'),
      off_duty: this.t('schedules.clock_status_off_duty')
    };
    return map[this.state()];
  }

  statusColorClass(): string {
    const map = {
      loading: 'bg-surface-400 animate-pulse',
      not_started: 'bg-amber-400',
      working: 'bg-emerald-500',
      completed: 'bg-primary-500',
      off_duty: 'bg-surface-500'
    };
    return map[this.state()];
  }
}
