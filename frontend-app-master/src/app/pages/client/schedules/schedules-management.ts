import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { PlanAccessService } from '../../../core/services/plan-access.service';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { firstValueFrom, Subscription } from 'rxjs';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ConfirmationService } from 'primeng/api';
import { AuSkeleton } from '../../../shared/components';
import { EmployeeService } from '../../../core/services/employee/employee.service';
import { AuthService } from '../../../core/services/auth/auth.service';
import { BranchService } from '../../../core/services/branch/branch.service';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { I18nPipe } from '../../../core/pipes/i18n.pipe';

type DayValue =
    | 'monday'
    | 'tuesday'
    | 'wednesday'
    | 'thursday'
    | 'friday'
    | 'saturday'
    | 'sunday';

interface ScheduleFormState {
    id: number | null;
    employee: number | null;
    day_of_week: DayValue;
    start_time: string;
    end_time: string;
}

@Component({
    selector: 'app-schedules-management',
    standalone: true,
    imports: [CommonModule, FormsModule, ConfirmDialogModule, AuSkeleton, I18nPipe],
    providers: [ConfirmationService],
    template: `
        <div class="p-4 md:p-6 space-y-6">
            <p-confirmDialog></p-confirmDialog>

            <!-- Hero/Header -->
            <section class="overflow-hidden rounded-[2rem] border border-surface-200/70 bg-surface-0 shadow-lg dark:border-surface-800 dark:bg-surface-900">
                <div class="relative overflow-hidden px-6 py-6 md:px-8 md:py-8 lg:px-10">
                    <div class="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-teal-500/5 dark:from-primary/10"></div>
                    <div class="relative grid gap-8 lg:grid-cols-[minmax(0,1.5fr)_minmax(320px,0.9fr)] lg:items-start">
                        <div class="space-y-4">
                            <div class="inline-flex items-center gap-2 rounded-full border border-surface-200 bg-surface-50/90 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.24em] text-surface-600 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-300">
                                <i class="pi pi-calendar-clock text-[0.7rem] text-primary"></i>
                                {{ t('schedules.turns') }}
                            </div>
                            <div>
                                <h2 class="display-4 text-surface-950 dark:text-white">{{ t('schedules.title') }}</h2>
                                <p class="mt-2 text-sm text-surface-600 dark:text-surface-450">{{ t('schedules.subtitle') }}</p>
                            </div>
                            <div class="grid grid-cols-3 gap-3 pt-2">
                                <ng-container *ngIf="!loading; else heroSkeleton">
                                    <article class="rounded-2xl border border-surface-200 bg-white/80 p-3 shadow-sm dark:border-surface-800 dark:bg-surface-800/40">
                                        <div class="text-[10px] font-semibold uppercase tracking-wider text-surface-500">{{ t('schedules.shifts') }}</div>
                                        <div class="mt-1 text-xl font-black text-surface-950 dark:text-white">{{ schedules.length }}</div>
                                    </article>
                                    <article class="rounded-2xl border border-surface-200 bg-white/80 p-3 shadow-sm dark:border-surface-800 dark:bg-surface-800/40">
                                        <div class="text-[10px] font-semibold uppercase tracking-wider text-surface-500">{{ t('schedules.team') }}</div>
                                        <div class="mt-1 text-xl font-black text-surface-950 dark:text-white">{{ employees.length }}</div>
                                    </article>
                                    <article class="rounded-2xl border border-surface-200 bg-white/80 p-3 shadow-sm dark:border-surface-800 dark:bg-surface-800/40">
                                        <div class="text-[10px] font-semibold uppercase tracking-wider text-surface-500">{{ 'schedules.todays_attendance' | t }}</div>
                                        <div class="mt-1 text-xl font-black text-surface-950 dark:text-white">{{ attendanceRecords.length }}</div>
                                    </article>
                                </ng-container>
                                <ng-template #heroSkeleton>
                                    <article class="rounded-2xl border border-surface-200 bg-white/80 p-3 shadow-sm dark:border-surface-800 dark:bg-surface-800/40">
                                        <au-skeleton width="60%" height="12px" />
                                        <au-skeleton width="40%" height="28px" class="mt-2" />
                                    </article>
                                    <article class="rounded-2xl border border-surface-200 bg-white/80 p-3 shadow-sm dark:border-surface-800 dark:bg-surface-800/40">
                                        <au-skeleton width="60%" height="12px" />
                                        <au-skeleton width="40%" height="28px" class="mt-2" />
                                    </article>
                                    <article class="rounded-2xl border border-surface-200 bg-white/80 p-3 shadow-sm dark:border-surface-800 dark:bg-surface-800/40">
                                        <au-skeleton width="60%" height="12px" />
                                        <au-skeleton width="40%" height="28px" class="mt-2" />
                                    </article>
                                </ng-template>
                            </div>
                        </div>

                        <!-- Sidebar Info -->
                        <div class="rounded-2xl border border-surface-200 bg-white/80 p-4 shadow-sm dark:border-surface-800 dark:bg-surface-850 space-y-3">
                            <div *ngIf="showBranchSelector">
                                <div class="text-xs font-semibold uppercase tracking-wider text-surface-400">{{ 'schedules.filter_by_branch' | t }}</div>
                                <select class="w-full mt-1.5 p-2 border rounded-xl bg-white dark:bg-surface-800 border-surface-300 dark:border-surface-700 text-xs focus:ring-2 focus:ring-primary focus:outline-none"
                                    [(ngModel)]="selectedBranchFilter" (change)="loadData()">
                                    <option [ngValue]="null">{{ 'schedules.all_branches' | t }}</option>
                                    <option *ngFor="let branch of branchesList" [ngValue]="branch.id">
                                        {{ branch.name }}
                                    </option>
                                </select>
                                <hr class="border-surface-200 dark:border-surface-800 mt-3" />
                            </div>
                            <div>
                                <div class="text-xs font-semibold uppercase tracking-wider text-surface-400">{{ 'schedules.quick_summary' | t }}</div>
                                <div class="mt-2 text-sm leading-relaxed text-surface-600 dark:text-surface-300">
                                    {{ getSchedulesNarrative() }}
                                </div>
                            </div>
                            <div class="mt-4 flex gap-2">
                                <button class="flex-1 rounded-xl bg-surface-950 px-4 py-2.5 text-xs font-semibold text-white transition hover:bg-surface-800 dark:bg-surface-750 dark:hover:bg-surface-700"
                                    (click)="resetForm()">
                                    {{ t('schedules.new_shift') }}
                                </button>
                                <button class="rounded-xl border border-surface-300 px-4 py-2.5 text-xs font-semibold text-surface-700 transition hover:bg-surface-100 dark:border-surface-700 dark:text-surface-300 dark:hover:bg-surface-800"
                                    (click)="loadData()">
                                    <i class="pi pi-refresh mr-1"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Tabs de Navegación -->
            <div class="flex border-b border-surface-250 dark:border-surface-800">
                <button (click)="activeTab = 'shifts'" 
                        [class]="activeTab === 'shifts' ? 'border-primary text-primary font-bold border-b-2' : 'text-surface-500 hover:text-surface-700'"
                        class="px-6 py-3 text-sm transition-all focus:outline-none">
                    <i class="pi pi-calendar mr-2"></i> {{ 'schedules.weekly_planning' | t }}
                </button>
                <button (click)="activeTab = 'attendance'" 
                        [class]="activeTab === 'attendance' ? 'border-primary text-primary font-bold border-b-2' : 'text-surface-500 hover:text-surface-700'"
                        class="px-6 py-3 text-sm transition-all focus:outline-none">
                    <i class="pi pi-check-square mr-2"></i> {{ 'schedules.attendance_monitoring' | t }}
                </button>
            </div>

            <!-- Error message global -->
            <div *ngIf="errorMessage" class="p-3 rounded-xl border border-red-200 bg-red-50 text-xs text-red-600 dark:border-red-950/40 dark:bg-red-950/20 dark:text-red-400">
                <i class="pi pi-exclamation-circle mr-1"></i> {{ errorMessage }}
            </div>

            <!-- Pestaña 1: Planificación de Turnos -->
            <div *ngIf="activeTab === 'shifts'" class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <!-- Formulario lateral -->
                <div class="bg-white dark:bg-surface-900 rounded-2xl p-5 border border-surface-200 dark:border-surface-800 lg:col-span-1 space-y-4">
                    <div class="rounded-xl bg-surface-950 p-4 text-white dark:bg-surface-850">
                        <div class="text-[10px] font-semibold uppercase tracking-wider text-surface-400">{{ t('schedules.shift') }}</div>
                        <div class="mt-1 text-lg font-black">{{ form.id ? t('schedules.edit_shift') : t('schedules.new_shift') }}</div>
                    </div>

                    <div class="space-y-3">
                        <label class="block">
                            <span class="text-xs font-semibold text-surface-700 dark:text-surface-300">{{ t('schedules.employee') }}</span>
                            <select class="w-full mt-1 p-2.5 border rounded-xl bg-white dark:bg-surface-800 border-surface-300 dark:border-surface-700 text-sm focus:ring-2 focus:ring-primary focus:outline-none"
                                [(ngModel)]="form.employee" name="employee">
                                <option [ngValue]="null">{{ 'schedules.select_collaborator' | t }}</option>
                                <option *ngFor="let emp of employees" [ngValue]="emp.id">
                                    {{ getEmployeeName(emp) }}
                                </option>
                            </select>
                        </label>

                        <label class="block">
                            <span class="text-xs font-semibold text-surface-700 dark:text-surface-300">{{ t('schedules.day') }}</span>
                            <select class="w-full mt-1 p-2.5 border rounded-xl bg-white dark:bg-surface-800 border-surface-300 dark:border-surface-700 text-sm focus:ring-2 focus:ring-primary focus:outline-none"
                                [(ngModel)]="form.day_of_week" name="day_of_week">
                                <option *ngFor="let day of days" [ngValue]="day.value">{{ day.label }}</option>
                            </select>
                        </label>

                        <div class="grid grid-cols-2 gap-3">
                            <label class="block">
                                <span class="text-xs font-semibold text-surface-700 dark:text-surface-300">{{ t('schedules.start_time') }}</span>
                                <input type="time" class="w-full mt-1 p-2.5 border rounded-xl bg-white dark:bg-surface-800 border-surface-300 dark:border-surface-700 text-sm focus:ring-2 focus:ring-primary focus:outline-none"
                                    [(ngModel)]="form.start_time" name="start_time" />
                            </label>

                            <label class="block">
                                <span class="text-xs font-semibold text-surface-700 dark:text-surface-300">{{ t('schedules.end_time') }}</span>
                                <input type="time" class="w-full mt-1 p-2.5 border rounded-xl bg-white dark:bg-surface-800 border-surface-300 dark:border-surface-700 text-sm focus:ring-2 focus:ring-primary focus:outline-none"
                                    [(ngModel)]="form.end_time" name="end_time" />
                            </label>
                        </div>

                        <div class="flex gap-2 pt-3">
                            <button class="flex-1 py-2.5 rounded-xl text-sm font-semibold text-white bg-teal-600 hover:bg-teal-700 transition"
                                (click)="saveSchedule()" [disabled]="loading">
                                {{ form.id ? t('schedules.update') : t('schedules.create') }}
                            </button>
                            <button class="px-4 py-2.5 rounded-xl border border-surface-300 text-sm font-semibold hover:bg-surface-50 dark:border-surface-700 dark:hover:bg-surface-800 transition"
                                (click)="resetForm()">
                                {{ t('schedules.clear') }}
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Matriz semanal -->
                <div class="bg-white dark:bg-surface-900 rounded-2xl p-5 border border-surface-200 dark:border-surface-800 lg:col-span-2 space-y-4">
                    <div class="flex justify-between items-center">
                        <h3 class="text-lg font-bold text-surface-900 dark:text-white">{{ 'schedules.weekly_matrix_title' | t }}</h3>
                        <div class="text-xs text-surface-400">{{ 'schedules.weekly_matrix_subtitle' | t }}</div>
                    </div>

                    <div class="overflow-x-auto rounded-xl border border-surface-200 dark:border-surface-800">
                        <table class="min-w-full divide-y divide-surface-200 dark:divide-surface-850 text-xs">
                            <thead>
                                <tr class="bg-surface-50 dark:bg-surface-800 text-left font-bold text-surface-500">
                                    <th class="p-3 w-40">{{ 'schedules.collaborator' | t }}</th>
                                    <th *ngFor="let day of days" class="p-3 text-center">{{ day.label }}</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-surface-150 dark:divide-surface-800">
                                <ng-container *ngIf="!loading; else gridSkeleton">
                                    <tr *ngFor="let row of gridData">
                                        <td class="p-3 font-semibold text-surface-900 dark:text-white border-r border-surface-200 dark:border-surface-850">
                                            {{ getEmployeeName(row.employee) }}
                                        </td>
                                        <td *ngFor="let day of days" class="p-2 text-center min-w-[100px]">
                                            <div *ngIf="row.dayMap[day.value] as sched; else noSched" 
                                                 class="group relative rounded-xl border border-teal-200/50 bg-teal-50/50 p-2 dark:border-teal-900/20 dark:bg-teal-950/15">
                                                <div class="font-bold text-teal-800 dark:text-teal-350">
                                                    {{ formatTimeForInput(sched.start_time) }} - {{ formatTimeForInput(sched.end_time) }}
                                                </div>
                                                <div class="absolute inset-0 flex items-center justify-center gap-1.5 bg-teal-50/95 dark:bg-surface-900/95 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-150">
                                                    <button (click)="editSchedule(sched)" class="p-1 rounded text-teal-700 hover:bg-teal-100 dark:text-teal-400 dark:hover:bg-teal-950/50" [title]="'schedules.edit' | t">
                                                        <i class="pi pi-pencil text-[10px]"></i>
                                                    </button>
                                                    <button *ngIf="canDeleteSchedule()" (click)="deleteSchedule(sched)" class="p-1 rounded text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/50" [title]="'schedules.delete' | t">
                                                        <i class="pi pi-trash text-[10px]"></i>
                                                    </button>
                                                </div>
                                            </div>
                                            <ng-template #noSched>
                                                <button (click)="quickNewShift(row.employee.id, day.value)" 
                                                        class="w-full py-2 border border-dashed border-surface-300 hover:border-primary/50 hover:bg-surface-50 dark:border-surface-750 dark:hover:bg-surface-800/40 rounded-xl text-surface-400 hover:text-primary transition flex justify-center items-center">
                                                    <i class="pi pi-plus text-[9px]"></i>
                                                </button>
                                            </ng-template>
                                        </td>
                                    </tr>
                                    <tr *ngIf="gridData.length === 0">
                                        <td colspan="8" class="p-8 text-center text-surface-400">
                                            {{ 'schedules.no_employees_registered' | t }}
                                        </td>
                                    </tr>
                                </ng-container>
                                <ng-template #gridSkeleton>
                                    <tr *ngFor="let _ of [1,2,3,4]">
                                        <td class="p-3 border-r border-surface-200 dark:border-surface-850">
                                            <au-skeleton width="80%" height="16px" />
                                        </td>
                                        <td *ngFor="let __ of days" class="p-2 text-center min-w-[100px]">
                                             <au-skeleton width="100%" height="40px" />
                                        </td>
                                    </tr>
                                </ng-template>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Pestaña 2: Monitoreo de Asistencia -->
            <div *ngIf="activeTab === 'attendance'" class="space-y-6">
                <!-- Controles de Check-In rápidos para admin -->
                <div class="bg-white dark:bg-surface-900 rounded-2xl p-4 border border-surface-200 dark:border-surface-800 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div class="space-y-1">
                        <h4 class="text-sm font-bold text-surface-900 dark:text-white">{{ 'schedules.auxiliary_attendance_title' | t }}</h4>
                        <p class="text-xs text-surface-450">{{ 'schedules.auxiliary_attendance_desc' | t }}</p>
                    </div>
                    <div class="flex flex-wrap items-center gap-2">
                        <select class="p-2 border rounded-xl bg-white dark:bg-surface-800 border-surface-300 dark:border-surface-700 text-xs focus:outline-none"
                            [(ngModel)]="selectedAttendanceEmployeeId" name="attendance_employee">
                            <option [ngValue]="null">{{ 'schedules.select_employee_placeholder' | t }}</option>
                            <option *ngFor="let emp of employees" [ngValue]="emp.id">{{ getEmployeeName(emp) }}</option>
                        </select>
                        <button class="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 transition"
                            (click)="performCheckIn()" [disabled]="loading || !selectedAttendanceEmployeeId">
                            {{ 'schedules.register_checkin' | t }}
                        </button>
                        <button class="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-orange-650 hover:bg-orange-700 transition"
                            (click)="performCheckOut()" [disabled]="loading || !selectedAttendanceEmployeeId">
                            {{ 'schedules.register_checkout' | t }}
                        </button>
                    </div>
                </div>

                <!-- Team Attendance Monitor Grid -->
                <div class="space-y-3">
                    <h3 class="text-lg font-bold text-surface-900 dark:text-white">{{ 'schedules.attendance_monitor_title' | t }}</h3>
                    
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <!-- Categoría: Presentes -->
                        <div class="space-y-3">
                            <h4 class="text-xs font-bold uppercase tracking-wider text-emerald-600 flex items-center gap-2">
                                <span class="h-2 w-2 rounded-full bg-emerald-500"></span> {{ 'schedules.present_count' | t }} ({{ getMonitorCount('present') }})
                            </h4>
                            <ng-container *ngIf="!loading; else presentSkeleton">
                                <div class="space-y-2">
                                    <div *ngFor="let item of filterMonitor('present')" class="bg-white dark:bg-surface-900 p-4 rounded-2xl border border-surface-200 dark:border-surface-800 shadow-sm space-y-3">
                                        <div class="flex justify-between items-start">
                                            <div class="font-bold text-surface-900 dark:text-white">{{ getEmployeeName(item.employee) }}</div>
                                            <div class="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-400">
                                                {{ item.label }}
                                            </div>
                                        </div>
                                        <div class="text-xs text-surface-500 dark:text-surface-400 space-y-1">
                                            <div><i class="pi pi-sign-in mr-1 text-[10px]"></i> {{ 'schedules.check_in_col' | t }}: {{ item.checkInTime | date:'shortTime' }}</div>
                                            @if (item.notes) {
                                                <div class="italic text-[10px] text-surface-400">{{ item.notes }}</div>
                                            }
                                        </div>
                                    </div>
                                    <div *ngIf="getMonitorCount('present') === 0" class="py-6 text-center text-xs text-surface-400 border border-dashed border-surface-200 dark:border-surface-800 rounded-2xl">
                                        {{ 'schedules.no_collab_present' | t }}
                                    </div>
                                </div>
                            </ng-container>
                            <ng-template #presentSkeleton>
                                <div class="space-y-2">
                                    <div *ngFor="let _ of [1,2]" class="bg-white dark:bg-surface-900 p-4 rounded-2xl border border-surface-200 dark:border-surface-800 shadow-sm space-y-3">
                                        <div class="flex justify-between items-start">
                                            <au-skeleton width="55%" height="16px" />
                                             <au-skeleton width="64px" height="18px" />
                                        </div>
                                        <au-skeleton width="70%" height="12px" />
                                    </div>
                                </div>
                            </ng-template>
                        </div>

                        <!-- Categoría: Retrasados / Tardanzas -->
                        <div class="space-y-3">
                            <h4 class="text-xs font-bold uppercase tracking-wider text-amber-600 flex items-center gap-2">
                                <span class="h-2 w-2 rounded-full bg-amber-500"></span> {{ 'schedules.late_count' | t }} ({{ getMonitorCount('late') }})
                            </h4>
                            <ng-container *ngIf="!loading; else lateSkeleton">
                                <div class="space-y-2">
                                    <div *ngFor="let item of filterMonitor('late')" class="bg-white dark:bg-surface-900 p-4 rounded-2xl border border-surface-200 dark:border-surface-800 shadow-sm space-y-3">
                                        <div class="flex justify-between items-start">
                                            <div class="font-bold text-surface-900 dark:text-white">{{ getEmployeeName(item.employee) }}</div>
                                            <div class="text-[10px] px-2 py-0.5 rounded-full font-semibold" 
                                                 [ngClass]="item.isJustified ? 'bg-teal-100 text-teal-800 dark:bg-teal-950/30 dark:text-teal-400' : 'bg-amber-100 text-amber-800 dark:bg-amber-950/30 dark:text-amber-400'">
                                                {{ item.label }}
                                            </div>
                                        </div>
                                        <div class="text-xs text-surface-500 dark:text-surface-400 space-y-1">
                                            @if (item.checkInTime) {
                                                <div><i class="pi pi-sign-in mr-1 text-[10px]"></i> {{ 'schedules.check_in_col' | t }}: {{ item.checkInTime | date:'shortTime' }}</div>
                                            } @else {
                                                <div class="text-red-500"><i class="pi pi-exclamation-triangle mr-1 text-[10px]"></i> {{ 'schedules.late_not_entered' | t }}</div>
                                            }
                                            <div><i class="pi pi-clock mr-1 text-[10px]"></i> {{ 'schedules.shift_label' | t }}: {{ item.schedule?.start_time?.slice(0,5) }}</div>
                                            @if (item.notes) {
                                                <div class="italic text-[10px] text-surface-450">{{ item.notes }}</div>
                                            }
                                        </div>
                                        <div class="flex justify-end pt-1">
                                            @if (!item.isJustified && item.recordId) {
                                                <button (click)="showJustifyDialog(item)" 
                                                        class="px-2.5 py-1 text-[10px] font-bold rounded-lg border border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-800 dark:border-amber-900 dark:bg-amber-950/20 dark:text-amber-400 transition">
                                                    <i class="pi pi-shield mr-1"></i> {{ 'schedules.justify' | t }}
                                                </button>
                                            } @else if (item.isJustified) {
                                                <div class="text-[10px] text-teal-600 dark:text-teal-400 font-semibold flex items-center gap-1">
                                                    <i class="pi pi-check text-[9px]"></i> {{ 'schedules.justified_label' | t }}: {{ item.justificationReason || 'Aprobado' }}
                                                </div>
                                            }
                                        </div>
                                    </div>
                                    <div *ngIf="getMonitorCount('late') === 0" class="py-6 text-center text-xs text-surface-400 border border-dashed border-surface-200 dark:border-surface-800 rounded-2xl">
                                        {{ 'schedules.no_tardiness_today' | t }}
                                    </div>
                                </div>
                            </ng-container>
                            <ng-template #lateSkeleton>
                                <div class="space-y-2">
                                    <div *ngFor="let _ of [1,2]" class="bg-white dark:bg-surface-900 p-4 rounded-2xl border border-surface-200 dark:border-surface-800 shadow-sm space-y-3">
                                        <div class="flex justify-between items-start">
                                            <au-skeleton width="55%" height="16px" />
                                             <au-skeleton width="64px" height="18px" />
                                        </div>
                                        <au-skeleton width="70%" height="12px" />
                                        <au-skeleton width="50%" height="12px" />
                                        <div class="flex justify-end pt-1">
                                            <au-skeleton width="80px" height="24px" />
                                        </div>
                                    </div>
                                </div>
                            </ng-template>
                        </div>

                        <!-- Categoría: Pendientes de Entrada -->
                        <div class="space-y-3">
                            <h4 class="text-xs font-bold uppercase tracking-wider text-surface-500 flex items-center gap-2">
                                <span class="h-2 w-2 rounded-full bg-surface-300"></span> {{ 'schedules.pending_count' | t }} ({{ getMonitorCount('pending') }})
                            </h4>
                            <ng-container *ngIf="!loading; else pendingSkeleton">
                                <div class="space-y-2">
                                    <div *ngFor="let item of filterMonitor('pending')" class="bg-white dark:bg-surface-900 p-4 rounded-2xl border border-surface-200 dark:border-surface-800 shadow-sm space-y-2">
                                        <div class="flex justify-between items-start">
                                            <div class="font-bold text-surface-900 dark:text-white">{{ getEmployeeName(item.employee) }}</div>
                                            <div class="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400">
                                                {{ item.label }}
                                            </div>
                                        </div>
                                        <div class="text-xs text-surface-500 dark:text-surface-400 space-y-1">
                                            <div><i class="pi pi-clock mr-1 text-[10px]"></i> {{ 'schedules.shift_label' | t }}: {{ item.schedule?.start_time?.slice(0,5) }} a {{ item.schedule?.end_time?.slice(0,5) }}</div>
                                        </div>
                                    </div>
                                    <div *ngIf="getMonitorCount('pending') === 0" class="py-6 text-center text-xs text-surface-400 border border-dashed border-surface-200 dark:border-surface-800 rounded-2xl">
                                        {{ 'schedules.no_collab_pending' | t }}
                                    </div>
                                </div>
                            </ng-container>
                            <ng-template #pendingSkeleton>
                                <div class="space-y-2">
                                    <div *ngFor="let _ of [1,2]" class="bg-white dark:bg-surface-900 p-4 rounded-2xl border border-surface-200 dark:border-surface-800 shadow-sm space-y-2">
                                        <div class="flex justify-between items-start">
                                            <au-skeleton width="55%" height="16px" />
                                             <au-skeleton width="64px" height="18px" />
                                        </div>
                                        <au-skeleton width="70%" height="12px" />
                                    </div>
                                </div>
                            </ng-template>
                        </div>

                        <!-- Categoría: Ausentes / Fuera de turno -->
                        <div class="space-y-3">
                            <h4 class="text-xs font-bold uppercase tracking-wider text-red-650 flex items-center gap-2">
                                <span class="h-2 w-2 rounded-full bg-red-500"></span> {{ 'schedules.absent_or_free_count' | t }} ({{ getMonitorCount('absent_or_free') }})
                            </h4>
                            <ng-container *ngIf="!loading; else absentSkeleton">
                                <div class="space-y-2">
                                    <div *ngFor="let item of filterMonitor('absent_or_free')" class="bg-white dark:bg-surface-900 p-4 rounded-2xl border border-surface-200 dark:border-surface-800 shadow-sm space-y-3">
                                        <div class="flex justify-between items-start">
                                            <div class="font-bold text-surface-900 dark:text-white">{{ getEmployeeName(item.employee) }}</div>
                                            <div class="text-[10px] px-2 py-0.5 rounded-full font-semibold"
                                                 [ngClass]="item.status === 'absent' ? (item.isJustified ? 'bg-teal-100 text-teal-800 dark:bg-teal-950/30' : 'bg-red-100 text-red-800 dark:bg-red-950/30') : 'bg-surface-100 text-surface-600 dark:bg-surface-800'">
                                                {{ item.label }}
                                            </div>
                                        </div>
                                        <div class="text-xs text-surface-500 dark:text-surface-400 space-y-1">
                                            @if (item.status === 'absent') {
                                                <div class="text-red-500"><i class="pi pi-times-circle mr-1 text-[10px]"></i> {{ 'schedules.absent_shift' | t }}</div>
                                            } @else {
                                                <div><i class="pi pi-calendar mr-1 text-[10px]"></i> {{ 'schedules.no_shift_scheduled' | t }}</div>
                                            }
                                        </div>
                                        <div class="flex justify-end pt-1">
                                            @if (item.status === 'absent' && !item.isJustified && item.recordId) {
                                                <button (click)="showJustifyDialog(item)" 
                                                        class="px-2.5 py-1 text-[10px] font-bold rounded-lg border border-red-300 bg-red-50 hover:bg-red-100 text-red-800 dark:border-red-900 dark:bg-red-950/20 dark:text-red-450 transition">
                                                    <i class="pi pi-shield mr-1"></i> {{ 'schedules.justify_absence' | t }}
                                                </button>
                                            } @else if (item.status === 'absent' && item.isJustified) {
                                                <div class="text-[10px] text-teal-600 dark:text-teal-400 font-semibold flex items-center gap-1">
                                                    <i class="pi pi-check text-[9px]"></i> {{ 'schedules.justified_label' | t }}: {{ item.justificationReason || 'Aprobado' }}
                                                </div>
                                            }
                                        </div>
                                    </div>
                                    <div *ngIf="getMonitorCount('absent_or_free') === 0" class="py-6 text-center text-xs text-surface-400 border border-dashed border-surface-200 dark:border-surface-800 rounded-2xl">
                                        {{ 'schedules.empty_label' | t }}
                                    </div>
                                </div>
                            </ng-container>
                            <ng-template #absentSkeleton>
                                <div class="space-y-2">
                                    <div *ngFor="let _ of [1,2]" class="bg-white dark:bg-surface-900 p-4 rounded-2xl border border-surface-200 dark:border-surface-800 shadow-sm space-y-3">
                                        <div class="flex justify-between items-start">
                                            <au-skeleton width="55%" height="16px" />
                                             <au-skeleton width="64px" height="18px" />
                                        </div>
                                        <au-skeleton width="80%" height="12px" />
                                        <div class="flex justify-end pt-1">
                                            <au-skeleton width="90px" height="24px" />
                                        </div>
                                    </div>
                                </div>
                            </ng-template>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Modal de Justificación -->
            <div *ngIf="showJustifyModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
                <div class="w-full max-w-md bg-white dark:bg-surface-900 rounded-3xl border border-surface-200 dark:border-surface-800 shadow-2xl p-6 space-y-4">
                    <div class="flex justify-between items-center">
                        <h3 class="text-lg font-bold text-surface-900 dark:text-white">{{ 'schedules.justify_attendance_title' | t }}</h3>
                        <button (click)="showJustifyModal = false" class="text-surface-400 hover:text-surface-650 transition"><i class="pi pi-times"></i></button>
                    </div>
                    <div class="text-xs text-surface-600 dark:text-surface-400 leading-relaxed">
                        {{ t('schedules.justify_attendance_desc').replace('{name}', getEmployeeName(selectedMonitorItem?.employee)).replace('{date}', selectedMonitorItem?.record?.work_date ?? '') }}
                    </div>
                    <div class="space-y-1.5">
                        <label class="text-xs font-semibold text-surface-700 dark:text-surface-300">{{ 'schedules.detailed_reason' | t }}</label>
                        <textarea [(ngModel)]="justificationReason" rows="3" 
                            class="w-full p-3 border rounded-xl bg-white dark:bg-surface-800 border-surface-300 dark:border-surface-700 text-sm focus:ring-2 focus:ring-primary focus:outline-none" 
                            [placeholder]="'schedules.detailed_reason_placeholder' | t"></textarea>
                    </div>
                    <div class="flex gap-2 justify-end pt-2">
                        <button (click)="showJustifyModal = false" class="px-4 py-2 border rounded-xl text-xs font-semibold hover:bg-surface-50 dark:border-surface-700 dark:hover:bg-surface-800 transition">
                            {{ 'schedules.reject_delete' | t }}
                        </button>
                        <button (click)="submitJustification()" class="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-teal-600 hover:bg-teal-700 transition" [disabled]="!justificationReason || loading">
                            {{ 'schedules.apply_justification' | t }}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `
})
export class SchedulesManagement implements OnInit, OnDestroy {
    private readonly employeeService = inject(EmployeeService);
    private readonly authService = inject(AuthService);
    private readonly confirmationService = inject(ConfirmationService);
    private readonly branchService = inject(BranchService);
    private readonly planAccessService = inject(PlanAccessService);
    private readonly localeService = inject(LocaleService);

