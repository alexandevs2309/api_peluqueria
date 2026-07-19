import { Component, OnInit, OnDestroy, inject, signal, computed } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { SelectModule } from 'primeng/select';
import { DialogModule } from 'primeng/dialog';
import { ToastModule } from 'primeng/toast';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ConfirmationService, MessageService } from 'primeng/api';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { AuBtn } from '../../shared/components';
import { SubscriptionService } from '../../core/services/subscription/subscription.service';
import { TenantService, Tenant } from '../../core/services/tenant/tenant.service';
import { LocaleService } from '../../core/services/locale/locale.service';

interface PromotionalCredit {
    id: number;
    tenant: number;
    tenant_name: string;
    months: number;
    reason: string;
    campaign_tag: string;
    created_by: number;
    created_by_name: string;
    used_at: string;
    created_at: string;
}

@Component({
    selector: 'app-promotional-credits',
    standalone: true,
    imports: [
        FormsModule, DatePipe,
        ButtonModule, InputTextModule, InputNumberModule,
        SelectModule, DialogModule, ToastModule, ConfirmDialogModule,
        TableModule, TagModule, AuBtn
    ],
    providers: [ConfirmationService, MessageService],
    template: `
        <p-toast></p-toast>
        <p-confirmDialog [style]="{ maxWidth: '450px' }"></p-confirmDialog>

        <section class="mb-8 overflow-hidden rounded-[2rem] border border-surface-200/70 bg-surface-0 shadow-[0_24px_80px_-42px_rgba(15,23,42,0.45)] dark:border-surface-800 dark:bg-surface-900">
            <div class="relative overflow-hidden px-8 py-8 lg:px-10">
                <div class="hero-gradient"></div>
                <div class="relative grid gap-8 lg:grid-cols-[minmax(0,1.5fr)_minmax(320px,0.9fr)] lg:items-start">
                    <div>
                        <div class="mb-4 inline-flex items-center gap-2 rounded-full border border-surface-200 bg-surface-50/90 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.24em] text-surface-600 dark:border-surface-700 dark:bg-surface-800/80 dark:text-surface-300">
                            <i class="pi pi-gift text-[0.7rem] text-primary"></i>
                            {{ t('admin.promotional_credits.badge') }}
                        </div>
                        <h1 class="text-3xl font-semibold tracking-tight text-surface-950 dark:text-surface-0 lg:text-4xl">
                            {{ t('admin.promotional_credits.title') }}
                        </h1>
                        <p class="mt-3 max-w-2xl text-base leading-7 text-surface-600 dark:text-surface-300">
                            {{ t('admin.promotional_credits.description') }}
                        </p>
                    </div>
                    <div class="grid gap-3 grid-cols-2">
                        <article class="rounded-3xl border border-surface-200 bg-white/80 p-5 shadow-sm backdrop-blur dark:border-surface-700 dark:bg-surface-800/80">
                            <div class="text-xs font-semibold uppercase tracking-[0.24em] text-surface-500 dark:text-surface-400">{{ t('admin.promotional_credits.total') }}</div>
                            <div class="mt-3 text-3xl font-semibold text-surface-950 dark:text-surface-0">{{ credits().length }}</div>
                        </article>
                        <article class="rounded-3xl border border-surface-200 bg-white/80 p-5 shadow-sm backdrop-blur dark:border-surface-700 dark:bg-surface-800/80">
                            <div class="text-xs font-semibold uppercase tracking-[0.24em] text-surface-500 dark:text-surface-400">{{ t('admin.promotional_credits.unused') }}</div>
                            <div class="mt-3 text-3xl font-semibold text-green-600 dark:text-green-400">{{ unusedCount() }}</div>
                        </article>
                        <article class="rounded-3xl border border-surface-200 bg-white/80 p-5 shadow-sm backdrop-blur dark:border-surface-700 dark:bg-surface-800/80">
                            <div class="text-xs font-semibold uppercase tracking-[0.24em] text-surface-500 dark:text-surface-400">{{ t('admin.promotional_credits.used') }}</div>
                            <div class="mt-3 text-3xl font-semibold text-surface-500 dark:text-surface-400">{{ usedCount() }}</div>
                        </article>
                        <article class="rounded-3xl border border-surface-200 bg-white/80 p-5 shadow-sm backdrop-blur dark:border-surface-700 dark:bg-surface-800/80">
                            <div class="text-xs font-semibold uppercase tracking-[0.24em] text-surface-500 dark:text-surface-400">{{ t('admin.promotional_credits.total_months') }}</div>
                            <div class="mt-3 text-3xl font-semibold text-primary">{{ totalMonths() }}</div>
                        </article>
                    </div>
                </div>
            </div>
        </section>

        <div class="mb-6 flex items-center justify-between gap-4">
            <div class="flex-1">
                <div class="relative">
                    <i class="pi pi-search absolute left-3 top-1/2 -translate-y-1/2 text-surface-400"></i>
                    <input type="text" [placeholder]="t('admin.promotional_credits.search_placeholder')"
                           class="w-full max-w-sm rounded-xl border border-surface-200 bg-surface-0 py-2.5 pl-10 pr-4 text-sm text-surface-700 placeholder-surface-400 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-200"
                           [(ngModel)]="searchQuery" (input)="onSearch()" />
                </div>
            </div>
            <button au-btn [icon]="'pi pi-plus'" (click)="showCreateDialog()">{{ t('admin.promotional_credits.create_button') }}</button>
        </div>

        <div class="overflow-hidden rounded-[2rem] border border-surface-200 bg-surface-0 shadow-sm dark:border-surface-800 dark:bg-surface-900">
            <p-table [value]="filteredCredits()" [loading]="loading()" [paginator]="true" [rows]="20"
                     [rowsPerPageOptions]="[10, 20, 50]" styleClass="p-datatable-sm" responsiveLayout="scroll">
                <ng-template pTemplate="header">
                    <tr>
                        <th>{{ t('admin.promotional_credits.col_tenant') }}</th>
                        <th>{{ t('admin.promotional_credits.col_months') }}</th>
                        <th>{{ t('admin.promotional_credits.col_reason') }}</th>
                        <th>{{ t('admin.promotional_credits.col_tag') }}</th>
                        <th>{{ t('admin.promotional_credits.col_status') }}</th>
                        <th>{{ t('admin.promotional_credits.col_created_at') }}</th>
                        <th>{{ t('admin.promotional_credits.col_used_at') }}</th>
                        <th>{{ t('admin.promotional_credits.col_created_by') }}</th>
                        <th></th>
                    </tr>
                </ng-template>
                <ng-template pTemplate="body" let-credit>
                    <tr>
                        <td class="font-medium text-surface-900 dark:text-surface-0">{{ credit.tenant_name }}</td>
                        <td>{{ credit.months }}</td>
                        <td class="max-w-[200px] truncate" [title]="credit.reason">{{ credit.reason }}</td>
                        <td>
                            @if (credit.campaign_tag) {
                                <p-tag [value]="credit.campaign_tag" severity="info" />
                            }
                        </td>
                        <td>
                            <p-tag [value]="credit.used_at ? t('admin.promotional_credits.status_used') : t('admin.promotional_credits.status_unused')"
                                   [severity]="credit.used_at ? 'secondary' : 'success'" />
                        </td>
                        <td>{{ credit.created_at | date:'short' }}</td>
                        <td>
                            @if (credit.used_at) {
                                {{ credit.used_at | date:'short' }}
                            }
                        </td>
                        <td>{{ credit.created_by_name }}</td>
                        <td>
                            @if (!credit.used_at) {
                                <button au-btn variant="danger" [icon]="'pi pi-trash'"
                                        (click)="confirmDelete(credit)"></button>
                            }
                        </td>
                    </tr>
                </ng-template>
                <ng-template pTemplate="emptymessage">
                    <tr>
                        <td colspan="9" class="text-center py-12 text-surface-500">
                            {{ t('admin.promotional_credits.empty') }}
                        </td>
                    </tr>
                </ng-template>
            </p-table>
        </div>

        <p-dialog [header]="t('admin.promotional_credits.dialog_title')" [(visible)]="dialogVisible" [modal]="true"
                  [style]="{ width: '500px' }" [breakpoints]="{'960px':'75vw','640px':'100vw'}" [draggable]="false" [resizable]="false">
            <div class="flex flex-col gap-5 py-4">
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-surface-500 mb-2">{{ t('admin.promotional_credits.field_tenant') }}</label>
                    <p-select [options]="tenants()" [(ngModel)]="formTenant" optionLabel="name" optionValue="id"
                              [placeholder]="t('admin.promotional_credits.field_tenant_placeholder')"
                              class="w-full" [filter]="true" />
                </div>
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-surface-500 mb-2">{{ t('admin.promotional_credits.field_months') }}</label>
                    <p-inputNumber [(ngModel)]="formMonths" [min]="1" [max]="36" class="w-full" />
                </div>
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-surface-500 mb-2">{{ t('admin.promotional_credits.field_reason') }}</label>
                    <input type="text" pInputText [(ngModel)]="formReason"
                           class="w-full" />
                </div>
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-surface-500 mb-2">{{ t('admin.promotional_credits.field_tag') }}</label>
                    <input type="text" pInputText [(ngModel)]="formTag"
                           class="w-full" />
                    <p class="mt-1 text-xs text-surface-400">{{ t('admin.promotional_credits.field_tag_hint') }}</p>
                </div>
            </div>
            <div class="flex justify-end gap-3 pt-4 border-t border-surface-200 dark:border-surface-700">
                <button au-btn variant="secondary" (click)="dialogVisible = false">{{ t('admin.promotional_credits.cancel') }}</button>
                <button au-btn [icon]="'pi pi-check'" [disabled]="!formTenant || !formMonths || !formReason" (click)="createCredit()">{{ t('admin.promotional_credits.save') }}</button>
            </div>
        </p-dialog>
    `
})
export class PromotionalCredits implements OnInit, OnDestroy {
    private subscriptionService = inject(SubscriptionService);
    private tenantService = inject(TenantService);
    private localeService = inject(LocaleService);
    private confirmationService = inject(ConfirmationService);
    private messageService = inject(MessageService);

