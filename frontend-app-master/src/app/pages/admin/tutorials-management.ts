import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { ToastModule } from 'primeng/toast';
import { InputTextModule } from 'primeng/inputtext';
import { TextareaModule } from 'primeng/textarea';
import { InputNumberModule } from 'primeng/inputnumber';
import { SelectModule } from 'primeng/select';
import { CheckboxModule } from 'primeng/checkbox';
import { DialogModule } from 'primeng/dialog';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { TooltipModule } from 'primeng/tooltip';
import { MessageService, ConfirmationService } from 'primeng/api';
import { TutorialAdminService, Tutorial } from '../../core/services/tutorials/tutorial-admin.service';

interface ModuleOption {
  value: string;
  label: string;
}

@Component({
  selector: 'app-tutorials-management',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ButtonModule,
    ToastModule,
    InputTextModule,
    TextareaModule,
    InputNumberModule,
    SelectModule,
    CheckboxModule,
    DialogModule,
    ConfirmDialogModule,
    TooltipModule,
  ],
  providers: [MessageService, ConfirmationService],
  template: `
    <div class="card">
      <div class="sm:flex sm:items-center sm:justify-between">
        <div class="sm:flex-auto">
          <div class="flex items-center gap-3">
            <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-[#2563EB]/10 text-[#2563EB]">
              <i class="pi pi-video text-lg"></i>
            </div>
            <div>
              <h1 class="text-base font-semibold text-surface-950 dark:text-surface-0">Tutoriales</h1>
              <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">Gestiona los videos tutoriales de la plataforma</p>
            </div>
          </div>
        </div>
        <div class="mt-4 flex items-center gap-3 sm:mt-0 sm:ml-16 sm:flex-none">
          <p-button label="Nuevo Tutorial" icon="pi pi-plus" (click)="openNew()" styleClass="!bg-[#2563EB] !border-0" />
        </div>
      </div>

      <div class="mt-8 overflow-x-auto">
        <table class="min-w-full divide-y divide-surface-200 dark:divide-surface-700">
          <thead>
            <tr>
              <th scope="col" class="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-surface-900 dark:text-surface-100">Orden</th>
              <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-900 dark:text-surface-100">Título</th>
              <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-900 dark:text-surface-100">Módulo</th>
              <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-surface-900 dark:text-surface-100">Duración</th>
              <th scope="col" class="px-3 py-3.5 text-center text-sm font-semibold text-surface-900 dark:text-surface-100">Publicado</th>
              <th scope="col" class="relative py-3.5 pl-3 pr-4 sm:pr-6 text-right text-sm font-semibold text-surface-900 dark:text-surface-100">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-surface-200 dark:divide-surface-700">
            @for (tutorial of tutorials(); track tutorial.id) {
              <tr class="hover:bg-surface-50 dark:hover:bg-surface-800/50 transition-colors">
                <td class="whitespace-nowrap py-4 pl-4 pr-3 text-sm text-surface-600 dark:text-surface-400">{{ tutorial.order }}</td>
                <td class="whitespace-nowrap px-3 py-4 text-sm font-medium text-surface-900 dark:text-surface-100">{{ tutorial.title }}</td>
                <td class="whitespace-nowrap px-3 py-4 text-sm text-surface-600 dark:text-surface-400">{{ moduleLabel(tutorial.module) }}</td>
                <td class="whitespace-nowrap px-3 py-4 text-sm text-surface-600 dark:text-surface-400">{{ tutorial.duration || '—' }}</td>
                <td class="whitespace-nowrap px-3 py-4 text-center">
                  <i class="pi" [class.pi-check-circle]="tutorial.is_published" [class.text-green-500]="tutorial.is_published" [class.pi-times-circle]="!tutorial.is_published" [class.text-red-400]="!tutorial.is_published"></i>
                </td>
                <td class="whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm">
                  <p-button icon="pi pi-pencil" severity="secondary" [text]="true" (click)="editTutorial(tutorial)" pTooltip="Editar" />
                  <p-button icon="pi pi-trash" severity="danger" [text]="true" (click)="deleteTutorial(tutorial)" pTooltip="Eliminar" />
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="6" class="py-20 text-center text-surface-400 dark:text-surface-500">
                  <i class="pi pi-video text-4xl mb-3 block opacity-50"></i>
                  <p class="text-sm">No hay tutoriales aún</p>
                  <p-button label="Crear primer tutorial" icon="pi pi-plus" (click)="openNew()" styleClass="mt-4 !bg-[#2563EB] !border-0" />
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </div>

    <p-dialog [(visible)]="dialogVisible" [style]="{ width: '550px' }" [breakpoints]="{'960px':'75vw','640px':'100vw'}" [header]="editing() ? 'Editar Tutorial' : 'Nuevo Tutorial'" [modal]="true" [draggable]="false" [resizable]="false">
      <ng-template pTemplate="content">
        <div class="flex flex-col gap-5">
          <div>
            <label class="block font-bold mb-2 text-sm">Módulo</label>
            <p-select [(ngModel)]="form.module" [options]="moduleOptions" optionLabel="label" optionValue="value" placeholder="Seleccionar módulo" appendTo="body" class="w-full" />
            @if (submitted && !form.module) {
              <small class="text-red-500">El módulo es obligatorio.</small>
            }
          </div>

          <div>
            <label class="block font-bold mb-2 text-sm">Título</label>
            <input pInputText [(ngModel)]="form.title" class="w-full" required />
            @if (submitted && !form.title) {
              <small class="text-red-500">El título es obligatorio.</small>
            }
          </div>

          <div>
            <label class="block font-bold mb-2 text-sm">Descripción</label>
            <textarea pTextarea [(ngModel)]="form.description" rows="3" class="w-full"></textarea>
          </div>

          <div>
            <label class="block font-bold mb-2 text-sm">URL del video (YouTube embed)</label>
            <input pInputText [(ngModel)]="form.video_url" class="w-full" placeholder="https://www.youtube.com/embed/..." required />
            @if (submitted && !form.video_url) {
              <small class="text-red-500">La URL del video es obligatoria.</small>
            }
          </div>

          <div>
            <label class="block font-bold mb-2 text-sm">URL del thumbnail (opcional)</label>
            <input pInputText [(ngModel)]="form.thumbnail_url" class="w-full" placeholder="https://..." />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block font-bold mb-2 text-sm">Duración</label>
              <input pInputText [(ngModel)]="form.duration" class="w-full" placeholder="3:45" />
            </div>
            <div>
              <label class="block font-bold mb-2 text-sm">Orden</label>
              <p-inputNumber [(ngModel)]="form.order" [min]="0" class="w-full" />
            </div>
          </div>

          <div class="flex items-center gap-2">
            <p-checkbox [(ngModel)]="form.is_published" [binary]="true" inputId="is_published" />
            <label for="is_published" class="text-sm">Publicado</label>
          </div>
        </div>
      </ng-template>
      <ng-template pTemplate="footer">
        <p-button label="Cancelar" icon="pi pi-times" [text]="true" (click)="hideDialog()" />
        <p-button label="Guardar" icon="pi pi-check" (click)="saveTutorial()" [loading]="saving()" class="!bg-[#2563EB] !border-0" />
      </ng-template>
    </p-dialog>

    <p-toast />
    <p-confirmdialog />
  `
})
export class TutorialsManagement implements OnInit {
  private readonly service = inject(TutorialAdminService);
  private readonly messageService = inject(MessageService);
  private readonly confirmationService = inject(ConfirmationService);

