import { AfterViewInit, Component, DestroyRef, ElementRef, OnInit, ViewChild, ViewEncapsulation, effect, inject, signal, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Calendar } from '@fullcalendar/core';
import dayGridPlugin from '@fullcalendar/daygrid';
import interactionPlugin from '@fullcalendar/interaction';
import listPlugin from '@fullcalendar/list';
import timeGridPlugin from '@fullcalendar/timegrid';
import esLocale from '@fullcalendar/core/locales/es';
import frLocale from '@fullcalendar/core/locales/fr';
import ptLocale from '@fullcalendar/core/locales/pt';
import deLocale from '@fullcalendar/core/locales/de';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { environment } from '../../../../environments/environment';
import { MessageService, ConfirmationService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { TagModule } from 'primeng/tag';
import { AppointmentService, AppointmentWithDetails } from '../../../core/services/appointment/appointment.service';
import { extractErrorDetail } from '../../../core/utils/http-error-message';
import { AuthService } from '../../../core/services/auth/auth.service';
import { AppointmentDialogComponent, AppointmentDialogValue } from './appointment-dialog.component';
import { firstValueFrom } from 'rxjs';
import { AppointmentsDataService } from './appointments-data.service';
import { AppointmentsUiService } from './appointments-ui.service';
import { AuBtn } from '../../../shared/components';

@Component({
    selector: 'app-appointments-calendar',
    standalone: true,
    imports: [CommonModule, DialogModule, TagModule, InputTextModule, ToastModule, ConfirmDialogModule, AppointmentDialogComponent, AuBtn],
    providers: [MessageService, ConfirmationService],
    template: `
        <div class="mb-4 rounded-2xl border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900/60 p-4">
            <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                    <div class="text-sm font-semibold text-surface-900 dark:text-white">{{ t('appointments.agenda_visual') }}</div>
                    <div class="text-sm text-surface-600 dark:text-surface-400">
                        {{ t('appointments.click_to_view') }}
                    </div>
                </div>
                <div class="flex flex-wrap gap-2 text-xs">
                    <span class="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-blue-700 dark:bg-blue-500/10 dark:text-blue-300">
                        <span class="h-2.5 w-2.5 rounded-full bg-blue-500"></span> {{ t('appointments.programada') }}
                    </span>
                    <span class="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300">
                        <span class="h-2.5 w-2.5 rounded-full bg-emerald-500"></span> {{ t('appointments.completada') }}
                    </span>
                    <span class="inline-flex items-center gap-2 rounded-full bg-rose-50 px-3 py-1 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300">
                        <span class="h-2.5 w-2.5 rounded-full bg-rose-500"></span> {{ t('appointments.cancelada') }}
                    </span>
                    <span class="inline-flex items-center gap-2 rounded-full bg-amber-50 px-3 py-1 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300">
                        <span class="h-2.5 w-2.5 rounded-full bg-amber-500"></span> {{ t('appointments.no_asistio') }}
                    </span>
                </div>
            </div>
        </div>

        <div class="calendar-wrapper relative">
            <div #calendarEl [class.opacity-40]="loading()" class="transition-opacity duration-300"></div>
            
            <!-- Glassmorphic Premium Loader Overlay -->
            <div *ngIf="loading()" class="absolute inset-0 z-10 flex flex-col items-center justify-center bg-surface-0/60 dark:bg-surface-950/60 backdrop-blur-xs transition-all duration-300 rounded-lg">
                <div class="flex flex-col items-center gap-4 p-6 rounded-2xl bg-surface-card/80 border border-surface-200 dark:border-surface-800 shadow-xl max-w-sm w-full animate-pulse">
                    <!-- Fake Calendar Header -->
                    <div class="flex justify-between w-full border-b border-surface-200 dark:border-surface-700 pb-3 mb-2">
                        <div class="h-6 w-24 bg-surface-300 dark:bg-surface-700 rounded"></div>
                        <div class="flex gap-2">
                            <div class="h-6 w-8 bg-surface-300 dark:bg-surface-700 rounded"></div>
                            <div class="h-6 w-8 bg-surface-300 dark:bg-surface-700 rounded"></div>
                        </div>
                    </div>
                    <!-- Fake Grid Rows -->
                    <div class="w-full space-y-3">
                        <div class="grid grid-cols-5 gap-2">
                            <div class="h-8 bg-surface-300 dark:bg-surface-700 rounded-md"></div>
                            <div class="h-8 bg-surface-300 dark:bg-surface-700 rounded-md"></div>
                            <div class="h-8 bg-surface-200 dark:bg-surface-800 rounded-md"></div>
                            <div class="h-8 bg-surface-300 dark:bg-surface-700 rounded-md"></div>
                            <div class="h-8 bg-surface-200 dark:bg-surface-800 rounded-md"></div>
                        </div>
                        <div class="grid grid-cols-5 gap-2">
                            <div class="h-12 bg-surface-200 dark:bg-surface-800 rounded-md col-span-2"></div>
                            <div class="h-12 bg-surface-300 dark:bg-surface-700 rounded-md col-span-1"></div>
                            <div class="h-12 bg-surface-200 dark:bg-surface-800 rounded-md col-span-2"></div>
                        </div>
                        <div class="grid grid-cols-5 gap-2">
                            <div class="h-10 bg-surface-300 dark:bg-surface-700 rounded-md col-span-1"></div>
                            <div class="h-10 bg-surface-200 dark:bg-surface-800 rounded-md col-span-3"></div>
                            <div class="h-10 bg-surface-300 dark:bg-surface-700 rounded-md col-span-1"></div>
                        </div>
                    </div>
                    <!-- Spinner micro-animation -->
                    <div class="flex items-center gap-2 mt-4 text-primary-500 font-semibold text-sm">
                        <i class="pi pi-spin pi-spinner text-lg"></i>
                        <span>{{ t('appointments.syncing') }}</span>
                    </div>
                </div>
            </div>
        </div>

        <p-dialog [(visible)]="mostrarDetalle" [modal]="true" [style]="{ width: '92vw', maxWidth: '450px' }" [breakpoints]="{'960px':'75vw','640px':'100vw'}" [header]="t('appointments.detalle_cita')">
            <div *ngIf="citaSeleccionada" class="space-y-4">
                <div class="flex items-center gap-3 rounded bg-surface-50 p-3 dark:bg-surface-800/70">
                    <i class="pi pi-user text-2xl text-blue-600"></i>
                    <div>
                        <label class="text-xs text-surface-500 dark:text-surface-400">{{ t('appointments.client') }}</label>
                        <p class="font-semibold">{{ citaSeleccionada.client_name }}</p>
                    </div>
                </div>
                <div class="flex items-center gap-3 rounded bg-surface-50 p-3 dark:bg-surface-800/70">
                    <i class="pi pi-briefcase text-2xl text-[var(--brand)]"></i>
                    <div>
                        <label class="text-xs text-surface-500 dark:text-surface-400">{{ t('appointments.employee') }}</label>
                        <p class="font-semibold">{{ citaSeleccionada.stylist_name }}</p>
                    </div>
                </div>
                <div class="flex items-center gap-3 rounded bg-surface-50 p-3 dark:bg-surface-800/70">
                    <i class="pi pi-star text-2xl text-yellow-600"></i>
                    <div>
                        <label class="text-xs text-surface-500 dark:text-surface-400">{{ t('appointments.services') }}</label>
                        <p class="font-semibold">{{ citaSeleccionada.service_name }}</p>
                        <p class="text-sm text-surface-600 dark:text-surface-400">{{ citaSeleccionada.service_duration || 30 }} {{ t('appointments.min') }}</p>
                    </div>
                </div>
                <div class="flex items-center gap-3 rounded bg-surface-50 p-3 dark:bg-surface-800/70">
                    <i class="pi pi-clock text-2xl text-green-600"></i>
                    <div>
                        <label class="text-xs text-surface-500 dark:text-surface-400">{{ t('appointments.date') }} y {{ t('appointments.time') }}</label>
                        <p class="font-semibold">{{ citaSeleccionada.date_time | date: 'dd/MM/yyyy HH:mm' }}</p>
                    </div>
                </div>
                <div class="flex items-center gap-3 rounded bg-surface-50 p-3 dark:bg-surface-800/70">
                    <i class="pi pi-info-circle text-2xl text-surface-600 dark:text-surface-300"></i>
                    <div class="flex-1">
                        <label class="text-xs text-surface-500 dark:text-surface-400">{{ t('appointments.status') }}</label>
                        <div class="mt-1">
                            <p-tag [value]="getStatusLabel(citaSeleccionada.status)" [severity]="getStatusSeverity(citaSeleccionada.status)"></p-tag>
                        </div>
                    </div>
                </div>
                <div *ngIf="citaSeleccionada.description" class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded">
                    <label class="text-xs text-surface-500 dark:text-surface-400">{{ t('appointments.notes') }}</label>
                    <p class="text-sm mt-1">{{ citaSeleccionada.description }}</p>
                </div>
            </div>
            <ng-template pTemplate="footer">
                <div class="flex gap-2 flex-wrap">
                    <button au-btn variant="ghost" (click)="mostrarDetalle = false">{{ t('appointments.close') }}</button>
                    <button au-btn variant="primary" [icon]="'pi pi-pencil'" (click)="abrirEdicion()" *ngIf="citaSeleccionada?.status === 'scheduled'">{{ t('appointments.editar') }}</button>
                    <button au-btn variant="primary" [icon]="'pi pi-check'" (click)="completarCita()" *ngIf="citaSeleccionada?.status === 'scheduled'">{{ t('appointments.completar') }}</button>
                    <button au-btn variant="secondary" [icon]="'pi pi-times'" (click)="cancelarCita()" *ngIf="citaSeleccionada?.status === 'scheduled'">{{ t('appointments.cancelar') }}</button>
                    <button au-btn variant="danger" [icon]="'pi pi-user-minus'" (click)="marcarNoShow()" *ngIf="citaSeleccionada?.status === 'scheduled'">{{ t('appointments.no_show') }}</button>
                    <button au-btn variant="danger" [icon]="'pi pi-trash'" (click)="confirmarEliminar()" *ngIf="citaSeleccionada && canDeleteAppointments">{{ t('appointments.eliminar') }}</button>
                </div>
            </ng-template>
        </p-dialog>

        <app-appointment-dialog
            [(visible)]="mostrarFormulario"
            [saving]="guardando()"
            [appointment]="citaSeleccionada"
            [clientsOptions]="clientesOptions()"
            [employeesOptions]="empleadosOptions()"
            [servicesOptions]="servicesOptionsForDialog()"
            (save)="guardarCita($event)"
            (cancel)="cerrarFormulario()"
        ></app-appointment-dialog>

        <p-toast></p-toast>
        <p-confirmDialog></p-confirmDialog>
    `,
    styleUrl: './appointments-calendar.scss',
    encapsulation: ViewEncapsulation.None
})
export class AppointmentsCalendar implements OnInit, AfterViewInit {
    @ViewChild('calendarEl', { static: false }) calendarEl!: ElementRef;

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
    private readonly destroyRef = inject(DestroyRef);

    private calendar!: Calendar;

    citas = this.appointmentsDataService.appointments;
    clientesOptions = this.appointmentsDataService.clientsOptions;
    empleadosOptions = this.appointmentsDataService.employeesOptions;
    serviciosOptions = this.appointmentsDataService.servicesOptions;
    loading = this.appointmentsDataService.loading;

    guardando = signal(false);
    mostrarDetalle = false;
    mostrarFormulario = false;
    citaSeleccionada: AppointmentWithDetails | null = null;
    canDeleteAppointments = false;

    constructor() {
        effect(() => {
            this.citas();
            this.actualizarEventos();
        });
    }

    ngOnInit(): void {
        this.canDeleteAppointments = this.computeCanDeleteAppointments();
        this.cargarCitas(true);
        this.appointmentsUiService.refresh$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
            this.cargarCitas(true);
        });
        this.appointmentsUiService.create$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((target) => {
            if (target === 'calendar') {
                this.abrirFormulario();
            }
        });
        this.localeService.languageChanged$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(lang => {
            if (this.calendar) {
                this.calendar.setOption('locale', lang);
            }
        });
    }

    ngAfterViewInit(): void {
        this.initCalendar();
        this.actualizarEventos();
    }

    loadAppointments(): void {
        this.cargarCitas();
    }

    async abrirFormulario(): Promise<void> {
        await this.appointmentsDataService.load(true);
        this.citaSeleccionada = null;
        this.mostrarFormulario = true;
    }

    async abrirEdicion(): Promise<void> {
        if (!this.citaSeleccionada) {
            return;
        }
        await this.appointmentsDataService.load(true);
        this.mostrarDetalle = false;
        this.mostrarFormulario = true;
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

            const payload = {
                client: formData.client,
                stylist: formData.stylist,
                service: formData.service ?? undefined,
                date_time: fecha.toISOString(),
                description: formData.description,
                status: 'scheduled' as const,
                branch: formData.branch ?? undefined
            };

            if (this.citaSeleccionada) {
                await firstValueFrom(this.appointmentService.updateAppointment(this.citaSeleccionada.id, payload));
                this.messageService.add({ severity: 'success', summary: this.t('common.success'), detail: this.t('appointments.cita_actualizada') });
            } else {
                await firstValueFrom(this.appointmentService.createAppointment(payload));
                this.messageService.add({ severity: 'success', summary: this.t('common.success'), detail: this.t('appointments.cita_creada') });
            }

            this.cerrarFormulario();
            this.appointmentsUiService.requestRefresh();
        } catch (error: any) {
            if (!environment.production) console.error('[AppointmentsCalendar] Error al guardar cita:', {
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

    confirmarEliminar(): void {
        if (!this.canDeleteAppointments) {
            this.messageService.add({
                severity: 'warn',
                summary: this.t('appointments.acceso_restringido'),
                detail: this.t('appointments.no_puede_eliminar')
            });
            return;
        }

        this.confirmationService.confirm({
            message: this.t('appointments.eliminar_cita_confirm'),
            header: this.t('appointments.confirmar'),
            icon: 'pi pi-exclamation-triangle',
            acceptLabel: this.t('appointments.si'),
            rejectLabel: this.t('appointments.no'),
            accept: () => this.eliminarCita()
        });
    }

    async eliminarCita(): Promise<void> {
        if (!this.canDeleteAppointments || !this.citaSeleccionada) {
            return;
        }

        try {
            await firstValueFrom(this.appointmentService.deleteAppointment(this.citaSeleccionada.id));
            this.messageService.add({ severity: 'success', summary: this.t('common.success'), detail: this.t('appointments.delete_success') });
            this.mostrarDetalle = false;
            this.appointmentsUiService.requestRefresh();
        } catch {
            this.messageService.add({ severity: 'error', summary: this.t('common.error'), detail: this.t('appointments.error_eliminar') });
        }
    }

    cerrarFormulario(): void {
        this.mostrarFormulario = false;
        this.citaSeleccionada = null;
    }

    getStatusLabel(status: string): string {
        const labels: Record<string, string> = {
            scheduled: this.t('appointments.programada'),
            completed: this.t('appointments.completada'),
            cancelled: this.t('appointments.cancelada'),
            no_show: this.t('appointments.no_asistio')
        };
        return labels[status] || status;
    }

    getStatusSeverity(status: string): 'success' | 'info' | 'danger' | 'warn' | 'secondary' {
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

    servicesOptionsForDialog(): Array<{ label: string; value: number }> {
        return this.serviciosOptions().map((service) => ({
            label: service.label.replace(/ \(\d+min\)$/, ''),
            value: service.value
        }));
    }

    private async cargarCitas(force = false): Promise<void> {
        try {
            await this.appointmentsDataService.load(force);
        } catch {
            this.messageService.add({
                severity: 'error',
                summary: this.t('common.error'),
                detail: this.t('appointments.error_cargar_citas')
            });
        }
    }

    private getInitialCalendarView(): string {
        const width = window.innerWidth;
        if (width < 768) {
            return 'listWeek';
        } else if (width < 1024) {
            return 'timeGridDay';
        }
        return 'dayGridMonth';
    }

    private initCalendar(): void {
        this.calendar = new Calendar(this.calendarEl.nativeElement, {
            plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin, listPlugin],
            initialView: this.getInitialCalendarView(),
            locales: [esLocale, frLocale, ptLocale, deLocale],
            locale: this.localeService.getCurrentLanguage(),
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek'
            },
            slotMinTime: '08:00:00',
            slotMaxTime: '21:00:00',
            slotDuration: '00:15:00',
            allDaySlot: false,
            height: 'auto',
            eventClick: (info) => this.onEventClick(info),
            events: [],
            eventColor: '#3b82f6',
            eventTimeFormat: {
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            }
        });

        this.calendar.render();
    }

    private actualizarEventos(): void {
        if (!this.calendar) {
            return;
        }

        const eventos = this.citas().map((cita) => ({
            id: cita.id.toString(),
            title: `${cita.client_name} - ${cita.service_name}`,
            start: cita.date_time,
            end: this.calcularFechaFin(cita),
            backgroundColor: this.getColorByCita(cita),
            borderColor: this.getColorByCita(cita),
            extendedProps: { cita }
        }));

        this.calendar.removeAllEvents();
        this.calendar.addEventSource(eventos);
    }

    private calcularFechaFin(cita: AppointmentWithDetails): string {
        const inicio = new Date(cita.date_time);
        const fin = new Date(inicio.getTime() + (cita.service_duration || 30) * 60000);
        return fin.toISOString();
    }

    private getColorByCita(cita: AppointmentWithDetails): string {
        switch (cita.status) {
            case 'scheduled':
                return '#3b82f6';
            case 'completed':
                return '#10b981';
            case 'cancelled':
                return '#ef4444';
            case 'no_show':
                return '#f59e0b';
            default:
                return '#6b7280';
        }
    }

    private onEventClick(info: any): void {
        this.citaSeleccionada = info.event.extendedProps.cita;
        this.mostrarDetalle = true;
    }

    @HostListener('window:resize', ['$event'])
    onResize(event: any) {
        if (!this.calendar) return;
        const width = event.target.innerWidth;
        if (width < 768) {
            this.calendar.changeView('listWeek');
        } else if (width < 1024) {
            this.calendar.changeView('timeGridDay');
        } else {
            this.calendar.changeView('dayGridMonth');
        }
    }

    private computeCanDeleteAppointments(): boolean {
        const role = this.authService.getCurrentUser()?.role;
        return role === 'CLIENT_ADMIN' || role === 'Manager';
    }

    completarCita(): void {
        if (!this.citaSeleccionada) return;
        this.citaSeleccionada.status = 'completed';
        this.mostrarDetalle = false;
        this.messageService.add({ severity: 'success', summary: 'Cita completada', detail: 'La cita ha sido marcada como completada' });
    }

    cancelarCita(): void {
        if (!this.citaSeleccionada) return;
        this.citaSeleccionada.status = 'cancelled';
        this.mostrarDetalle = false;
        this.messageService.add({ severity: 'warn', summary: 'Cita cancelada', detail: 'La cita ha sido marcada como cancelada' });
    }

    marcarNoShow(): void {
        if (!this.citaSeleccionada) return;
        this.citaSeleccionada.status = 'no_show';
        this.mostrarDetalle = false;
        this.messageService.add({ severity: 'error', summary: 'No show', detail: 'La cita ha sido marcada como no show' });
    }
}
