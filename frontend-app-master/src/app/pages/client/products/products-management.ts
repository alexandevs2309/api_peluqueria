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
import { FileUploadModule } from 'primeng/fileupload';
import { InventoryService, Product } from '../../../core/services/inventory/inventory.service';
import { environment } from '../../../../environments/environment';
import { SettingsService } from '../../../core/services/settings/settings.service';
import { AuthService } from '../../../core/services/auth/auth.service';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { I18nPipe } from '../../../core/pipes/i18n.pipe';
import { firstValueFrom } from 'rxjs';
import { BranchService } from '../../../core/services/branch/branch.service';
import { AuronEmptyStateComponent } from '../../../shared/components/auron-empty-state/auron-empty-state.component';
import { AuronEyebrowComponent } from '../../../shared/components/auron-eyebrow/auron-eyebrow.component';
import { AuBtn, AuSkeleton } from '../../../shared/components';

interface StockMovementRow {
    id: number;
    product: number | { id?: number; name?: string };
    quantity: number;
    reason: string;
    created_at?: string;
    date?: string;
}

@Component({
    selector: 'app-products-management',
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
        FileUploadModule,
        AuSkeleton,
        I18nPipe,
        AuronEmptyStateComponent,
        AuronEyebrowComponent,
        AuBtn
    ],
    providers: [MessageService, ConfirmationService],
    template: `
        <div class="space-y-6">
        <section class="overflow-hidden rounded-[2rem] border border-surface-200 bg-white shadow-sm shadow-[var(--shadow-elevated)] dark:border-surface-700 dark:bg-surface-900">
                <div class="relative overflow-hidden px-8 py-8 lg:px-10">
                    <div class="hero-gradient pointer-events-none absolute inset-0 bg-gradient-to-br from-primary-50/30 via-transparent to-transparent dark:from-primary-950/20"></div>
                    <div class="relative space-y-7">
                        <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                            <div>
                                <auron-eyebrow class="mb-4 block" icon="pi pi-box" label="Control de inventario"></auron-eyebrow>
                                <h2 class="display-4 text-surface-950 dark:text-white">Inventario para cabinas y POS</h2>
                                <p class="mt-3 max-w-3xl text-base leading-7 text-surface-600 dark:text-surface-300">
                                    Seguimiento de productos, stock mínimo y valor disponible para vender o usar en servicios del salón.
                                </p>
                            </div>
                            <div class="flex flex-wrap gap-2">
                                <button *ngIf="canManageProducts()" au-btn variant="primary" icon="pi pi-plus" (click)="abrirDialogo()">{{ 'products.new' | t }}</button>
                                <button *ngIf="canManageProducts()" au-btn variant="secondary" icon="pi pi-refresh" (click)="abrirDialogoStock()">{{ 'products.adjust_stock' | t }}</button>
                            </div>
                        </div>

                        <div *ngIf="productosStockBajo().length > 0; else inventoryHealthy" class="rounded-2xl border border-amber-300 bg-amber-50 p-4 dark:border-amber-900/60 dark:bg-amber-900/20">
                            <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                                <div>
                                    <div class="text-xs font-semibold uppercase tracking-[0.2em] text-amber-700 dark:text-amber-300">Reposición pendiente</div>
                                    <div class="mt-2 text-2xl font-semibold text-amber-950 dark:text-amber-100">{{ productosStockBajo().length }} productos bajo mínimo</div>
                                </div>
                                <div class="flex flex-wrap gap-2">
                                    <span *ngFor="let product of getCriticalProducts()" class="rounded-full bg-white px-3 py-1 text-sm font-medium text-amber-800 dark:bg-surface-900 dark:text-amber-200">
                                        {{ product.name }} · {{ product.stock }}/{{ product.min_stock }}
                                    </span>
                                </div>
                            </div>
                        </div>
                        <ng-template #inventoryHealthy>
                            <div class="rounded-2xl border border-emerald-200 bg-emerald-50/70 p-4 dark:border-emerald-900/60 dark:bg-emerald-900/10">
                                <div class="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700 dark:text-emerald-300">Inventario estable</div>
                                <div class="mt-2 text-2xl font-semibold text-emerald-900 dark:text-emerald-100">No hay alertas de stock mínimo</div>
                            </div>
                        </ng-template>

                        <div class="grid gap-3 md:grid-cols-3">
                            <article class="rounded-2xl border border-surface-200 bg-white/80 p-4 shadow-sm backdrop-blur dark:border-surface-700 dark:bg-surface-800/80">
                                <div class="text-[11px] font-semibold uppercase tracking-[0.24em] text-surface-500 dark:text-surface-400">Stock total</div>
                                <div class="mt-2 text-2xl font-semibold text-surface-950 dark:text-white">{{ getTotalStockUnits() }}</div>
                            </article>
                            <article class="rounded-2xl border border-surface-200 bg-white/80 p-4 shadow-sm backdrop-blur dark:border-surface-700 dark:bg-surface-800/80">
                                <div class="text-[11px] font-semibold uppercase tracking-[0.24em] text-surface-500 dark:text-surface-400">{{ 'services.active' | t }}</div>
                                <div class="mt-2 text-2xl font-semibold text-surface-950 dark:text-white">{{ getActiveProductsCount() }}</div>
                            </article>
                            <article class="rounded-2xl border border-[var(--brand)]/20 bg-[rgba(26,86,219,0.06)] p-4 dark:border-[var(--brand)]/30 dark:bg-[rgba(26,86,219,0.08)]">
                                <div class="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--brand)] dark:text-[var(--brand-400)]">Valor aprox.</div>
                                <div class="mt-2 text-2xl font-semibold text-surface-950 dark:text-white">{{ formatearMoneda(getInventoryValue()) }}</div>
                            </article>
                        </div>

                        <p class="rounded-2xl border border-surface-200/60 bg-surface-50/60 px-4 py-3 text-sm leading-6 text-surface-600 dark:border-surface-700/60 dark:bg-surface-800/40 dark:text-surface-300">
                            {{ getProductsNarrative() }}
                        </p>
                    </div>
                </div>
                <div class="border-t border-surface-200/80 px-6 py-5 dark:border-surface-800 xl:px-8">
                    <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                        <div class="rounded-2xl bg-surface-100 px-4 py-2 text-sm text-surface-500 dark:bg-surface-800 dark:text-surface-300">
                            {{ 'products.narrative_hint' | t }}
                        </div>
                        <button au-btn variant="ghost" icon="pi pi-refresh" (click)="cargarProductos(); cargarMovimientosStock()" class="self-start lg:self-auto">{{ 'products.reload' | t }}</button>
                    </div>
                </div>
            </section>

            <!-- Alertas de Stock Bajo -->
            <div class="mb-4" *ngIf="productosStockBajo().length > 0">
                <div class="bg-orange-50 border border-orange-200 rounded-lg p-4">
                    <div class="flex items-center">
                        <i class="pi pi-exclamation-triangle text-orange-500 mr-2"></i>
                        <span class="font-medium text-orange-800">
                            {{productosStockBajo().length}} {{ 'products.stock_low' | t | lowercase }}
                        </span>
                    </div>
                    <div class="mt-2 text-sm text-orange-700">
                        <span *ngFor="let producto of productosStockBajo(); let last = last">
                            {{producto.name}} ({{producto.stock}} unidades){{!last ? ', ' : ''}}
                        </span>
                    </div>
                </div>
            </div>

            <section class="overflow-hidden rounded-[1.75rem] border border-surface-200 bg-white shadow-sm dark:border-surface-700 dark:bg-surface-900">
            <!-- Escritorio: Tabla de productos -->
            <div class="hidden md:block">
            <p-table [value]="productos()" [loading]="false"
                     [globalFilterFields]="['name', 'sku', 'barcode', 'category']"
                     responsiveLayout="scroll"
                     #dt>
                <ng-template pTemplate="caption">
                    <div class="flex flex-col gap-3 p-2 lg:flex-row lg:items-center lg:justify-between">
                        <span class="text-sm text-surface-600 dark:text-surface-300">
                            {{ productos().length }} {{ 'menu.products' | t | lowercase }}
                        </span>
                        <span class="p-input-icon-left w-full lg:w-80">
                            <i class="pi pi-search"></i>
                            <input pInputText type="text" [placeholder]="'products.search_placeholder' | t"
                                   class="w-full"
                                   (input)="dt.filterGlobal($any($event.target).value, 'contains')"
                                   (keyup.enter)="dt.filterGlobal($any($event.target).value, 'contains')">
                        </span>
                    </div>
                </ng-template>

                <ng-template pTemplate="header">
                    <tr>
                        <th>{{ 'products.movement.th.product' | t }}</th>
                        <th>{{ 'products.th.sku' | t }}</th>
                        <th>{{ 'products.th.barcode' | t }}</th>
                        <th>{{ 'products.th.category' | t }}</th>
                        <th>{{ 'products.th.price' | t }}</th>
                        <th>{{ 'products.th.stock' | t }}</th>
                        <th>{{ 'products.th.status' | t }}</th>
                        <th>{{ 'products.th.actions' | t }}</th>
                    </tr>
                </ng-template>

                <ng-template pTemplate="body" let-producto>
                    @if (cargando()) {
                        @for (i of [1,2,3,4,5]; track i) {
                            <tr>
                                <td>
                                    <div class="flex items-center gap-3">
                                        <au-skeleton variant="avatar" width="3rem" height="3rem" />
                                        <div class="flex flex-col gap-1">
                                            <au-skeleton width="120px" height="16px" />
                                            <au-skeleton width="80px" height="12px" />
                                        </div>
                                    </div>
                                </td>
                                <td><au-skeleton width="80px" height="20px" /></td>
                                <td><au-skeleton width="100px" height="16px" /></td>
                                <td><au-skeleton width="90px" height="24px" /></td>
                                <td><au-skeleton width="80px" height="16px" /></td>
                                <td>
                                    <div class="flex items-center gap-2">
                                        <au-skeleton width="40px" height="16px" />
                                        <au-skeleton width="60px" height="16px" />
                                    </div>
                                </td>
                                <td><au-skeleton width="80px" height="24px" /></td>
                                <td>
                                    <div class="flex gap-1">
                                        <au-skeleton width="28px" height="28px" />
                                        <au-skeleton width="28px" height="28px" />
                                        <au-skeleton width="28px" height="28px" />
                                    </div>
                                </td>
                            </tr>
                        }
                    } @else {
                        <tr>
                            <td>
                                <div class="flex items-center gap-3">
                                    <img *ngIf="producto.image" [src]="producto.image" [alt]="producto.name"
                                         class="w-12 h-12 object-cover rounded border">
                                    <div class="flex h-12 w-12 items-center justify-center rounded border bg-surface-100 dark:bg-surface-800/70" *ngIf="!producto.image">
                                        <i class="pi pi-image text-surface-400 dark:text-surface-500"></i>
                                    </div>
                                    <div>
                                        <div class="font-medium">{{producto.name}}</div>
                                        <div class="text-sm text-surface-500 dark:text-surface-400" *ngIf="producto.description">
                                            {{producto.description}}
                                        </div>
                                    </div>
                                </div>
                            </td>
                            <td>
                                <code class="rounded bg-surface-100 px-2 py-1 text-sm text-surface-800 dark:bg-surface-800 dark:text-surface-200">{{producto.sku}}</code>
                            </td>
                            <td>
                                <span class="text-sm font-mono text-surface-600 dark:text-surface-400" *ngIf="producto.barcode">{{producto.barcode}}</span>
                                <span class="text-surface-400 dark:text-surface-500" *ngIf="!producto.barcode">-</span>
                            </td>
                            <td>
                                <span
                                    *ngIf="producto.category_name"
                                    class="inline-flex max-w-[14rem] items-center rounded-md border border-surface-200 bg-surface-50 px-2.5 py-1 text-xs font-semibold leading-5 text-surface-700 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200"
                                    [title]="producto.category_name">
                                    <span class="truncate">{{ producto.category_name }}</span>
                                </span>
                                <span class="text-surface-400 dark:text-surface-500" *ngIf="!producto.category_name">{{ 'products.no_category' | t }}</span>
                            </td>
                            <td class="font-medium">{{ formatearMoneda(producto.price) }}</td>
                            <td>
                                <div class="flex items-center gap-2">
                                    <span [class]="getStockClass(producto)">{{producto.stock}}</span>
                                    <p-badge [value]="'Min: ' + producto.min_stock"
                                             severity="secondary" size="small"></p-badge>
                                    <i class="pi pi-exclamation-triangle text-orange-500"
                                       *ngIf="producto.stock <= producto.min_stock"
                                       [pTooltip]="'products.stock_low' | t"></i>
                                </div>
                            </td>
                            <td>
                                <p-tag [value]="producto.is_active ? ('products.status.active' | t) : ('products.status.inactive' | t)"
                                       [severity]="producto.is_active ? 'success' : 'danger'">
                                </p-tag>
                            </td>
                            <td>
                                <div class="flex gap-1">
                                    <button *ngIf="canManageProducts()" pButton icon="pi pi-pencil" class="p-button-text p-button-sm"
                                            (click)="editarProducto(producto)" [pTooltip]="'common.edit' | t"></button>
                                    <button *ngIf="canManageProducts()" pButton icon="pi pi-plus-circle" class="p-button-text p-button-sm p-button-success"
                                            (click)="ajustarStockProducto(producto)" [pTooltip]="'products.adjust_stock' | t"></button>
                                    <button *ngIf="canManageProducts()" pButton icon="pi pi-trash" class="p-button-text p-button-sm p-button-danger"
                                            (click)="confirmarEliminar(producto)" [pTooltip]="'common.delete' | t"></button>
                                </div>
                            </td>
                        </tr>
                    }
                </ng-template>

                <ng-template pTemplate="emptymessage">
                    <tr>
                        <td colspan="8">
                            <auron-empty-state
                                icon="pi pi-box"
                                title="Sin productos aún"
                                description="Sin productos en inventario. Agrega uno para que aparezca en el POS."
                                [ctaLabel]="canManageProducts() ? t('products.new') : undefined"
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
                        {{ productos().length }} {{ 'menu.products' | t | lowercase }}
                    </span>
                    <span class="p-input-icon-left w-full">
                        <i class="pi pi-search"></i>
                        <input pInputText type="text" [placeholder]="'products.search_placeholder' | t"
                               class="w-full"
                               (input)="dt.filterGlobal($any($event.target).value, 'contains')">
                    </span>
                </div>

                @if (cargando()) {
                    @for (i of [1,2,3]; track i) {
                        <div class="bg-white dark:bg-surface-900 p-4 rounded-xl border border-surface-200 dark:border-surface-800 shadow-sm space-y-3">
                            <div class="flex items-center gap-3">
                                <au-skeleton variant="avatar" width="3rem" height="3rem" />
                                <div class="flex flex-col gap-1 w-full">
                                    <au-skeleton width="120px" height="16px" />
                                    <au-skeleton width="80px" height="12px" />
                                </div>
                            </div>
                            <div class="flex justify-between items-center mt-4">
                                <au-skeleton width="60px" height="16px" />
                                <au-skeleton width="60px" height="16px" />
                            </div>
                        </div>
                    }
                } @else {
                    @for (producto of (dt.filteredValue || productos()); track producto.id) {
                        <div class="bg-white dark:bg-surface-900 p-4 rounded-xl border border-surface-200 dark:border-surface-800 shadow-sm space-y-3">
                            <div class="flex items-center gap-3">
                                <img *ngIf="producto.image" [src]="producto.image" [alt]="producto.name"
                                     class="w-12 h-12 object-cover rounded border">
                                <div class="flex h-12 w-12 items-center justify-center rounded border bg-surface-100 dark:bg-surface-800/70" *ngIf="!producto.image">
                                    <i class="pi pi-image text-surface-400 dark:text-surface-500"></i>
                                </div>
                                <div>
                                    <h4 class="font-bold text-surface-900 dark:text-white">{{ producto.name }}</h4>
                                    <span class="text-xs text-surface-500" *ngIf="producto.description">{{ producto.description }}</span>
                                </div>
                            </div>
                            <div class="flex flex-wrap gap-2 text-xs font-mono">
                                <span class="rounded bg-surface-100 px-2 py-1 text-surface-800 dark:bg-surface-800 dark:text-surface-200" *ngIf="producto.sku">SKU: {{ producto.sku }}</span>
                                <span class="rounded bg-surface-100 px-2 py-1 text-surface-800 dark:bg-surface-800 dark:text-surface-200" *ngIf="producto.barcode">Code: {{ producto.barcode }}</span>
                            </div>
                            <div class="flex justify-between items-center pt-2 border-t border-surface-100 dark:border-surface-800">
                                <div>
                                    <span
                                        *ngIf="producto.category_name"
                                        class="inline-flex max-w-[11rem] items-center rounded-md border border-surface-200 bg-surface-50 px-2.5 py-1 text-xs font-semibold leading-5 text-surface-700 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200"
                                        [title]="producto.category_name">
                                        <span class="truncate">{{ producto.category_name }}</span>
                                    </span>
                                    <span class="text-xs text-surface-400" *ngIf="!producto.category_name">{{ 'products.no_category' | t }}</span>
                                </div>
                                <span class="font-bold text-primary-600 dark:text-primary-400">{{ formatearMoneda(producto.price) }}</span>
                            </div>
                            <div class="flex justify-between items-center pt-2 border-t border-surface-50 dark:border-surface-800">
                                <div class="flex items-center gap-2">
                                    <span [class]="getStockClass(producto)">Stock: {{ producto.stock }}</span>
                                    <i class="pi pi-exclamation-triangle text-orange-500" *ngIf="producto.stock <= producto.min_stock"></i>
                                </div>
                                <div class="flex gap-2">
                                    <button *ngIf="canManageProducts()" au-btn variant="ghost" size="sm" icon="pi pi-pencil" [iconOnly]="true"
                                            (click)="editarProducto(producto)"></button>
                                    <button *ngIf="canManageProducts()" au-btn variant="primary" size="sm" icon="pi pi-plus-circle" [iconOnly]="true"
                                            (click)="ajustarStockProducto(producto)"></button>
                                    <button *ngIf="canManageProducts()" au-btn variant="danger" size="sm" icon="pi pi-trash" [iconOnly]="true"
                                            (click)="confirmarEliminar(producto)"></button>
                                </div>
                            </div>
                        </div>
                    }
                    @if ((dt.filteredValue || productos()).length === 0) {
                        <auron-empty-state
                                icon="pi pi-box"
                                title="Sin productos aún"
                                description="Sin productos en inventario. Agrega uno para que aparezca en el POS."
                                [ctaLabel]="canManageProducts() ? t('products.new') : undefined"
                                variant="contextual"
                                (ctaAction)="abrirDialogo()">
                            </auron-empty-state>
                    }
                }
            </div>
            </section>

            <!-- Historial de Movimientos de Stock -->
            <div class="mt-6">
                <div class="flex items-center justify-between mb-3">
                    <h3 class="text-lg font-semibold text-surface-900 dark:text-white">{{ 'products.movement.history_title' | t }}</h3>
                    <button pButton icon="pi pi-refresh" class="p-button-text p-button-sm"
                            (click)="cargarMovimientosStock()" [pTooltip]="'products.movement.reload_tooltip' | t"></button>
                </div>

                <!-- Escritorio: Tabla de Movimientos -->
                <div class="hidden md:block">
                <p-table [value]="movimientosStock()" [loading]="false" responsiveLayout="scroll">
                    <ng-template pTemplate="header">
                        <tr>
                            <th>{{ 'products.movement.th.date' | t }}</th>
                            <th>{{ 'products.movement.th.product' | t }}</th>
                            <th>{{ 'products.movement.th.type' | t }}</th>
                            <th>{{ 'products.movement.th.quantity' | t }}</th>
                            <th>{{ 'products.movement.th.reason' | t }}</th>
                        </tr>
                    </ng-template>
                    <ng-template pTemplate="body" let-mov>
                        @if (cargandoMovimientos()) {
                            @for (i of [1,2,3,4,5]; track i) {
                                <tr>
                                    <td><au-skeleton width="120px" height="16px" /></td>
                                    <td><au-skeleton width="140px" height="16px" /></td>
                                    <td><au-skeleton width="80px" height="24px" /></td>
                                    <td><au-skeleton width="60px" height="16px" /></td>
                                    <td><au-skeleton width="100px" height="16px" /></td>
                                </tr>
                            }
                        } @else {
                            <tr>
                                <td>{{ getMovementDate(mov) | date:'dd/MM/yyyy HH:mm' }}</td>
                                <td>{{ getMovementProductName(mov) }}</td>
                                <td>
                                    <p-tag [value]="mov.quantity >= 0 ? ('products.movement.type.in' | t) : ('products.movement.type.out' | t)"
                                           [severity]="mov.quantity >= 0 ? 'success' : 'warn'">
                                    </p-tag>
                                </td>
                                <td [class]="mov.quantity >= 0 ? 'text-green-600 font-medium' : 'text-orange-600 font-medium'">
                                    {{ mov.quantity >= 0 ? '+' : '' }}{{ mov.quantity }}
                                </td>
                                <td>{{ mov.reason || this.t('products.movement.no_reason') }}</td>
                            </tr>
                        }
                    </ng-template>
                    <ng-template pTemplate="emptymessage">
                        <tr><td colspan="5" class="text-center py-4">{{ 'products.movement.empty' | t }}</td></tr>
                    </ng-template>
                </p-table>
                </div>

                <!-- Móvil: Tarjetas de Movimientos -->
                <div class="block md:hidden space-y-3">
                    @if (cargandoMovimientos()) {
                        @for (i of [1,2,3]; track i) {
                            <div class="bg-white dark:bg-surface-900 p-4 rounded-xl border border-surface-200 dark:border-surface-800 shadow-sm space-y-2">
                                <au-skeleton width="100px" height="12px" />
                                <au-skeleton width="150px" height="16px" />
                                <div class="flex justify-between items-center mt-2">
                                    <au-skeleton width="60px" height="20px" />
                                    <au-skeleton width="40px" height="16px" />
                                </div>
                            </div>
                        }
                    } @else {
                        @for (mov of movimientosStock(); track mov.id) {
                            <div class="bg-white dark:bg-surface-900 p-4 rounded-xl border border-surface-200 dark:border-surface-800 shadow-sm space-y-2">
                                <div class="flex justify-between items-center text-xs text-surface-500">
                                    <span>{{ getMovementDate(mov) | date:'dd/MM/yyyy HH:mm' }}</span>
                                    <p-tag [value]="mov.quantity >= 0 ? ('products.movement.type.in' | t) : ('products.movement.type.out' | t)"
                                           [severity]="mov.quantity >= 0 ? 'success' : 'warn'">
                                    </p-tag>
                                </div>
                                <div class="font-semibold text-surface-900 dark:text-white">{{ getMovementProductName(mov) }}</div>
                                <div class="flex justify-between items-center pt-2 border-t border-surface-50 dark:border-surface-800">
                                    <span class="text-xs text-surface-600 dark:text-surface-400">{{ mov.reason || t('products.movement.no_reason') }}</span>
                                    <span [class]="mov.quantity >= 0 ? 'text-green-600 font-bold' : 'text-orange-600 font-bold'">
                                        {{ mov.quantity >= 0 ? '+' : '' }}{{ mov.quantity }}
                                    </span>
                                </div>
                            </div>
                        }
                        @if (movimientosStock().length === 0) {
                            <div class="text-center py-8 text-surface-500 dark:text-surface-400">
                                {{ 'products.movement.empty' | t }}
                            </div>
                        }
                    }
                </div>
            </div>

            <!-- Diálogo de Producto -->
            <p-dialog [header]="productoSeleccionado ? ('products.edit' | t) : ('products.new' | t)"
                      [(visible)]="mostrarDialogo" [modal]="true" [style]="{ width: '92vw', maxWidth: '680px' }"
                      [breakpoints]="{'960px':'75vw','640px':'100vw'}"
                      styleClass="shadow-2xl"
                      [closable]="!guardando()" [closeOnEscape]="!guardando()">
                <form [formGroup]="formulario" (ngSubmit)="guardarProducto()" class="grid gap-4">
                    <div class="rounded-2xl bg-surface-950 p-4 text-white">
                        <div class="text-[11px] uppercase tracking-[0.24em] text-surface-400">{{ 'products.th.product' | t }}</div>
                        <div class="mt-2 text-xl font-black">{{ productoSeleccionado ? ('products.edit' | t) : ('products.new' | t) }}</div>
                        <div class="mt-2 text-sm text-surface-300">{{ 'products.dialog.fill_and_save' | t }}</div>
                    </div>

                    <div>
                        <label class="block font-medium mb-1">{{ 'products.name' | t }}</label>
                        <input pInputText formControlName="name" class="w-full"
                               [class.ng-invalid]="formulario.get('name')?.invalid && formulario.get('name')?.touched">
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div>
                            <label class="block font-medium mb-1">{{ 'products.form.sku' | t }}</label>
                            <input pInputText formControlName="sku" class="w-full"
                                   [placeholder]="'products.form.sku_placeholder' | t"
                                   [class.ng-invalid]="formulario.get('sku')?.invalid && formulario.get('sku')?.touched">
                        </div>
                        <div>
                            <label class="block font-medium mb-1">{{ 'products.barcode' | t }}</label>
                            <input pInputText formControlName="barcode" class="w-full"
                                   [placeholder]="'products.form.barcode_placeholder' | t"
                                   [class.ng-invalid]="formulario.get('barcode')?.invalid && formulario.get('barcode')?.touched">
                        </div>
                        <div>
                            <label class="block font-medium mb-1">{{ 'products.th.category' | t }}</label>
                            <p-select formControlName="category" [options]="categoriasOptions" appendTo="body"
                                      optionLabel="label" optionValue="value"
                                      [placeholder]="'products.th.category' | t" class="w-full"
                                      [showClear]="true">
                            </p-select>
                        </div>
                    </div>

                    <div>
                        <label class="block font-medium mb-1">{{ 'products.form.description' | t }}</label>
                        <textarea pInputTextarea formControlName="description" class="w-full" rows="3"></textarea>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div>
                            <label class="block font-medium mb-1">{{ 'products.price' | t }}</label>
                            <p-inputNumber formControlName="price" class="w-full"
                                           mode="currency" [currency]="currencyCode()" [locale]="currencyLocale()"
                                           [min]="0" [step]="0.01">
                            </p-inputNumber>
                        </div>
                        <div>
                            <label class="block font-medium mb-1">{{ 'products.form.stock_initial' | t }}</label>
                            <p-inputNumber formControlName="stock" class="w-full"
                                           [min]="0" [step]="1">
                            </p-inputNumber>
                        </div>
                        <div>
                            <label class="block font-medium mb-1">{{ 'products.min_stock' | t }}</label>
                            <p-inputNumber formControlName="min_stock" class="w-full"
                                           [min]="0" [step]="1">
                            </p-inputNumber>
                        </div>
                    </div>

                    <div>
                        <label class="block font-medium mb-1">{{ 'products.form.unit' | t }}</label>
                        <p-select formControlName="unit" [options]="unidadesOptions" appendTo="body"
                                  optionLabel="label" optionValue="value"
                                  [placeholder]="'products.form.unit_placeholder' | t" class="w-full">
                        </p-select>
                    </div>

                    <div>
                        <label class="block font-medium mb-1">{{ 'products.form.image' | t }}</label>
                        <p-fileUpload mode="basic" name="image" accept="image/*"
                                      [maxFileSize]="5000000" [auto]="false"
                                      (onSelect)="onImageSelect($event)"
                                      [chooseLabel]="'products.form.select_image' | t" class="w-full">
                        </p-fileUpload>
                        <small class="text-surface-500 dark:text-surface-400">{{ 'products.form.image_limit_hint' | t }}</small>
                        <div *ngIf="productoSeleccionado?.image" class="mt-2">
                            <img [src]="productoSeleccionado?.image" alt="{{ 'products.form.current_image' | t }}"
                                 class="w-20 h-20 object-cover rounded border"/>
                            <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">{{ 'products.form.current_image' | t }}</p>
                        </div>
                    </div>

                    <div class="flex items-center">
                        <p-checkbox formControlName="is_active" [binary]="true" inputId="activo"></p-checkbox>
                        <label for="activo" class="ml-2 font-medium">{{ 'products.form.active_checkbox' | t }}</label>
                    </div>

                    <div class="flex justify-end gap-2 mt-4">
                        <button au-btn variant="ghost" type="button"
                                (click)="cerrarDialogo()" [disabled]="guardando()">{{ 'common.cancel' | t }}</button>
                        <button au-btn variant="primary" type="submit" icon="pi pi-check" [loading]="guardando()"
                                [disabled]="formulario.invalid">{{ productoSeleccionado ? ('common.edit' | t) : ('common.save' | t) }}</button>
                    </div>
                </form>
            </p-dialog>

            <!-- Diálogo de Ajuste de Stock -->
            <p-dialog [header]="'products.adjust_stock' | t"
                      [(visible)]="mostrarDialogoStock" [modal]="true" [style]="{ width: '92vw', maxWidth: '500px' }"
                      [breakpoints]="{'960px':'75vw','640px':'100vw'}"
                      styleClass="shadow-2xl"
                      [closable]="!guardando()" [closeOnEscape]="!guardando()">
                <form [formGroup]="formularioStock" (ngSubmit)="ejecutarAjusteStock()" class="grid gap-4">
                    <div class="rounded-2xl bg-surface-950 p-4 text-white">
                        <div class="text-[11px] uppercase tracking-[0.24em] text-surface-400">{{ 'products.th.stock' | t }}</div>
                        <div class="mt-2 text-xl font-black">{{ 'products.adjust_stock' | t }}</div>
                        <div class="mt-2 text-sm text-surface-300">{{ 'products.dialog.adjust_stock.in_out_reason' | t }}</div>
                    </div>

                    <div *ngIf="productoStock">
                        <label class="block font-medium mb-1">{{ 'products.th.product' | t }}</label>
                        <div class="rounded-xl bg-surface-50 p-3 dark:bg-surface-800/70">
                            <div class="font-medium">{{productoStock.name}}</div>
                            <div class="text-sm text-surface-500 dark:text-surface-400">{{ t('products.dialog.adjust_stock.current_stock').replace('{stock}', productoStock.stock.toString()) }}</div>
                        </div>
                    </div>

                    <div *ngIf="!productoStock">
                        <label class="block font-medium mb-1">{{ 'products.dialog.adjust_stock.select_product' | t }}</label>
                        <p-select formControlName="product_id" [options]="productosOptions" appendTo="body"
                                  optionLabel="label" optionValue="value"
                                  [placeholder]="'products.dialog.adjust_stock.select_product_placeholder' | t" class="w-full">
                        </p-select>
                    </div>

                    <div>
                        <label class="block font-medium mb-1">{{ 'products.dialog.adjust_stock.type' | t }}</label>
                        <p-select formControlName="movement_type" [options]="tiposMovimientoOptions" appendTo="body"
                                  optionLabel="label" optionValue="value"
                                  [placeholder]="'products.dialog.adjust_stock.select_type_placeholder' | t" class="w-full">
                        </p-select>
                    </div>

                    <div>
                        <label class="block font-medium mb-1">{{ 'products.dialog.adjust_stock.quantity' | t }}</label>
                        <p-inputNumber formControlName="quantity" class="w-full"
                                       [min]="1" [step]="1">
                        </p-inputNumber>
                    </div>

                    <div>
                        <label class="block font-medium mb-1">{{ 'products.dialog.adjust_stock.reason' | t }}</label>
                        <input pInputText formControlName="reason" class="w-full"
                               [placeholder]="'products.dialog.adjust_stock.reason_placeholder' | t">
                    </div>

                    <div class="flex justify-end gap-2 mt-4">
                        <button au-btn variant="ghost" type="button"
                                (click)="cerrarDialogoStock()" [disabled]="guardando()">{{ 'common.cancel' | t }}</button>
                        <button au-btn variant="primary" type="submit" icon="pi pi-check"
                                [loading]="guardando()" [disabled]="formularioStock.invalid">{{ 'products.adjust_stock' | t }}</button>
                    </div>
                </form>
            </p-dialog>
        </div>

        <p-confirmDialog></p-confirmDialog>
        <p-toast></p-toast>
    `
})
export class ProductsManagement implements OnInit {
    private inventoryService = inject(InventoryService);
    private localeService = inject(LocaleService);
    private settingsService = inject(SettingsService);
    private branchService = inject(BranchService);