  tutorials = signal<Tutorial[]>([]);
  loading = signal(false);
  saving = signal(false);
  dialogVisible = false;
  submitted = false;

  editing = computed(() => !!this.form.id);

  form: Tutorial = {
    module: '',
    title: '',
    description: '',
    video_url: '',
    thumbnail_url: '',
    duration: '',
    order: 0,
    is_published: true,
  };

  moduleOptions: ModuleOption[] = [
    { value: 'appointments', label: 'Citas' },
    { value: 'employees', label: 'Empleados' },
    { value: 'pos', label: 'POS / Ventas' },
    { value: 'inventory', label: 'Inventario' },
    { value: 'services', label: 'Servicios' },
    { value: 'clients', label: 'Clientes' },
    { value: 'reports', label: 'Reportes' },
    { value: 'settings', label: 'Configuración' },
    { value: 'payroll', label: 'Nómina' },
    { value: 'subscriptions', label: 'Suscripciones' },
  ];

  ngOnInit() {
    this.loadTutorials();
  }

  loadTutorials() {
    this.loading.set(true);
    this.service.getAll().subscribe({
      next: (data) => this.tutorials.set(data),
      error: () => this.messageService.add({ severity: 'error', summary: 'Error', detail: 'No se pudieron cargar los tutoriales', life: 3000 }),
      complete: () => this.loading.set(false),
    });
  }

  moduleLabel(value: string): string {
    return this.moduleOptions.find(m => m.value === value)?.label || value;
  }

  openNew() {
    this.form = { module: '', title: '', description: '', video_url: '', thumbnail_url: '', duration: '', order: 0, is_published: true };
    this.submitted = false;
    this.dialogVisible = true;
  }

  editTutorial(tutorial: Tutorial) {
    this.form = { ...tutorial };
    this.submitted = false;
    this.dialogVisible = true;
  }

  hideDialog() {
    this.dialogVisible = false;
    this.submitted = false;
  }

  saveTutorial() {
    this.submitted = true;
    if (!this.form.title || !this.form.module || !this.form.video_url) return;

    this.saving.set(true);
    const obs = this.form.id
      ? this.service.update(this.form.id, this.form)
      : this.service.create(this.form);

    obs.subscribe({
      next: () => {
        this.messageService.add({ severity: 'success', summary: 'Éxito', detail: this.form.id ? 'Tutorial actualizado' : 'Tutorial creado', life: 3000 });
        this.hideDialog();
        this.loadTutorials();
      },
      error: () => this.messageService.add({ severity: 'error', summary: 'Error', detail: 'No se pudo guardar el tutorial', life: 3000 }),
      complete: () => this.saving.set(false),
    });
  }

  deleteTutorial(tutorial: Tutorial) {
    this.confirmationService.confirm({
      message: `¿Estás seguro de eliminar "${tutorial.title}"?`,
      header: 'Confirmar',
      icon: 'pi pi-exclamation-triangle',
      accept: () => {
        if (tutorial.id) {
          this.service.remove(tutorial.id).subscribe({
            next: () => {
              this.messageService.add({ severity: 'success', summary: 'Eliminado', detail: 'Tutorial eliminado', life: 3000 });
              this.loadTutorials();
            },
            error: () => this.messageService.add({ severity: 'error', summary: 'Error', detail: 'No se pudo eliminar', life: 3000 }),
          });
        }
      }
    });
  }
}