    private languageSub?: Subscription;

    t(key: string): string {
        return this.localeService.t(key as any);
    }

    // Navegación
    activeTab: 'shifts' | 'attendance' = 'shifts';

    loading = false;
    errorMessage = '';
    employees: any[] = [];
    schedules: any[] = [];
    attendanceRecords: any[] = [];
    
    // Matriz de horarios
    gridData: any[] = [];
    
    // Monitor de asistencia
    attendanceMonitorList: any[] = [];

    // Filtro local de sucursal
    selectedBranchFilter: number | null = null;
    branchesList: any[] = [];

    // Modales y estados
    showJustifyModal = false;
    selectedMonitorItem: any = null;
    justificationReason = '';

    selectedAttendanceEmployeeId: number | null = null;
    currentRole: string | null = null;

    days: { label: string; value: DayValue }[] = [];

    form: ScheduleFormState = this.createEmptyForm();

    get showBranchSelector(): boolean {
        return this.planAccessService.canAccessFeature('multi_location') && this.branchesList.length > 1;
    }

    getSchedulesNarrative(): string {
        if (!this.employees.length) {
            return this.t('schedules.no_employees_narrative');
        }

        return this.t('schedules.schedules_narrative')
            .replace('{count}', String(this.schedules.length))
            .replace('{records}', String(this.attendanceRecords.length));
    }

