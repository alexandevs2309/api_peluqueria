import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MessageService, ConfirmationService } from 'primeng/api';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { TextareaModule } from 'primeng/textarea';
import { InputNumberModule } from 'primeng/inputnumber';
import { MultiSelectModule } from 'primeng/multiselect';
import { CheckboxModule } from 'primeng/checkbox';
import { TagModule } from 'primeng/tag';
import { ToastModule } from 'primeng/toast';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { TooltipModule } from 'primeng/tooltip';
import { FileUploadModule } from 'primeng/fileupload';
import { ServiceService, Service, ServiceCategory } from '../../../core/services/service/service.service';
import { environment } from '../../../../environments/environment';
import { ServiceDto, ServiceCategoryDto, CreateServiceDto, UpdateServiceDto } from '../../../core/dto/service.dto';
import { SettingsService } from '../../../core/services/settings/settings.service';
import { AuthService } from '../../../core/services/auth/auth.service';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { firstValueFrom } from 'rxjs';
import { I18nPipe } from '../../../core/pipes/i18n.pipe';
import { AuronEmptyStateComponent } from '../../../shared/components/auron-empty-state/auron-empty-state.component';
import { AuronEyebrowComponent } from '../../../shared/components/auron-eyebrow/auron-eyebrow.component';
import { AuBtn, AuSkeleton } from '../../../shared/components';

