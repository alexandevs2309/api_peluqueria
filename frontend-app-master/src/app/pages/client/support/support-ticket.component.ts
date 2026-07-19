import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { TextareaModule } from 'primeng/textarea';
import { SelectModule } from 'primeng/select';
import { ToastModule } from 'primeng/toast';
import { TagModule } from 'primeng/tag';
import { DialogModule } from 'primeng/dialog';
import { MessageService } from 'primeng/api';
import { SupportTicketService, SupportTicket } from '../../../core/services/support/support-ticket.service';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { AuthService } from '../../../core/services/auth/auth.service';
import { AuBtn } from '../../../shared/components';

@Component({
  selector: 'app-support-ticket',
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    CardModule, ButtonModule, InputTextModule,
    TextareaModule,
    SelectModule,
    ToastModule,
    TagModule,
    DialogModule,
    AuBtn,
  ],
  providers: [MessageService],
  template: `
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 p-4 md:p-6">
      <div class="lg:col-span-2">
        <p-card header="Mis Tickets">
          @if (loading()) {
            <div class="text-center py-8 text-gray-500 dark:text-gray-400">Cargando...</div>
          } @else if (tickets().length === 0) {
            <div class="text-center py-12">
              <i class="pi pi-ticket text-4xl text-gray-300 dark:text-gray-600 mb-3"></i>
              <p class="text-gray-500 dark:text-gray-400">No tienes tickets de soporte</p>
            </div>
          } @else {
            <div class="space-y-3">
              @for (ticket of tickets(); track ticket.id) {
                <div class="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-pointer"
                     (click)="selectedTicket.set(ticket)">
                  <div class="min-w-0 flex-1">
                    <div class="font-medium text-gray-900 dark:text-white truncate">{{ ticket.subject }}</div>
                    <div class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                      {{ ticket.created_at | date:'short' }} — {{ ticket.created_by_name }}
                    </div>
                  </div>
                  <div class="flex items-center gap-2 shrink-0 ml-4">
                    <p-tag [value]="statusLabel(ticket.status)" [severity]="statusSeverity(ticket.status)" />
                    <p-tag [value]="priorityLabel(ticket.priority)" [severity]="prioritySeverity(ticket.priority)" />
                  </div>
                </div>
              }
            </div>
          }
        </p-card>
      </div>

      <div>
        <p-card header="Abrir nuevo ticket">
          <form #ticketForm="ngForm" (ngSubmit)="submitTicket()" class="space-y-4">
            <div>
              <label class="block font-medium text-sm text-gray-700 dark:text-gray-300 mb-1">Asunto</label>
              <input pInputText name="subject" [(ngModel)]="newSubject" required
                     class="w-full" placeholder="Resumen del problema" />
            </div>
            <div>
              <label class="block font-medium text-sm text-gray-700 dark:text-gray-300 mb-1">Prioridad</label>
              <p-select name="priority" [options]="priorityOptions" [(ngModel)]="newPriority"
                        optionLabel="label" optionValue="value" class="w-full"
                        placeholder="Selecciona prioridad">
              </p-select>
            </div>
            <div>
              <label class="block font-medium text-sm text-gray-700 dark:text-gray-300 mb-1">Descripción</label>
              <textarea pInputTextarea name="description" [(ngModel)]="newDescription" required
                        class="w-full" rows="5" placeholder="Describe tu problema en detalle..."></textarea>
            </div>
            <button au-btn variant="primary" icon="pi pi-send"
                    type="submit" [loading]="saving()" [disabled]="!!ticketForm.invalid"
                    class="w-full">Enviar ticket</button>
          </form>
        </p-card>
      </div>
    </div>

    @if (selectedTicket(); as ticket) {
      <p-dialog [header]="ticket.subject" [(visible)]="showDetail" [modal]="true"
                [style]="{width: '600px'}" [breakpoints]="{'960px':'75vw','640px':'100vw'}" (onHide)="selectedTicket.set(null)">
        <div class="space-y-4">
          <div class="flex gap-2">
            <p-tag [value]="statusLabel(ticket.status)" [severity]="statusSeverity(ticket.status)" />
            <p-tag [value]="priorityLabel(ticket.priority)" [severity]="prioritySeverity(ticket.priority)" />
          </div>
          <div class="rounded-xl border border-surface-200 dark:border-surface-700 p-4">
            <div class="text-xs font-semibold uppercase tracking-wider text-surface-400 mb-2">Tu solicitud</div>
            <p class="text-gray-700 dark:text-gray-300 whitespace-pre-wrap text-sm leading-relaxed">{{ ticket.description }}</p>
          </div>

          <!-- Admin Reply -->
          @if (ticket.admin_reply) {
            <div class="rounded-xl border border-green-200 bg-green-50 dark:border-green-900/50 dark:bg-green-900/10 p-4">
              <div class="flex items-center gap-2 mb-2">
                <i class="pi pi-headphones text-green-600 dark:text-green-400"></i>
                <span class="text-xs font-semibold uppercase tracking-wider text-green-700 dark:text-green-300">Respuesta del soporte</span>
                @if (ticket.replied_at) {
                  <span class="text-xs text-green-500 ml-auto">{{ ticket.replied_at | date:'dd/MM/yy HH:mm' }}</span>
                }
              </div>
              <p class="text-sm text-green-800 dark:text-green-200 whitespace-pre-wrap leading-relaxed">{{ ticket.admin_reply }}</p>
            </div>
          } @else {
            <div class="rounded-xl border border-dashed border-surface-300 dark:border-surface-600 p-4 text-center">
              <i class="pi pi-clock text-surface-400 mb-1 block"></i>
              <p class="text-xs text-surface-400">Tu ticket está siendo revisado. Te notificaremos por email cuando el soporte responda.</p>
            </div>
          }

          <div class="text-sm text-gray-500 dark:text-gray-400">
            Creado: {{ ticket.created_at | date:'medium' }}<br/>
            Actualizado: {{ ticket.updated_at | date:'medium' }}
          </div>
          @if (canClose(ticket)) {
            <button au-btn variant="secondary" icon="pi pi-check"
                    (click)="closeTicket(ticket)">Cerrar ticket</button>
          }
        </div>
      </p-dialog>
    }

    <p-toast />
  `,
  styles: [`
    :host { display: block; }
  `]
})
export class SupportTicketComponent implements OnInit {
  private readonly service = inject(SupportTicketService);
  private readonly messageService = inject(MessageService);
  private readonly localeService = inject(LocaleService);
  private readonly authService = inject(AuthService);