    ngOnInit(): void {
        this.updateDaysList();
        this.languageSub = this.localeService.languageChanged$.subscribe(() => {
            this.updateDaysList();
            if (this.employees.length > 0) {
                this.precalculateGrid();
                this.precalculateAttendanceMonitor();
            }
        });

        this.currentRole = this.authService.getCurrentUserRole();
        // Inicializar el filtro local con la sucursal activa global
        this.selectedBranchFilter = this.branchService.activeBranchId();
        // Cargar las sucursales disponibles en el negocio
        this.branchService.loadBranches().subscribe(branches => {
            this.branchesList = this.normalizeArray(branches);
        });
        this.loadData();
    }

    ngOnDestroy(): void {
        if (this.languageSub) {
            this.languageSub.unsubscribe();
        }
    }

    private updateDaysList(): void {
        this.days = [
            { label: this.t('schedules.day_monday'), value: 'monday' },
            { label: this.t('schedules.day_tuesday'), value: 'tuesday' },
            { label: this.t('schedules.day_wednesday'), value: 'wednesday' },
            { label: this.t('schedules.day_thursday'), value: 'thursday' },
            { label: this.t('schedules.day_friday'), value: 'friday' },
            { label: this.t('schedules.day_saturday'), value: 'saturday' },
            { label: this.t('schedules.day_sunday'), value: 'sunday' }
        ];
    }