@Component({
    selector: 'app-services-management',
    standalone: true,
    imports: [
        CommonModule,
        I18nPipe,
        FormsModule,
        ReactiveFormsModule,
        TableModule,
        ButtonModule,
        DialogModule,
        InputTextModule,
        TextareaModule,
        InputNumberModule,
        MultiSelectModule,
        CheckboxModule,
        TagModule,
        ToastModule,
        ConfirmDialogModule,
        TooltipModule,
        FileUploadModule,
        AuSkeleton,
        AuronEmptyStateComponent,
        AuronEyebrowComponent,
        AuBtn
    ],
    providers: [MessageService, ConfirmationService],
    template: `
        <div class="space-y-6">
            <section class="relative overflow-hidden rounded-[2rem] border border-surface-200 bg-white shadow-[var(--shadow-elevated)] dark:border-surface-700 dark:bg-surface-900">
                <div class="hero-gradient pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(99,102,241,0.12),transparent_50%)]"></div>
                <div class="relative overflow-hidden px-8 py-8 lg:px-10">
                    <div class="relative space-y-7">
                        <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                            <div>
                                <auron-eyebrow class="mb-4 block" icon="pi pi-wrench" label="Catálogo vivo"></auron-eyebrow>
                                <h2 class="display-4 text-surface-950 dark:text-white">Servicios del salón</h2>
                                <p class="mt-3 max-w-3xl text-base leading-7 text-surface-600 dark:text-surface-300">
                                    Catálogo conectado al POS para vender cortes, color, spa y tratamientos con precio, duración y categoría claros.
                                </p>
                            </div>
                            <button *ngIf="canManageServices()" au-btn variant="primary" icon="pi pi-plus" (click)="abrirDialogo()" class="self-start">{{ 'services.new' | t }}</button>
                        </div>

                        <div class="grid gap-3 sm:grid-cols-3">
                            <div class="rounded-2xl border border-surface-200 bg-white/70 p-4 dark:border-surface-700 dark:bg-surface-800/70">
                                <div class="text-xs font-semibold uppercase tracking-[0.22em] text-surface-500 dark:text-surface-400">{{ 'services.total' | t }}</div>
                                <div class="mt-2 text-3xl font-black text-surface-950 dark:text-white">{{ servicios().length }}</div>
                            </div>
                            <div class="rounded-2xl border border-emerald-200/30 bg-emerald-50/70 p-4 dark:border-emerald-500/20 dark:bg-emerald-500/10">
                                <div class="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-700 dark:text-emerald-200">{{ 'services.active' | t }}</div>
                                <div class="mt-2 text-3xl font-black text-emerald-700 dark:text-emerald-200">{{ getActiveServicesCount() }}</div>
                            </div>
                            <div class="rounded-2xl border border-[var(--brand)]/20 bg-[rgba(26,86,219,0.06)] p-4 dark:border-[var(--brand)]/30 dark:bg-[rgba(26,86,219,0.08)]">
                                <div class="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--brand)] dark:text-[var(--brand-400)]">{{ 'services.categories' | t }}</div>
                                <div class="mt-2 text-3xl font-black text-surface-950 dark:text-white">{{ categoriasDisponibles.length }}</div>
                            </div>
                        </div>

                        <div class="grid gap-3 lg:grid-cols-3">
                            <div *ngFor="let highlight of getServiceHighlights()" class="rounded-2xl border border-surface-200 bg-white/70 p-4 dark:border-surface-700 dark:bg-surface-800/70">
                                <div class="text-[11px] font-semibold uppercase tracking-[0.2em] text-surface-500 dark:text-surface-400">{{ highlight.label }}</div>
                                <div class="mt-2 text-lg font-semibold text-surface-950 dark:text-white">{{ highlight.name }}</div>
                                <div class="mt-1 text-sm text-surface-500 dark:text-surface-400">{{ highlight.meta }}</div>
                            </div>
                        </div>

                        <p class="rounded-2xl border border-surface-200 bg-surface-50/70 px-4 py-3 text-sm leading-6 text-surface-600 dark:border-surface-700 dark:bg-surface-800/50 dark:text-surface-300">
                            {{ getServicesNarrative() }}
                        </p>
                    </div>
                </div>
                <div class="border-t border-surface-200/80 px-6 py-5 dark:border-surface-800 xl:px-8">
                    <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                        <div class="rounded-2xl bg-surface-100 px-4 py-2 text-sm text-surface-500 dark:bg-surface-800 dark:text-surface-300">
                            {{ 'services.narrative_hint' | t }}
                        </div>
                    </div>
                </div>
            </section>

            <section class="overflow-hidden rounded-[1.75rem] border border-surface-200 bg-white shadow-sm dark:border-surface-700 dark:bg-surface-900">
            <!-- Escritorio: Tabla tradicional -->
            <div class="hidden md:block">
            <p-table [value]="servicios()" [loading]="false"
                     [globalFilterFields]="['name', 'category', 'description']"
                     responsiveLayout="scroll"
                     #dt>
                <ng-template pTemplate="caption">
                    <div class="flex flex-col gap-3 p-2 lg:flex-row lg:items-center lg:justify-between">
                        <span class="text-sm text-surface-600 dark:text-surface-300">
                            {{ servicios().length }} {{ 'menu.services' | t | lowercase }}
                        </span>
                        <span class="p-input-icon-left w-full lg:w-80">
                            <i class="pi pi-search"></i>
                            <input pInputText type="text" [placeholder]="'services.search_placeholder' | t"
                                   class="w-full"
                                   (input)="dt.filterGlobal($any($event.target).value, 'contains')"
                                   (keyup.enter)="dt.filterGlobal($any($event.target).value, 'contains')">
                        </span>
                    </div>
                </ng-template>

                <ng-template pTemplate="header">
                    <tr>
                        <th>{{ 'services.th.service' | t }}</th>
                        <th>{{ 'services.th.category' | t }}</th>
                        <th>{{ 'services.th.price' | t }}</th>
                        <th>{{ 'services.th.duration' | t }}</th>
                        <th>{{ 'services.th.status' | t }}</th>
                        <th>{{ 'services.th.actions' | t }}</th>
                    </tr>
                </ng-template>

                <ng-template pTemplate="body" let-servicio>
                    @if (cargando()) {
                        @for (i of [1,2,3,4,5]; track i) {
                            <tr>
                                <td>
                                    <div class="flex flex-col gap-1">
                                        <au-skeleton width="140px" height="16px" />
                                        <au-skeleton width="80px" height="12px" />
                                    </div>
                                </td>
                                <td><au-skeleton width="100px" height="24px" /></td>
                                <td><au-skeleton width="80px" height="16px" /></td>
                                <td><au-skeleton width="60px" height="16px" /></td>
                                <td><au-skeleton width="80px" height="24px" /></td>
                                <td>
                                    <div class="flex gap-1">
                                        <au-skeleton width="28px" height="28px" />
                                        <au-skeleton width="28px" height="28px" />
                                    </div>
                                </td>
                            </tr>
                        }
                    } @else {
                        <tr>
                            <td>
                                <div>
                                    <div class="font-medium">{{servicio.name}}</div>
                                    <div class="text-sm text-surface-500 dark:text-surface-400" *ngIf="servicio.description">
                                        {{servicio.description}}
                                    </div>
                                </div>
                            </td>
                            <td>
                                <div class="flex flex-wrap gap-1" *ngIf="servicio.category_names && servicio.category_names.length > 0; else singleCategory">
                                    <p-tag *ngFor="let categoryName of servicio.category_names" 
                                           [value]="categoryName" severity="info">
                                    </p-tag>
                                </div>
                                <ng-template #singleCategory>
                                    <p-tag [value]="servicio.category || ('services.no_category' | t)"
                                           severity="info" *ngIf="servicio.category">
                                    </p-tag>
                                    <span class="text-surface-400 dark:text-surface-500" *ngIf="!servicio.category">{{ 'services.no_category' | t }}</span>
                                </ng-template>
                            </td>
                            <td class="font-medium">{{ formatearMoneda(servicio.price) }}</td>
                            <td>{{servicio.duration}} min</td>
                            <td>
                                <p-tag [value]="servicio.is_active ? ('services.status.active' | t) : ('services.status.inactive' | t)"
                                       [severity]="servicio.is_active ? 'success' : 'danger'">
                                </p-tag>
                            </td>
                            <td>
                                <div class="flex gap-1">
                                    <button *ngIf="canManageServices()" pButton icon="pi pi-pencil" class="p-button-text p-button-sm"
                                            (click)="editarServicio(servicio)" [pTooltip]="'common.edit' | t"></button>
                                    <button *ngIf="canManageServices()" pButton icon="pi pi-trash" class="p-button-text p-button-sm p-button-danger"
                                            (click)="confirmarEliminar(servicio)" [pTooltip]="'common.delete' | t"></button>
                                </div>
                            </td>
                        </tr>
                    }
                </ng-template>

                <ng-template pTemplate="emptymessage">
                    <tr>
                      <td colspan="6">
                        <auron-empty-state
                          icon="pi pi-scissors"
                          title="Sin servicios registrados"
                          description="Sin servicios, el POS no puede procesar ventas."
                          [ctaLabel]="canManageServices() ? t('services.new') : undefined"
                          variant="contextual"
                          (ctaAction)="abrirDialogo()">
                        </auron-empty-state>
                      </td>
                    </tr>
                </ng-template>
            </p-table>
            </div>

            <!-- Móvil: Tarjetas apiladas -->
            <div class="block md:hidden p-4 space-y-4">
                <div class="flex flex-col gap-3 mb-2">
                    <span class="text-sm text-surface-600 dark:text-surface-300">
                        {{ servicios().length }} {{ 'menu.services' | t | lowercase }}
                    </span>
                    <span class="p-input-icon-left w-full">
                        <i class="pi pi-search"></i>
                        <input pInputText type="text" [placeholder]="'services.search_placeholder' | t"
                               class="w-full"
                               (input)="dt.filterGlobal($any($event.target).value, 'contains')">
                    </span>
                </div>

                @if (cargando()) {
                    @for (i of [1,2,3]; track i) {
                        <div class="bg-white dark:bg-surface-900 p-4 rounded-xl border border-surface-200 dark:border-surface-800 shadow-sm space-y-3">
                            <div class="flex justify-between items-start">
                                <div class="space-y-2">
                                    <au-skeleton width="120px" height="16px" />
                                    <au-skeleton width="80px" height="12px" />
                                </div>
                                <au-skeleton width="60px" height="16px" />
                            </div>
                            <div class="flex justify-between items-center mt-4">
                                <au-skeleton width="80px" height="20px" />
                                <div class="flex gap-2">
                                    <au-skeleton width="28px" height="28px" />
                                    <au-skeleton width="28px" height="28px" />
                                </div>
                            </div>
                        </div>
                    }
                } @else {
                    @for (servicio of (dt.filteredValue || servicios()); track servicio.id) {
                        <div class="bg-white dark:bg-surface-900 p-4 rounded-xl border border-surface-200 dark:border-surface-800 shadow-sm space-y-3">
                            <div class="flex justify-between items-start">
                                <div>
                                    <h4 class="font-bold text-surface-900 dark:text-white">{{ servicio.name }}</h4>
                                    <p class="text-sm text-surface-500 dark:text-surface-400 mt-1" *ngIf="servicio.description">
                                        {{ servicio.description }}
                                    </p>
                                </div>
                                <span class="font-black text-primary-600 dark:text-primary-400">{{ formatearMoneda(servicio.price) }}</span>
                            </div>
                            <div class="flex flex-wrap gap-1">
                                <div class="flex flex-wrap gap-1" *ngIf="servicio.category_names && servicio.category_names.length > 0; else singleCategoryMobile">
                                    <p-tag *ngFor="let categoryName of servicio.category_names" 
                                           [value]="categoryName" severity="info">
                                    </p-tag>
                                </div>
                                <ng-template #singleCategoryMobile>
                                    <p-tag [value]="servicio.category || ('services.no_category' | t)"
                                           severity="info" *ngIf="servicio.category">
                                    </p-tag>
                                    <span class="text-xs text-surface-400 dark:text-surface-500" *ngIf="!servicio.category">{{ 'services.no_category' | t }}</span>
                                </ng-template>
                            </div>
                            <div class="flex justify-between items-center pt-2 border-t border-surface-100 dark:border-surface-800">
                                <div class="flex items-center gap-2">
                                    <span class="text-xs text-surface-500">{{ servicio.duration }} min</span>
                                    <p-tag [value]="servicio.is_active ? ('services.status.active' | t) : ('services.status.inactive' | t)"
                                           [severity]="servicio.is_active ? 'success' : 'danger'">
                                    </p-tag>
                                </div>
                                <div class="flex gap-2">
                                    <button *ngIf="canManageServices()" au-btn variant="ghost" size="sm" icon="pi pi-pencil" [iconOnly]="true"
                                            (click)="editarServicio(servicio)"></button>
                                    <button *ngIf="canManageServices()" au-btn variant="danger" size="sm" icon="pi pi-trash" [iconOnly]="true"
                                            (click)="confirmarEliminar(servicio)"></button>
                                </div>
                            </div>
                        </div>
                    }
                    @if ((dt.filteredValue || servicios()).length === 0) {
                        <auron-empty-state
                          icon="pi pi-scissors"
                          title="Sin servicios registrados"
                          description="Sin servicios, el POS no puede procesar ventas."
                          [ctaLabel]="canManageServices() ? t('services.new') : undefined"
                          variant="contextual"
                          (ctaAction)="abrirDialogo()">
                        </auron-empty-state>
                    }
                }
            </div>
            </section>

            <p-dialog [header]="servicioSeleccionado ? ('services.edit' | t) : ('services.new' | t)"
                      [(visible)]="mostrarDialogo" [modal]="true" [style]="{ width: '92vw', maxWidth: '500px' }"
                      [breakpoints]="{'960px':'75vw','640px':'100vw'}"
                      [closable]="!guardando()" [closeOnEscape]="!guardando()">
                <form [formGroup]="formulario" (ngSubmit)="guardarServicio()" class="grid gap-4">
                    <div class="rounded-2xl bg-surface-950 p-4 text-white">
                        <div class="text-[11px] uppercase tracking-[0.24em] text-surface-400">{{ 'services.th.service' | t }}</div>
                        <div class="mt-2 text-xl font-black">{{ servicioSeleccionado ? ('services.edit' | t) : ('services.new' | t) }}</div>
                        <div class="mt-2 text-sm text-surface-300">{{ 'services.dialog.fill_and_save' | t }}</div>
                    </div>
                    <div>
                        <label class="block font-medium mb-1">{{ 'services.name' | t }}</label>
                        <input pInputText formControlName="name" class="w-full"
                               [class.ng-invalid]="formulario.get('name')?.invalid && formulario.get('name')?.touched">
                    </div>

                    <div>
                        <label class="block font-medium mb-1">{{ 'services.description' | t }}</label>
                        <textarea pInputTextarea formControlName="description" class="w-full" rows="3"></textarea>
                    </div>

                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block font-medium mb-1">{{ 'services.categories' | t }}</label>
                            <div class="flex gap-2">
                                <p-multiSelect formControlName="categories" appendTo="body"
                                                [options]="categoriasDisponibles" 
                                              optionLabel="name" 
                                              optionValue="id"
                                              [placeholder]="'services.form.select_categories_placeholder' | t" 
                                              class="w-full"
                                              [showClear]="true"
                                              display="chip">
                                </p-multiSelect>
                                <button pButton icon="pi pi-plus" class="p-button-outlined p-button-sm flex-shrink-0"
                                        (click)="mostrarDialogoCategoria = true"
                                        [pTooltip]="'services.category_dialog.title' | t"></button>
                            </div>
                            <small class="text-surface-500 dark:text-surface-400" *ngIf="categoriasDisponibles.length === 0">
                                {{ 'services.form.no_categories_available' | t }}
                            </small>
                        </div>
                        <div>
                            <label class="block font-medium mb-1">{{ 'services.form.duration' | t }}</label>
                            <p-inputNumber formControlName="duration" class="w-full"
                                           [min]="5" [max]="480" [step]="5">
                            </p-inputNumber>
                        </div>
                    </div>

                    <div>
                        <label class="block font-medium mb-1">{{ 'services.price' | t }}</label>
                        <p-inputNumber formControlName="price" class="w-full"
                                       mode="currency" [currency]="currencyCode()" [locale]="currencyLocale()"
                                       [min]="0" [step]="0.01">
                        </p-inputNumber>
                    </div>

                    <div>
                        <label class="block font-medium mb-1">{{ 'services.form.image' | t }}</label>
                        <p-fileUpload mode="basic" name="image" accept="image/*"
                                      [maxFileSize]="5000000" [auto]="false"
                                      (onSelect)="onImageSelect($event)"
                                      [chooseLabel]="'services.form.select_image' | t" class="w-full">
                        </p-fileUpload>
                        <small class="text-surface-500 dark:text-surface-400">{{ 'services.form.image_limit_hint' | t }}</small>
                        <div *ngIf="servicioImagenActual()" class="mt-2">
                            <img [src]="servicioImagenActual()" alt="{{ 'services.form.current_image' | t }}"
                                 class="w-20 h-20 object-cover rounded border"/>
                            <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">{{ 'services.form.current_image' | t }}</p>
                        </div>
                    </div>

                    <div class="flex items-center">
                        <p-checkbox formControlName="is_active" [binary]="true" inputId="activo"></p-checkbox>
                        <label for="activo" class="ml-2 font-medium">{{ 'services.form.active_checkbox' | t }}</label>
                    </div>

                    <div class="flex justify-end gap-2 mt-4">
                        <button au-btn variant="ghost" type="button"
                                (click)="cerrarDialogo()" [disabled]="guardando()">{{ 'common.cancel' | t }}</button>
                        <button au-btn variant="primary" type="submit" icon="pi pi-check" [loading]="guardando()"
                                [disabled]="formulario.invalid">{{ servicioSeleccionado ? ('common.edit' | t) : ('common.save' | t) }}</button>
                    </div>
                </form>
            </p-dialog>

            <p-dialog [header]="'services.category_dialog.title' | t" [(visible)]="mostrarDialogoCategoria" [modal]="true" [style]="{ width: '92vw', maxWidth: '400px' }" [breakpoints]="{'960px':'75vw','640px':'100vw'}">
                <div class="flex flex-col gap-4">
                    <div>
                        <label class="block font-medium mb-1">{{ 'services.category_dialog.name' | t }}</label>
                        <input pInputText [(ngModel)]="nuevaCategoria.name" class="w-full" [placeholder]="'services.category_dialog.name_placeholder' | t">
                    </div>
                    <div>
                        <label class="block font-medium mb-1">{{ 'services.description' | t }}</label>
                        <textarea pInputTextarea [(ngModel)]="nuevaCategoria.description" class="w-full" rows="2"></textarea>
                    </div>
                    <div class="flex justify-end gap-2">
                        <button au-btn variant="ghost" (click)="cerrarDialogoCategoria()">{{ 'common.cancel' | t }}</button>
                        <button au-btn variant="primary" [loading]="creandoCategoria" [disabled]="!nuevaCategoria.name.trim()" (click)="crearCategoria()">{{ 'services.category_dialog.create' | t }}</button>
                    </div>
                </div>
            </p-dialog>
        </div>

        <p-confirmDialog></p-confirmDialog>
        <p-toast></p-toast>
    `
})
export class ServicesManagement implements OnInit {
    private serviceService = inject(ServiceService);
    private localeService = inject(LocaleService);
    private settingsService = inject(SettingsService);
    private messageService = inject(MessageService);
    private confirmationService = inject(ConfirmationService);
    private fb = inject(FormBuilder);
    private authService = inject(AuthService);

