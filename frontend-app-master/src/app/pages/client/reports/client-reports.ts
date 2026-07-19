import { ChangeDetectionStrategy, Component, DestroyRef, OnInit, inject, signal, effect, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { CardModule } from 'primeng/card';
import { DatePickerModule } from 'primeng/datepicker';
import { SelectModule } from 'primeng/select';
import { ButtonModule } from 'primeng/button';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ProgressBarModule } from 'primeng/progressbar';
import { ToastModule } from 'primeng/toast';
import { MessageService } from 'primeng/api';
import { DashboardService } from '../../../core/services/dashboard/dashboard.service';
import { TenantService } from '../../../core/services/tenant/tenant.service';
import { SettingsService } from '../../../core/services/settings/settings.service';
import { PlanAccessService } from '../../../core/services/plan-access.service';
import { environment } from '../../../../environments/environment';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ClientRevenueChartComponent } from './components/client-revenue-chart.component';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { I18nPipe } from '../../../core/pipes/i18n.pipe';
import { BranchService } from '../../../core/services/branch/branch.service';
import { PosService } from '../../../core/services/pos/pos.service';
import { AuronEyebrowComponent } from '../../../shared/components/auron-eyebrow/auron-eyebrow.component';
import { AuBtn } from '../../../shared/components';