    async loadData(): Promise<void> {
        this.loading = true;
        this.errorMessage = '';
        try {
            const params: any = {};
            // Filtrar localmente por sucursal
            if (this.selectedBranchFilter) {
                params.branch_id = this.selectedBranchFilter;
            }
            const [employeesResponse, schedulesResponse, attendanceResponse] = await Promise.all([
                firstValueFrom(this.employeeService.getEmployees(params)),
                firstValueFrom(this.employeeService.getSchedules(params)),
                firstValueFrom(this.employeeService.getAttendance(params))
            ]);
            this.employees = this.normalizeArray(employeesResponse);
            this.schedules = this.normalizeArray(schedulesResponse);
            this.attendanceRecords = this.normalizeArray(attendanceResponse);
            
            if (!this.selectedAttendanceEmployeeId && this.employees.length > 0) {
                this.selectedAttendanceEmployeeId = this.employees[0].id;
            }
            
            this.precalculateGrid();
            this.precalculateAttendanceMonitor();
        } catch (error: any) {
            this.errorMessage = error?.error?.error || this.t('schedules.error_load');
        } finally {
            this.loading = false;
        }
    }

    // Precalcular cuadrícula semanal
    precalculateGrid(): void {
        this.gridData = this.employees.map(emp => {
            const empSchedules = this.schedules.filter(s => s.employee === emp.id);
            const dayMap: Record<string, any> = {};
            this.days.forEach(day => {
                dayMap[day.value] = empSchedules.find(s => s.day_of_week === day.value) || null;
            });
            return {
                employee: emp,
                dayMap
            };
        });
    }