        t(key: string): string {
        return this.localeService.t(key as any);
    }

    servicios = signal<ServiceDto[]>([]);
    cargando = signal(false);
    guardando = signal(false);
    currencyCode = computed(() => this.settingsService.settings().currency || 'DOP');
    currencyLocale = computed(() => this.settingsService.getCurrencyLocale());
    canManageServices = computed(() => {
        const user = this.authService.getCurrentUser();
        if (!user) return false;
        const role = (user.role || '').trim().toUpperCase().replace(/[\s-]+/g, '_');
        const businessRole = (user.business_role || '').trim().toLowerCase().replace(/[\s-]+/g, '_');
        return role === 'CLIENT_ADMIN' || businessRole === 'owner';
    });
    mostrarDialogo = false;
    servicioSeleccionado: ServiceDto | null = null;
    categoriasDisponibles: ServiceCategoryDto[] = [];
    imagenSeleccionada: File | null = null;
    servicioImagenActual = signal<string | null>(null);
    mostrarDialogoCategoria = false;
    creandoCategoria = false;
    nuevaCategoria = { name: '', description: '' };

    getActiveServicesCount(): number {
        return this.servicios().filter((service) => service.is_active).length;
    }

    getServicesNarrative(): string {
        const total = this.servicios().length;
        if (!total) {
            return this.t('services.narrative_empty');
        }

        return this.t('services.narrative_active')
            .replace('{active}', String(this.getActiveServicesCount()))
            .replace('{total}', String(total))
            .replace('{categories}', String(this.categoriasDisponibles.length));
    }

