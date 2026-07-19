import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MessageService, ConfirmationService } from 'primeng/api';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { TextareaModule } from 'primeng/textarea';
import { InputNumberModule } from 'primeng/inputnumber';
import { SelectModule } from 'primeng/select';
import { CheckboxModule } from 'primeng/checkbox';
import { TagModule } from 'primeng/tag';
import { ToastModule } from 'primeng/toast';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { TooltipModule } from 'primeng/tooltip';
import { BadgeModule } from 'primeng/badge';
import { PosService } from '../../../core/services/pos/pos.service';
import { SettingsService } from '../../../core/services/settings/settings.service';
import { AuthService } from '../../../core/services/auth/auth.service';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { I18nPipe } from '../../../core/pipes/i18n.pipe';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { AuBtn, AuSkeleton } from '../../../shared/components';

interface Promotion {
    id: number;
    name: string;
    description: string;
    type: 'percentage' | 'fixed' | 'buy_x_get_y' | 'combo';
    conditions?: any;
    discount_value: number;
    min_amount: number;
    start_date: string;
    end_date: string;
    is_active: boolean;
    max_uses?: number | null;
    current_uses: number;
}

@Component({
    selector: 'app-promotions-management',
    standalone: true,
    imports: [
        CommonModule,
        ReactiveFormsModule,
        TableModule,
        ButtonModule,
        DialogModule,
        InputTextModule,
        TextareaModule,
        InputNumberModule,
        SelectModule,
        CheckboxModule,
        TagModule,
        ToastModule,
        ConfirmDialogModule,
        TooltipModule,
        BadgeModule,
        AuSkeleton,
        I18nPipe,
        AuBtn
    ],
    providers: [MessageService, ConfirmationService],
    template: `
        <div class="space-y-6">
            <section class="overflow-hidden rounded-[2rem] border border-surface-200 bg-white shadow-sm shadow-[var(--shadow-elevated)] dark:border-surface-700 dark:bg-surface-900">
                <div class="relative overflow-hidden px-8 py-8 lg:px-10">
                    <div class="hero-gradient pointer-events-none absolute inset-0 bg-gradient-to-br from-primary-50/30 via-transparent to-transparent dark:from-primary-950/20"></div>
                    <div class="relative grid gap-8 lg:grid-cols-[minmax(0,1.5fr)_minmax(320px,0.9fr)] lg:items-start">
                        <div class="space-y-5">
                            <div class="inline-flex items-center gap-2 rounded-full bg-surface-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-surface-600 dark:bg-surface-800 dark:text-surface-300">
                                <i class="pi pi-tags text-[0.7rem] text-primary"></i>
                                {{ 'menu.promotions' | t }}
                            </div>
                            <div>
                                <h2 class="display-4 text-surface-950 dark:text-white">{{ 'menu.promotions' | t }}</h2>
                                <p class="mt-3 max-w-3xl text-base leading-7 text-surface-600 dark:text-surface-300">
                                    {{ 'promotions.subtitle' | t }}
                                </p>
                             </div>
                            <div class="grid gap-3 md:grid-cols-3">
                                <article class="rounded-2xl border border-surface-200 bg-white/80 p-4 shadow-sm backdrop-blur dark:border-surface-700 dark:bg-surface-800/80">
                                    <div class="text-[11px] font-semibold uppercase tracking-[0.24em] text-surface-500 dark:text-surface-400">{{ 'promotions.total' | t }}</div>
                                    <div class="mt-2 text-2xl font-semibold text-surface-950 dark:text-white">{{ promociones().length }}</div>
                                </article>
                                <article class="rounded-2xl border border-surface-200 bg-white/80 p-4 shadow-sm backdrop-blur dark:border-surface-700 dark:bg-surface-800/80">
                                    <div class="text-[11px] font-semibold uppercase tracking-[0.24em] text-surface-500 dark:text-surface-400">{{ 'promotions.active' | t }}</div>
                                    <div class="mt-2 text-2xl font-semibold text-surface-950 dark:text-white">{{ getActivePromotionsCount() }}</div>
                                </article>
                                <article class="rounded-2xl border border-surface-200 bg-white/80 p-4 shadow-sm backdrop-blur dark:border-surface-700 dark:bg-surface-800/80">
                                    <div class="text-[11px] font-semibold uppercase tracking-[0.24em] text-surface-500 dark:text-surface-400">{{ 'auth.verify.invalid_link_title' | t }}</div>
                                    <div class="mt-2 text-2xl font-semibold text-surface-950 dark:text-white">{{ getExpiredPromotionsCount() }}</div>
                                </article>
                            </div>
                        </div>

                        <div class="rounded-3xl border border-surface-200 bg-white/80 p-5 shadow-sm backdrop-blur dark:border-surface-700 dark:bg-surface-800/80">
                            <div class="flex items-start justify-between gap-4">
                                <div>
                                    <div class="text-[11px] font-semibold uppercase tracking-[0.28em] text-surface-500 dark:text-surface-400">{{ 'promotions.main_action' | t }}</div>
                                    <div class="mt-2 text-2xl font-semibold text-surface-950 dark:text-white">{{ 'promotions.new' | t }}</div>
                                </div>
                                <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-50 dark:bg-primary-900/30">
                                    <i class="pi pi-percentage text-lg text-primary"></i>
                                </div>
                            </div>
                            <div class="mt-5 rounded-2xl border border-surface-200/60 bg-surface-50/60 p-4 text-sm leading-6 text-surface-600 dark:border-surface-700/60 dark:bg-surface-800/40 dark:text-surface-300">
                                {{ getPromotionsNarrative() }}
                            </div>
                            <div class="mt-5 flex flex-col gap-2">
                                <button *ngIf="canManagePromotions()" au-btn variant="primary" icon="pi pi-plus" (click)="abrirDialogo()" class="w-full">{{ 'promotions.new' | t }}</button>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="border-t border-surface-200/80 px-6 py-5 dark:border-surface-800 xl:px-8">
                    <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                        <div class="rounded-2xl bg-surface-100 px-4 py-2 text-sm text-surface-500 dark:bg-surface-800 dark:text-surface-300">
                            {{ 'promotions.narrative_hint' | t }}
                        </div>
                        <button au-btn variant="ghost" icon="pi pi-refresh" (click)="cargarPromociones()" class="self-start lg:self-auto">{{ 'promotions.reload' | t }}</button>
                    </div>
                </div>
            </section>

            <section class="overflow-hidden rounded-[1.75rem] border border-surface-200 bg-white shadow-sm dark:border-surface-700 dark:bg-surface-900">
                <!-- Escritorio: Tabla de promociones -->
                <div class="hidden md:block">
                <p-table [value]="promociones()" [loading]="cargando()"
                         [globalFilterFields]="['name', 'type', 'description']"
                         responsiveLayout="scroll"
                         #dt>
                    <ng-template pTemplate="caption">
                        <div class="flex flex-col gap-3 p-2 lg:flex-row lg:items-center lg:justify-between">
                            <span class="text-sm text-surface-600 dark:text-surface-300">
                                {{ promociones().length }} {{ 'menu.promotions' | t | lowercase }}
                            </span>
                            <span class="p-input-icon-left w-full lg:w-80">
                                <i class="pi pi-search"></i>
                                <input pInputText type="text" [placeholder]="'promotions.search_placeholder' | t"
                                       class="w-full"
                                       (input)="dt.filterGlobal($any($event.target).value, 'contains')"
                                       (keyup.enter)="dt.filterGlobal($any($event.target).value, 'contains')">
                            </span>
                        </div>
                    </ng-template>

                    <ng-template pTemplate="header">
                        <tr>
                            <th>{{ 'auth.register.owner_name' | t }}</th>
                            <th>{{ 'promotions.th.type' | t }}</th>
                            <th>{{ 'promotions.th.value' | t }}</th>
                            <th>{{ 'promotions.min_amount' | t }}</th>
                            <th>{{ 'promotions.th.start_date' | t }}</th>
                            <th>{{ 'promotions.th.actions' | t }}</th>
                            <th>{{ 'promotions.th.status' | t }}</th>
                            <th *ngIf="canManagePromotions()">{{ 'promotions.th.actions' | t }}</th>
                        </tr>
                    </ng-template>

                    <ng-template pTemplate="body" let-promo>
                        <tr>
                            <td>
                                <div class="font-medium text-surface-900 dark:text-white">{{ promo.name }}</div>
                                <div class="text-xs text-surface-500 dark:text-surface-400 mt-0.5" *ngIf="promo.description">
                                    {{ promo.description }}
                                </div>
                            </td>
                            <td>
                                <p-tag [value]="getPromoTypeLabel(promo.type)" [severity]="getPromoTypeSeverity(promo.type)"></p-tag>
                            </td>
                            <td class="font-medium">
                                {{ promo.type === 'percentage' ? (promo.discount_value | number:'1.0-2') + '%' : formatearMoneda(promo.discount_value) }}
                            </td>
                            <td>{{ formatearMoneda(promo.min_amount) }}</td>
                            <td>
                                <div class="text-xs text-surface-700 dark:text-surface-300">
                                    <span>Desde: {{ promo.start_date | date:'dd/MM/yyyy HH:mm' }}</span>
                                    <br>
                                    <span [class.text-red-500]="isExpired(promo.end_date)">
                                        Hasta: {{ promo.end_date | date:'dd/MM/yyyy HH:mm' }}
                                    </span>
                                </div>
                            </td>
                            <td>
                                <div class="text-sm">
                                    {{ promo.current_uses }} / {{ promo.max_uses || '∞' }}
                                </div>
                            </td>
                            <td>
                                <p-tag [value]="getPromoStatusLabel(promo)" [severity]="getPromoStatusSeverity(promo)"></p-tag>
                            </td>
                            <td *ngIf="canManagePromotions()">
                                <div class="flex gap-1">
                                    <button pButton icon="pi pi-pencil" class="p-button-text p-button-sm"
                                            (click)="editarPromocion(promo)" [pTooltip]="'common.edit' | t"></button>
                                    <button pButton icon="pi pi-trash" class="p-button-text p-button-sm p-button-danger"
                                            (click)="confirmarEliminar(promo)" [pTooltip]="'common.delete' | t"></button>
                                </div>
                            </td>
                        </tr>
                    </ng-template>

                    <ng-template pTemplate="emptymessage">
                        <tr>
                            <td [attr.colspan]="canManagePromotions() ? 8 : 7" class="text-center py-6 text-surface-500 dark:text-surface-400">
                                {{ 'promotions.no_promotions' | t }}
                            </td>
                        </tr>
                    </ng-template>
                </p-table>
                </div>

                <!-- Móvil: Tarjetas apiladas -->
                <div class="block md:hidden p-4 space-y-4">
                    <div class="flex flex-col gap-3 mb-2">
                        <span class="text-sm text-surface-600 dark:text-surface-300">
                            {{ promociones().length }} {{ 'menu.promotions' | t | lowercase }}
                        </span>
                        <span class="p-input-icon-left w-full">
                            <i class="pi pi-search"></i>
                            <input pInputText type="text" [placeholder]="'promotions.search_placeholder' | t"
                                   class="w-full"
                                   (input)="dt.filterGlobal($any($event.target).value, 'contains')">
                        </span>
                    </div>

                    @if (cargando()) {
                        @for (i of [1,2,3]; track i) {
                            <div class="bg-white dark:bg-surface-900 p-4 rounded-xl border border-surface-200 dark:border-surface-800 shadow-sm space-y-3">
                                <div class="space-y-2">
                                    <au-skeleton width="140px" height="16px" />
                                    <au-skeleton width="100px" height="12px" />
                                </div>
                                <div class="flex justify-between items-center mt-4">
                                    <au-skeleton width="80px" height="20px" />
                                    <au-skeleton width="60px" height="16px" />
                                </div>
                            </div>
                        }
                    } @else {
                        @for (promo of (dt.filteredValue || promociones()); track promo.id) {
                            <div class="bg-white dark:bg-surface-900 p-4 rounded-xl border border-surface-200 dark:border-surface-800 shadow-sm space-y-3">
                                <div class="flex justify-between items-start">
                                    <div>
                                        <h4 class="font-bold text-surface-900 dark:text-white">{{ promo.name }}</h4>
                                        <span class="text-xs text-surface-500" *ngIf="promo.description">{{ promo.description }}</span>
                                    </div>
                                    <p-tag [value]="getPromoTypeLabel(promo.type)" [severity]="getPromoTypeSeverity(promo.type)"></p-tag>
                                </div>
                                <div class="flex justify-between items-center text-xs text-surface-700 dark:text-surface-300">
                                    <span>{{ 'promotions.th.value' | t }}:</span>
                                    <span class="font-bold text-surface-900 dark:text-white">
                                        {{ promo.type === 'percentage' ? (promo.discount_value | number:'1.0-2') + '%' : formatearMoneda(promo.discount_value) }}
                                    </span>
                                </div>
                                <div class="flex justify-between items-center text-xs text-surface-700 dark:text-surface-300" *ngIf="promo.min_amount">
                                    <span>{{ 'promotions.min_amount' | t }}:</span>
                                    <span class="font-bold text-surface-900 dark:text-white">{{ formatearMoneda(promo.min_amount) }}</span>
                                </div>
                                <div class="flex justify-between items-center text-xs text-surface-700 dark:text-surface-300">
                                    <span>{{ 'promotions.th.actions' | t }}:</span>
                                    <span>{{ promo.current_uses }} / {{ promo.max_uses || '∞' }}</span>
                                </div>
                                <div class="text-xs space-y-1 text-surface-500 pt-2 border-t border-surface-100 dark:border-surface-800">
                                    <div>Desde: {{ promo.start_date | date:'dd/MM/yyyy HH:mm' }}</div>
                                    <div [class.text-red-500]="isExpired(promo.end_date)">Hasta: {{ promo.end_date | date:'dd/MM/yyyy HH:mm' }}</div>
                                </div>
                                <div class="flex justify-between items-center pt-2">
                                    <p-tag [value]="getPromoStatusLabel(promo)" [severity]="getPromoStatusSeverity(promo)"></p-tag>
                                    <div class="flex gap-2" *ngIf="canManagePromotions()">
                                        <button au-btn variant="ghost" size="sm" icon="pi pi-pencil" [iconOnly]="true"
                                                (click)="editarPromocion(promo)"></button>
                                        <button au-btn variant="danger" size="sm" icon="pi pi-trash" [iconOnly]="true"
                                                (click)="confirmarEliminar(promo)"></button>
                                    </div>
                                </div>
                            </div>
                        }
                        @if ((dt.filteredValue || promociones()).length === 0) {
                            <div class="text-center py-8 text-surface-500 dark:text-surface-400">
                                {{ 'promotions.no_promotions' | t }}
                            </div>
                        }
                    }
                </div>
            </section>
        </div>

        <!-- Diálogo para Crear / Editar Promoción -->
        <p-dialog [header]="promocionSeleccionada ? ('promotions.edit' | t) : ('promotions.new' | t)"
                  [(visible)]="mostrarDialogo" [modal]="true" [style]="{ width: '92vw', maxWidth: '600px' }"
                  [breakpoints]="{'960px':'75vw','640px':'100vw'}"
                  styleClass="shadow-2xl" (onHide)="cerrarDialogo()">
            <form [formGroup]="formulario" (ngSubmit)="guardarPromocion()" class="space-y-4 pt-2" *ngIf="mostrarDialogo">
                
                <div>
                    <label class="block font-semibold mb-1">{{ 'promotions.name' | t }}</label>
                    <input pInputText formControlName="name" class="w-full"
                           [placeholder]="'promotions.name' | t"
                           [class.ng-invalid]="formulario.get('name')?.invalid && formulario.get('name')?.touched">
                </div>

                <div>
                    <label class="block font-semibold mb-1">{{ 'promotions.form.description' | t }}</label>
                    <textarea pInputTextarea formControlName="description" class="w-full" rows="2"
                              [placeholder]="'promotions.form.description' | t"></textarea>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label class="block font-semibold mb-1">{{ 'promotions.type' | t }}</label>
                        <p-select formControlName="type" [options]="tiposOptions" appendTo="body"
                                  optionLabel="label" optionValue="value"
                                  [placeholder]="'promotions.type' | t" class="w-full">
                        </p-select>
                    </div>
                    <div>
                        <label class="block font-semibold mb-1">
                            {{ formulario.get('type')?.value === 'percentage' ? ('promotions.types.percentage' | t) : ('promotions.types.fixed' | t) }}
                        </label>
                        <p-inputNumber formControlName="discount_value" class="w-full"
                                       [min]="0" [max]="formulario.get('type')?.value === 'percentage' ? 100 : 999999"
                                       [step]="formulario.get('type')?.value === 'percentage' ? 1 : 0.01"
                                       [mode]="formulario.get('type')?.value === 'percentage' ? 'decimal' : 'currency'"
                                       [currency]="currencyCode()" [locale]="currencyLocale()">
                        </p-inputNumber>
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label class="block font-semibold mb-1">{{ 'promotions.min_amount' | t }}</label>
                        <p-inputNumber formControlName="min_amount" class="w-full"
                                       [min]="0" mode="currency" [currency]="currencyCode()" [locale]="currencyLocale()">
                        </p-inputNumber>
                    </div>
                    <div>
                        <label class="block font-semibold mb-1">{{ 'promotions.th.actions' | t }}</label>
                        <p-inputNumber formControlName="max_uses" class="w-full" [min]="1" [step]="1">
                        </p-inputNumber>
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label class="block font-semibold mb-1">{{ 'promotions.start_date' | t }}</label>
                        <input type="datetime-local" pInputText formControlName="start_date" class="w-full"
                               [class.ng-invalid]="formulario.get('start_date')?.invalid && formulario.get('start_date')?.touched">
                    </div>
                    <div>
                        <label class="block font-semibold mb-1">{{ 'promotions.end_date' | t }}</label>
                        <input type="datetime-local" pInputText formControlName="end_date" class="w-full"
                               [class.ng-invalid]="formulario.get('end_date')?.invalid && formulario.get('end_date')?.touched">
                    </div>
                </div>

                <div class="flex items-center">
                    <p-checkbox formControlName="is_active" [binary]="true" inputId="is_active"></p-checkbox>
                    <label for="is_active" class="ml-2 font-medium">{{ 'promotions.form.active_checkbox' | t }}</label>
                </div>

                <div class="flex justify-end gap-2 mt-6">
                    <button au-btn variant="ghost" type="button"
                            (click)="cerrarDialogo()" [disabled]="guardando()">{{ 'common.cancel' | t }}</button>
                    <button au-btn variant="primary" type="submit" icon="pi pi-check" [loading]="guardando()"
                            [disabled]="formulario.invalid">{{ promocionSeleccionada ? ('common.edit' | t) : ('common.save' | t) }}</button>
                </div>
            </form>
        </p-dialog>

        <p-confirmDialog></p-confirmDialog>
        <p-toast></p-toast>
    `
})
export class PromotionsManagement implements OnInit {
    private posService = inject(PosService);
    private localeService = inject(LocaleService);
    private settingsService = inject(SettingsService);
    private messageService = inject(MessageService);
    private confirmationService = inject(ConfirmationService);
    private fb = inject(FormBuilder);
    private authService = inject(AuthService);