    // Precalcular monitor de asistencia
    precalculateAttendanceMonitor(): void {
        const todayStr = new Date().toISOString().split('T')[0];
        const days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
        const todayName = days[new Date().getDay()];

        this.attendanceMonitorList = this.employees.map(emp => {
            const schedule = this.schedules.find(s => s.employee === emp.id && s.day_of_week === todayName);
            const record = this.attendanceRecords.find(r => r.employee === emp.id && r.work_date === todayStr);

            let status = 'off_duty';
            let checkInTime = null;
            let checkOutTime = null;
            let recordId = null;
            let isJustified = false;
            let justificationReason = '';
            let notes = '';

            if (record) {
                recordId = record.id;
                isJustified = record.is_justified;
                justificationReason = record.justification_reason;
                notes = record.notes || '';

                if (record.check_out_at) {
                    status = 'completed';
                    checkInTime = record.check_in_at;
                    checkOutTime = record.check_out_at;
                } else if (record.check_in_at) {
                    status = record.status === 'late' ? 'late' : 'present';
                    checkInTime = record.check_in_at;
                } else if (record.status === 'absent') {
                    status = 'absent';
                }
            } else if (schedule) {
                // Verificar si ya va tarde según horario local
                const [shour, smin] = schedule.start_time.split(':').map(Number);
                const now = new Date();
                const target = new Date();
                target.setHours(shour, smin, 0, 0);

                if (now > target) {
                    status = 'late_pending';
                } else {
                    status = 'pending';
                }
            }

            const label = this.t('schedules.status.' + status);

            return {
                employee: emp,
                schedule,
                record,
                recordId,
                status,
                label,
                checkInTime,
                checkOutTime,
                isJustified,
                justificationReason,
                notes
            };
        });
    }