    getServiceHighlights(): { label: string; name: string; meta: string }[] {
        const services = this.servicios().filter((service) => service.is_active);
        if (!services.length) {
            return [
                { label: 'POS', name: 'Sin servicios activos', meta: 'Agrega servicios para vender en caja' },
                { label: 'Rentabilidad', name: 'Pendiente', meta: 'Define precios por servicio' },
                { label: 'Duración', name: 'Pendiente', meta: 'Configura tiempos de atención' }
            ];
        }

        const byPrice = [...services].sort((a, b) => Number(b.price) - Number(a.price))[0];
        const byDuration = [...services].sort((a, b) => Number(a.duration) - Number(b.duration))[0];
        const posReady = services[0];

        return [
            { label: 'Listo para POS', name: posReady.name, meta: `${this.formatearMoneda(posReady.price)} · ${posReady.duration} min` },
            { label: 'Mayor precio', name: byPrice.name, meta: this.formatearMoneda(byPrice.price) },
            { label: 'Más rápido', name: byDuration.name, meta: `${byDuration.duration} min` }
        ];
    }

    // Utility function to normalize API responses
    private normalizeArray<T>(response: any): T[] {
        if (!response) return [];
        if (Array.isArray(response)) return response;
        if (response.results && Array.isArray(response.results)) return response.results;
        return [];
    }