        t(key: string): string {
        return this.localeService.t(key as any);
    }

    promociones = signal<Promotion[]>([]);
    cargando = signal(false);
    guardando = signal(false);

    mostrarDialogo = false;
    promocionSeleccionada: Promotion | null = null;

    currencyCode = computed(() => this.settingsService.settings().currency || 'DOP');
    currencyLocale = computed(() => this.settingsService.getCurrencyLocale());

    get tiposOptions() {
        return [
            { label: this.t('promotions.types.percentage'), value: 'percentage' },
            { label: this.t('promotions.types.fixed'), value: 'fixed' }
        ];
    }

    formulario: FormGroup = this.fb.group({
        name: ['', [Validators.required, Validators.maxLength(255)]],
        description: [''],
        type: ['percentage', [Validators.required]],
        discount_value: [0, [Validators.required, Validators.min(0)]],
        min_amount: [0, [Validators.required, Validators.min(0)]],
        max_uses: [null, [Validators.min(1)]],
        start_date: ['', [Validators.required]],
        end_date: ['', [Validators.required]],
        is_active: [true]
    }, { validators: this.datesValidator });

    ngOnInit() {
        this.cargarPromociones();
    }

    datesValidator(group: FormGroup) {
        const start = group.get('start_date')?.value;
        const end = group.get('end_date')?.value;
        if (start && end && new Date(start) >= new Date(end)) {
            group.get('end_date')?.setErrors({ dateLessThanStart: true });
            return { dateLessThanStart: true };
        }
        return null;
    }

