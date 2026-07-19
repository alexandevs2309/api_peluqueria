import { CommonModule } from '@angular/common';
import { Component, DestroyRef, OnInit, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { MessageService, ConfirmationService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { DatePickerModule } from 'primeng/datepicker';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ToastModule } from 'primeng/toast';
import { TooltipModule } from 'primeng/tooltip';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { AppointmentService, AppointmentWithDetails } from '../../../core/services/appointment/appointment.service';
import { AppointmentAlertService } from '../../../core/services/appointment/appointment-alert.service';
import { AuthService } from '../../../core/services/auth/auth.service';
import { environment } from '../../../../environments/environment';
import { BranchService, Branch } from '../../../core/services/branch/branch.service';
import { extractErrorDetail } from '../../../core/utils/http-error-message';
import { AppointmentDialogComponent, AppointmentDialogValue } from './appointment-dialog.component';
import { AppointmentAlertDialogComponent } from './appointment-alert-dialog.component';
import { firstValueFrom } from 'rxjs';
import { AppointmentsDataService } from './appointments-data.service';
import { AppointmentsUiService } from './appointments-ui.service';
import { AuronEmptyStateComponent } from '../../../shared/components/auron-empty-state/auron-empty-state.component';
import { AuronEyebrowComponent } from '../../../shared/components/auron-eyebrow/auron-eyebrow.component';
import { AuronIconComponent } from '../../../shared/components/auron-icon/auron-icon.component';
import { AuBtn } from '../../../shared/components';

@Component({
    selector: 'app-appointments-management',
    standalone: true,
    imports: [CommonModule, FormsModule, TableModule, ButtonModule, InputTextModule, SelectModule, DatePickerModule, TagModule, ToastModule, ConfirmDialogModule, TooltipModule, CardModule, AppointmentDialogComponent, AppointmentAlertDialogComponent, AuronEmptyStateComponent, AuronEyebrowComponent, AuronIconComponent, AuBtn],
    providers: [MessageService, ConfirmationService],
    template: `
        <div class="appts-list">
            <section class="appts-list__hero">
                <div class="appts-list__hero-copy">
                    <div class="appts-list__identity">
                        <auron-icon name="agenda" [size]="24"></auron-icon>
                        <auron-eyebrow label="Estado del día"></auron-eyebrow>
                    </div>
                    <h3 class="display-4">{{ getCurrentTimeLabel() }}</h3>
                    <p>{{ getNextAppointmentLabel() }}</p>
                </div>
                <div class="appts-list__hero-actions">
                    <button au-btn variant="primary" [icon]="'pi pi-plus'" (click)="abrirDialogo()" class="appts-list__primary-btn">{{ t('appointments.new') }}</button>
                    <div class="appts-list__quick-actions">
                        <button au-btn variant="ghost" size="sm" (click)="aplicarFiltroHoy()">{{ t('appointments.hoy') }}</button>
                        <button au-btn variant="ghost" size="sm" (click)="aplicarFiltroRapido('scheduled')">{{ t('appointments.pendientes') }}</button>
                        <button au-btn variant="ghost" size="sm" (click)="limpiarFiltros()">{{ t('appointments.limpiar') }}</button>
                    </div>
                </div>
                <div class="appts-list__metrics">
                    <div class="appts-metric">
                        <span>Citas hoy</span>
                        <strong>{{ getTodayAppointmentsCount() }}</strong>
                    </div>
                    <div class="appts-metric appts-metric--warn">
                        <span>{{ t('appointments.pendientes') }}</span>
                        <strong>{{ getVisibleCountByStatus('scheduled') }}</strong>
                    </div>
                    <div class="appts-metric appts-metric--ok">
                        <span>{{ t('appointments.completadas') }}</span>
                        <strong>{{ getVisibleCountByStatus('completed') }}</strong>
                    </div>
                </div>
            </section>

            <div class="appts-list__toolbar">
                <div class="appts-list__filters appts-list__filters--wide">
                    <span class="p-input-icon-left appts-list__search">
                        <i class="pi pi-search"></i>
                        <input pInputText [(ngModel)]="textoBusqueda" (ngModelChange)="aplicarFiltros()" [placeholder]="t('appointments.buscar_placeholder')" />
                    </span>
                    <p-datepicker [(ngModel)]="fechaFiltro" dateFormat="dd/mm/yy" (onSelect)="filtrarPorFecha()" [showClear]="true" [placeholder]="t('appointments.date')"></p-datepicker>
                    <p-select [(ngModel)]="estadoFiltro" [options]="estadosOptions" optionLabel="label" optionValue="value" (onChange)="filtrarPorEstado()" [showClear]="true" [placeholder]="t('appointments.status')"></p-select>
                    <p-select [(ngModel)]="empleadoFiltro" [options]="empleadosOptions()" optionLabel="label" optionValue="value" (onChange)="filtrarPorEmpleado()" [showClear]="true" [placeholder]="t('appointments.employee')"></p-select>
                    <button pButton icon="pi pi-filter-slash" (click)="limpiarFiltros()" class="p-button-text p-button-sm" [pTooltip]="t('appointments.limpiar_filtros')"></button>
                </div>
                <span class="appts-list__count">{{ citasFiltradas().length }} {{ citasFiltradas().length === 1 ? t('appointments.resultado') : t('appointments.resultados') }}</span>
            </div>

            <div *ngIf="cargando()" class="appts-list__loading">
                <i class="pi pi-spin pi-spinner"></i> {{ t('appointments.cargando_citas') }}
            </div>

            <auron-empty-state
                *ngIf="!cargando() && citasFiltradas().length === 0"
                icon="pi pi-calendar"
                [title]="t('appointments.sin_citas')"
                description="No hay citas para este período. Crea la primera o ajusta los filtros."
                [ctaLabel]="t('appointments.limpiar_filtros')"
                variant="contextual"
                (ctaAction)="limpiarFiltros()"
            ></auron-empty-state>

            <div *ngIf="!cargando() && citasFiltradas().length > 0" class="appts-list__rows">
                <div *ngFor="let cita of citasFiltradas()" class="appt-row" [class.appt-row--overdue]="cita.status === 'scheduled' && isOverdue(cita)">
                    <div class="appt-row__time">
                        <strong>{{ cita.date_time | date: 'dd/MM' }}</strong>
                        <span>{{ cita.date_time | date: 'HH:mm' }}</span>
                    </div>
                    <div class="appt-row__info">
                        <strong>{{ cita.client_name || (t('appointments.client_hash') + cita.client) }}</strong>
                        <span>{{ cita.stylist_name || (t('appointments.employee_hash') + cita.stylist) }}</span>
                        <span *ngIf="cita.service_name" class="appt-row__service">{{ cita.service_name }}</span>
                    </div>
                    <p-tag [value]="getEstadoLabel(cita.status)" [severity]="getEstadoSeverity(cita.status)" class="appt-row__tag"></p-tag>
                    <div class="appt-row__actions">
                        <button *ngIf="cita.status === 'scheduled'" pButton icon="pi pi-check" class="p-button-success p-button-sm" (click)="completarCita(cita)" [pTooltip]="t('appointments.completar')"></button>
                        <button *ngIf="cita.status === 'scheduled'" pButton icon="pi pi-times" class="p-button-warning p-button-sm p-button-outlined" (click)="cancelarCita(cita)" [pTooltip]="t('appointments.cancelar')"></button>
                        <button pButton icon="pi pi-pencil" class="p-button-text p-button-sm" (click)="editarCita(cita)" [disabled]="cita.status === 'completed'" [pTooltip]="t('appointments.edit_tooltip')"></button>
                        <button *ngIf="canDeleteAppointments" pButton icon="pi pi-trash" class="p-button-text p-button-sm p-button-danger" (click)="confirmarEliminar(cita)" [pTooltip]="t('appointments.eliminar')"></button>
                    </div>
                </div>
            </div>

            <app-appointment-dialog
                [(visible)]="mostrarDialogo"
                [saving]="guardando()"
                [appointment]="citaSeleccionada"
                [clientsOptions]="clientesOptions()"
                [employeesOptions]="empleadosOptions()"
                [servicesOptions]="serviciosOptions()"
                [branchOptions]="branchOptions()"
                [selectedBranchId]="selectedBranchId()"
                (save)="guardarCita($event)"
                (cancel)="cerrarDialogo()"
            ></app-appointment-dialog>

            <!-- Alerta Modal Persistente para Cambios de Estado -->
            <app-appointment-alert-dialog></app-appointment-alert-dialog>

            <p-confirmDialog></p-confirmDialog>
            <p-toast></p-toast>
        </div>

        <style>
        .appts-list { display: flex; flex-direction: column; gap: 0.75rem; }

        .appts-list__hero {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 1rem;
            padding: 1rem;
            border: 1px solid var(--surface-border);
            background: var(--surface-card);
            border-radius: 1rem;
        }

        .appts-list__hero-copy h3 {
            margin: 0.25rem 0 0;
            font-size: 1.55rem;
            line-height: 1.1;
            color: var(--text-color);
        }

        .appts-list__hero-copy p {
            margin: 0.65rem 0 0;
            max-width: 42rem;
            color: var(--text-color-secondary);
        }

        .appts-list__identity {
            display: inline-flex;
            align-items: center;
            gap: 0.65rem;
            width: fit-content;
            margin-bottom: 0.75rem;
            color: var(--brand);
        }

        .appts-list__metrics {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.75rem;
            grid-column: 1 / -1;
            margin-top: 1rem;
        }

        .appts-metric {
            padding: 0.85rem 1rem;
            border-radius: 0.9rem;
            background: color-mix(in srgb, var(--surface-card) 75%, #f8fafc 25%);
            border: 1px solid var(--surface-border);
        }

        .appts-metric span {
            display: block;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            color: var(--text-color-secondary);
        }

        .appts-metric strong {
            display: block;
            margin-top: 0.35rem;
            font-size: 2rem;
            line-height: 1;
            color: var(--text-color);
        }

        .appts-metric--warn { border-color: rgba(217, 119, 6, 0.25); background: rgba(245, 158, 11, 0.08); }
        .appts-metric--ok { border-color: rgba(5, 150, 105, 0.22); background: rgba(16, 185, 129, 0.08); }

        .appts-list__hero-actions {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            align-items: flex-end;
            color: var(--text-color);
        }

        .appts-list__hero-note {
            padding: 0.9rem 1rem;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 0.9rem;
            background: rgba(255, 255, 255, 0.04);
            font-size: 0.92rem;
            line-height: 1.5;
        }

        .appts-list__primary-btn {
            width: 100%;
            border: 0 !important;
            background: var(--brand) !important;
            color: #ffffff !important;
        }
        .appts-list__primary-btn:hover { background: #1447c0 !important; }

        .appts-list__quick-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 0.35rem;
        }

        .appts-list__toolbar {
            display: flex; align-items: center; justify-content: space-between;
            flex-wrap: wrap; gap: 0.5rem;
            padding: 0.75rem;
            border: 1px solid var(--surface-border);
            background: var(--surface-card);
            border-radius: 0.75rem;
        }

        .appts-list__filters { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
        .appts-list__filters--wide { width: min(100%, 64rem); }
        .appts-list__search { flex: 1 1 14rem; }
        .appts-list__search input { width: 100%; }
        .appts-list__filters .p-datepicker-input, .appts-list__filters .p-select { min-width: 9rem; }

        .appts-list__count { font-size: 0.82rem; color: var(--text-color-secondary); white-space: nowrap; }

        .appts-list__loading, .appts-list__empty {
            display: flex; align-items: center; justify-content: center; gap: 0.65rem;
            padding: 2rem; color: var(--text-color-secondary); font-size: 0.9rem;
            border: 1px dashed var(--surface-border); border-radius: 0.75rem;
        }

        .appts-list__rows { display: flex; flex-direction: column; gap: 0.35rem; }

        .appt-row {
            display: grid;
            grid-template-columns: 4rem 1fr auto auto;
            align-items: center;
            gap: 0.75rem;
            padding: 0.65rem 0.85rem;
            border: 1px solid var(--surface-border);
            background: var(--surface-card);
            border-radius: 0.65rem;
            transition: border-color 120ms;
        }

        .appt-row:hover { border-color: rgba(26, 86, 219, 0.45); box-shadow: 0 0 0 1px rgba(26, 86, 219, 0.15); }
        .appt-row--overdue { border-left: 3px solid #d97706; }

        .appt-row__time {
            display: flex; flex-direction: column; align-items: center;
            font-size: 0.82rem; line-height: 1.3;
        }

        .appt-row__time strong { font-size: 0.9rem; color: var(--text-color); }
        .appt-row__time span { color: var(--text-color-secondary); }

        .appt-row__info {
            display: flex; flex-direction: column; gap: 0.1rem; min-width: 0;
        }

        .appt-row__info strong { font-size: 0.95rem; font-weight: 600; color: var(--text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .appt-row__info span { font-size: 0.78rem; color: var(--text-color-secondary); }
        .appt-row__service { font-size: 0.78rem; font-style: italic; color: var(--text-color-secondary); opacity: 0.8; }

        .appt-row__actions { display: flex; gap: 0.25rem; }

        @media (max-width: 640px) {
            .appts-list__hero { grid-template-columns: 1fr; }
            .appts-list__metrics { grid-template-columns: 1fr; }
            .appt-row { grid-template-columns: 3.5rem 1fr; grid-template-rows: auto auto; }
            .appt-row__tag { grid-column: 2; }
            .appt-row__actions { grid-column: 1 / -1; justify-content: flex-end; }
        }
        </style>
    `
})
export class AppointmentsManagement implements OnInit {
    private readonly localeService = inject(LocaleService);
    private readonly appointmentService = inject(AppointmentService);

    t(key: string): string {
        return this.localeService.t(key as any);
    }
    private readonly authService = inject(AuthService);
    private readonly messageService = inject(MessageService);
    private readonly confirmationService = inject(ConfirmationService);
    private readonly appointmentsUiService = inject(AppointmentsUiService);
    private readonly appointmentsDataService = inject(AppointmentsDataService);
    private readonly alertService = inject(AppointmentAlertService);
    private readonly branchService = inject(BranchService);
    private readonly destroyRef = inject(DestroyRef);

    citas = this.appointmentsDataService.appointments;
    cargando = this.appointmentsDataService.loading;
    clientesOptions = this.appointmentsDataService.clientsOptions;
    empleadosOptions = this.appointmentsDataService.employeesOptions;
    serviciosOptions = this.appointmentsDataService.servicesOptions;

    citasFiltradas = signal<AppointmentWithDetails[]>([]);
    guardando = signal(false);
    mostrarDialogo = false;
    citaSeleccionada: AppointmentWithDetails | null = null;
    canDeleteAppointments = false;
    branchOptions = signal<Array<{ label: string; value: number }>>([]);
    selectedBranchId = signal<number | null>(null);

    fechaFiltro: Date | null = null;
    estadoFiltro: string | null = null;
    empleadoFiltro: number | null = null;
    textoBusqueda = '';

    get estadosOptions() {
        return [
            { label: this.t('appointments.programada'), value: 'scheduled' },
            { label: this.t('appointments.completadas'), value: 'completed' },
            { label: this.t('appointments.canceladas'), value: 'cancelled' },
            { label: this.t('appointments.no_asistio'), value: 'no_show' }
        ];
    }

    ngOnInit(): void {
        this.canDeleteAppointments = this.computeCanDeleteAppointments();
        this.cargarDatos(true);
        this.cargarSucursales();
        this.appointmentsUiService.refresh$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
            this.cargarDatos(true);
        });
        this.appointmentsUiService.create$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((target) => {
            if (target === 'list') {
                this.abrirDialogo();
            }
        });
    }

    private cargarSucursales(): void {
        this.branchService.getAll().subscribe({
            next: (data) => {
                this.branchOptions.set(data.map(b => ({ label: b.name, value: b.id })));
                const main = data.find(b => b.is_main) || data[0] || null;
                this.selectedBranchId.set(main?.id ?? null);
            },
        });
    }

    async cargarDatos(force = false): Promise<void> {
        try {
            await this.appointmentsDataService.load(force);
            this.aplicarFiltros();
        } catch (error) {
            if (!environment.production) {
            }
            this.messageService.add({
                severity: 'error',
                summary: this.t('common.error'),
                detail: this.t('appointments.error_cargar')
            });
        }
    }

    loadAppointments(): void {
        this.cargarDatos();
    }

    async abrirDialogo(): Promise<void> {
        await this.appointmentsDataService.load(true);
        this.citaSeleccionada = null;
        this.mostrarDialogo = true;
    }

    async editarCita(cita: AppointmentWithDetails): Promise<void> {
        await this.appointmentsDataService.load(true);
        this.citaSeleccionada = cita;
        this.mostrarDialogo = true;
    }

    async guardarCita(formData: AppointmentDialogValue): Promise<void> {
        if (!formData.date || !formData.time) {
            this.messageService.add({
                severity: 'warn',
                summary: this.t('appointments.form_incompleto'),
                detail: this.t('appointments.seleccione_fecha_hora')
            });
            return;
        }

        this.guardando.set(true);
        try {
            const fecha = new Date(formData.date);
            const hora = new Date(formData.time);
            fecha.setHours(hora.getHours(), hora.getMinutes(), 0, 0);

            const citaData = {
                client: formData.client,
                stylist: formData.stylist,
                service: formData.service ?? undefined,
                date_time: fecha.toISOString(),
                description: formData.description,
                status: 'scheduled' as const,
                branch: formData.branch ?? undefined,
            };

            if (this.citaSeleccionada) {
                await firstValueFrom(this.appointmentService.updateAppointment(this.citaSeleccionada.id, citaData));
                this.messageService.add({ severity: 'success', summary: this.t('common.success'), detail: this.t('appointments.cita_actualizada') });
            } else {
                await firstValueFrom(this.appointmentService.createAppointment(citaData));
                this.messageService.add({ severity: 'success', summary: this.t('common.success'), detail: this.t('appointments.cita_creada') });
            }

            this.cerrarDialogo();
            this.appointmentsUiService.requestRefresh();
        } catch (error: any) {
            if (!environment.production) console.error('[AppointmentsManagement] Error al guardar cita:', {
                status: error?.status,
                body: error?.error
            });
            this.messageService.add({
                severity: 'error',
                summary: this.t('common.error'),
                detail: extractErrorDetail(error) || this.t('appointments.error_guardar')
            });
        } finally {
            this.guardando.set(false);
        }
    }

    async completarCita(cita: AppointmentWithDetails): Promise<void> {
        try {
            await firstValueFrom(this.appointmentService.completeAppointment(cita.id));
            
            // Mostrar alerta modal persistente
            this.alertService.showAlert({
                id: cita.id,
                clientName: cita.client_name || `Cliente #${cita.client}`,
                clientPhone: cita.client_phone,
                stylistName: cita.stylist_name || `Empleado #${cita.stylist}`,
                serviceName: cita.service_name,
                status: 'completed',
                dateTime: new Date(cita.date_time),
                description: cita.description
            });

            this.messageService.add({ 
                severity: 'success', 
                summary: this.t('common.success'), 
                detail: this.t('appointments.cita_completada') 
            });
            this.appointmentsUiService.requestRefresh();
        } catch (error: any) {
            this.messageService.add({
                severity: 'error',
                summary: this.t('common.error'),
                detail: error?.error?.detail || this.t('appointments.error_completar')
            });
        }
    }

    async cancelarCita(cita: AppointmentWithDetails): Promise<void> {
        try {
            await firstValueFrom(this.appointmentService.cancelAppointment(cita.id));
            
            // Mostrar alerta modal persistente
            this.alertService.showAlert({
                id: cita.id,
                clientName: cita.client_name || `Cliente #${cita.client}`,
                clientPhone: cita.client_phone,
                stylistName: cita.stylist_name || `Empleado #${cita.stylist}`,
                serviceName: cita.service_name,
                status: 'cancelled',
                dateTime: new Date(cita.date_time),
                description: cita.description
            });

            this.messageService.add({ 
                severity: 'success', 
                summary: this.t('common.success'), 
                detail: this.t('appointments.cita_cancelada') 
            });
            this.appointmentsUiService.requestRefresh();
        } catch (error: any) {
            this.messageService.add({
                severity: 'error',
                summary: this.t('common.error'),
                detail: error?.error?.detail || this.t('appointments.error_cancelar')
            });
        }
    }

    confirmarEliminar(cita: AppointmentWithDetails): void {
        if (!this.canDeleteAppointments) {
            this.messageService.add({
                severity: 'warn',
                summary: this.t('appointments.acceso_restringido'),
                detail: this.t('appointments.no_puede_eliminar')
            });
            return;
        }

        this.confirmationService.confirm({
            message: this.t('appointments.seguro_eliminar').replace('{fecha}', new Date(cita.date_time).toLocaleDateString()),
            header: this.t('appointments.confirmar_eliminacion'),
            icon: 'pi pi-exclamation-triangle',
            acceptLabel: this.t('appointments.si_eliminar'),
            rejectLabel: this.t('appointments.cancelar'),
            accept: () => this.eliminarCita(cita)
        });
    }

    async eliminarCita(cita: AppointmentWithDetails): Promise<void> {
        if (!this.canDeleteAppointments) {
            return;
        }

        try {
            await firstValueFrom(this.appointmentService.deleteAppointment(cita.id));
            this.messageService.add({ severity: 'success', summary: this.t('common.success'), detail: this.t('appointments.delete_success') });
            this.appointmentsUiService.requestRefresh();
        } catch (error: any) {
            this.messageService.add({
                severity: 'error',
                summary: this.t('common.error'),
                detail: error?.error?.detail || this.t('appointments.error_eliminar')
            });
        }
    }

    isOverdue(cita: AppointmentWithDetails): boolean {
        return new Date(cita.date_time) < new Date();
    }

    filtrarPorFecha(): void {
        this.aplicarFiltros();
    }

    filtrarPorEstado(): void {
        this.aplicarFiltros();
    }

    filtrarPorEmpleado(): void {
        this.aplicarFiltros();
    }

    limpiarFiltros(): void {
        this.fechaFiltro = null;
        this.estadoFiltro = null;
        this.empleadoFiltro = null;
        this.textoBusqueda = '';
        this.citasFiltradas.set(this.citas());
    }

    aplicarFiltroRapido(status: string): void {
        this.estadoFiltro = status;
        this.aplicarFiltros();
    }

    aplicarFiltroHoy(): void {
        this.fechaFiltro = new Date();
        this.aplicarFiltros();
    }

    getEstadoLabel(status: string): string {
        const estado = this.estadosOptions.find((item) => item.value === status);
        return estado?.label || status;
    }

    getEstadoSeverity(status: string): 'success' | 'info' | 'danger' | 'warn' | 'secondary' {
        switch (status) {
            case 'scheduled':
                return 'info';
            case 'completed':
                return 'success';
            case 'cancelled':
                return 'danger';
            case 'no_show':
                return 'warn';
            default:
                return 'secondary';
        }
    }

    cerrarDialogo(): void {
        this.mostrarDialogo = false;
        this.citaSeleccionada = null;
    }

    aplicarFiltros(): void {
        let citasFiltradas = [...this.citas()];

        if (this.fechaFiltro) {
            const fechaStr = this.fechaFiltro.toISOString().split('T')[0];
            citasFiltradas = citasFiltradas.filter((cita) => cita.date_time.startsWith(fechaStr));
        }

        if (this.estadoFiltro) {
            citasFiltradas = citasFiltradas.filter((cita) => cita.status === this.estadoFiltro);
        }

        if (this.empleadoFiltro) {
            citasFiltradas = citasFiltradas.filter((cita) => cita.stylist === this.empleadoFiltro);
        }

        const termino = this.textoBusqueda.trim().toLowerCase();
        if (termino) {
            citasFiltradas = citasFiltradas.filter((cita) =>
                [cita.client_name, cita.stylist_name, cita.service_name]
                    .filter(Boolean)
                    .some((value) => String(value).toLowerCase().includes(termino))
            );
        }

        this.citasFiltradas.set(citasFiltradas);
    }

    getVisibleCountByStatus(status: AppointmentWithDetails['status']): number {
        return this.citasFiltradas().filter((cita) => cita.status === status).length;
    }

    getCurrentTimeLabel(): string {
        return new Date().toLocaleTimeString(this.localeService.getCurrentAppLocale(), {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    getTodayAppointmentsCount(): number {
        const today = new Date().toISOString().slice(0, 10);
        return this.citas().filter((cita) => cita.date_time?.startsWith(today)).length;
    }

    getNextAppointmentLabel(): string {
        const now = Date.now();
        const next = this.citas()
            .filter((cita) => cita.status === 'scheduled')
            .map((cita) => ({ cita, time: new Date(cita.date_time).getTime() }))
            .filter((item) => Number.isFinite(item.time) && item.time >= now)
            .sort((a, b) => a.time - b.time)[0];

        if (!next) {
            return 'No hay próximas citas programadas. La agenda está lista para nuevos turnos.';
        }

        const minutes = Math.max(0, Math.round((next.time - now) / 60000));
        const client = next.cita.client_name || 'cliente';
        const service = next.cita.service_name || 'servicio';
        return `Próxima cita en ${minutes} min · ${client} · ${service}`;
    }

    getOperationHint(): string {
        const pendientes = this.getVisibleCountByStatus('scheduled');
        if (pendientes > 0) {
            return this.t('appointments.hint_pendientes')
                .replace('{count}', String(pendientes))
                .replace(/{plural}/g, pendientes === 1 ? '' : 's');
        }

        if (this.citasFiltradas().length === 0) {
            return this.t('appointments.hint_vacio');
        }

        return this.t('appointments.hint_limpio');
    }

    private computeCanDeleteAppointments(): boolean {
        const role = this.currentRoleKey();
        return role === 'CLIENT_ADMIN' || role === 'MANAGER';
    }

    private currentRoleKey(): string {
        return String(this.authService.getCurrentUser()?.role || '').trim().toUpperCase().replace(/[\s-]+/g, '_');
    }
}