@Component({
    selector: 'app-client-reports',
    standalone: true,
    imports: [
        CommonModule,
        ReactiveFormsModule,
        CardModule,
        DatePickerModule,
        SelectModule,
        ButtonModule,
        TableModule,
        TagModule,
        ProgressBarModule,
        ToastModule,
        ClientRevenueChartComponent,
        I18nPipe,
        AuronEyebrowComponent,
        AuBtn
    ],
    providers: [MessageService],
    changeDetection: ChangeDetectionStrategy.OnPush,
    template: `
<div class="w-full p-6 space-y-8 transition-colors">
  <section class="overflow-hidden rounded-[2rem] border border-surface-200/70 bg-surface-0 shadow-[var(--shadow-elevated)] dark:border-surface-800 dark:bg-surface-900">
    <div class="relative overflow-hidden px-8 py-8 lg:px-10">
      <div class="hero-gradient"></div>
      <div class="relative space-y-7">
        <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <auron-eyebrow class="mb-4 block" icon="pi pi-chart-bar" label="Lectura del negocio"></auron-eyebrow>
            <h1 class="display-3 text-surface-950 dark:text-surface-0">{{ branding().businessName }}</h1>
            <p class="mt-3 max-w-4xl text-base leading-7 text-surface-600 dark:text-surface-300">
              {{ getReportHeadline() }}
            </p>
          </div>
          <img *ngIf="branding().logoUrl" [src]="branding().logoUrl!" alt="Logo negocio" class="h-14 w-14 rounded-2xl bg-white/10 object-contain p-2 dark:bg-surface-700/50" />
        </div>

        <div class="flex flex-wrap items-center gap-3 text-sm text-surface-500 dark:text-surface-400">
          <div class="inline-flex items-center gap-2 rounded-full bg-surface-100 px-3 py-1.5 dark:bg-surface-800">
            <i class="pi pi-calendar text-xs"></i>
            {{ getActiveRangeLabel() }}
          </div>
          <div class="inline-flex items-center gap-2 rounded-full bg-surface-100 px-3 py-1.5 dark:bg-surface-800">
            <i class="pi pi-chart-line text-xs"></i>
            {{ filteredRevenue().length }} {{ (filteredRevenue().length === 1 ? 'reports.month_visible' : 'reports.months_visible') | t }}
          </div>
          <div class="inline-flex items-center gap-2 rounded-full bg-surface-100 px-3 py-1.5 dark:bg-surface-800">
            <i class="pi pi-wallet text-xs"></i>
            {{ activeTab() === 'cash_registers' ? 'Cierres de caja' : 'Ingresos del POS' }}
          </div>
        </div>

        <div class="grid gap-3 md:grid-cols-3">
          <div class="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 dark:border-emerald-900/60 dark:bg-emerald-900/10">
            <div class="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700 dark:text-emerald-300">{{ 'reports.best_month' | t }}</div>
            <div class="mt-2 text-2xl font-semibold text-emerald-900 dark:text-emerald-100">{{ getBestMonthLabel() }}</div>
          </div>
          <div class="rounded-2xl border border-[var(--brand)]/20 bg-[rgba(26,86,219,0.06)] px-4 py-3 dark:border-[var(--brand)]/30 dark:bg-[rgba(26,86,219,0.08)]">
            <div class="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--brand)] dark:text-[var(--brand-400)]">{{ 'reports.peak_revenue' | t }}</div>
            <div class="mt-2 text-2xl font-semibold text-surface-900 dark:text-surface-0">{{ formatearMoneda(getMaxRevenue()) }}</div>
          </div>
          <div class="rounded-2xl border border-surface-200 bg-surface-50/70 px-4 py-3 dark:border-surface-700 dark:bg-surface-800/50">
            <div class="text-xs font-semibold uppercase tracking-[0.18em] text-surface-500 dark:text-surface-400">{{ 'reports.average_visible' | t }}</div>
            <div class="mt-2 text-2xl font-semibold text-surface-900 dark:text-surface-0">{{ formatearMoneda(getAverageRevenue()) }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="border-t border-surface-200/80 px-6 py-6 dark:border-surface-800 lg:px-8">
      <form [formGroup]="filtrosForm" class="grid gap-3 xl:grid-cols-[1fr,1fr,auto,auto]">
        <p-datePicker formControlName="fechaInicio" [placeholder]="'reports.start_date' | t" [showIcon]="true" dateFormat="dd/mm/yy"></p-datePicker>
        <p-datePicker formControlName="fechaFin" [placeholder]="'reports.end_date' | t" [showIcon]="true" dateFormat="dd/mm/yy"></p-datePicker>
        <button au-btn type="button" icon="pi pi-filter" (click)="aplicarFiltros()">{{ 'reports.apply_filter' | t }}</button>
        <button au-btn type="button" variant="danger" icon="pi pi-file-pdf" (click)="descargarReportePDF()">{{ 'reports.export_pdf' | t }}</button>
        <button *ngIf="canExportReports" au-btn type="button" variant="primary" icon="pi pi-file-excel" (click)="descargarReporteExcel(activeTab() === 'cash_registers' ? 'cash_registers' : 'sales')">Exportar Excel</button>
      </form>
    </div>
  </section>

  <div class="flex gap-4 border-b border-surface-200 dark:border-surface-800 pb-2 mb-4">
    <button pButton type="button" 
            [label]="'Ingresos'" 
            icon="pi pi-chart-line"
            [class]="activeTab() === 'revenue' ? 'p-button-text font-bold text-primary border-b-2 border-primary rounded-none !py-1' : 'p-button-text p-button-secondary rounded-none !py-1'"
            (click)="activeTab.set('revenue')"></button>
    <button pButton type="button" 
            [label]="'Cierres de Caja'" 
            icon="pi pi-inbox"
            [class]="activeTab() === 'cash_registers' ? 'p-button-text font-bold text-primary border-b-2 border-primary rounded-none !py-1' : 'p-button-text p-button-secondary rounded-none !py-1'"
            (click)="activeTab.set('cash_registers'); cargarCajas()"></button>
  </div>

  @if (loading() || (activeTab() === 'cash_registers' && loadingCajas())) {
    <div class="rounded-[1.75rem] border border-surface-200 bg-white p-10 text-center text-surface-500 shadow-sm dark:border-surface-700 dark:bg-surface-900 dark:text-surface-300">
      {{ 'reports.loading' | t }}
    </div>
  } @else if (loadError(); as errorMessage) {
    <div class="rounded-[1.75rem] border border-surface-200 bg-white p-10 text-center shadow-sm dark:border-surface-700 dark:bg-surface-900">
      <div class="text-lg font-semibold text-red-600 mb-2">{{ 'reports.load_error' | t }}</div>
      <p class="text-surface-600 dark:text-surface-300 mb-4">{{ errorMessage }}</p>
      <button au-btn type="button" icon="pi pi-refresh" (click)="cargarDatos()">{{ 'reports.retry' | t }}</button>
    </div>
  } @else {
    @if (activeTab() === 'revenue') {
      <section class="grid grid-cols-1 gap-5 md:grid-cols-2 2xl:grid-cols-4">
        <article *ngFor="let card of kpiCards" class="rounded-[1.6rem] border border-surface-200 bg-white p-5 shadow-sm transition-transform duration-150 hover:-translate-y-0.5 dark:border-surface-700 dark:bg-surface-900">
          <div class="text-[11px] font-semibold uppercase tracking-[0.22em] text-surface-500 dark:text-surface-400">{{ card.label }}</div>
          <div [ngClass]="card.color" class="mt-3 text-3xl font-black tracking-tight">{{ card.value }}</div>
          <div class="mt-4 flex items-center justify-between text-sm text-surface-500 dark:text-surface-400">
            <span>{{ card.trendText }}</span>
            <i class="pi pi-arrow-up-right text-xs text-surface-400"></i>
          </div>
        </article>
      </section>

      <section class="grid gap-6 2xl:grid-cols-[1.3fr,0.7fr]">
        <article class="rounded-[1.75rem] border border-surface-200 bg-white p-6 shadow-sm dark:border-surface-700 dark:bg-surface-900">
          <div class="mb-5 flex items-start justify-between gap-4">
            <div>
              <h5 class="text-xl font-bold text-surface-900 dark:text-white">{{ 'reports.revenue_trend' | t }}</h5>
              <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">{{ 'reports.trend_description' | t }}</p>
            </div>
            <div class="rounded-2xl bg-surface-100 px-3 py-2 text-right text-xs text-surface-500 dark:bg-surface-800 dark:text-surface-300">
              <div class="font-semibold uppercase tracking-[0.2em]">{{ 'reports.range' | t }}</div>
              <div class="mt-1 text-sm font-bold text-surface-800 dark:text-white">{{ getActiveRangeLabel() }}</div>
            </div>
          </div>

          @if (filteredRevenue().length > 0) {
            <div class="h-[22rem]">
              @defer (on viewport) {
                <app-client-revenue-chart [data]="chartIngresos" [options]="chartOptions"></app-client-revenue-chart>
              } @placeholder {
                <div class="h-[22rem] animate-pulse rounded-2xl bg-surface-100 dark:bg-surface-800"></div>
              }
            </div>
          } @else {
            <div class="flex h-[22rem] items-center justify-center rounded-2xl border border-dashed border-surface-300 text-surface-500 dark:border-surface-700 dark:text-surface-400">
              {{ 'reports.no_data_range' | t }}
            </div>
          }
        </article>

        <article class="rounded-[1.75rem] border border-surface-200 bg-white p-6 shadow-sm dark:border-surface-700 dark:bg-surface-900">
          <div class="mb-5">
            <h5 class="text-xl font-bold text-surface-900 dark:text-white">{{ 'reports.quick_read' | t }}</h5>
            <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">{{ 'reports.quick_read_desc' | t }}</p>
          </div>

          <div class="space-y-4">
            <div class="rounded-2xl bg-surface-100 p-4 dark:bg-surface-800">
              <div class="text-[11px] uppercase tracking-[0.2em] text-surface-500 dark:text-surface-400">{{ 'reports.lead_month' | t }}</div>
              <div class="mt-2 text-lg font-bold text-surface-900 dark:text-white">{{ getBestMonthLabel() }}</div>
              <div class="mt-1 text-sm text-surface-500 dark:text-surface-400">{{ formatearMoneda(getMaxRevenue()) }}</div>
            </div>

            <div class="rounded-2xl bg-surface-100 p-4 dark:bg-surface-800">
              <div class="text-[11px] uppercase tracking-[0.2em] text-surface-500 dark:text-surface-400">{{ 'reports.average_visible' | t }}</div>
              <div class="mt-2 text-lg font-bold text-surface-900 dark:text-white">{{ formatearMoneda(getAverageRevenue()) }}</div>
              <div class="mt-1 text-sm text-surface-500 dark:text-surface-400">{{ 'reports.calculated_on_revenue' | t }}</div>
            </div>

            <div class="rounded-2xl border border-surface-200 p-4 dark:border-surface-700">
              <div class="text-sm leading-6 text-surface-600 dark:text-surface-300">
                {{ getReportNarrative() }}
              </div>
            </div>
          </div>
        </article>
      </section>

      <section class="rounded-[1.75rem] border border-surface-200 bg-white p-6 shadow-sm dark:border-surface-700 dark:bg-surface-900">
        <div class="mb-5 flex items-center justify-between gap-4">
          <div>
            <h5 class="text-xl font-bold text-surface-900 dark:text-white">{{ 'reports.monthly_detail' | t }}</h5>
            <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">{{ 'reports.monthly_detail_desc' | t }}</p>
          </div>
          <span class="rounded-full bg-surface-100 px-3 py-1 text-sm text-surface-500 dark:bg-surface-800 dark:text-surface-300">{{ filteredRevenue().length }} {{ (filteredRevenue().length === 1 ? 'reports.month' : 'reports.months') | t }}</span>
        </div>

        @if (filteredRevenue().length > 0) {
          <p-table [value]="filteredRevenue()" responsiveLayout="scroll" styleClass="p-datatable-sm">
            <ng-template pTemplate="header">
              <tr>
                <th>{{ 'reports.table.month' | t }}</th>
                <th>{{ 'reports.table.revenue' | t }}</th>
                <th>{{ 'reports.table.share' | t }}</th>
              </tr>
            </ng-template>
            <ng-template pTemplate="body" let-row>
              <tr>
                <td>
                  <div class="font-semibold text-surface-900 dark:text-white">{{ row.month || 'Mes' }}</div>
                </td>
                <td>
                  <div class="font-semibold text-surface-900 dark:text-white">{{ formatearMoneda(toRevenueValue(row.revenue)) }}</div>
                </td>
                <td class="min-w-[220px]">
                  <div class="flex items-center gap-3">
                    <p-progressBar [value]="getRevenueShare(row.revenue)" [showValue]="false" styleClass="flex-1 h-2"></p-progressBar>
                    <span class="text-sm font-medium text-surface-500 dark:text-surface-300">{{ getRevenueShare(row.revenue) }}%</span>
                  </div>
                </td>
              </tr>
            </ng-template>
          </p-table>
        } @else {
          <div class="py-12 text-center text-surface-500 dark:text-surface-400">
            {{ 'reports.no_revenue_period' | t }}
          </div>
        }
      </section>
    } @else if (activeTab() === 'cash_registers') {
      <section class="grid grid-cols-1 gap-5 md:grid-cols-2 2xl:grid-cols-4 mb-6">
        <article class="rounded-[1.6rem] border border-surface-200 bg-white p-5 shadow-sm transition-transform duration-150 hover:-translate-y-0.5 dark:border-surface-700 dark:bg-surface-900">
          <div class="text-[11px] font-semibold uppercase tracking-[0.22em] text-surface-500 dark:text-surface-400">Sesiones Cerradas</div>
          <div class="mt-3 text-3xl font-black tracking-tight text-[var(--brand)] dark:text-[var(--brand-400)]">{{ cashRegisterKpis().totalCount }}</div>
          <div class="mt-4 flex items-center justify-between text-sm text-surface-500 dark:text-surface-400">
            <span>En el período seleccionado</span>
            <i class="pi pi-inbox text-xs text-surface-400"></i>
          </div>
        </article>
        <article class="rounded-[1.6rem] border border-surface-200 bg-white p-5 shadow-sm transition-transform duration-150 hover:-translate-y-0.5 dark:border-surface-700 dark:bg-surface-900">
          <div class="text-[11px] font-semibold uppercase tracking-[0.22em] text-surface-500 dark:text-surface-400">Ventas en Efectivo</div>
          <div class="mt-3 text-3xl font-black tracking-tight text-[var(--brand)] dark:text-[var(--brand-400)]">{{ formatearMoneda(cashRegisterKpis().totalCashSales) }}</div>
          <div class="mt-4 flex items-center justify-between text-sm text-surface-500 dark:text-surface-400">
            <span>Registrado en caja</span>
            <i class="pi pi-dollar text-xs text-surface-400"></i>
          </div>
        </article>
        <article class="rounded-[1.6rem] border border-surface-200 bg-white p-5 shadow-sm transition-transform duration-150 hover:-translate-y-0.5 dark:border-surface-700 dark:bg-surface-900">
          <div class="text-[11px] font-semibold uppercase tracking-[0.22em] text-surface-500 dark:text-surface-400">Total Faltantes (Shortages)</div>
          <div class="mt-3 text-3xl font-black tracking-tight text-red-600 dark:text-red-300">{{ formatearMoneda(cashRegisterKpis().totalShortage) }}</div>
          <div class="mt-4 flex items-center justify-between text-sm text-red-600 dark:text-red-400 font-semibold">
            <span>Pérdidas de cuadre</span>
            <i class="pi pi-arrow-down text-xs"></i>
          </div>
        </article>
        <article class="rounded-[1.6rem] border border-surface-200 bg-white p-5 shadow-sm transition-transform duration-150 hover:-translate-y-0.5 dark:border-surface-700 dark:bg-surface-900">
          <div class="text-[11px] font-semibold uppercase tracking-[0.22em] text-surface-500 dark:text-surface-400">Balance de Discrepancia</div>
          <div class="mt-3 text-3xl font-black tracking-tight" [ngClass]="cashRegisterKpis().netBalance < 0 ? 'text-red-600 dark:text-red-300' : 'text-emerald-600 dark:text-emerald-300'">
            {{ cashRegisterKpis().netBalance > 0 ? '+' : '' }}{{ formatearMoneda(cashRegisterKpis().netBalance) }}
          </div>
          <div class="mt-4 flex items-center justify-between text-sm text-surface-500 dark:text-surface-400">
            <span>{{ cashRegisterKpis().netBalance < 0 ? 'Déficit acumulado' : (cashRegisterKpis().netBalance > 0 ? 'Superávit acumulado' : 'Sin diferencias') }}</span>
            <i class="pi pi-sliders-h text-xs text-surface-400"></i>
          </div>
        </article>
      </section>

      <section class="rounded-[1.75rem] border border-surface-200 bg-white p-6 shadow-sm dark:border-surface-700 dark:bg-surface-900">
        <div class="mb-5">
          <h5 class="text-xl font-bold text-surface-900 dark:text-white">Cierres y Arqueos de Caja</h5>
          <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">Historial de sesiones de caja con control de discrepancias, faltantes y sobrantes.</p>
        </div>

        @if (filteredCashRegisters().length > 0) {
          <p-table [value]="filteredCashRegisters()" responsiveLayout="scroll" styleClass="p-datatable-sm">
            <ng-template pTemplate="header">
              <tr>
                <th>Apertura</th>
                <th>Cierre</th>
                <th>Usuario</th>
                <th>Monto Inicial</th>
                <th>Ventas Efectivo</th>
                <th>Esperado</th>
                <th>Declarado</th>
                <th>Diferencia</th>
                <th>Estado</th>
              </tr>
            </ng-template>
            <ng-template pTemplate="body" let-row>
              <tr>
                <td>{{ row.opened_at | date:'dd/MM/yyyy HH:mm' }}</td>
                <td>{{ row.closed_at ? (row.closed_at | date:'dd/MM/yyyy HH:mm') : '—' }}</td>
                <td>{{ row.user_name || '—' }}</td>
                <td class="font-mono">{{ formatearMoneda(toNum(row.initial_cash)) }}</td>
                <td class="font-mono">{{ formatearMoneda(toNum(row.sales_amount)) }}</td>
                <td class="font-mono font-semibold text-surface-700 dark:text-surface-300">
                  {{ formatearMoneda(toNum(row.initial_cash) + toNum(row.sales_amount)) }}
                </td>
                <td class="font-mono font-semibold">
                  {{ row.is_open ? '—' : formatearMoneda(toNum(row.final_cash)) }}
                </td>
                <td>
                  @if (row.is_open) {
                    <span class="text-surface-400 font-medium">Abierta</span>
                  } @else {
                    @if (getDiff(row) === 0) {
                      <p-tag severity="success" value="Cuadrado (0.00)" />
                    } @else if (getDiff(row) < 0) {
                      <p-tag severity="danger" [value]="'Faltante: ' + formatearMoneda(getDiff(row))" />
                    } @else {
                      <p-tag severity="info" [value]="'Sobrante: +' + formatearMoneda(getDiff(row))" />
                    }
                  }
                </td>
                <td>
                  <p-tag [severity]="row.is_open ? 'warn' : 'secondary'" [value]="row.is_open ? 'Abierta' : 'Cerrada'" />
                </td>
              </tr>
            </ng-template>
          </p-table>
        } @else {
          <div class="py-12 text-center text-surface-500 dark:text-surface-400">
            No se encontraron cierres de caja en el período seleccionado.
          </div>
        }
      </section>
    }
  }
</div>
<p-toast></p-toast>
    `
})
export class ClientReports implements OnInit {
    private dashboardService = inject(DashboardService);
    private fb = inject(FormBuilder);
    private messageService = inject(MessageService);
    private tenantService = inject(TenantService);
    private settingsService = inject(SettingsService);
    private destroyRef = inject(DestroyRef);
    protected localeService = inject(LocaleService);
    private branchService = inject(BranchService);
    private planAccessService = inject(PlanAccessService);

