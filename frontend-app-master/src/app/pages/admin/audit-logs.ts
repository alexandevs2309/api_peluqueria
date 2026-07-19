import { Component, DestroyRef, OnInit, inject, computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { AuBtn } from '../../shared/components';
import { ActivityLogService, AuditLog, AuditSummaryBreakdown } from '../../core/services/activity-log/activity-log.service';
import { DatePipe } from '@angular/common';
import { MessageService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { environment } from '../../../environments/environment';

@Component({
    selector: 'app-audit-logs',
    standalone: true,
    imports: [
        FormsModule, ButtonModule, InputTextModule,
        DatePipe, ToastModule, AuBtn
    ],
    providers: [MessageService],
    template: `
        <p-toast></p-toast>

        <section class="mb-8 overflow-hidden rounded-[2rem] border border-surface-200/70 bg-surface-0 shadow-[0_24px_80px_-42px_rgba(15,23,42,0.45)] dark:border-surface-800 dark:bg-surface-900">
            <div class="relative overflow-hidden px-8 py-8 lg:px-10">
                <div class="hero-gradient"></div>
                <div class="relative grid gap-8 lg:grid-cols-[minmax(0,1.5fr)_minmax(320px,0.9fr)] lg:items-start">
                    <div>
                        <div class="mb-4 inline-flex items-center gap-2 rounded-full border border-surface-200 bg-surface-50/90 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.24em] text-surface-600 dark:border-surface-700 dark:bg-surface-800/80 dark:text-surface-300">
                            <i class="pi pi-list text-[0.7rem] text-primary"></i>
                            Auditoría
                        </div>
                        <h1 class="text-3xl font-semibold tracking-tight text-surface-950 dark:text-surface-0 lg:text-4xl">
                            Logs del sistema
                        </h1>
                        <p class="mt-3 max-w-2xl text-base leading-7 text-surface-600 dark:text-surface-300">
                            Monitorea cambios, errores y eventos de seguridad en toda la plataforma.
                        </p>
                    </div>
                    <div class="grid gap-3 grid-cols-2">
                        <article class="rounded-3xl border border-surface-200 bg-white/80 p-5 shadow-sm backdrop-blur dark:border-surface-700 dark:bg-surface-800/80">
                            <div class="text-xs font-semibold uppercase tracking-[0.24em] text-surface-500 dark:text-surface-400">Total</div>
                            <div class="mt-3 text-3xl font-semibold text-surface-950 dark:text-surface-0">{{ summary().total }}</div>
                        </article>
                        <article class="rounded-3xl border border-surface-200 bg-white/80 p-5 shadow-sm backdrop-blur dark:border-surface-700 dark:bg-surface-800/80">
                            <div class="text-xs font-semibold uppercase tracking-[0.24em] text-surface-500 dark:text-surface-400">Errores</div>
                            <div class="mt-3 text-3xl font-semibold text-red-600 dark:text-red-400">{{ summary().errors }}</div>
                        </article>
                        <article class="rounded-3xl border border-surface-200 bg-white/80 p-5 shadow-sm backdrop-blur dark:border-surface-700 dark:bg-surface-800/80">
                            <div class="text-xs font-semibold uppercase tracking-[0.24em] text-surface-500 dark:text-surface-400">Advertencias</div>
                            <div class="mt-3 text-3xl font-semibold text-yellow-600 dark:text-yellow-400">{{ summary().warnings }}</div>
                        </article>
                        <article class="rounded-3xl border border-surface-200 bg-white/80 p-5 shadow-sm backdrop-blur dark:border-surface-700 dark:bg-surface-800/80">
                            <div class="text-xs font-semibold uppercase tracking-[0.24em] text-surface-500 dark:text-surface-400">Últimas 24h</div>
                            <div class="mt-3 text-3xl font-semibold text-blue-600 dark:text-blue-400">{{ summary().last_24h }}</div>
                        </article>
                    </div>
                </div>
            </div>
        </section>

        <!-- Filters section -->
        <div class="mb-6 rounded-[2rem] border border-surface-200 bg-surface-0 p-6 shadow-sm dark:border-surface-800 dark:bg-surface-900">
            <div class="flex flex-wrap items-center justify-between gap-4 border-b border-surface-100 pb-4 dark:border-surface-800 mb-6">
                <div>
                    <div class="text-xs font-semibold uppercase tracking-[0.24em] text-surface-500 dark:text-surface-400">Filtros Avanzados</div>
                    <h4 class="m-0 mt-1 text-lg font-semibold text-surface-950 dark:text-surface-0">Filtrar registros de actividad</h4>
                </div>
                <button au-btn [icon]="'pi pi-filter-slash'" (click)="clearFilters()">Limpiar filtros</button>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-surface-500 mb-2">Fuente</label>
                    <select [(ngModel)]="selectedSource" (change)="filterLogs()"
                            class="w-full rounded-lg border border-surface-200 bg-surface-0 px-3 py-2 text-sm text-surface-700 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-200">
                        @for (opt of sourceOptions; track opt.value) {
                            <option [ngValue]="opt.value">{{ opt.label }}</option>
                        }
                    </select>
                </div>
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-surface-500 mb-2">Acción</label>
                    <select [(ngModel)]="selectedAction" (change)="filterLogs()"
                            class="w-full rounded-lg border border-surface-200 bg-surface-0 px-3 py-2 text-sm text-surface-700 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-200">
                        @for (opt of actionOptions; track opt.value) {
                            <option [ngValue]="opt.value">{{ opt.label }}</option>
                        }
                    </select>
                </div>
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-surface-500 mb-2">Fecha Inicio</label>
                    <input type="date" [(ngModel)]="startDate" (change)="filterLogs()"
                           class="w-full rounded-lg border border-surface-200 bg-surface-0 px-3 py-2 text-sm text-surface-700 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-200" />
                </div>
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-surface-500 mb-2">Fecha Fin</label>
                    <input type="date" [(ngModel)]="endDate" (change)="filterLogs()"
                           class="w-full rounded-lg border border-surface-200 bg-surface-0 px-3 py-2 text-sm text-surface-700 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-200" />
                </div>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <div class="rounded-[2rem] border border-surface-200 bg-surface-0 p-6 shadow-sm dark:border-surface-800 dark:bg-surface-900">
                <div class="text-xs font-semibold uppercase tracking-[0.24em] text-surface-500 dark:text-surface-400">Desglose</div>
                <h4 class="mt-2 mb-4 text-lg font-semibold text-surface-950 dark:text-surface-0">Acciones más frecuentes</h4>
                @if (actionsBreakdown().length) {
                    <div class="space-y-2">
                        @for (item of actionsBreakdown(); track item.action || $index) {
                            <div class="flex items-center justify-between rounded-xl border border-surface-200 dark:border-surface-800 px-4 py-2.5 bg-surface-50/50 dark:bg-surface-800/30">
                                <span class="text-sm font-medium text-surface-700 dark:text-surface-300">{{ formatActionLabel(item.action || 'N/A') }}</span>
                                <span class="inline-flex items-center rounded-md bg-blue-50 dark:bg-blue-900/20 px-2.5 py-0.5 text-xs font-medium text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">{{ item.count }}</span>
                            </div>
                        }
                    </div>
                } @else {
                    <div class="text-sm text-surface-500 py-4">Sin desglose disponible.</div>
                }
            </div>
            <div class="rounded-[2rem] border border-surface-200 bg-surface-0 p-6 shadow-sm dark:border-surface-800 dark:bg-surface-900">
                <div class="text-xs font-semibold uppercase tracking-[0.24em] text-surface-500 dark:text-surface-400">Desglose</div>
                <h4 class="mt-2 mb-4 text-lg font-semibold text-surface-950 dark:text-surface-0">Fuentes con más actividad</h4>
                @if (sourcesBreakdown().length) {
                    <div class="space-y-2">
                        @for (item of sourcesBreakdown(); track item.source || $index) {
                            <div class="flex items-center justify-between rounded-xl border border-surface-200 dark:border-surface-800 px-4 py-2.5 bg-surface-50/50 dark:bg-surface-800/30">
                                <span class="text-sm font-medium text-surface-700 dark:text-surface-300">{{ formatSourceLabel(item.source || 'N/A') }}</span>
                                <span class="inline-flex items-center rounded-md bg-surface-100 dark:bg-surface-800 px-2.5 py-0.5 text-xs font-medium text-surface-700 dark:text-surface-300 border border-surface-200 dark:border-surface-700">{{ item.count }}</span>
                            </div>
                        }
                    </div>
                } @else {
                    <div class="text-sm text-surface-500 py-4">Sin desglose disponible.</div>
                }
            </div>
        </div>

        <!-- Logs Table Card -->
        <div class="overflow-hidden rounded-[2rem] border border-surface-200/70 bg-surface-0 shadow-[0_24px_80px_-42px_rgba(15,23,42,0.45)] dark:border-surface-800 dark:bg-surface-900">
            <div class="flex flex-wrap items-center justify-between gap-4 border-b border-surface-200 px-6 py-5 dark:border-surface-800">
                <div>
                    <div class="text-xs font-semibold uppercase tracking-[0.24em] text-surface-500 dark:text-surface-400">Listado</div>
                    <div class="mt-1 text-lg font-semibold text-surface-950 dark:text-surface-0">Historial de eventos</div>
                </div>
                <div class="relative">
                    <i class="pi pi-search absolute left-3 top-1/2 -translate-y-1/2 text-surface-400 text-sm"></i>
                    <input
                        type="text"
                        placeholder="Buscar logs..."
                        (input)="onSearch($event)"
                        class="w-64 rounded-lg border border-surface-200 bg-surface-0 py-2 pl-9 pr-3 text-sm text-surface-700 placeholder:text-surface-400 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-200 dark:placeholder:text-surface-500"
                    />
                </div>
            </div>

            <!-- Móvil: Tarjetas apiladas -->
            <div class="block md:hidden p-1 space-y-3">
                @for (log of displayLogs(); track trackByLog($index, log)) {
                    <div class="bg-white dark:bg-surface-900 rounded-xl border border-surface-200 dark:border-surface-800 shadow-sm overflow-hidden" [class]="getRowClass(log.action)">
                        <div class="p-4">
                            <div class="flex items-start justify-between mb-3">
                                <div class="min-w-0">
                                    <h4 class="font-bold text-sm text-surface-900 dark:text-white truncate">{{ log.user?.email || 'Sistema' }}</h4>
                                    <div class="flex items-center gap-2 mt-1">
                                        <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
                                              [class.bg-emerald-100!]="getActionSeverity(log.action) === 'success'"
                                              [class.text-emerald-700!]="getActionSeverity(log.action) === 'success'"
                                              [class.dark:bg-emerald-900/30!]="getActionSeverity(log.action) === 'success'"
                                              [class.dark:text-emerald-300!]="getActionSeverity(log.action) === 'success'"
                                              [class.bg-blue-100!]="getActionSeverity(log.action) === 'info'"
                                              [class.text-blue-700!]="getActionSeverity(log.action) === 'info'"
                                              [class.dark:bg-blue-900/30!]="getActionSeverity(log.action) === 'info'"
                                              [class.dark:text-blue-300!]="getActionSeverity(log.action) === 'info'"
                                              [class.bg-amber-100!]="getActionSeverity(log.action) === 'warn'"
                                              [class.text-amber-700!]="getActionSeverity(log.action) === 'warn'"
                                              [class.dark:bg-amber-900/30!]="getActionSeverity(log.action) === 'warn'"
                                              [class.dark:text-amber-300!]="getActionSeverity(log.action) === 'warn'"
                                              [class.bg-rose-100!]="getActionSeverity(log.action) === 'danger'"
                                              [class.text-rose-700!]="getActionSeverity(log.action) === 'danger'"
                                              [class.dark:bg-rose-900/30!]="getActionSeverity(log.action) === 'danger'"
                                              [class.dark:text-rose-300!]="getActionSeverity(log.action) === 'danger'"
                                              [class.bg-surface-100!]="getActionSeverity(log.action) === 'secondary'"
                                              [class.text-surface-500!]="getActionSeverity(log.action) === 'secondary'"
                                              [class.dark:bg-surface-800!]="getActionSeverity(log.action) === 'secondary'"
                                              [class.dark:text-surface-400!]="getActionSeverity(log.action) === 'secondary'">
                                            {{ formatActionLabel(log.action) }}
                                        </span>
                                        <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
                                              [class.bg-emerald-100!]="getSourceSeverity(log.source) === 'success'"
                                              [class.text-emerald-700!]="getSourceSeverity(log.source) === 'success'"
                                              [class.dark:bg-emerald-900/30!]="getSourceSeverity(log.source) === 'success'"
                                              [class.dark:text-emerald-300!]="getSourceSeverity(log.source) === 'success'"
                                              [class.bg-blue-100!]="getSourceSeverity(log.source) === 'info'"
                                              [class.text-blue-700!]="getSourceSeverity(log.source) === 'info'"
                                              [class.dark:bg-blue-900/30!]="getSourceSeverity(log.source) === 'info'"
                                              [class.dark:text-blue-300!]="getSourceSeverity(log.source) === 'info'"
                                              [class.bg-amber-100!]="getSourceSeverity(log.source) === 'warn'"
                                              [class.text-amber-700!]="getSourceSeverity(log.source) === 'warn'"
                                              [class.dark:bg-amber-900/30!]="getSourceSeverity(log.source) === 'warn'"
                                              [class.dark:text-amber-300!]="getSourceSeverity(log.source) === 'warn'"
                                              [class.bg-rose-100!]="getSourceSeverity(log.source) === 'danger'"
                                              [class.text-rose-700!]="getSourceSeverity(log.source) === 'danger'"
                                              [class.dark:bg-rose-900/30!]="getSourceSeverity(log.source) === 'danger'"
                                              [class.dark:text-rose-300!]="getActionSeverity(log.source) === 'danger'"
                                              [class.bg-surface-100!]="getSourceSeverity(log.source) === 'secondary'"
                                              [class.text-surface-500!]="getSourceSeverity(log.source) === 'secondary'"
                                              [class.dark:bg-surface-800!]="getSourceSeverity(log.source) === 'secondary'"
                                              [class.dark:text-surface-400!]="getSourceSeverity(log.source) === 'secondary'">
                                            {{ formatSourceLabel(log.source) }}
                                        </span>
                                    </div>
                                </div>
                            </div>
                            <div class="text-sm text-surface-900 dark:text-surface-100 mb-2">{{ formatDescription(log.description) }}</div>
                            @if (log.extra_data && Object.keys(log.extra_data).length > 0) {
                                <div class="text-xs text-surface-500 dark:text-surface-400 mb-2 flex flex-wrap gap-x-2">
                                    @for (key of Object.keys(log.extra_data); track key; let last = $last) {
                                        @if (formatExtraDataValue(log.extra_data[key])) {
                                            <span>{{key}}: {{formatExtraDataValue(log.extra_data[key])}}{{!last ? ', ' : ''}}</span>
                                        }
                                    }
                                </div>
                            }
                            <div class="flex items-center justify-between pt-2 border-t border-surface-100 dark:border-surface-800">
                                <div class="flex items-center gap-2 text-xs text-surface-500 dark:text-surface-400">
                                    <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
                                          [class.bg-emerald-100!]="getActionSeverity(log.action) === 'success'"
                                          [class.text-emerald-700!]="getActionSeverity(log.action) === 'success'"
                                          [class.dark:bg-emerald-900/30!]="getActionSeverity(log.action) === 'success'"
                                          [class.dark:text-emerald-300!]="getActionSeverity(log.action) === 'success'"
                                          [class.bg-blue-100!]="getActionSeverity(log.action) === 'info'"
                                          [class.text-blue-700!]="getActionSeverity(log.action) === 'info'"
                                          [class.dark:bg-blue-900/30!]="getActionSeverity(log.action) === 'info'"
                                          [class.dark:text-blue-300!]="getActionSeverity(log.action) === 'info'"
                                          [class.bg-amber-100!]="getActionSeverity(log.action) === 'warn'"
                                          [class.text-amber-700!]="getActionSeverity(log.action) === 'warn'"
                                          [class.dark:bg-amber-900/30!]="getActionSeverity(log.action) === 'warn'"
                                          [class.dark:text-amber-300!]="getActionSeverity(log.action) === 'warn'"
                                          [class.bg-rose-100!]="getActionSeverity(log.action) === 'danger'"
                                          [class.text-rose-700!]="getActionSeverity(log.action) === 'danger'"
                                          [class.dark:bg-rose-900/30!]="getActionSeverity(log.action) === 'danger'"
                                          [class.dark:text-rose-300!]="getActionSeverity(log.action) === 'danger'"
                                          [class.bg-surface-100!]="getActionSeverity(log.action) === 'secondary'"
                                          [class.text-surface-500!]="getActionSeverity(log.action) === 'secondary'"
                                          [class.dark:bg-surface-800!]="getActionSeverity(log.action) === 'secondary'"
                                          [class.dark:text-surface-400!]="getActionSeverity(log.action) === 'secondary'">
                                        {{ getSeverityLabel(log.action) }}
                                    </span>
                                    <span>{{ log.ip_address || 'N/A' }}</span>
                                </div>
                                <span class="text-xs text-surface-500 dark:text-surface-400">{{ log.timestamp | date:'dd/MM/yyyy HH:mm' }}</span>
                            </div>
                        </div>
                    </div>
                } @empty {
                    <div class="py-8 text-center text-surface-500 dark:text-surface-400">
                        <div class="flex flex-col items-center gap-3">
                            <i class="pi pi-info-circle text-4xl block opacity-50"></i>
                            <p class="m-0 font-medium">No hay logs de auditoría disponibles</p>
                            <p class="text-xs opacity-75 m-0">Los logs aparecerán aquí cuando los usuarios realicen acciones en el sistema</p>
                        </div>
                    </div>
                }
                @if (totalPages() > 1) {
                    <div class="flex items-center justify-between px-2 py-2">
                        <span class="text-sm text-surface-500 dark:text-surface-400">{{ (currentPage() - 1) * pageSize + 1 }}–{{ min(currentPage() * pageSize, filteredLogs().length) }} de {{ filteredLogs().length }}</span>
                        <div class="flex items-center gap-2">
                            <button au-btn variant="ghost" [icon]="'pi pi-chevron-left'"
                                    [disabled]="currentPage() === 1" (click)="prevPage()"></button>
                            <span class="text-sm text-surface-500 dark:text-surface-400">{{ currentPage() }}/{{ totalPages() }}</span>
                            <button au-btn variant="ghost" [icon]="'pi pi-chevron-right'"
                                    [disabled]="currentPage() === totalPages()" (click)="nextPage()"></button>
                        </div>
                    </div>
                }
            </div>

            <!-- Desktop: Tabla -->
            <div class="hidden md:block">
            <div class="overflow-x-auto">
                <table class="w-full text-sm">
                    <thead>
                        <tr class="border-b border-surface-200 dark:border-surface-700 bg-surface-50/50 dark:bg-surface-800/50">
                            <th class="cursor-pointer select-none py-4 pl-6 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400" (click)="toggleSort('user.email')">
                                Usuario
                                <i class="pi ml-1" [class.pi-sort-up]="sortField() === 'user.email' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'user.email' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'user.email'"></i>
                            </th>
                            <th class="cursor-pointer select-none py-4 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400" (click)="toggleSort('action')">
                                Acción
                                <i class="pi ml-1" [class.pi-sort-up]="sortField() === 'action' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'action' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'action'"></i>
                            </th>
                            <th class="cursor-pointer select-none py-4 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400" (click)="toggleSort('source')">
                                Fuente
                                <i class="pi ml-1" [class.pi-sort-up]="sortField() === 'source' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'source' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'source'"></i>
                            </th>
                            <th class="py-4 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">Descripción</th>
                            <th class="py-4 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">Severidad</th>
                            <th class="py-4 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">IP</th>
                            <th class="cursor-pointer select-none py-4 pr-6 text-right text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400" (click)="toggleSort('timestamp')">
                                Fecha
                                <i class="pi ml-1" [class.pi-sort-up]="sortField() === 'timestamp' && sortOrder() === 'asc'" [class.pi-sort-down]="sortField() === 'timestamp' && sortOrder() === 'desc'" [class.pi-sort]="sortField() !== 'timestamp'"></i>
                            </th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-surface-100 dark:divide-surface-800">
                        @for (log of displayLogs(); track trackByLog($index, log)) {
                            <tr class="hover:bg-surface-50 dark:hover:bg-surface-800/50 transition-colors" [class]="getRowClass(log.action)">
                                <td class="py-4 pl-6 pr-4 font-medium text-surface-900 dark:text-surface-100">{{ log.user?.email || 'Sistema' }}</td>
                                <td class="py-4 pr-4">
                                    <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                                          [class.bg-emerald-100!]="getActionSeverity(log.action) === 'success'"
                                          [class.text-emerald-700!]="getActionSeverity(log.action) === 'success'"
                                          [class.dark:bg-emerald-900/30!]="getActionSeverity(log.action) === 'success'"
                                          [class.dark:text-emerald-300!]="getActionSeverity(log.action) === 'success'"
                                          [class.bg-blue-100!]="getActionSeverity(log.action) === 'info'"
                                          [class.text-blue-700!]="getActionSeverity(log.action) === 'info'"
                                          [class.dark:bg-blue-900/30!]="getActionSeverity(log.action) === 'info'"
                                          [class.dark:text-blue-300!]="getActionSeverity(log.action) === 'info'"
                                          [class.bg-amber-100!]="getActionSeverity(log.action) === 'warn'"
                                          [class.text-amber-700!]="getActionSeverity(log.action) === 'warn'"
                                          [class.dark:bg-amber-900/30!]="getActionSeverity(log.action) === 'warn'"
                                          [class.dark:text-amber-300!]="getActionSeverity(log.action) === 'warn'"
                                          [class.bg-rose-100!]="getActionSeverity(log.action) === 'danger'"
                                          [class.text-rose-700!]="getActionSeverity(log.action) === 'danger'"
                                          [class.dark:bg-rose-900/30!]="getActionSeverity(log.action) === 'danger'"
                                          [class.dark:text-rose-300!]="getActionSeverity(log.action) === 'danger'"
                                          [class.bg-surface-100!]="getActionSeverity(log.action) === 'secondary'"
                                          [class.text-surface-500!]="getActionSeverity(log.action) === 'secondary'"
                                          [class.dark:bg-surface-800!]="getActionSeverity(log.action) === 'secondary'"
                                          [class.dark:text-surface-400!]="getActionSeverity(log.action) === 'secondary'">
                                        {{ formatActionLabel(log.action) }}
                                    </span>
                                </td>
                                <td class="py-4 pr-4">
                                    <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                                          [class.bg-emerald-100!]="getSourceSeverity(log.source) === 'success'"
                                          [class.text-emerald-700!]="getSourceSeverity(log.source) === 'success'"
                                          [class.dark:bg-emerald-900/30!]="getSourceSeverity(log.source) === 'success'"
                                          [class.dark:text-emerald-300!]="getSourceSeverity(log.source) === 'success'"
                                          [class.bg-blue-100!]="getSourceSeverity(log.source) === 'info'"
                                          [class.text-blue-700!]="getSourceSeverity(log.source) === 'info'"
                                          [class.dark:bg-blue-900/30!]="getSourceSeverity(log.source) === 'info'"
                                          [class.dark:text-blue-300!]="getSourceSeverity(log.source) === 'info'"
                                          [class.bg-amber-100!]="getSourceSeverity(log.source) === 'warn'"
                                          [class.text-amber-700!]="getSourceSeverity(log.source) === 'warn'"
                                          [class.dark:bg-amber-900/30!]="getSourceSeverity(log.source) === 'warn'"
                                          [class.dark:text-amber-300!]="getSourceSeverity(log.source) === 'warn'"
                                          [class.bg-rose-100!]="getSourceSeverity(log.source) === 'danger'"
                                          [class.text-rose-700!]="getSourceSeverity(log.source) === 'danger'"
                                          [class.dark:bg-rose-900/30!]="getSourceSeverity(log.source) === 'danger'"
                                          [class.dark:text-rose-300!]="getSourceSeverity(log.source) === 'danger'"
                                          [class.bg-surface-100!]="getSourceSeverity(log.source) === 'secondary'"
                                          [class.text-surface-500!]="getSourceSeverity(log.source) === 'secondary'"
                                          [class.dark:bg-surface-800!]="getSourceSeverity(log.source) === 'secondary'"
                                          [class.dark:text-surface-400!]="getSourceSeverity(log.source) === 'secondary'">
                                        {{ formatSourceLabel(log.source) }}
                                    </span>
                                </td>
                                <td class="py-4 pr-4">
                                    <div class="max-w-md">
                                        <div class="text-surface-900 dark:text-surface-100">{{ formatDescription(log.description) }}</div>
                                        @if (log.extra_data && Object.keys(log.extra_data).length > 0) {
                                            <div class="text-xs text-surface-500 dark:text-surface-400 mt-1 space-x-1">
                                                @for (key of Object.keys(log.extra_data); track key; let last = $last) {
                                                    @if (formatExtraDataValue(log.extra_data[key])) {
                                                        <span>{{key}}: {{formatExtraDataValue(log.extra_data[key])}}{{!last ? ', ' : ''}}</span>
                                                    }
                                                }
                                            </div>
                                        }
                                    </div>
                                </td>
                                <td class="py-4 pr-4">
                                    <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                                          [class.bg-emerald-100!]="getActionSeverity(log.action) === 'success'"
                                          [class.text-emerald-700!]="getActionSeverity(log.action) === 'success'"
                                          [class.dark:bg-emerald-900/30!]="getActionSeverity(log.action) === 'success'"
                                          [class.dark:text-emerald-300!]="getActionSeverity(log.action) === 'success'"
                                          [class.bg-blue-100!]="getActionSeverity(log.action) === 'info'"
                                          [class.text-blue-700!]="getActionSeverity(log.action) === 'info'"
                                          [class.dark:bg-blue-900/30!]="getActionSeverity(log.action) === 'info'"
                                          [class.dark:text-blue-300!]="getActionSeverity(log.action) === 'info'"
                                          [class.bg-amber-100!]="getActionSeverity(log.action) === 'warn'"
                                          [class.text-amber-700!]="getActionSeverity(log.action) === 'warn'"
                                          [class.dark:bg-amber-900/30!]="getActionSeverity(log.action) === 'warn'"
                                          [class.dark:text-amber-300!]="getActionSeverity(log.action) === 'warn'"
                                          [class.bg-rose-100!]="getActionSeverity(log.action) === 'danger'"
                                          [class.text-rose-700!]="getActionSeverity(log.action) === 'danger'"
                                          [class.dark:bg-rose-900/30!]="getActionSeverity(log.action) === 'danger'"
                                          [class.dark:text-rose-300!]="getActionSeverity(log.action) === 'danger'"
                                          [class.bg-surface-100!]="getActionSeverity(log.action) === 'secondary'"
                                          [class.text-surface-500!]="getActionSeverity(log.action) === 'secondary'"
                                          [class.dark:bg-surface-800!]="getActionSeverity(log.action) === 'secondary'"
                                          [class.dark:text-surface-400!]="getActionSeverity(log.action) === 'secondary'">
                                        {{ getSeverityLabel(log.action) }}
                                    </span>
                                </td>
                                <td class="py-4 pr-4 text-surface-600 dark:text-surface-300">{{ log.ip_address || 'N/A' }}</td>
                                <td class="py-4 pr-6 text-right text-surface-600 dark:text-surface-300">{{ log.timestamp | date:'dd/MM/yyyy HH:mm' }}</td>
                            </tr>
                        } @empty {
                            <tr>
                                <td colspan="7" class="py-12 text-center text-surface-500 dark:text-surface-400">
                                    <div class="flex flex-col items-center gap-3">
                                        <i class="pi pi-info-circle text-4xl block opacity-50"></i>
                                        <p class="m-0 font-medium">No hay logs de auditoría disponibles</p>
                                        <p class="text-xs opacity-75 m-0">Los logs aparecerán aquí cuando los usuarios realicen acciones en el sistema</p>
                                    </div>
                                </td>
                            </tr>
                        }
                    </tbody>
                </table>
            </div>
            @if (totalPages() > 1) {
                <div class="flex items-center justify-between border-t border-surface-200 px-6 py-4 dark:border-surface-800">
                    <span class="text-sm text-surface-500 dark:text-surface-400">
                        Mostrando {{ (currentPage() - 1) * pageSize + 1 }}–{{ min(currentPage() * pageSize, filteredLogs().length) }} de {{ filteredLogs().length }}
                    </span>
                    <div class="flex items-center gap-2">
                        <button au-btn variant="ghost" [icon]="'pi pi-chevron-left'"
                                [disabled]="currentPage() === 1" (click)="prevPage()"></button>
                        @for (p of pages(); track p) {
                            <button au-btn [variant]="p === currentPage() ? 'primary' : 'ghost'"
                                    (click)="goToPage(p)">{{ p }}</button>
                        }
                        <button au-btn variant="ghost" [icon]="'pi pi-chevron-right'"
                                [disabled]="currentPage() === totalPages()" (click)="nextPage()"></button>
                    </div>
                </div>
            }
            </div>
        </div>
    `
})
export class AuditLogs implements OnInit {
    logs = signal<AuditLog[]>([]);
    summary = signal<{ total: number; errors: number; warnings: number; last_24h: number }>({
        total: 0,
        errors: 0,
        warnings: 0,
        last_24h: 0
    });
    actionsBreakdown = signal<AuditSummaryBreakdown[]>([]);
    sourcesBreakdown = signal<AuditSummaryBreakdown[]>([]);
    loading = signal(false);
    selectedAction: string | null = null;
    selectedSource: string | null = null;
    startDate: string | null = null;
    endDate: string | null = null;

    sortField = signal<string>('');
    sortOrder = signal<'asc' | 'desc'>('asc');
    globalFilter = signal('');
    currentPage = signal(1);
    pageSize = 20;

    filteredLogs = computed(() => {
        const filter = this.globalFilter().toLowerCase();
        if (!filter) return this.logs();
        return this.logs().filter(log =>
            (log.user?.email || 'Sistema').toLowerCase().includes(filter) ||
            (log.action || '').toLowerCase().includes(filter) ||
            (log.description || '').toLowerCase().includes(filter) ||
            (log.source || '').toLowerCase().includes(filter) ||
            (log.extra_data && JSON.stringify(log.extra_data).toLowerCase().includes(filter))
        );
    });

    sortedLogs = computed(() => {
        const field = this.sortField();
        const order = this.sortOrder();
        const list = [...this.filteredLogs()];

        if (!field) return list;

        list.sort((a: any, b: any) => {
            let aVal = a;
            let bVal = b;

            // Handle nested field sorting (e.g. 'user.email')
            if (field.includes('.')) {
                const parts = field.split('.');
                for (const part of parts) {
                    aVal = aVal ? aVal[part] : '';
                    bVal = bVal ? bVal[part] : '';
                }
            } else {
                aVal = a[field] ?? '';
                bVal = b[field] ?? '';
            }

            const cmp = typeof aVal === 'string' ? aVal.localeCompare(bVal) : (aVal > bVal ? 1 : -1);
            return order === 'asc' ? cmp : -cmp;
        });

        return list;
    });

    displayLogs = computed(() => {
        const start = (this.currentPage() - 1) * this.pageSize;
        return this.sortedLogs().slice(start, start + this.pageSize);
    });

    totalPages = computed(() => Math.max(1, Math.ceil(this.filteredLogs().length / this.pageSize)));

    pages = computed(() => {
        const tp = this.totalPages();
        return Array.from({ length: tp }, (_, i) => i + 1);
    });

    sourceOptions: { label: string; value: string | null }[] = [
        { label: 'Todas las fuentes', value: null },
        { label: 'Sistema', value: 'SYSTEM' },
        { label: 'Integraciones', value: 'INTEGRATIONS' },
        { label: 'Rendimiento', value: 'PERFORMANCE' },
        { label: 'Autenticacion', value: 'AUTH' },
        { label: 'Configuracion', value: 'SETTINGS' },
        { label: 'Roles y permisos', value: 'ROLES' },
        { label: 'Suscripciones', value: 'SUBSCRIPTIONS' },
        { label: 'Usuarios', value: 'USERS' }
    ];

    actionOptions: { label: string; value: string | null }[] = [
        { label: 'Todas las acciones', value: null },
        { label: 'Errores del sistema', value: 'SYSTEM_ERROR' },
        { label: 'Errores de integraciones', value: 'INTEGRATION_ERROR' },
        { label: 'Alertas de rendimiento', value: 'PERFORMANCE_ALERT' },
        { label: 'Errores de Stripe', value: 'STRIPE_ERROR' },
        { label: 'Errores de PayPal', value: 'PAYPAL_ERROR' },
        { label: 'Errores de Twilio', value: 'TWILIO_ERROR' },
        { label: 'Errores de SendGrid', value: 'SENDGRID_ERROR' }
    ];

    constructor(
        private activityLogService: ActivityLogService,
        private messageService: MessageService,
        private destroyRef: DestroyRef
    ) {}

    ngOnInit() {
        this.loadActions();
        this.loadSummary();
        this.loadLogs();
    }

    loadSummary() {
        this.activityLogService.getSummary().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (data: any) => {
                this.summary.set({
                    total: Number(data?.total_logs ?? data?.total ?? 0),
                    errors: Number(data?.error_logs ?? data?.errors ?? 0),
                    warnings: Number(data?.warning_logs ?? data?.warnings ?? 0),
                    last_24h: Number(data?.last_24h ?? data?.recent ?? 0)
                });
                this.actionsBreakdown.set(Array.isArray(data?.actions_breakdown) ? data.actions_breakdown : []);
                this.sourcesBreakdown.set(Array.isArray(data?.sources_breakdown) ? data.sources_breakdown : []);
            },
            error: () => {
                // Keep defaults if summary endpoint is unavailable.
                this.actionsBreakdown.set([]);
                this.sourcesBreakdown.set([]);
            }
        });
    }

    loadActions() {
        this.activityLogService.getActions().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (actions) => {
                this.actionOptions = [
                    { label: 'Todas las acciones', value: null },
                    ...actions.map(action => ({ label: action.label, value: action.value as string }))
                ];
            },
            error: (error) => {
                this.showErrorMessage('Error al cargar las acciones', error);
                this.actionOptions = [{ label: 'Todas las acciones', value: null }];
            }
        });
    }

    loadLogs() {
        this.loading.set(true);
        const params: any = {};

        if (this.selectedAction) {
            params.action = this.selectedAction;
        }

        if (this.startDate) {
            params.date_from = this.startDate;
        }

        if (this.endDate) {
            params.date_to = this.endDate;
        }

        if (this.selectedSource) {
            params.source = this.selectedSource;
        }

        this.activityLogService.getAuditLogs(params).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (response) => {
                const logs = (response.results || []).filter(log => this.isValidLog(log));
                this.logs.set(logs);
                this.currentPage.set(1);
                this.loading.set(false);
            },
            error: (error) => {
                this.showErrorMessage('Error al cargar los logs de auditoria', error);
                this.loading.set(false);
                this.logs.set([]);
            }
        });
    }

    filterLogs() {
        // Reload logs with filters applied on the server side
        this.loadLogs();
    }

    clearFilters() {
        this.selectedAction = null;
        this.selectedSource = null;
        this.startDate = null;
        this.endDate = null;
        this.loadLogs();
    }

    onSearch(event: Event) {
        this.globalFilter.set((event.target as HTMLInputElement).value);
        this.currentPage.set(1);
    }

    toggleSort(field: string) {
        if (this.sortField() === field) {
            this.sortOrder.set(this.sortOrder() === 'asc' ? 'desc' : 'asc');
        } else {
            this.sortField.set(field);
            this.sortOrder.set('asc');
        }
        this.currentPage.set(1);
    }

    prevPage() {
        if (this.currentPage() > 1) this.currentPage.update(p => p - 1);
    }

    nextPage() {
        if (this.currentPage() < this.totalPages()) this.currentPage.update(p => p + 1);
    }

    goToPage(page: number) {
        this.currentPage.set(page);
    }

    min(a: number, b: number): number {
        return Math.min(a, b);
    }

    getActionSeverity(action: string): 'success' | 'info' | 'warn' | 'danger' | 'secondary' | 'contrast' {
        switch (action) {
            case 'CREATE': return 'success';
            case 'UPDATE': return 'info';
            case 'DELETE': return 'danger';
            case 'LOGIN': return 'secondary';
            case 'LOGOUT': return 'secondary';
            case 'SYSTEM_ERROR':
            case 'STRIPE_ERROR':
            case 'PAYPAL_ERROR':
            case 'TWILIO_ERROR':
            case 'SENDGRID_ERROR':
            case 'INTEGRATION_ERROR': return 'danger';
            case 'PERFORMANCE_ALERT': return 'warn';
            default: return 'info';
        }
    }

    getSourceSeverity(source: string): 'success' | 'info' | 'warn' | 'danger' | 'secondary' | 'contrast' {
        switch (source) {
            case 'INTEGRATIONS': return 'warn';
            case 'PERFORMANCE': return 'info';
            case 'SYSTEM': return 'secondary';
            case 'AUTH': return 'success';
            default: return 'secondary';
        }
    }

    getRowClass(action: string): string {
        if (action.includes('ERROR')) {
            return 'bg-red-50 dark:bg-red-900/10';
        }
        if (action === 'PERFORMANCE_ALERT') {
            return 'bg-yellow-50 dark:bg-yellow-900/10';
        }
        return '';
    }

    getSeverityLabel(action: string): string {
        if (action.includes('ERROR')) {
            return 'Error';
        }
        if (action === 'PERFORMANCE_ALERT') {
            return 'Advertencia';
        }
        if (action === 'CREATE') {
            return 'Exito';
        }
        if (action === 'UPDATE') {
            return 'Info';
        }
        if (action === 'DELETE') {
            return 'Critico';
        }
        return 'Info';
    }

    getLogStats(): string {
        const total = this.filteredLogs().length;
        const errors = this.filteredLogs().filter(log => log.action.includes('ERROR')).length;
        const alerts = this.filteredLogs().filter(log => log.action === 'PERFORMANCE_ALERT').length;
        return `${total} logs (${errors} errores, ${alerts} alertas)`;
    }

    Object = Object;

    trackByLog(index: number, log: AuditLog): any {
        return log.id || `${log.timestamp}-${index}`;
    }

    trackByKey(index: number, key: string): string {
        return key;
    }

    formatExtraDataValue(value: any): string {
        if (value === null || value === undefined) {
            return 'null';
        }
        if (typeof value === 'object') {
            try {
                const jsonStr = JSON.stringify(value);
                // Don't show empty objects
                if (jsonStr === '{}' || jsonStr === '[]') {
                    return '';
                }
                return jsonStr;
            } catch (error) {
                return '[Complex Object]';
            }
        }
        return String(value);
    }

    isValidLog(log: any): boolean {
        // Filter out meaningless logs
        if (!log.description || log.description.trim() === '') {
            return false;
        }
        
        // Filter out periodic tasks with no real changes
        if (log.description.includes('periodic task') && 
            log.extra_data && 
            JSON.stringify(log.extra_data).includes('{}')) {
            return false;
        }
        
        // Filter out system updates with no meaningful data
        if (log.action === 'UPDATE' && 
            log.source === 'SYSTEM' && 
            log.description.includes('changes: {}')) {
            return false;
        }
        
        return true;
    }

    formatDescription(description: string): string {
        if (!description) return '';
        
        // Fix spacing issues
        return description
            .replace(/([a-z])([A-Z])/g, '$1 $2') // Add space between camelCase
            .replace(/track updated/g, 'track updated ') // Fix specific spacing
            .replace(/changes:\s*\{\}/g, '') // Remove empty changes
            .trim();
    }

    formatActionLabel(action: string): string {
        const labels: Record<string, string> = {
            SYSTEM_ERROR: 'Error de sistema',
            INTEGRATION_ERROR: 'Error de integracion',
            PERFORMANCE_ALERT: 'Alerta de rendimiento',
            STRIPE_ERROR: 'Error de Stripe',
            PAYPAL_ERROR: 'Error de PayPal',
            TWILIO_ERROR: 'Error de Twilio',
            SENDGRID_ERROR: 'Error de SendGrid',
            LOGIN: 'Inicio de sesion',
            LOGOUT: 'Cierre de sesion',
            CREATE: 'Creacion',
            UPDATE: 'Actualizacion',
            DELETE: 'Eliminacion'
        };
        return labels[action] || action;
    }

    formatSourceLabel(source: string): string {
        const labels: Record<string, string> = {
            SYSTEM: 'Sistema',
            INTEGRATIONS: 'Integraciones',
            PERFORMANCE: 'Rendimiento',
            AUTH: 'Autenticacion',
            SETTINGS: 'Configuracion',
            ROLES: 'Roles y permisos',
            SUBSCRIPTIONS: 'Suscripciones',
            USERS: 'Usuarios'
        };
        return labels[source] || source;
    }

    private showErrorMessage(message: string, error?: any): void {
        this.logError(message, error);
        this.messageService.add({
            severity: 'error',
            summary: 'Error',
            detail: this.sanitizeErrorMessage(error, message),
            life: 3000
        });
    }

    private sanitizeErrorMessage(error: any, fallback: string): string {
        const errorMessage = error?.message || error?.error?.message;
        return typeof errorMessage === 'string' ? errorMessage.substring(0, 200) : fallback;
    }

    private logError(context: string, error: any): void {
        const errorInfo = {
            context,
            timestamp: new Date().toISOString(),
            error: error?.message || 'Unknown error',
            component: 'AuditLogs'
        };
        if (!environment.production) console.error(errorInfo);
    }
}