    getActiveProductsCount(): number {
        return this.productos().filter((product) => product.is_active).length;
    }

    getProductsNarrative(): string {
        const total = this.productos().length;
        if (!total) {
            return this.t('products.narrative_empty');
        }

        return this.t('products.narrative_active')
            .replace('{active}', String(this.getActiveProductsCount()))
            .replace('{low_stock}', String(this.productosStockBajo().length));
    }

    getCriticalProducts(): Product[] {
        return this.productosStockBajo().slice(0, 4);
    }

    getTotalStockUnits(): number {
        return this.productos().reduce((sum, product) => sum + (Number(product.stock) || 0), 0);
    }

    getInventoryValue(): number {
        return this.productos().reduce((sum, product) => sum + ((Number(product.stock) || 0) * (Number(product.price) || 0)), 0);
    }
    private messageService = inject(MessageService);
    private confirmationService = inject(ConfirmationService);
    private fb = inject(FormBuilder);
    private authService = inject(AuthService);

    t(key: string): string {
        return this.localeService.t(key as any);
    }

    productos = signal<Product[]>([]);
    productosStockBajo = signal<Product[]>([]);
    movimientosStock = signal<StockMovementRow[]>([]);
    cargando = signal(false);
    cargandoMovimientos = signal(false);
    guardando = signal(false);
    currencyCode = computed(() => this.settingsService.settings().currency || 'DOP');
    currencyLocale = computed(() => this.settingsService.getCurrencyLocale());
    canManageProducts = computed(() => {
        const user = this.authService.getCurrentUser();
        if (!user) return false;
        const role = (user.role || '').trim().toUpperCase().replace(/[\s-]+/g, '_');
        const businessRole = (user.business_role || '').trim().toLowerCase().replace(/[\s-]+/g, '_');
        return role === 'CLIENT_ADMIN' || businessRole === 'owner';
    });
    mostrarDialogo = false;
    mostrarDialogoStock = false;
    productoSeleccionado: Product | null = null;
    productoStock: Product | null = null;
    imagenSeleccionada: File | null = null;