    // Adaptador Backend → Frontend DTO
    private mapBackendToServiceDto(backendService: any, categorias: ServiceCategoryDto[]): ServiceDto {
        // Manejar tanto categories (array) como category (string legacy)
        let categoryIds: number[] = [];
        let categoryNames: string[] = [];
        
        if (backendService.categories && Array.isArray(backendService.categories)) {
            categoryIds = backendService.categories;
            categoryNames = backendService.categories.map((catId: number) => {
                const categoria = categorias.find(c => c.id === catId);
                return categoria?.name;
            }).filter(Boolean);
        } else if (backendService.category) {
            // Legacy: category como string
            categoryNames = [backendService.category];
        }

        return {
            id: backendService.id,
            name: backendService.name,
            description: backendService.description,
            image: backendService.image || undefined,
            categories: categoryIds,
            category_names: categoryNames,
            price: backendService.price,
            duration: backendService.duration,
            is_active: backendService.is_active,
            created_at: backendService.created_at,
            updated_at: backendService.updated_at
        };
    }

    categoriasOptions = [
        { label: 'Corte de Cabello', value: 'Corte de Cabello' },
        { label: 'Barba', value: 'Barba' },
        { label: 'Tratamientos', value: 'Tratamientos' },
        { label: 'Peinado', value: 'Peinado' },
        { label: 'Coloración', value: 'Coloración' },
        { label: 'Afeitado', value: 'Afeitado' },
        { label: 'Combo', value: 'Combo' }
    ];