  tickets = signal<SupportTicket[]>([]);
  loading = signal(false);
  saving = signal(false);
  selectedTicket = signal<SupportTicket | null>(null);

  newSubject = '';
  newDescription = '';
  newPriority = 'normal';

  readonly priorityOptions = [
    { label: 'Baja', value: 'low' },
    { label: 'Normal', value: 'normal' },
    { label: 'Alta', value: 'high' },
    { label: 'Urgente', value: 'urgent' },
  ];

  get showDetail(): boolean {
    return this.selectedTicket() !== null;
  }
  set showDetail(v: boolean) {
    if (!v) this.selectedTicket.set(null);
  }

  ngOnInit() {
    this.loadTickets();
  }

  loadTickets() {
    this.loading.set(true);
    this.service.getMyTickets().subscribe({
      next: (tickets) => this.tickets.set(tickets),
      error: () => this.messageService.add({ severity: 'error', summary: 'Error', detail: 'No se pudieron cargar los tickets' }),
      complete: () => this.loading.set(false),
    });
  }

  submitTicket() {
    if (!this.newSubject || !this.newDescription) return;
    this.saving.set(true);
    this.service.createTicket({
      subject: this.newSubject,
      description: this.newDescription,
      priority: this.newPriority as SupportTicket['priority'],
    }).subscribe({
      next: () => {
        this.messageService.add({ severity: 'success', summary: 'Enviado', detail: 'Ticket creado con éxito' });
        this.newSubject = '';
        this.newDescription = '';
        this.newPriority = 'normal';
        this.loadTickets();
      },
      error: () => this.messageService.add({ severity: 'error', summary: 'Error', detail: 'No se pudo crear el ticket' }),
      complete: () => this.saving.set(false),
    });
  }

  canClose(ticket: SupportTicket): boolean {
    if (ticket.status === 'closed') return false;
    const user = this.authService.getCurrentUser();
    if (!user) return false;
    const isOwnerOrAdmin = ['CLIENT_ADMIN', 'SUPER_ADMIN', 'Client-Admin', 'SuperAdmin', 'owner'].includes(user.role);
    if (isOwnerOrAdmin) return true;
    return ticket.created_by === user.id;
  }

  closeTicket(ticket: SupportTicket) {
    this.service.closeTicket(ticket.id).subscribe({
      next: () => {
        this.messageService.add({ severity: 'success', summary: 'Cerrado', detail: 'Ticket cerrado' });
        this.selectedTicket.set({ ...ticket, status: 'closed' });
        this.loadTickets();
      },
      error: () => this.messageService.add({ severity: 'error', summary: 'Error', detail: 'No se pudo cerrar el ticket' }),
    });
  }

  statusLabel(s: string): string {
    const m: Record<string, string> = { open: 'Abierto', in_progress: 'En progreso', resolved: 'Resuelto', closed: 'Cerrado' };
    return m[s] || s;
  }

  statusSeverity(s: string): 'warn' | 'info' | 'success' | 'secondary' {
    const m: Record<string, 'warn' | 'info' | 'success' | 'secondary'> = {
      open: 'warn', in_progress: 'info', resolved: 'success', closed: 'secondary',
    };
    return m[s] || 'info';
  }

  priorityLabel(p: string): string {
    const m: Record<string, string> = { low: 'Baja', normal: 'Normal', high: 'Alta', urgent: 'Urgente' };
    return m[p] || p;
  }

  prioritySeverity(p: string): 'success' | 'info' | 'warn' | 'danger' {
    const m: Record<string, 'success' | 'info' | 'warn' | 'danger'> = {
      low: 'success', normal: 'info', high: 'warn', urgent: 'danger',
    };
    return m[p] || 'info';
  }

  t(key: string): string {
    return this.localeService.t(key as any);
  }
}
