import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnChanges, OnDestroy, Output, SimpleChanges, inject, signal, computed } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Subject, debounceTime, distinctUntilChanged, } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { DatePickerModule } from 'primeng/datepicker';
import { DialogModule } from 'primeng/dialog';
import { SelectModule } from 'primeng/select';
import { TextareaModule } from 'primeng/textarea';
import { AppointmentService, AppointmentWithDetails } from '../../../core/services/appointment/appointment.service';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { BranchService } from '../../../core/services/branch/branch.service';
import { PlanAccessService } from '../../../core/services/plan-access.service';
import { AuBtn } from '../../../shared/components';

export interface AppointmentDialogValue {
    client: number;
    stylist: number;
    service: number | null;
    date: Date | null;
    time: Date | null;
    description: string;
    branch?: number | null;
}

type EmployeeOption = { label: string; value: number; serviceIds?: number[] };

@Component({
    selector: 'app-appointment-dialog',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, DialogModule, SelectModule, DatePickerModule, TextareaModule, AuBtn],
    template: `
        <p-dialog
            [header]="appointment ? t('appointments.edit') : t('appointments.new')"
            [(visible)]="visible"
            [modal]="true"
            [style]="{ width: '95%', maxWidth: '600px' }"
            [closable]="!saving"
            [closeOnEscape]="!saving"
            (onHide)="handleHide()"
        >
            <form [formGroup]="form" class="grid gap-4" (ngSubmit)="onSubmit()">
                <div class="grid md:grid-cols-2 gap-4">
                    <div>
                        <label class="block font-medium mb-1">{{ t('appointments.client') }} *</label>
                        <p-select
                            formControlName="client"
                            [options]="clientsOptions"
                            appendTo="body"
                            optionLabel="label"
                            optionValue="value"
                            [placeholder]="t('appointments.seleccionar_cliente')"
                            class="w-full"
                            [filter]="true"
                        ></p-select>
                    </div>
                    <div>
                        <label class="block font-medium mb-1">{{ t('appointments.employee') }} *</label>
                        <p-select
                            formControlName="stylist"
                            [options]="filteredEmployeesOptions"
                            appendTo="body"
                            optionLabel="label"
                            optionValue="value"
                            [placeholder]="t('appointments.seleccionar_empleado')"
                            class="w-full"
                        ></p-select>
                        <small class="block mt-1 text-surface-500 dark:text-surface-400">
                            {{ form.controls.service.value ? t('appointments.hint_filtered_employees') : t('appointments.hint_all_employees') }}
                        </small>
                    </div>
                </div>

                <div class="grid md:grid-cols-2 gap-4">
                    <div>
                        <label class="block font-medium mb-1">{{ t('appointments.date') }} *</label>
                        <p-datepicker
                            formControlName="date"
                            dateFormat="dd/mm/yy"
                            appendTo="body"
                            class="w-full"
                            [minDate]="today"
                        ></p-datepicker>
                    </div>
                    <div>
                        <label class="block font-medium mb-1">{{ t('appointments.time') }} *</label>
                        @if (loadingSlots) {
                            <div class="flex items-center gap-2 p-3 text-surface-500 dark:text-surface-400">
                                <i class="pi pi-spin pi-spinner"></i>
                                <span>{{ t('appointments.cargando_horarios') }}</span>
                            </div>
                        } @else if (!form.controls.stylist.value || !form.controls.date.value) {
                            <div class="p-3 text-surface-400 text-sm border rounded-md">
                                {{ t('appointments.select_employee_date_first') }}
                            </div>
                        } @else if (availableTimes.length === 0) {
                            <div class="p-3 text-red-500 text-sm border border-red-200 rounded-md bg-red-50 dark:bg-red-900/20 dark:border-red-800">
                                {{ t('appointments.no_slots_available') }}
                            </div>
                        } @else {
                            <div class="flex flex-wrap gap-2">
                                @for (slot of availableTimes; track slot) {
                                    <button
                                        type="button"
                                        class="px-3 py-1.5 text-sm rounded-md border transition-colors cursor-pointer"
                                        [class.bg-primary-500]="form.controls.time.value && formatTimeButton(form.controls.time.value) === slot"
                                        [class.text-white]="form.controls.time.value && formatTimeButton(form.controls.time.value) === slot"
                                        [class.border-primary-500]="form.controls.time.value && formatTimeButton(form.controls.time.value) === slot"
                                        [class.border-surface-300]="!form.controls.time.value || formatTimeButton(form.controls.time.value) !== slot"
                                        [class.hover:border-primary-400]="true"
                                        (click)="selectTime(slot)"
                                    >
                                        {{ formatSlotTime(slot) }}
                                    </button>
                                }
                            </div>
                            @if (!form.controls.time.value) {
                                <small class="block mt-1 text-surface-400">{{ t('appointments.select_available_time') }}</small>
                            }
                        }
                    </div>
                </div>

                <div>
                    <label class="block font-medium mb-1">{{ t('appointments.services') }}</label>
                    <p-select
                        formControlName="service"
                        [options]="servicesOptions"
                        appendTo="body"
                        optionLabel="label"
                        optionValue="value"
                        [placeholder]="t('appointments.seleccionar_servicio')"
                        class="w-full"
                        [showClear]="true"
                    ></p-select>
                </div>

                 @if (showBranchField()) {
                    <div>
                        <label class="block font-medium mb-1">{{ t('appointments.branch') }}</label>
                        <p-select
                            formControlName="branch"
                            [options]="displayBranchOptions()"
                            appendTo="body"
                            optionLabel="label"
                            optionValue="value"
                            [placeholder]="t('appointments.sucursal')"
                            class="w-full"
                            [showClear]="true"
                        ></p-select>
                    </div>
                }

                <div>
                    <label class="block font-medium mb-1">{{ t('appointments.notes') }}</label>
                    <textarea pTextarea formControlName="description" class="w-full" rows="3" [placeholder]="t('appointments.notas_placeholder')"></textarea>
                </div>

                <div class="flex justify-end gap-2 mt-4">
                    <button au-btn variant="ghost" type="button" (click)="onCancel()" [disabled]="saving">{{ t('appointments.cancelar') }}</button>
                    <button au-btn variant="primary" type="submit" [icon]="'pi pi-check'" [loading]="saving" [disabled]="form.invalid">{{ appointment ? t('common.save') : t('appointments.crear') }}</button>
                </div>
            </form>
        </p-dialog>
    `
})
export class AppointmentDialogComponent implements OnChanges, OnDestroy {
    @Input() visible = false;
    @Input() saving = false;
    @Input() appointment: AppointmentWithDetails | null = null;
    @Input() clientsOptions: Array<{ label: string; value: number }> = [];
    @Input() employeesOptions: EmployeeOption[] = [];
    @Input() branchOptions: Array<{ label: string; value: number }> = [];
    @Input() selectedBranchId: number | null = null;
    @Input() servicesOptions: Array<{ label: string; value: number }> = [];