    loading = signal(true);
    allCredits = signal<PromotionalCredit[]>([]);
    tenants = signal<Tenant[]>([]);
    searchQuery = '';

    dialogVisible = false;
    formTenant: number | null = null;
    formMonths: number = 1;
    formReason = '';
    formTag = '';

    private languageSubscription: any;

    credits = computed(() => this.allCredits());

    unusedCount = computed(() => this.credits().filter(c => !c.used_at).length);
    usedCount = computed(() => this.credits().filter(c => c.used_at).length);
    totalMonths = computed(() => this.credits().reduce((sum, c) => sum + c.months, 0));

    filteredCredits = computed(() => {
        const q = this.searchQuery.toLowerCase().trim();
        if (!q) return this.credits();
        return this.credits().filter(c =>
            c.tenant_name.toLowerCase().includes(q) ||
            c.reason.toLowerCase().includes(q) ||
            (c.campaign_tag || '').toLowerCase().includes(q) ||
            c.created_by_name.toLowerCase().includes(q)
        );
    });

    ngOnInit(): void {
        this.load();
    }

    ngOnDestroy(): void {
        if (this.languageSubscription) {
            this.languageSubscription.unsubscribe();
        }
    }

    t(key: string): string {
        return this.localeService.t(key as any);
    }

    load(): void {
        this.loading.set(true);
        this.subscriptionService.getPromotionalCredits().subscribe({
            next: (res: any) => {
                this.allCredits.set(Array.isArray(res) ? res : (res?.results || []));
                this.loading.set(false);
            },
            error: () => {
                this.loading.set(false);
                this.messageService.add({ severity: 'error', summary: 'Error', detail: this.t('admin.promotional_credits.load_error') });
            }
        });
        this.tenantService.getTenants({ is_active: true }).subscribe({
            next: (res: any) => {
                this.tenants.set(Array.isArray(res) ? res : (res?.results || []));
            }
        });
    }