    canExportReports = this.planAccessService.canAccessFeature('export_reports');

    constructor() {
        effect(() => {
            const _branchId = this.branchService.activeBranchId();
            this.cargarDatos();
            if (this.activeTab() === 'cash_registers') {
                this.cargarCajas();
            }
        });
    }

    t(key: string): string {
        return this.localeService.t(key as any);
    }

    private posService = inject(PosService);

    activeTab = signal('revenue');
    loading = signal(false);
    loadError = signal<string | null>(null);
    cashRegisters = signal<any[]>([]);
    loadingCajas = signal(false);

    cashRegisterKpis = computed(() => {
        const registers = this.filteredCashRegisters();
        let totalCount = 0;
        let totalCashSales = 0;
        let totalShortage = 0;
        let totalSurplus = 0;

        registers.forEach(r => {
            if (!r.is_open) {
                totalCount++;
                const diff = this.getDiff(r);
                if (diff < 0) {
                    totalShortage += Math.abs(diff);
                } else if (diff > 0) {
                    totalSurplus += diff;
                }
                totalCashSales += this.toNum(r.sales_amount);
            }
        });

        return {
            totalCount,
            totalCashSales,
            totalShortage,
            totalSurplus,
            netBalance: totalSurplus - totalShortage
        };
    });

