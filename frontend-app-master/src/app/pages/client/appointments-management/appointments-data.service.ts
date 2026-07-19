import { Injectable, computed, inject, signal, effect, untracked } from '@angular/core';
import { firstValueFrom, interval } from 'rxjs';
import { AppointmentService, AppointmentWithDetails } from '../../../core/services/appointment/appointment.service';
import { AppointmentAlertService } from '../../../core/services/appointment/appointment-alert.service';
import { ClientService } from '../../../core/services/client/client.service';
import { EmployeeService } from '../../../core/services/employee/employee.service';
import { ServiceService } from '../../../core/services/service/service.service';
import { BranchService } from '../../../core/services/branch/branch.service';

type SelectOption = { label: string; value: number };
type EmployeeOption = SelectOption & { serviceIds: number[]; branchId: number | null };
type AppointmentStatus = 'scheduled' | 'completed' | 'cancelled' | 'no_show';

@Injectable({ providedIn: 'root' })
export class AppointmentsDataService {
    private readonly appointmentService = inject(AppointmentService);
    private readonly alertService = inject(AppointmentAlertService);
    private readonly serviceService = inject(ServiceService);
    private readonly employeeService = inject(EmployeeService);
    private readonly clientService = inject(ClientService);
    private readonly branchService = inject(BranchService);

    private readonly appointmentsState = signal<AppointmentWithDetails[]>([]);
    private readonly previousAppointmentsState = signal<Map<number, AppointmentStatus>>(new Map());
    private readonly clientsOptionsState = signal<SelectOption[]>([]);
    private readonly employeesOptionsState = signal<EmployeeOption[]>([]);
    private readonly servicesOptionsState = signal<SelectOption[]>([]);
    private readonly loadingState = signal(false);
    private readonly loadedState = signal(false);

    // Rastrea citas que ya dispararon alerta de ciclo completado
    private cycleAlerterIds = new Set<number>();
    private cycleWatcherStarted = false;

    constructor() {
        // Recargar automáticamente al cambiar de sucursal
        effect(() => {
            const _branchId = this.branchService.activeBranchId();
            untracked(() => {
                if (this.loadedState()) {
                    this.load(true);
                }
            });
        });
    }

    readonly appointments = computed(() => this.appointmentsState());
    readonly clientsOptions = computed(() => this.clientsOptionsState());
    readonly employeesOptions = computed(() => {
        const activeBranchId = this.branchService.activeBranchId();
        const allEmployees = this.employeesOptionsState();
        if (!activeBranchId) {
            return allEmployees;
        }
        return allEmployees.filter(emp => emp.branchId === null || emp.branchId === activeBranchId);
    });
    readonly servicesOptions = computed(() => this.servicesOptionsState());
    readonly loading = computed(() => this.loadingState());
    readonly loaded = computed(() => this.loadedState());
    readonly stats = computed(() => {
        const appointments = this.appointmentsState();
        const now = new Date();
        const statusCounts: Record<AppointmentStatus, number> = {
            scheduled: 0,
            completed: 0,
            cancelled: 0,
            no_show: 0
        };

        for (const appointment of appointments) {
            statusCounts[appointment.status] += 1;
        }

        const todayKey = this.toDateKey(now);
        const todayCount = appointments.filter((appointment) => this.toDateKey(new Date(appointment.date_time)) === todayKey).length;
        const overdueCount = appointments.filter((appointment) => appointment.status === 'scheduled' && new Date(appointment.date_time) < now).length;
        const nextAppointment =
            [...appointments]
                .filter((appointment) => appointment.status === 'scheduled' && new Date(appointment.date_time) >= now)
                .sort((a, b) => new Date(a.date_time).getTime() - new Date(b.date_time).getTime())[0] || null;

        return {
            total: appointments.length,
            todayCount,
            overdueCount,
            statusCounts,
            nextAppointment
        };
    });

