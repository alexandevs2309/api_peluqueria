import { Component, signal, computed, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { TextareaModule } from 'primeng/textarea';
import { DialogModule } from 'primeng/dialog';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ToastModule } from 'primeng/toast';
import { CheckboxModule } from 'primeng/checkbox';
import { ToggleSwitchModule } from 'primeng/toggleswitch';
import { ConfirmationService, MessageService } from 'primeng/api';
import { BranchService, Branch } from '../../../core/services/branch/branch.service';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { environment } from '../../../../environments/environment';
import { I18nPipe } from '../../../core/pipes/i18n.pipe';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { AuBtn } from '../../../shared/components';

@Component({
  selector: 'app-branches-management',
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    TableModule, ButtonModule, InputTextModule, TextareaModule,
    DialogModule, ConfirmDialogModule, ToastModule,
    CheckboxModule, ToggleSwitchModule, TagModule,
    I18nPipe, EmptyStateComponent,
    AuBtn,
  ],
  providers: [ConfirmationService, MessageService],
  template: `
    <div class="space-y-6">
      <section class="overflow-hidden rounded-[2rem] border border-surface-200 bg-white shadow-sm dark:border-surface-700 dark:bg-surface-900">
        <div class="relative overflow-hidden px-8 py-8 lg:px-10">
          <div class="hero-gradient pointer-events-none absolute inset-0 bg-gradient-to-br from-primary-50/30 via-transparent to-transparent dark:from-primary-950/20"></div>
          <div class="relative flex items-center justify-between gap-4">
            <div class="space-y-5">
              <div class="inline-flex items-center gap-2 rounded-full bg-surface-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-surface-600 dark:bg-surface-800 dark:text-surface-300">
                <i class="pi pi-sitemap text-[0.7rem] text-primary"></i>
                {{ 'branches.title' | t }}
              </div>
              <div>
                <h2 class="display-4 text-surface-950 dark:text-white">{{ 'branches.title' | t }}</h2>
                <p class="mt-3 max-w-3xl text-base leading-7 text-surface-600 dark:text-surface-300">
                  {{ 'branches.subtitle' | t }}
                </p>
              </div>
            </div>
            <button au-btn variant="primary" icon="pi pi-plus" (click)="openNew()">{{ 'branches.new' | t }}</button>
          </div>
        </div>
        <div class="border-t border-surface-200/80 px-6 py-5 dark:border-surface-800">
          <p-table [value]="branches()" [paginator]="true" [rows]="10" [rowsPerPageOptions]="[5,10,20]" responsiveLayout="scroll" styleClass="p-datatable-striped">
            <ng-template #header>
              <tr>
                <th pSortableColumn="name">{{ 'branches.name' | t }} <p-sortIcon field="name"></p-sortIcon></th>
                <th>{{ 'branches.address' | t }}</th>
                <th>{{ 'branches.main' | t }}</th>
                <th>{{ 'branches.active' | t }}</th>
                <th>{{ 'branches.employees' | t }}</th>
                <th style="width:120px">{{ 'branches.actions' | t }}</th>
              </tr>
            </ng-template>
            <ng-template #body let-branch>
              <tr>
                <td class="font-medium">{{ branch.name }}</td>
                <td class="text-surface-500">{{ branch.address || '&mdash;' }}</td>
                <td>
                  <p-tag [severity]="branch.is_main ? 'success' : 'secondary'" [value]="branch.is_main ? t('common.yes') : t('common.no')"></p-tag>
                </td>
                <td>
                  <p-toggleswitch [ngModel]="branch.is_active" (onChange)="toggleActive(branch, $event)"></p-toggleswitch>
                </td>
                <td>{{ branch.employee_count }}</td>
                <td>
                  <button au-btn variant="ghost" size="sm" icon="pi pi-pencil" [iconOnly]="true" (click)="editBranch(branch)"></button>
                  <button au-btn variant="danger" size="sm" icon="pi pi-trash" [iconOnly]="true" (click)="deleteBranch(branch)"></button>
                </td>
              </tr>
            </ng-template>
            <ng-template #emptymessage>
              <tr>
                <td colspan="6">
                  <app-empty-state
                    title="Sin sucursales registradas"
                    description="Comienza agregando tu primera sucursal."
                    actionLabel="branches.new"
                    (actionClicked)="openNew()">
                  </app-empty-state>
                </td>
              </tr>
            </ng-template>
          </p-table>
        </div>
      </section>

      <p-toast></p-toast>
      <p-confirmdialog></p-confirmdialog>

      <p-dialog [header]="dialogTitle()" [(visible)]="showDialog" [modal]="true" [style]="{width:'92vw', 'maxWidth':'500px'}" [breakpoints]="{'960px':'75vw','640px':'100vw'}" (onHide)="hideDialog()">
        <div class="flex flex-column gap-3 p-3">
          <div>
            <label for="name" class="block font-medium mb-1">{{ 'branches.name' | t }}</label>
            <input id="name" pInputText [(ngModel)]="form.name" class="w-full" required />
          </div>
          <div>
            <label for="address" class="block font-medium mb-1">{{ 'branches.address' | t }}</label>
            <textarea id="address" pInputTextarea [(ngModel)]="form.address" class="w-full" rows="3"></textarea>
          </div>
          <div class="flex align-items-center gap-2">
            <p-checkbox [binary]="true" [(ngModel)]="form.is_main" inputId="is_main"></p-checkbox>
            <label for="is_main">{{ 'branches.is_main' | t }}</label>
          </div>
        </div>
        <div class="flex justify-end gap-2 mt-4">
          <button au-btn variant="ghost" icon="pi pi-times" (click)="hideDialog()">{{ 'common.cancel' | t }}</button>
          <button au-btn variant="primary" icon="pi pi-check" (click)="saveBranch()" [disabled]="saving()">{{ isEditing() ? t('common.save') : t('common.create') }}</button>
        </div>
      </p-dialog>
    </div>
  `,
})
export class BranchesManagement implements OnInit {
  private branchService = inject(BranchService);
  private confirmationService = inject(ConfirmationService);
  private messageService = inject(MessageService);
  private localeService = inject(LocaleService);