    cargarCajas() {
        this.loadingCajas.set(true);
        const branchId = this.branchService.activeBranchId();
        const params: any = { limit: 100 };
        if (branchId) {
            params.branch = branchId;
        }
        this.posService.getCashRegisters(params).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (res: any) => {
                this.cashRegisters.set(res?.results || []);
                this.loadingCajas.set(false);
            },
            error: () => {
                this.cashRegisters.set([]);
                this.loadingCajas.set(false);
                this.messageService.add({
                    severity: 'error',
                    summary: 'Error',
                    detail: 'No se pudieron cargar los cierres de caja.'
                });
            }
        });
    }

    filteredCashRegisters() {
        const { fechaInicio, fechaFin } = this.filtrosForm.value;
        let registers = this.cashRegisters();
        
        if (fechaInicio) {
            const start = new Date(fechaInicio);
            start.setHours(0, 0, 0, 0);
            registers = registers.filter(r => new Date(r.opened_at) >= start);
        }
        if (fechaFin) {
            const end = new Date(fechaFin);
            end.setHours(23, 59, 59, 999);
            registers = registers.filter(r => new Date(r.opened_at) <= end);
        }
        return registers;
    }

    toNum(val: any): number {
        return Number(val) || 0;
    }

    getDiff(row: any): number {
        if (row.is_open) return 0;
        return this.toNum(row.final_cash) - (this.toNum(row.initial_cash) + this.toNum(row.sales_amount));
    }

    // SOLO datos reales del backend
    kpis = signal({
        ingresos: 0,
        citas: 0,
        clientesNuevos: 0,
        ticketPromedio: 0
    });

    // KPI Cards solo con datos reales
    kpiCards = [
        {
            label: '',
            value: '$0.00',
            color: 'text-[var(--brand)] dark:text-[var(--brand-400)]',
            trendIcon: '',
            trendColor: '',
            trendText: ''
        },
        {
            label: '', 
            value: '0',
            color: 'text-[var(--brand)] dark:text-[var(--brand-400)]',
            trendIcon: '',
            trendColor: '',
            trendText: ''
        },
        {
            label: '',
            value: '0',
            color: 'text-[var(--brand)] dark:text-[var(--brand-400)]',
            trendIcon: '',
            trendColor: '',
            trendText: ''
        },
        {
            label: '',
            value: '0',
            color: 'text-surface-700 dark:text-surface-200',
            trendIcon: '',
            trendColor: '',
            trendText: ''
        }
    ];

    filtrosForm: FormGroup = this.fb.group({
        fechaInicio: [new Date(new Date().getFullYear(), new Date().getMonth(), 1)],
        fechaFin: [new Date()]
    });

    chartIngresos: any;
    chartOptions: any;
    monthlyRevenueRaw: any[] = [];
    filteredRevenue = signal<any[]>([]);
    currencyCode = signal('DOP');
    branding = signal<{ businessName: string; logoUrl: string | null }>({
        businessName: 'Mi Barbería',
        logoUrl: null
    });

    ngOnInit() {
        this.initCharts();
        this.cargarMoneda();
        this.cargarTenantActual();
    }

    cargarTenantActual() {
        this.tenantService.getCurrentTenant().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (tenant) => {
                const tenantCreatedAt = tenant?.created_at ? new Date(tenant.created_at) : null;
                if (!tenantCreatedAt || Number.isNaN(tenantCreatedAt.getTime())) {
                    return;
                }

                const startOfCurrentMonth = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
                const defaultStartDate = tenantCreatedAt > startOfCurrentMonth ? tenantCreatedAt : startOfCurrentMonth;

                this.filtrosForm.patchValue({
                    fechaInicio: defaultStartDate,
                    fechaFin: new Date()
                });
            },
            error: () => {
                // Mantener rango por defecto actual si no se puede obtener el tenant
            }
        });
    }

    cargarMoneda() {
        this.settingsService.getBarbershopSettings().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (settings) => {
                const posConfigBusinessName = typeof settings?.pos_config?.['business_name'] === 'string'
                    ? settings.pos_config['business_name']
                    : null;
                if (settings?.currency) {
                    this.currencyCode.set(settings.currency);
                }
                this.branding.set({
                    businessName: settings?.name || posConfigBusinessName || 'Mi Barbería',
                    logoUrl: this.normalizeLogoUrl(settings?.logo || null)
                });
            },
            error: () => {
                // Usar fallback por defecto
            }
        });
    }

    initCharts() {
        // Gráfico vacío hasta cargar datos reales
        this.chartIngresos = {
            labels: [],
            datasets: [{
                label: 'Ingresos',
                data: [],
                borderColor: 'var(--brand-400)',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.4,
                fill: true
            }]
        };

        this.chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        };
    }

    cargarDatos() {
        this.loading.set(true);
        this.loadError.set(null);
        const branchId = this.branchService.activeBranchId();
        this.dashboardService.getDashboardStats(branchId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (stats: any) => {
                const monthlyRevenue = stats.monthly_revenue || [];
                this.monthlyRevenueRaw = monthlyRevenue;
                this.actualizarKPIsYGrafico(monthlyRevenue);
                this.loading.set(false);
            },
            error: (error) => {
                if (!environment.production) {
                    console.error('❌ Error cargando reportes:', error);
                    console.error('Error completo:', error);
                }
                this.monthlyRevenueRaw = [];
                this.filteredRevenue.set([]);
                this.actualizarKPIsYGrafico([]);
                this.loadError.set('No fue posible obtener las metricas del dashboard en este momento.');
                this.loading.set(false);
            }
        });
    }

    actualizarGraficoIngresosMensuales(monthlyRevenue: any[]) {
        this.filteredRevenue.set(monthlyRevenue);
        const labels = monthlyRevenue.map(item => item.month || 'Mes');
        const data = monthlyRevenue.map(item => item.revenue || 0);

        this.chartIngresos = {
            labels,
            datasets: [{
                label: 'Ingresos',
                data,
                borderColor: 'var(--brand-400)',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.4,
                fill: true
            }]
        };
    }

    actualizarKPIsYGrafico(monthlyRevenue: any[]) {
        const currentMonthRevenue = monthlyRevenue.length > 0 ?
            monthlyRevenue[monthlyRevenue.length - 1].revenue : 0;

        const totalRevenue = monthlyRevenue.reduce((sum: number, item: any) => sum + (item.revenue || 0), 0);
        const activeMonths = monthlyRevenue.filter((item: any) => item.revenue > 0).length;
        const averageRevenue = activeMonths > 0 ? totalRevenue / activeMonths : 0;

        const appLocale = this.localeService.getCurrentAppLocale();
        const monthLabel = new Intl.DateTimeFormat(appLocale, { month: 'long' }).format(new Date());
        const currentMonthLabel = monthLabel.charAt(0).toUpperCase() + monthLabel.slice(1);

        this.kpiCards[0].label = this.t('reports.kpi.month_revenue_format').replace('{month}', currentMonthLabel);
        this.kpiCards[0].value = this.formatearMoneda(currentMonthRevenue);
        this.kpiCards[0].trendText = this.t('reports.kpi.current_month');

        this.kpiCards[1].label = this.t('reports.kpi.total_revenue');
        this.kpiCards[1].value = this.formatearMoneda(totalRevenue);
        this.kpiCards[1].trendText = this.t('reports.kpi.last_6_months');

        this.kpiCards[2].label = this.t('reports.kpi.monthly_average');
        this.kpiCards[2].value = this.formatearMoneda(averageRevenue);
        this.kpiCards[2].trendText = this.t('reports.kpi.last_6_months');

        this.kpiCards[3].label = this.t('reports.kpi.active_months');
        this.kpiCards[3].value = activeMonths.toString();
        this.kpiCards[3].trendText = this.t('reports.kpi.with_sales');

        this.actualizarGraficoIngresosMensuales(monthlyRevenue);
    }

    aplicarFiltros() {
        const filtros = this.filtrosForm.value;
        const fechaInicio: Date | null = filtros.fechaInicio ? new Date(filtros.fechaInicio) : null;
        const fechaFin: Date | null = filtros.fechaFin ? new Date(filtros.fechaFin) : null;

        if (!fechaInicio || !fechaFin || this.monthlyRevenueRaw.length === 0) {
            this.actualizarKPIsYGrafico(this.monthlyRevenueRaw);
            return;
        }

        const fechaInicioMes = new Date(fechaInicio.getFullYear(), fechaInicio.getMonth(), 1);
        const fechaFinMes = new Date(fechaFin.getFullYear(), fechaFin.getMonth(), 1);

        const monthsCount = this.monthlyRevenueRaw.length;
        const baseMonth = new Date(new Date().getFullYear(), new Date().getMonth() - (monthsCount - 1), 1);

        const filtrado = this.monthlyRevenueRaw.filter((_: any, index: number) => {
            const monthDate = new Date(baseMonth.getFullYear(), baseMonth.getMonth() + index, 1);
            return monthDate >= fechaInicioMes && monthDate <= fechaFinMes;
        });

        this.actualizarKPIsYGrafico(filtrado);
    }

    formatearMoneda(valor: number): string {
        const currency = this.currencyCode();
        const localeMap: Record<string, string> = {
            DOP: 'es-DO',
            COP: 'es-CO',
            USD: 'en-US',
            EUR: 'es-ES'
        };
        const locale = localeMap[currency] || 'es-DO';
        return new Intl.NumberFormat(locale, {
            style: 'currency',
            currency,
            currencyDisplay: 'symbol'
        }).format(valor);
    }

    toRevenueValue(valor: unknown): number {
        return Number(valor || 0);
    }

    getActiveRangeLabel(): string {
        const { fechaInicio, fechaFin } = this.filtrosForm.value;
        if (!fechaInicio || !fechaFin) {
            return this.t('reports.range.current_period');
        }

        const start = new Date(fechaInicio);
        const end = new Date(fechaFin);
        const appLocale = this.localeService.getCurrentAppLocale();

        return `${start.toLocaleDateString(appLocale, { day: '2-digit', month: 'short' })} - ${end.toLocaleDateString(appLocale, { day: '2-digit', month: 'short', year: 'numeric' })}`;
    }

    getMaxRevenue(): number {
        return this.filteredRevenue().reduce((max, item) => Math.max(max, this.toRevenueValue(item.revenue)), 0);
    }

    getAverageRevenue(): number {
        const values = this.filteredRevenue()
            .map((item) => this.toRevenueValue(item.revenue))
            .filter((value) => value > 0);

        if (!values.length) return 0;
        return values.reduce((sum, value) => sum + value, 0) / values.length;
    }

    getBestMonthLabel(): string {
        const rows = this.filteredRevenue();
        if (!rows.length) {
            return this.t('reports.pdf.no_data_summary');
        }

        const bestRow = rows.reduce((best, current) =>
            this.toRevenueValue(current.revenue) > this.toRevenueValue(best.revenue) ? current : best
        );

        return bestRow.month || this.t('reports.kpi.current_month');
    }

    getRevenueShare(revenue: unknown): number {
        const maxRevenue = this.getMaxRevenue();
        if (!maxRevenue) {
            return 0;
        }

        return Math.round((this.toRevenueValue(revenue) / maxRevenue) * 100);
    }

    getReportNarrative(): string {
        const totalMonths = this.filteredRevenue().length;
        const bestMonth = this.getBestMonthLabel();
        const peak = this.getMaxRevenue();

        if (!totalMonths || peak === 0) {
            return this.t('reports.narrative_empty');
        }

        return this.t('reports.narrative_format')
            .replace('{month}', bestMonth)
            .replace('{peak}', this.formatearMoneda(peak));
    }

    getReportHeadline(): string {
        if (this.activeTab() === 'cash_registers') {
            const kpis = this.cashRegisterKpis();
            return `Auron Suite · ${this.getActiveRangeLabel()} · ${kpis.totalCount} cierres revisados con ventas en efectivo por ${this.formatearMoneda(kpis.totalCashSales)}.`;
        }

        if (!this.filteredRevenue().length || this.getMaxRevenue() === 0) {
            return `Auron Suite · ${this.getActiveRangeLabel()} · Aún no hay ingresos suficientes para generar una lectura del período.`;
        }

        return `Auron Suite · ${this.getActiveRangeLabel()} · Tu mejor período fue ${this.getBestMonthLabel()} con ${this.formatearMoneda(this.getMaxRevenue())}.`;
    }

    descargarReportePDF() {
        if (this.activeTab() === 'cash_registers') {
            if (!this.filteredCashRegisters().length) {
                this.messageService.add({
                    severity: 'warn',
                    summary: 'Sin datos',
                    detail: 'No hay cierres de caja en el período seleccionado.'
                });
                return;
            }

            const html = this.generarHtmlReporteCajas();
            const ventana = window.open('', '_blank');
            if (!ventana) {
                this.messageService.add({
                    severity: 'warn',
                    summary: 'Pop-up bloqueado',
                    detail: 'Por favor, habilita los pop-ups para imprimir.'
                });
                return;
            }

            ventana.document.write(html);
            ventana.document.close();
            ventana.focus();
            setTimeout(() => ventana.print(), 400);
        } else {
            if (!this.filteredRevenue().length) {
                this.messageService.add({
                    severity: 'warn',
                    summary: this.t('reports.pdf.no_data_summary'),
                    detail: this.t('reports.pdf.no_data_detail')
                });
                return;
            }

            const html = this.generarHtmlReporteCliente();
            const ventana = window.open('', '_blank');
            if (!ventana) {
                this.messageService.add({
                    severity: 'warn',
                    summary: this.t('reports.pdf.popup_blocked_summary'),
                    detail: this.t('reports.pdf.popup_blocked_detail')
                });
                return;
            }

            ventana.document.write(html);
            ventana.document.close();
            ventana.focus();
            setTimeout(() => ventana.print(), 400);
        }
    }

    private generarHtmlReporteCajas(): string {
        const branding = this.branding();
        const logo = branding.logoUrl
            ? `<img src="${branding.logoUrl}" alt="Logo" style="max-height:56px;max-width:180px;object-fit:contain;margin-bottom:8px;" />`
            : '';
        const appLocale = this.localeService.getCurrentAppLocale();
        const fecha = new Date().toLocaleDateString(appLocale);
        const kpis = this.cashRegisterKpis();
        const rows = this.filteredCashRegisters().map((r: any) => `
            <tr>
                <td>${new Date(r.opened_at).toLocaleDateString(appLocale) + ' ' + new Date(r.opened_at).toLocaleTimeString(appLocale, {hour: '2-digit', minute:'2-digit'})}</td>
                <td>${r.closed_at ? (new Date(r.closed_at).toLocaleDateString(appLocale) + ' ' + new Date(r.closed_at).toLocaleTimeString(appLocale, {hour: '2-digit', minute:'2-digit'})) : '—'}</td>
                <td>${this.escapeHtml(r.user_name || '—')}</td>
                <td>${this.formatearMoneda(this.toNum(r.initial_cash))}</td>
                <td>${this.formatearMoneda(this.toNum(r.sales_amount))}</td>
                <td>${this.formatearMoneda(this.toNum(r.initial_cash) + this.toNum(r.sales_amount))}</td>
                <td>${r.is_open ? '—' : this.formatearMoneda(this.toNum(r.final_cash))}</td>
                <td>${r.is_open ? 'Abierta' : this.formatearMoneda(this.getDiff(r))}</td>
            </tr>
        `).join('');

        return `<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Reporte de Cierres de Caja</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; color: #111; }
    .header { border-bottom: 2px solid #e5e7eb; padding-bottom: 12px; margin-bottom: 20px; text-align: center; }
    .kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 18px; }
    .kpi { border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; }
    .kpi-label { font-size: 11px; color: #6b7280; margin-bottom: 4px; text-transform: uppercase; }
    .kpi-value { font-size: 16px; font-weight: 700; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; }
    th, td { border: 1px solid #e5e7eb; padding: 8px; text-align: left; font-size: 12px; }
    th { background: #f9fafb; }
    @media print { @page { margin: 1cm; } }
  </style>
</head>
<body>
  <div class="header">
    ${logo}
    <h2 style="margin:0;">${this.escapeHtml(branding.businessName)}</h2>
    <h3 style="margin:8px 0 4px 0;">Reporte de Cierres y Arqueos de Caja</h3>
    <div style="color:#6b7280;">Período: ${this.getActiveRangeLabel()} | Generado el: ${fecha}</div>
  </div>
  <div class="kpis">
    <div class="kpi">
      <div class="kpi-label">Cierres de Caja</div>
      <div class="kpi-value">${kpis.totalCount}</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Ventas Efectivo</div>
      <div class="kpi-value">${this.formatearMoneda(kpis.totalCashSales)}</div>
    </div>
    <div class="kpi">
      <div class="kpi-label" style="color: #b91c1c;">Total Faltantes</div>
      <div class="kpi-value" style="color: #b91c1c;">${this.formatearMoneda(kpis.totalShortage)}</div>
    </div>
    <div class="kpi">
      <div class="kpi-label" style="color: ${kpis.netBalance < 0 ? '#b91c1c' : '#15803d'};">Balance Neto</div>
      <div class="kpi-value" style="color: ${kpis.netBalance < 0 ? '#b91c1c' : '#15803d'};">${kpis.netBalance > 0 ? '+' : ''}${this.formatearMoneda(kpis.netBalance)}</div>
    </div>
  </div>
  <table>
    <thead>
      <tr>
        <th>Apertura</th>
        <th>Cierre</th>
        <th>Usuario</th>
        <th>Monto Inicial</th>
        <th>Ventas Efectivo</th>
        <th>Esperado</th>
        <th>Declarado</th>
        <th>Diferencia</th>
      </tr>
    </thead>
    <tbody>
      ${rows}
    </tbody>
  </table>
</body>
</html>`;
    }

    descargarReporteExcel(tipo: string) {
        const branchId = this.branchService.activeBranchId();
        const params = new URLSearchParams({ type: tipo });
        if (branchId) params.set('branch', String(branchId));
        const url = `${environment.apiUrl}/reports/export/?${params}`;

        fetch(url, {
            credentials: 'include'
        })
        .then(res => {
            if (!res.ok) throw new Error(res.status === 403 ? 'Plan no habilitado' : 'Error de descarga');
            return res.blob();
        })
        .then(blob => {
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `${tipo}_report.xlsx`;
            link.click();
            URL.revokeObjectURL(link.href);
        })
        .catch(() => {
            this.messageService.add({
                severity: 'error',
                summary: 'Error',
                detail: 'No se pudo descargar el reporte. Verifica tu plan.'
            });
        });
    }

    private generarHtmlReporteCliente(): string {
        const branding = this.branding();
        const logo = branding.logoUrl
            ? `<img src="${branding.logoUrl}" alt="Logo" style="max-height:56px;max-width:180px;object-fit:contain;margin-bottom:8px;" />`
            : '';
        const appLocale = this.localeService.getCurrentAppLocale();
        const fecha = new Date().toLocaleDateString(appLocale);
        const rows = this.filteredRevenue().map((r: any) => `
            <tr>
                <td>${this.escapeHtml(r.month || this.t('reports.table.month'))}</td>
                <td>${this.formatearMoneda(Number(r.revenue || 0))}</td>
            </tr>
        `).join('');

        return `<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>${this.t('reports.pdf.title')}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; color: #111; }
    .header { border-bottom: 2px solid #e5e7eb; padding-bottom: 12px; margin-bottom: 20px; text-align: center; }
    .kpis { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 18px; }
    .kpi { border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; }
    .kpi-label { font-size: 12px; color: #6b7280; margin-bottom: 4px; }
    .kpi-value { font-size: 18px; font-weight: 700; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid #e5e7eb; padding: 8px; text-align: left; }
    th { background: #f9fafb; }
    @media print { @page { margin: 1cm; } }
  </style>
</head>
<body>
  <div class="header">
    ${logo}
    <h2 style="margin:0;">${this.escapeHtml(branding.businessName)}</h2>
    <h3 style="margin:8px 0 4px 0;">${this.t('reports.pdf.title')}</h3>
    <div style="color:#6b7280;">${this.t('reports.pdf.generated_at')} ${fecha}</div>
  </div>
  <div class="kpis">
    ${this.kpiCards.map(card => `
      <div class="kpi">
        <div class="kpi-label">${this.escapeHtml(card.label)}</div>
        <div class="kpi-value">${this.escapeHtml(card.value)}</div>
      </div>
    `).join('')}
  </div>
  <table>
    <thead>
      <tr>
        <th>${this.t('reports.table.month')}</th>
        <th>${this.t('reports.table.revenue')}</th>
      </tr>
    </thead>
    <tbody>
      ${rows}
    </tbody>
  </table>
</body>
</html>`;
    }

    private normalizeLogoUrl(rawUrl: string | null): string | null {
        if (!rawUrl) return null;
        if (/^https?:\/\//i.test(rawUrl)) return rawUrl;
        const apiOrigin = new URL(environment.apiUrl).origin;
        return rawUrl.startsWith('/') ? `${apiOrigin}${rawUrl}` : `${apiOrigin}/${rawUrl}`;
    }

    private escapeHtml(text: string): string {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