    @Output() visibleChange = new EventEmitter<boolean>();
    @Output() save = new EventEmitter<AppointmentDialogValue>();
    @Output() cancel = new EventEmitter<void>();

    private readonly localeService = inject(LocaleService);
    private readonly fb = inject(FormBuilder);
    private readonly branchService = inject(BranchService);
    private readonly planAccessService = inject(PlanAccessService);

 
    private readonly appointmentService = inject(AppointmentService);
    private readonly destroy$ = new Subject<void>();

    today = new Date();
    availableTimes: string[] = [];
    loadingSlots = false;

    form = this.fb.group({
        client: [null as number | null, Validators.required],
        stylist: [null as number | null, Validators.required],
        service: [null as number | null],
        date: [null as Date | null, Validators.required],
        time: [null as Date | null, Validators.required],
        description: [''],
        branch: [null as number | null]
    });
        branchOptionsInput = signal<Array<{ label: string; value: number }>>([]);

            displayBranchOptions = computed(() => {
                const inputOpts = this.branchOptionsInput();
                if (inputOpts.length > 0) {
                    return inputOpts;
                }
                return this.branchService.branches().map(b => ({ label: b.name, value: b.id }));
            });

            showBranchField = computed(() => {
                const hasAccess = this.planAccessService.canAccessFeature('multi_location');
                return hasAccess && this.displayBranchOptions().length > 1;
            });



   t(key: string): string {
        return this.localeService.t(key as any);
    }
    constructor() {
        this.form.controls.stylist.valueChanges
            .pipe(takeUntil(this.destroy$))
            .subscribe(() => {
                this.form.patchValue({ time: null });
                this.fetchAvailability();
            });

        this.form.controls.date.valueChanges
            .pipe(
                debounceTime(300),
                distinctUntilChanged(),
                takeUntil(this.destroy$)
            )
            .subscribe(() => {
                this.form.patchValue({ time: null });
                this.fetchAvailability();
            });
    }

    
   