    formulario: FormGroup = this.fb.group({
        name: ['', [Validators.required, Validators.maxLength(100)]],
        description: [''],
        categories: [[]], // ✅ Normalizado array IDs
        price: [0, [Validators.required, Validators.min(0)]],
        duration: [30, [Validators.required, Validators.min(5)]],
        is_active: [true]
    });

    ngOnInit() {
        this.cargarCategorias().then(() => {
            this.cargarServicios();
        });
    }

    crearCategoria() {
        if (!this.nuevaCategoria.name.trim()) return;
        this.creandoCategoria = true;
        this.serviceService.createServiceCategory({ name: this.nuevaCategoria.name, description: this.nuevaCategoria.description })
            .subscribe({
                next: () => {
                    this.messageService.add({ severity: 'success', summary: this.t('common.success'), detail: this.t('services.toast.category_created') });
                    this.cerrarDialogoCategoria();
                    this.cargarCategorias();
                },
                error: (err: any) => {
                    this.messageService.add({ severity: 'error', summary: 'Error', detail: err?.error?.detail || 'Error al crear categoría' });
                    this.creandoCategoria = false;
                }
            });
    }

    cerrarDialogoCategoria() {
        this.mostrarDialogoCategoria = false;
        this.nuevaCategoria = { name: '', description: '' };
        this.creandoCategoria = false;
    }