    productosOptions: any[] = [];

    categoriasOptions: { label: string; value: number }[] = [];

    get unidadesOptions() {
        return [
            { label: this.t('products.units.unit'), value: 'unidad' },
            { label: this.t('products.units.bottle'), value: 'botella' },
            { label: this.t('products.units.tube'), value: 'tubo' },
            { label: this.t('products.units.flask'), value: 'frasco' },
            { label: this.t('products.units.package'), value: 'paquete' }
        ];
    }

    get tiposMovimientoOptions() {
        return [
            { label: this.t('products.movement.type.in') + ' (+)', value: 'entrada' },
            { label: this.t('products.movement.type.out') + ' (-)', value: 'salida' }
        ];
    }

    formulario: FormGroup = this.fb.group({
        name: ['', [Validators.required, Validators.maxLength(255)]],
        sku: ['', [Validators.maxLength(100)]],
        barcode: ['', [Validators.maxLength(100)]],
        description: [''],
        category: [''],
        price: [0, [Validators.required, Validators.min(0)]],
        stock: [0, [Validators.min(0)]],
        min_stock: [1, [Validators.required, Validators.min(0)]],
        unit: ['unidad'],
        is_active: [true]
    });

    formularioStock: FormGroup = this.fb.group({
        product_id: [null, [Validators.required]],
        movement_type: ['', [Validators.required]],
        quantity: [1, [Validators.required, Validators.min(1)]],
        reason: ['', [Validators.required]]
    });