    // Acciones de Justificación
    showJustifyDialog(monitorItem: any): void {
        this.selectedMonitorItem = monitorItem;
        this.justificationReason = '';
        this.showJustifyModal = true;
    }

    async submitJustification(): Promise<void> {
        if (!this.selectedMonitorItem || !this.justificationReason) return;

        this.loading = true;
        this.errorMessage = '';
        try {
            await firstValueFrom(
                this.employeeService.justifyAttendance(this.selectedMonitorItem.recordId, this.justificationReason)
            );
            this.showJustifyModal = false;
            await this.loadData();
        } catch (error: any) {
            this.errorMessage = this.extractErrorMessage(error, 'schedules.error_save');
        } finally {
            this.loading = false;
        }
    }

    // Rápida asignación desde cuadrícula
    quickNewShift(employeeId: number, dayValue: DayValue): void {
        this.form = {
            id: null,
            employee: employeeId,
            day_of_week: dayValue,
            start_time: '09:00',
            end_time: '17:00'
        };
    }

    // Agrupación en el Monitor de Asistencia
    filterMonitor(group: 'present' | 'late' | 'pending' | 'absent_or_free'): any[] {
        if (group === 'present') {
            return this.attendanceMonitorList.filter(item => item.status === 'present' || item.status === 'completed');
        }
        if (group === 'late') {
            return this.attendanceMonitorList.filter(item => item.status === 'late' || item.status === 'late_pending');
        }
        if (group === 'pending') {
            return this.attendanceMonitorList.filter(item => item.status === 'pending');
        }
        if (group === 'absent_or_free') {
            return this.attendanceMonitorList.filter(item => item.status === 'absent' || item.status === 'off_duty');
        }
        return [];
    }