    onSearch(): void {
    }

    showCreateDialog(): void {
        this.formTenant = null;
        this.formMonths = 1;
        this.formReason = '';
        this.formTag = '';
        this.dialogVisible = true;
    }

    createCredit(): void {
        if (!this.formTenant || !this.formMonths || !this.formReason) return;
        this.subscriptionService.createPromotionalCredit({
            tenant: this.formTenant,
            months: this.formMonths,
            reason: this.formReason,
            campaign_tag: this.formTag || undefined
        }).subscribe({
            next: () => {
                this.messageService.add({ severity: 'success', summary: this.t('admin.promotional_credits.success_title'), detail: this.t('admin.promotional_credits.success_detail') });
                this.dialogVisible = false;
                this.load();
            },
            error: () => {
                this.messageService.add({ severity: 'error', summary: 'Error', detail: this.t('admin.promotional_credits.create_error') });
            }
        });
    }

    confirmDelete(credit: PromotionalCredit): void {
        this.confirmationService.confirm({
            message: `${this.t('admin.promotional_credits.delete_confirm')} "${credit.reason}" (${credit.tenant_name})?`,
            header: this.t('admin.promotional_credits.delete_header'),
            icon: 'pi pi-exclamation-triangle',
            acceptLabel: this.t('admin.promotional_credits.delete_accept'),
            rejectLabel: this.t('admin.promotional_credits.delete_reject'),
            accept: () => {
                this.deleteCredit(credit.id);
            }
        });
    }

    deleteCredit(id: number): void {
        this.subscriptionService.deletePromotionalCredit(id).subscribe({
            next: () => {
                this.messageService.add({ severity: 'success', summary: this.t('admin.promotional_credits.deleted_title'), detail: this.t('admin.promotional_credits.deleted_detail') });
                this.load();
            },
            error: () => {
                this.messageService.add({ severity: 'error', summary: 'Error', detail: this.t('admin.promotional_credits.delete_error') });
            }
        });
    }
}