    get filteredEmployeesOptions(): EmployeeOption[] {
        const selectedServiceId = this.form.controls.service.value;
        if (!selectedServiceId) {
            return this.employeesOptions;
        }
        return this.employeesOptions.filter((employee) => employee.serviceIds?.includes(selectedServiceId));
    }


    ngOnChanges(changes: SimpleChanges): void {
        if (changes['appointment'] || changes['visible']) {
            this.syncForm();
        }

        if (changes['employeesOptions']) {
            this.ensureSelectedStylistIsStillValid();
        }

        if (changes['branchOptions']) {
            this.branchOptionsInput.set(this.branchOptions || []);
        }
    }

    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
    }

    onSubmit(): void {
        if (this.form.invalid) {
            this.form.markAllAsTouched();
            return;
        }

        const value = this.form.getRawValue();
        this.save.emit({
            client: value.client as number,
            stylist: value.stylist as number,
            service: value.service ?? null,
            date: value.date,
            time: value.time,
            description: value.description?.trim() || '',
            branch: value.branch ?? null
        });
    }

    onCancel(): void {
        this.visible = false;
        this.visibleChange.emit(false);
        this.cancel.emit();
    }

    handleHide(): void {
        this.onCancel();
    }

    selectTime(timeStr: string): void {
        const dateValue = this.form.controls.date.value;
        if (!dateValue) return;

        const [hours, minutes] = timeStr.split(':').map(Number);
        const timeDate = new Date(dateValue);
        timeDate.setHours(hours, minutes, 0, 0);
        this.form.patchValue({ time: timeDate });
    }

    formatTimeButton(date: Date): string {
        const h = date.getHours().toString().padStart(2, '0');
        const m = date.getMinutes().toString().padStart(2, '0');
        return `${h}:${m}`;
    }

    private syncForm(): void {
        const defaultBranchId = this.selectedBranchId || this.branchService.activeBranchId();
        if (!this.visible) {
            this.form.reset({
                client: null,
                stylist: null,
                service: null,
                date: null,
                time: null,
                description: '',
                branch: null
            });
            this.availableTimes = [];
            return;
        }

        if (!this.appointment) {
            this.form.reset({
                client: null,
                stylist: null,
                service: null,
                date: null,
                time: null,
                description: '',
                branch: defaultBranchId
            });
            this.availableTimes = [];
            return;
        }

        const appointmentDate = new Date(this.appointment.date_time);
        this.form.reset({
            client: this.appointment.client,
            stylist: this.appointment.stylist,
            service: this.appointment.service ?? null,
            date: appointmentDate,
            time: appointmentDate,
            description: this.appointment.description || '',
            branch: this.appointment.branch ?? null
        });
        this.ensureSelectedStylistIsStillValid();
        this.fetchAvailability();
    }

    private ensureSelectedStylistIsStillValid(): void {
        const selectedStylist = this.form.controls.stylist.value;
        if (!selectedStylist) {
            return;
        }

        const allowedIds = new Set(this.filteredEmployeesOptions.map((employee) => employee.value));
        if (!allowedIds.has(selectedStylist)) {
            this.form.patchValue({ stylist: null });
        }
    }

    formatSlotTime(time24: string): string {
        const [h, m] = time24.split(':').map(Number);
        const period = h >= 12 ? 'PM' : 'AM';
        const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
        return `${h12}:${m.toString().padStart(2, '0')} ${period}`;
    }

    private fetchAvailability(): void {
        const stylistId = this.form.controls.stylist.value;
        const dateValue = this.form.controls.date.value;

        if (!stylistId || !dateValue) {
            this.availableTimes = [];
            return;
        }

        this.loadingSlots = true;

        const dateStr = dateValue.toISOString().split('T')[0];
        const excludeId = this.appointment ? this.appointment.id : undefined;

        this.appointmentService.getAvailability(stylistId, dateStr, excludeId)
            .pipe(takeUntil(this.destroy$))
            .subscribe({
                next: (response) => {
                    if (response?.available_slots) {
                        this.availableTimes = response.available_slots
                            .filter((s: any) => s.available)
                            .map((s: any) => s.time);
                    } else {
                        this.availableTimes = [];
                    }
                    this.loadingSlots = false;
                },
                error: () => {
                    this.availableTimes = [];
                    this.loadingSlots = false;
                }
            });
    }
}