    async cargarCategorias() {
        try {
            const response: any = await firstValueFrom(this.serviceService.getServiceCategories());
            this.categoriasDisponibles = this.normalizeArray<ServiceCategoryDto>(response);
        } catch (error) {
            if (!environment.production) console.error('Error cargando categorías:', error);
            this.messageService.add({
                severity: 'warn',
                summary: 'Warning',
                detail: this.t('services.toast.load_categories_error')
            });
            this.categoriasDisponibles = [];
        }
    }

    async cargarServicios() {
        if (this.cargando()) return; // ✅ Prevenir llamadas concurrentes
        this.cargando.set(true);
        try {
            const response = await firstValueFrom(this.serviceService.getServices());
            const servicios = this.normalizeArray<any>(response);
            const serviciosNormalizados = servicios.map((servicio: any) => 
                this.mapBackendToServiceDto(servicio, this.categoriasDisponibles)
            );
            this.servicios.set(serviciosNormalizados);
        } catch (error) {
            if (!environment.production) {
                
            }
            this.messageService.add({
                severity: 'error',
                summary: 'Error',
                detail: this.t('services.toast.load_services_error')
            });
        } finally {
            this.cargando.set(false);
        }
    }

    abrirDialogo() {
        this.servicioSeleccionado = null;
        this.imagenSeleccionada = null;
        this.servicioImagenActual.set(null);
        this.formulario.reset({
            name: '',
            description: '',
            category: '',
            categories: [],
            price: 0,
            duration: 30,
            is_active: true
        });
        this.mostrarDialogo = true;
    }