    getMonitorCount(group: 'present' | 'late' | 'pending' | 'absent_or_free'): number {
        return this.filterMonitor(group).length;
    }

    async saveSchedule(): Promise<void> {
        if (!this.form.employee || !this.form.start_time || !this.form.end_time) {
            this.errorMessage = this.t('schedules.error_incomplete');
            return;
        }

        this.loading = true;
        this.errorMessage = '';
        const payload = {
            employee: this.form.employee,
            day_of_week: this.form.day_of_week,
            start_time: this.toBackendTime(this.form.start_time),
            end_time: this.toBackendTime(this.form.end_time)
        };

        try {
            if (this.form.id) {
                await firstValueFrom(this.employeeService.updateSchedule(this.form.id, payload));
            } else {
                await firstValueFrom(this.employeeService.createSchedule(payload));
            }
            this.resetForm();
            await this.loadData();
        } catch (error: any) {
            this.errorMessage = this.extractErrorMessage(error, 'schedules.error_save');
        } finally {
            this.loading = false;
        }
    }

    editSchedule(schedule: any): void {
        this.form = {
            id: schedule.id,
            employee: schedule.employee,
            day_of_week: schedule.day_of_week,
            start_time: this.formatTimeForInput(schedule.start_time),
            end_time: this.formatTimeForInput(schedule.end_time)
        };
    }