    ngOnInit() {
        this.cargarProductos();
        this.cargarMovimientosStock();
        this.cargarCategorias();
    }

    async cargarCategorias() {
        try {
            const response = await firstValueFrom(this.inventoryService.getCategories());
            const categorias = (response as any)?.results || response || [];
            this.categoriasOptions = (categorias as any[]).map((categoria) => ({
                label: categoria.name,
                value: categoria.id
            }));
        } catch (error: any) {
            if (error?.status !== 401 && error?.status !== 403) {
                this.messageService.add({
                    severity: 'warn',
                    summary: 'Warning',
                    detail: this.t('products.toast.load_categories_error')
                });
            }
        }
    }

    async cargarProductos() {
        this.cargando.set(true);
        try {
            const params: any = {};
            const activeBranchId = this.branchService.activeBranchId();
            if (activeBranchId) {
                params.branch_id = activeBranchId;
            }
            const response = await firstValueFrom(this.inventoryService.getProducts(params));
            const productos = (response as any)?.results || response || [];
            this.productos.set(productos);

            // Filtrar {{ 'products.stock_low' | t | lowercase }}
            const stockBajo = productos.filter((p: Product) => p.stock <= p.min_stock);
            this.productosStockBajo.set(stockBajo);

            // Configurar opciones para ajuste de stock
            this.productosOptions = productos.map((p: Product) => ({
                label: `${p.name} (Stock: ${p.stock})`,
                value: p.id
            }));

        } catch (error: any) {
            if (!environment.production) {
                
            }

            // Si es error 401/403, no mostrar mensaje ya que el interceptor maneja el logout
            if (error?.status !== 401 && error?.status !== 403) {
                this.messageService.add({
                    severity: 'error',
                    summary: 'Error',
                    detail: error?.error?.detail || this.t('products.toast.load_products_error')
                });
            }
        } finally {
            this.cargando.set(false);
        }
    }