    editarServicio(servicio: ServiceDto) {
        this.servicioSeleccionado = servicio;
        this.imagenSeleccionada = null;
        this.servicioImagenActual.set(servicio.image || null);
        this.formulario.patchValue({
            name: servicio.name,
            description: servicio.description || '',
            categories: servicio.categories || [],
            price: servicio.price,
            duration: servicio.duration,
            is_active: servicio.is_active
        });
        this.mostrarDialogo = true;
    }

    onImageSelect(event: any) {
        const file = event.files[0];
        if (file) {
            const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
            if (!allowedTypes.includes(file.type)) {
                this.messageService.add({ severity: 'error', summary: 'Error', detail: this.t('services.toast.invalid_image_format') });
                return;
            }
            if (file.size > 5000000) {
                this.messageService.add({ severity: 'error', summary: 'Error', detail: this.t('services.toast.image_too_large') });
                return;
            }
            this.imagenSeleccionada = file;
        }
    }

    async guardarServicio() {
        if (this.formulario.invalid) return;

        this.guardando.set(true);
        try {
            const servicioData = this.formulario.value;

            if (this.imagenSeleccionada) {
                const formData = new FormData();
                Object.keys(servicioData).forEach(key => {
                    if (key === 'categories') {
                        formData.append('categories', JSON.stringify(servicioData[key]));
                    } else if (servicioData[key] !== null && servicioData[key] !== undefined) {
                        formData.append(key, servicioData[key]);
                    }
                });
                formData.append('image', this.imagenSeleccionada);

                if (this.servicioSeleccionado?.id) {
                    await firstValueFrom(this.serviceService.updateServiceWithImage(this.servicioSeleccionado.id, formData));
                } else {
                    await firstValueFrom(this.serviceService.createServiceWithImage(formData));
                }
            } else {
                if (this.servicioSeleccionado?.id) {
                    await firstValueFrom(this.serviceService.updateService(this.servicioSeleccionado.id, servicioData));
                } else {
                    await firstValueFrom(this.serviceService.createService(servicioData));
                }
            }

            this.messageService.add({
                severity: 'success',
                summary: 'Éxito',
                detail: this.servicioSeleccionado ? this.t('services.toast.update_success') : this.t('services.toast.create_success')
            });

            this.cerrarDialogo();
            this.cargarServicios();
        } catch (error: any) {
            if (!environment.production) {
                console.error('Error al guardar servicio:', error);
            }
            const serverError = error?.error;
            const errorDetail = serverError?.detail
                || (serverError ? Object.values(serverError).flat().join('. ') : null)
                || 'Error al guardar el servicio';
            this.messageService.add({
                severity: 'error',
                summary: 'Error',
                detail: errorDetail
            });
        } finally {
            this.guardando.set(false);
        }
    }

    confirmarEliminar(servicio: ServiceDto) {
        this.confirmationService.confirm({
            message: this.t('services.delete_confirm_msg').replace('{name}', servicio.name),
            header: this.t('services.confirm_delete_title'),
            icon: 'pi pi-exclamation-triangle',
            acceptLabel: this.t('services.confirm_delete_accept'),
            rejectLabel: this.t('common.cancel'),
            accept: () => this.eliminarServicio(servicio)
        });
    }

    async eliminarServicio(servicio: ServiceDto) {
        try {
            await firstValueFrom(this.serviceService.deleteService(servicio.id));
            this.messageService.add({
                severity: 'success',
                summary: 'Éxito',
                detail: this.t('services.toast.delete_success')
            });
            this.cargarServicios();
        } catch (error: any) {
            if (!environment.production) {
                
            }
            this.messageService.add({
                severity: 'error',
                summary: 'Error',
                detail: error?.error?.detail || 'Error al eliminar el servicio'
            });
        }
    }

    formatearMoneda(valor: number | string | null | undefined): string {
        const amount = Number(valor) || 0;
        return new Intl.NumberFormat(this.currencyLocale(), {
            style: 'currency',
            currency: this.currencyCode()
        }).format(amount);
    }

    cerrarDialogo() {
        this.mostrarDialogo = false;
        this.servicioSeleccionado = null;
        this.formulario.reset();
    }
}