  branches = computed(() => this.branchService.branches());
  showDialog = false;
  saving = signal(false);
  editingId = signal<number | null>(null);

  form: { name: string; address: string; is_main: boolean } = {
    name: '',
    address: '',
    is_main: false,
  };

  t(key: string): string {
    return this.localeService.t(key as any);
  }

  isEditing = computed(() => this.editingId() !== null);
  dialogTitle = computed(() => this.isEditing() ? this.t('branches.edit') : this.t('branches.new'));

  ngOnInit(): void {
    this.loadBranches();
  }

  private loadBranches(): void {
    this.branchService.loadBranches(true).subscribe({
      error: (err) => {
        if (!environment.production) console.error('Error loading branches', err);
        this.messageService.add({ severity: 'error', summary: this.t('common.error'), detail: this.t('branches.load_error') });
      },
    });
  }

  openNew(): void {
    this.editingId.set(null);
    this.form = { name: '', address: '', is_main: false };
    this.showDialog = true;
  }

  editBranch(branch: Branch): void {
    this.editingId.set(branch.id);
    this.form = { name: branch.name, address: branch.address || '', is_main: branch.is_main };
    this.showDialog = true;
  }

  saveBranch(): void {
    if (!this.form.name.trim()) {
      this.messageService.add({ severity: 'warn', summary: this.t('common.error'), detail: this.t('branches.name_required') });
      return;
    }

    this.saving.set(true);
    const data: Partial<Branch> = { name: this.form.name.trim(), address: this.form.address.trim() || null, is_main: this.form.is_main };

    const request = this.isEditing()
      ? this.branchService.update(this.editingId()!, data)
      : this.branchService.create(data);

    request.subscribe({
      next: () => {
        this.messageService.add({ severity: 'success', summary: this.t('common.success'), detail: this.isEditing() ? this.t('branches.toast.update_success') : this.t('branches.toast.create_success') });
        this.hideDialog();
        this.loadBranches();
      },
      error: (err) => {
        this.saving.set(false);
        const detail = err.error?.name?.[0] || err.error?.is_main?.[0] || err.error?.detail || this.t('branches.save_error');
        this.messageService.add({ severity: 'error', summary: this.t('common.error'), detail });
      },
    });
  }

  deleteBranch(branch: Branch): void {
    this.confirmationService.confirm({
      message: this.t('branches.delete_confirm').replace('{name}', branch.name),
      header: this.t('branches.confirm_delete_title'),
      icon: 'pi pi-exclamation-triangle',
      accept: () => {
        this.branchService.remove(branch.id).subscribe({
          next: () => {
            this.messageService.add({ severity: 'success', summary: this.t('common.success'), detail: this.t('branches.delete_success') });
            this.loadBranches();
          },
          error: (err) => {
            this.messageService.add({ severity: 'error', summary: this.t('common.error'), detail: err.error?.detail || this.t('branches.delete_error') });
          },
        });
      },
    });
  }

  toggleActive(branch: Branch, event: any): void {
    const is_active = event.checked;
    this.branchService.update(branch.id, { is_active }).subscribe({
      next: () => this.loadBranches(),
      error: () => this.loadBranches(),
    });
  }

  hideDialog(): void {
    this.showDialog = false;
    this.saving.set(false);
  }
}