    async cargarMovimientosStock() {
        this.cargandoMovimientos.set(true);
        try {
            const params: any = {};
            const activeBranchId = this.branchService.activeBranchId();
            if (activeBranchId) {
                params.branch_id = activeBranchId;
            }
            const response = await firstValueFrom(this.inventoryService.getStockMovements(params));
            const movimientos = (response as any)?.results || response || [];
            this.movimientosStock.set((movimientos as StockMovementRow[]).slice(0, 20));
        } catch (error: any) {
            if (!environment.production) {
                
            }
            // Evitar ruido para errores de auth controlados por interceptor
            if (error?.status !== 401 && error?.status !== 403) {
                this.messageService.add({
                    severity: 'warn',
                    summary: 'Warning',
                    detail: this.t('products.movement.empty')
                });
            }
        } finally {
            this.cargandoMovimientos.set(false);
        }
    }

    abrirDialogo() {
        this.productoSeleccionado = null;
        this.imagenSeleccionada = null;
        this.formulario.reset({
            name: '',
            sku: '',
            barcode: '',
            description: '',
            category: '',
            price: 0,
            stock: 0,
            min_stock: 1,
            unit: 'unidad',
            is_active: true
        });
        this.mostrarDialogo = true;
    }

    editarProducto(producto: Product) {
        this.productoSeleccionado = producto;
        this.imagenSeleccionada = null;
        this.formulario.patchValue({
            name: producto.name,
            sku: producto.sku,
            barcode: producto.barcode || '',
            description: producto.description || '',
            category: producto.category || '',
            price: producto.price,
            stock: producto.stock,
            min_stock: producto.min_stock,
            unit: producto.unit || 'unidad',
            is_active: producto.is_active
        });
        this.mostrarDialogo = true;
    }