    async load(force = false): Promise<void> {
        if (this.loadingState()) {
            return;
        }

        if (this.loadedState() && !force) {
            return;
        }

        this.loadingState.set(true);
        try {
            const branchId = this.branchService.activeBranchId();
            const params = branchId ? { branch: branchId } : {};

            const [appointmentsRes, servicesRes, employeesRes, clientsRes] = await Promise.all([
                firstValueFrom(this.appointmentService.getAppointments(params)),
                firstValueFrom(this.serviceService.getActiveServices()),
                firstValueFrom(this.employeeService.getEmployees({})),
                firstValueFrom(this.clientService.getClients())
            ]);

            const appointments = this.normalizeArray<AppointmentWithDetails>(appointmentsRes);
            const services = this.normalizeArray<Record<string, any>>(servicesRes);
            const employees = this.normalizeArray<Record<string, any>>(employeesRes);
            const clients = this.normalizeArray<Record<string, any>>(clientsRes);

            type EmpRow = Record<string, any>;
            type UserRow = { id: number; full_name: string; role?: string };

            const users: UserRow[] = employees
                .map((employee: EmpRow): UserRow => ({
                    id: employee.user_id_read || employee.user?.id,
                    full_name: employee.user?.full_name || employee.full_name || employee.user?.email,
                    role: employee.user?.role
                }))
                .filter((user: UserRow) => !!user.id);

            const enrichedAppointments: AppointmentWithDetails[] = appointments.map((appointment: EmpRow): AppointmentWithDetails => {
                const service = services.find((item: EmpRow) => item.id === appointment.service);
                const employee = users.find((item: UserRow) => item.id === appointment.stylist);
                const client = clients.find((item: EmpRow) => item.id === appointment.client);

                return ({
                    ...appointment,
                    client_name: client?.name || client?.full_name || `Cliente #${appointment.client}`,
                    stylist_name: employee?.full_name || `Empleado #${appointment.stylist}`,
                    service_name: service?.name || 'Sin servicio',
                    service_price: service?.price,
                    service_duration: service?.duration || 30
                }) as AppointmentWithDetails;
            });

            this.appointmentsState.set(enrichedAppointments);
            
            // Detectar cambios de estado y disparar alertas automáticamente
            this.detectAndHandleStatusChanges(enrichedAppointments);
            
            type EmpOpt = { label: string; value: number; serviceIds: number[]; servicesCount: number; branchId: number | null };

            this.clientsOptionsState.set(
                clients.map((client: EmpRow) => ({
                    label: client.name || client.full_name || `Cliente #${client.id}`,
                    value: client.id
                }))
            );
            this.employeesOptionsState.set(
                (users
                    .map((user: UserRow): EmpOpt => {
                        const employee = employees.find((item: EmpRow) => (item.user_id_read || item.user?.id) === user.id);
                        const serviceIds = Array.isArray(employee?.service_ids) ? employee.service_ids : [];
                        const servicesCount = typeof employee?.services_count === 'number' ? employee.services_count : serviceIds.length;

                        return {
                            label: employee?.profession ? `${user.full_name || ''} (${employee.profession})` : (user.full_name || ''),
                            value: user.id,
                            serviceIds,
                            servicesCount,
                            branchId: employee?.branch ?? null
                        };
                    })
                    .filter((user: EmpOpt) => user.servicesCount > 0) as EmpOpt[])
                    .map((user: EmpOpt) => ({
                        label: user.label,
                        value: user.value,
                        serviceIds: user.serviceIds,
                        branchId: user.branchId
                    }))
            );
            this.servicesOptionsState.set(
                services.map((service: EmpRow) => ({
                    label: `${service.name} - $${service.price} (${service.duration || 30}min)`,
                    value: service.id
                }))
            );
            this.loadedState.set(true);

            // Iniciar watcher de ciclos si no está corriendo
            this.startCycleWatcher();
        } finally {
            this.loadingState.set(false);
        }
    }

    async refresh(): Promise<void> {
        // Limpiar IDs de citas que ya no están en estado scheduled
        const current = this.appointmentsState();
        const activeIds = new Set(current.filter(a => a.status === 'scheduled').map(a => a.id));
        for (const id of this.cycleAlerterIds) {
            if (!activeIds.has(id)) this.cycleAlerterIds.delete(id);
        }
        await this.load(true);
    }

    /**
     * Inicia un intervalo que verifica cada 30s si alguna cita agendada
     * completó su ciclo (hora actual >= hora inicio + duración).
     * Dispara alerta intermitente hasta que el usuario la cierre.
     */
    private startCycleWatcher(): void {
        if (this.cycleWatcherStarted) return;
        this.cycleWatcherStarted = true;

        interval(30000).subscribe(() => {
            const now = new Date().getTime();
            const appointments = this.appointmentsState();

            for (const appt of appointments) {
                if (appt.status !== 'scheduled') continue;
                if (this.cycleAlerterIds.has(appt.id)) continue;

                const startTime = new Date(appt.date_time).getTime();
                const durationMs = (appt.service_duration || 30) * 60 * 1000;
                const endTime = startTime + durationMs;

                if (now >= endTime) {
                    this.cycleAlerterIds.add(appt.id);
                    this.alertService.showAlert({
                        id: appt.id,
                        clientName: appt.client_name || `Cliente #${appt.client}`,
                        clientPhone: appt.client_phone,
                        stylistName: appt.stylist_name || `Empleado #${appt.stylist}`,
                        serviceName: appt.service_name,
                        status: 'cycle_completed',
                        dateTime: new Date(appt.date_time),
                        description: appt.description
                    });
                }
            }
        });
    }

    /**
     * Detecta cambios de estado en citas y dispara alertas automáticas
     * para estados terminales (completed, cancelled, no_show)
     * Ignora cambios de 'scheduled' a 'scheduled' (sin cambio real)
     */
    private detectAndHandleStatusChanges(currentAppointments: AppointmentWithDetails[]): void {
        const previousStates = this.previousAppointmentsState();
        const newStates = new Map<number, AppointmentStatus>();

        for (const appointment of currentAppointments) {
            const previousStatus = previousStates.get(appointment.id);
            const currentStatus = appointment.status as AppointmentStatus;

            newStates.set(appointment.id, currentStatus);

            // Solo procesar si el estado cambió Y es un estado terminal
            if (previousStatus && previousStatus !== currentStatus) {
                if (currentStatus === 'completed' || currentStatus === 'cancelled' || currentStatus === 'no_show') {
                    // Disparar alerta solo si la cita fue previamente 'scheduled'
                    // (Para evitar alertas falsas por cambios múltiples)
                    if (previousStatus === 'scheduled') {
                        this.alertService.showAlert({
                            id: appointment.id,
                            clientName: appointment.client_name || `Cliente #${appointment.client}`,
                            clientPhone: appointment.client_phone,
                            stylistName: appointment.stylist_name || `Empleado #${appointment.stylist}`,
                            serviceName: appointment.service_name,
                            status: currentStatus,
                            dateTime: new Date(appointment.date_time),
                            description: appointment.description
                        });
                    }
                }
            }
        }

        // Actualizar estado previo para la próxima comparación
        this.previousAppointmentsState.set(newStates);
    }

    private normalizeArray<T>(response: any): T[] {
        if (!response) return [];
        if (Array.isArray(response)) return response;
        if (response.results && Array.isArray(response.results)) return response.results;
        return [];
    }

    private toDateKey(date: Date): string {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
}