    deleteSchedule(schedule: any): void {
        if (!this.canDeleteSchedule()) {
            return;
        }
        this.confirmationService.confirm({
            message: this.t('schedules.confirm_delete_msg'),
            header: this.t('schedules.confirm_delete_title'),
            icon: 'pi pi-exclamation-triangle',
            acceptLabel: this.t('schedules.accept_delete'),
            rejectLabel: this.t('schedules.reject_delete'),
            acceptButtonStyleClass: 'p-button-danger',
            accept: () => {
                void this.deleteScheduleConfirmed(schedule);
            }
        });
    }

    private async deleteScheduleConfirmed(schedule: any): Promise<void> {
        this.loading = true;
        this.errorMessage = '';
        try {
            await firstValueFrom(this.employeeService.deleteSchedule(schedule.id));
            await this.loadData();
        } catch (error: any) {
            this.errorMessage = this.extractErrorMessage(error, 'schedules.error_delete');
        } finally {
            this.loading = false;
        }
    }

    async performCheckIn(): Promise<void> {
        if (!this.selectedAttendanceEmployeeId) {
            return;
        }
        this.loading = true;
        this.errorMessage = '';
        try {
            await firstValueFrom(this.employeeService.checkIn(this.selectedAttendanceEmployeeId));
            await this.loadData();
        } catch (error: any) {
            this.errorMessage = this.extractErrorMessage(error, 'schedules.error_checkin');
        } finally {
            this.loading = false;
        }
    }

    async performCheckOut(): Promise<void> {
        if (!this.selectedAttendanceEmployeeId) {
            return;
        }
        this.loading = true;
        this.errorMessage = '';
        try {
            await firstValueFrom(this.employeeService.checkOut(this.selectedAttendanceEmployeeId));
            await this.loadData();
        } catch (error: any) {
            this.errorMessage = this.extractErrorMessage(error, 'schedules.error_checkout');
        } finally {
            this.loading = false;
        }
    }

    resetForm(): void {
        this.form = this.createEmptyForm();
    }

    canDeleteSchedule(): boolean {
        return this.currentRole === 'CLIENT_ADMIN';
    }

    getEmployeeName(employee: any): string {
        return employee?.user?.full_name || employee?.full_name || this.t('schedules.employee_fallback').replace('{id}', String(employee?.id ?? ''));
    }

    formatTimeForInput(time: string): string {
        if (!time) {
            return '';
        }
        return time.slice(0, 5);
    }

    private toBackendTime(time: string): string {
        return time.length === 5 ? `${time}:00` : time;
    }

    private normalizeArray<T>(value: any): T[] {
        if (Array.isArray(value)) {
            return value;
        }
        if (value?.results && Array.isArray(value.results)) {
            return value.results;
        }
        return [];
    }

    private createEmptyForm(): ScheduleFormState {
        return {
            id: null,
            employee: null,
            day_of_week: 'monday',
            start_time: '09:00',
            end_time: '17:00'
        };
    }

    private extractErrorMessage(error: any, fallbackKey: string): string {
        const fallback = this.t(fallbackKey as any) || 'Error al procesar la solicitud';
        if (!error?.error) return fallback;
        const errObj = error.error;
        if (typeof errObj === 'string') return errObj;
        if (errObj.detail) return errObj.detail;
        if (errObj.error) return errObj.error;
        if (errObj.non_field_errors) {
            return Array.isArray(errObj.non_field_errors) ? errObj.non_field_errors.join(', ') : String(errObj.non_field_errors);
        }
        const keys = Object.keys(errObj);
        if (keys.length > 0) {
            const firstKey = keys[0];
            const firstVal = errObj[firstKey];
            const prefix = firstKey !== 'non_field_errors' ? `${firstKey}: ` : '';
            return prefix + (Array.isArray(firstVal) ? firstVal.join(', ') : String(firstVal));
        }
        return fallback;
    }
}