    canManagePromotions = computed(() => {
        const user = this.authService.getCurrentUser();
        if (!user) return false;
        const role = (user.role || '').trim().toUpperCase().replace(/[\s-]+/g, '_');
        const businessRole = (user.business_role || '').trim().toLowerCase().replace(/[\s-]+/g, '_');
        return role === 'CLIENT_ADMIN' || businessRole === 'owner' || businessRole === 'manager';
    });

    async cargarPromociones() {
        this.cargando.set(true);
        try {
            const response = await firstValueFrom(this.posService.getPromotions());
            const list = (response as any)?.results || response || [];
            this.promociones.set(list);
        } catch (error: any) {
            if (error?.status !== 401 && error?.status !== 403) {
                this.messageService.add({
                    severity: 'error',
                    summary: 'Error',
                    detail: error?.error?.detail || this.t('promotions.toast.load_error')
                });
            }
        } finally {
            this.cargando.set(false);
        }
    }

    getActivePromotionsCount() {
        const now = new Date();
        return this.promociones().filter(p => p.is_active && new Date(p.start_date) <= now && new Date(p.end_date) >= now).length;
    }

    getPromotionsNarrative(): string {
        const total = this.promociones().length;
        if (!total) {
            return this.t('promotions.narrative_empty');
        }
        return this.t('promotions.narrative_active')
            .replace('{active}', String(this.getActivePromotionsCount()))
            .replace('{upcoming}', String(this.promociones().filter(p => p.is_active && new Date(p.start_date) > new Date()).length))
            .replace('{total}', String(total));
    }