    async guardarProducto() {
        if (this.formulario.invalid) return;

        this.guardando.set(true);
        try {
            if (this.imagenSeleccionada) {
                // Con imagen: usar FormData
                const formData = new FormData();
                const productoData = { ...this.formulario.value };

                if (!this.productoSeleccionado) {
                    const activeBranchId = this.branchService.activeBranchId();
                    if (activeBranchId) {
                        productoData.branch = activeBranchId;
                    }
                }

                Object.keys(productoData).forEach(key => {
                    if (productoData[key] !== null && productoData[key] !== undefined) {
                        formData.append(key, productoData[key]);
                    }
                });
                formData.append('image', this.imagenSeleccionada);

                if (this.productoSeleccionado) {
                    await firstValueFrom(this.inventoryService.updateProductWithImage(this.productoSeleccionado.id, formData));
                } else {
                    await firstValueFrom(this.inventoryService.createProductWithImage(formData));
                }
            } else {
                // Sin imagen: usar JSON
                const productoData = { ...this.formulario.value };

                if (!this.productoSeleccionado) {
                    const activeBranchId = this.branchService.activeBranchId();
                    if (activeBranchId) {
                        productoData.branch = activeBranchId;
                    }
                }

                if (this.productoSeleccionado) {
                    await firstValueFrom(this.inventoryService.updateProduct(this.productoSeleccionado.id, productoData));
                } else {
                    await firstValueFrom(this.inventoryService.createProduct(productoData));
                }
            }

            this.messageService.add({
                severity: 'success',
                summary: 'Éxito',
                detail: this.productoSeleccionado ? this.t('products.toast.update_success') : this.t('products.toast.create_success')
            });

            this.cerrarDialogo();
            this.cargarProductos();
        } catch (error: any) {
            if (!environment.production) {
                
            }
            
            // Extraer mensaje de error específico de la imagen
            let errorDetail = 'Error al guardar el producto';
            if (error?.error?.image && Array.isArray(error.error.image)) {
                errorDetail = error.error.image[0];
            } else if (error?.error?.detail) {
                errorDetail = error.error.detail;
            } else if (error?.error && typeof error.error === 'object') {
                const firstField = Object.keys(error.error)[0];
                const firstFieldErrors = error.error[firstField];
                if (Array.isArray(firstFieldErrors) && firstFieldErrors.length > 0) {
                    errorDetail = `${firstField}: ${firstFieldErrors[0]}`;
                } else if (typeof firstFieldErrors === 'string') {
                    errorDetail = `${firstField}: ${firstFieldErrors}`;
                }
            }
            
            this.messageService.add({
                severity: 'error',
                summary: 'Error',
                detail: errorDetail
            });
        } finally {
            this.guardando.set(false);
        }
    }

    abrirDialogoStock() {
        this.productoStock = null;
        this.formularioStock.reset({
            product_id: null,
            movement_type: '',
            quantity: 1,
            reason: ''
        });
        this.mostrarDialogoStock = true;
    }

    ajustarStockProducto(producto: Product) {
        this.productoStock = producto;
        this.formularioStock.patchValue({
            product_id: producto.id,
            movement_type: '',
            quantity: 1,
            reason: ''
        });
        this.mostrarDialogoStock = true;
    }

    async ejecutarAjusteStock() {
        if (this.formularioStock.invalid) return;

        this.guardando.set(true);
        try {
            const formData = this.formularioStock.value;
            const cantidad = formData.movement_type === 'entrada' ?
                formData.quantity : -formData.quantity;

            await firstValueFrom(this.inventoryService.adjustStock(
                formData.product_id,
                cantidad,
                formData.reason
            ));

            this.messageService.add({
                severity: 'success',
                summary: this.t('common.success'),
                detail: this.t('products.toast.adjust_stock_success')
            });

            this.cerrarDialogoStock();
            this.cargarProductos();
            this.cargarMovimientosStock();
        } catch (error: any) {
            if (!environment.production) {
                
            }
            this.messageService.add({
                severity: 'error',
                summary: 'Error',
                detail: error?.error?.detail || this.t('products.toast.adjust_stock_error')
            });
        } finally {
            this.guardando.set(false);
        }
    }