    getExpiredPromotionsCount() {
        const now = new Date();
        return this.promociones().filter(p => new Date(p.end_date) < now).length;
    }

    isExpired(dateStr: string): boolean {
        return new Date(dateStr) < new Date();
    }

    getPromoTypeLabel(type: string): string {
        switch (type) {
            case 'percentage': return this.t('promotions.types.percentage');
            case 'fixed': return this.t('promotions.types.fixed');
            case 'buy_x_get_y': return 'Compra X lleva Y';
            case 'combo': return 'Combo';
            default: return type;
        }
    }

    getPromoTypeSeverity(type: string): 'info' | 'warn' | 'success' | 'secondary' {
        switch (type) {
            case 'percentage': return 'info';
            case 'fixed': return 'success';
            case 'buy_x_get_y': return 'warn';
            default: return 'secondary';
        }
    }

    getPromoStatusLabel(promo: Promotion): string {
        if (!promo.is_active) return this.t('promotions.status.inactive');
        const now = new Date();
        if (new Date(promo.start_date) > now) return this.t('promotions.status.scheduled');
        if (new Date(promo.end_date) < now) return this.t('promotions.status.expired');
        if (promo.max_uses && promo.current_uses >= promo.max_uses) return 'Agotada';
        return this.t('promotions.status.active');
    }

    getPromoStatusSeverity(promo: Promotion): 'success' | 'warn' | 'danger' | 'secondary' | 'info' {
        if (!promo.is_active) return 'secondary';
        const now = new Date();
        if (new Date(promo.start_date) > now) return 'info';
        if (new Date(promo.end_date) < now) return 'danger';
        if (promo.max_uses && promo.current_uses >= promo.max_uses) return 'warn';
        return 'success';
    }

    formatearMoneda(valor: number): string {
        try {
            return new Intl.NumberFormat(this.currencyLocale(), {
                style: 'currency',
                currency: this.currencyCode()
            }).format(valor);
        } catch {
            return `$${valor.toFixed(2)}`;
        }
    }

    abrirDialogo() {
        this.promocionSeleccionada = null;
        this.formulario.reset({
            name: '',
            description: '',
            type: 'percentage',
            discount_value: 0,
            min_amount: 0,
            max_uses: null,
            start_date: this.formatDateForInput(new Date()),
            end_date: this.formatDateForInput(new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)), // +30 dias
            is_active: true
        });
        this.mostrarDialogo = true;
    }

    editarPromocion(promo: Promotion) {
        this.promocionSeleccionada = promo;
        this.formulario.patchValue({
            name: promo.name,
            description: promo.description || '',
            type: promo.type,
            discount_value: promo.discount_value,
            min_amount: promo.min_amount,
            max_uses: promo.max_uses,
            start_date: this.formatDateForInput(new Date(promo.start_date)),
            end_date: this.formatDateForInput(new Date(promo.end_date)),
            is_active: promo.is_active
        });
        this.mostrarDialogo = true;
    }

    cerrarDialogo() {
        this.mostrarDialogo = false;
        this.promocionSeleccionada = null;
    }

    async guardarPromocion() {
        if (this.formulario.invalid) return;

        this.guardando.set(true);
        const data = { ...this.formulario.value };
        
        // Formatear fechas a ISO string para la API
        data.start_date = new Date(data.start_date).toISOString();
        data.end_date = new Date(data.end_date).toISOString();

        try {
            if (this.promocionSeleccionada) {
                await firstValueFrom(this.posService.updatePromotion(this.promocionSeleccionada.id, data));
            } else {
                await firstValueFrom(this.posService.createPromotion(data));
            }

            this.messageService.add({
                severity: 'success',
                summary: 'Éxito',
                detail: this.promocionSeleccionada ? this.t('promotions.toast.update_success') : this.t('promotions.toast.create_success')
            });

            this.cerrarDialogo();
            this.cargarPromociones();
        } catch (error: any) {
            this.messageService.add({
                severity: 'error',
                summary: 'Error al guardar',
                detail: error?.error?.detail || error?.message || 'Ocurrió un error inesperado'
            });
        } finally {
            this.guardando.set(false);
        }
    }

    confirmarEliminar(promo: Promotion) {
        this.confirmationService.confirm({
            message: this.t('promotions.delete_confirm_msg').replace('{name}', promo.name),
            header: this.t('promotions.confirm_delete_title'),
            icon: 'pi pi-exclamation-triangle',
            acceptLabel: this.t('promotions.confirm_delete_accept'),
            rejectLabel: this.t('common.cancel'),
            acceptButtonStyleClass: 'p-button-danger',
            rejectButtonStyleClass: 'p-button-text',
            accept: async () => {
                try {
                    await firstValueFrom(this.posService.deletePromotion(promo.id));
                    this.messageService.add({
                        severity: 'success',
                        summary: 'Éxito',
                        detail: this.t('promotions.toast.delete_success')
                    });
                    this.cargarPromociones();
                } catch (error: any) {
                    this.messageService.add({
                        severity: 'error',
                        summary: 'Error',
                        detail: error?.error?.detail || this.t('promotions.toast.delete_success')
                    });
                }
            }
        });
    }

    private formatDateForInput(date: Date): string {
        const pad = (num: number) => num.toString().padStart(2, '0');
        const yyyy = date.getFullYear();
        const MM = pad(date.getMonth() + 1);
        const dd = pad(date.getDate());
        const hh = pad(date.getHours());
        const mm = pad(date.getMinutes());
        return `${yyyy}-${MM}-${dd}T${hh}:${mm}`;
    }
}