    confirmarEliminar(producto: Product) {
        this.confirmationService.confirm({
            message: this.t('products.delete_confirm_msg').replace('{name}', producto.name),
            header: this.t('products.confirm_delete_title'),
            icon: 'pi pi-exclamation-triangle',
            acceptLabel: this.t('products.confirm_delete_accept'),
            rejectLabel: this.t('common.cancel'),
            accept: () => this.eliminarProducto(producto)
        });
    }

    async eliminarProducto(producto: Product) {
        try {
            await firstValueFrom(this.inventoryService.deleteProduct(producto.id));
            this.messageService.add({
                severity: 'success',
                summary: 'Éxito',
                detail: this.t('products.toast.delete_success')
            });
            this.cargarProductos();
        } catch (error: any) {
            if (!environment.production) {
                
            }
            this.messageService.add({
                severity: 'error',
                summary: 'Error',
                detail: error?.error?.detail || 'Error al eliminar el producto'
            });
        }
    }

    getStockClass(producto: Product): string {
        if (producto.stock <= producto.min_stock) {
            return 'text-red-600 font-bold';
        } else if (producto.stock <= producto.min_stock * 2) {
            return 'text-orange-600 font-medium';
        }
        return 'text-green-600';
    }

    getMovementDate(mov: StockMovementRow): string | null {
        return mov.created_at || mov.date || null;
    }

    getMovementProductName(mov: StockMovementRow): string {
        if (typeof mov.product === 'object' && mov.product?.name) {
            return mov.product.name;
        }
        const productId = typeof mov.product === 'number' ? mov.product : mov.product?.id;
        const product = this.productos().find((p) => p.id === productId);
        return product?.name || `Producto #${productId ?? 'N/A'}`;
    }

    formatearMoneda(valor: number | string | null | undefined): string {
        const amount = Number(valor) || 0;
        return new Intl.NumberFormat(this.currencyLocale(), {
            style: 'currency',
            currency: this.currencyCode()
        }).format(amount);
    }

    onImageSelect(event: any) {
        const file = event.files[0];
        if (file) {
            // Validar tipo de archivo
            const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
            if (!allowedTypes.includes(file.type)) {
                this.messageService.add({
                    severity: 'error',
                    summary: 'Formato Inválido',
                    detail: 'Solo se permiten imágenes en formato JPG, PNG o GIF'
                });
                return;
            }

            // Validar tamaño (5MB)
            if (file.size > 5000000) {
                this.messageService.add({
                    severity: 'error',
                    summary: 'Archivo muy grande',
                    detail: 'La imagen no debe superar los 5MB'
                });
                return;
            }

            this.imagenSeleccionada = file;
            this.messageService.add({
                severity: 'success',
                summary: 'Imagen Seleccionada',
                detail: `${file.name} listo para subir`
            });
        }
    }

    cerrarDialogo() {
        this.mostrarDialogo = false;
        this.productoSeleccionado = null;
        this.imagenSeleccionada = null;
        this.formulario.reset();
    }

    cerrarDialogoStock() {
        this.mostrarDialogoStock = false;
        this.productoStock = null;
        this.formularioStock.reset();
    }
}
