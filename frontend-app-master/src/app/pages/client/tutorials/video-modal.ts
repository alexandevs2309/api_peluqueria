import { Component, Input, Output, EventEmitter, OnChanges, SimpleChanges } from '@angular/core';
import { DialogModule } from 'primeng/dialog';
import { ButtonModule } from 'primeng/button';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

export interface ChecklistItem {
  id: number | string;
  text: string;
  helperText?: string;
  helperLink?: {
    href: string;
    text: string;
  };
}

function toEmbedUrl(url: string): string {
  try {
    const u = new URL(url);
    if (u.hostname === 'youtu.be') {
      const id = u.pathname.slice(1).split('?')[0];
      return `https://www.youtube-nocookie.com/embed/${id}?autoplay=1`;
    }
    if (u.hostname.includes('youtube.com') || u.hostname.includes('youtube-nocookie.com')) {
      if (u.pathname.startsWith('/shorts/')) {
        const id = u.pathname.split('/')[2];
        return `https://www.youtube-nocookie.com/embed/${id}?autoplay=1`;
      }
      const id = u.searchParams.get('v');
      if (id) return `https://www.youtube-nocookie.com/embed/${id}?autoplay=1`;
    }
    return url;
  } catch {
    return url;
  }
}

@Component({
  selector: 'video-modal',
  standalone: true,
  imports: [DialogModule, ButtonModule],
  template: `
    <p-dialog
      [(visible)]="visible"
      (onHide)="onClose()"
      [modal]="true"
      [closable]="false"
      [draggable]="false"
      [resizable]="false"
      styleClass="video-modal"
      [style]="{ width: isTutorial ? '90vw' : '90vw', maxWidth: isTutorial ? '960px' : '1100px' }">

      @if (isTutorial) {
        <!-- Tutorial mode: full-width video -->
        <div class="relative bg-black rounded-2xl overflow-hidden" style="aspect-ratio: 16 / 9;">
          @if (!resolvedUrl) {
            <div class="absolute inset-0 flex items-center justify-center bg-slate-900">
              <i class="pi pi-spin pi-spinner text-3xl text-white/40"></i>
            </div>
          }
          @if (resolvedUrl) {
            <iframe
              width="100%"
              height="100%"
              [src]="resolvedUrl"
              title="Tutorial"
              frameborder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowfullscreen
              class="absolute inset-0 w-full h-full">
            </iframe>
          }
          <!-- Close button overlay -->
          <button
            (click)="onClose()"
            class="absolute top-3 right-3 z-10 w-9 h-9 flex items-center justify-center rounded-full bg-black/50 text-white/80 hover:bg-black/70 hover:text-white transition-all backdrop-blur-sm border-0 cursor-pointer">
            <i class="pi pi-times text-base"></i>
          </button>
        </div>
      } @else {
        <!-- Landing mode: 2-column checklist + video -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-0">
          <div class="p-6 md:p-8 bg-white dark:bg-gray-900 rounded-t-2xl md:rounded-l-2xl md:rounded-tr-none">
            <div class="flex flex-col h-full">
              <h2 class="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                Comienza en 10 minutos
              </h2>
              <p class="mt-2 text-sm text-slate-500 dark:text-slate-400">
                Ten estos datos listos para un registro rápido
              </p>

              <ul class="mt-6 space-y-5 flex-1">
                @for (item of items; track item.id) {
                  <li
                    class="flex flex-col transition-all duration-300 ease-out"
                    [class.animate-fade-in]="visible"
                    [style.animation-delay]="50 * $index + 'ms'">
                    <div class="flex items-start gap-3">
                      <i class="pi pi-check-circle text-[var(--brand)] text-lg mt-0.5 flex-shrink-0"></i>
                      <span class="text-sm font-medium text-slate-800 dark:text-slate-200">{{ item.text }}</span>
                    </div>
                    @if (item.helperText && item.helperLink) {
                      <div class="ml-8 mt-1 text-xs text-slate-400 dark:text-slate-500">
                        {{ item.helperText }}
                        <a
                          [href]="item.helperLink.href"
                          target="_blank"
                          class="text-[var(--brand)] hover:text-[var(--brand-400)] underline-offset-4 hover:underline transition-colors">
                          {{ item.helperLink.text }}
                        </a>
                      </div>
                    }
                  </li>
                }
              </ul>

              <div class="mt-6 pt-5 border-t border-slate-100 dark:border-slate-800">
                <div class="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500">
                  <i class="pi pi-clock"></i>
                  <span>Duración del demo: 3 minutos</span>
                </div>
              </div>
            </div>
          </div>

          <div class="relative bg-black rounded-b-2xl md:rounded-r-2xl md:rounded-bl-none overflow-hidden flex items-center" style="min-height: 300px;">
            @if (!resolvedUrl) {
              <div class="absolute inset-0 flex items-center justify-center bg-slate-900">
                <i class="pi pi-spin pi-spinner text-3xl text-white/40"></i>
              </div>
            }
            @if (resolvedUrl) {
              <iframe
                width="100%"
                height="100%"
                [src]="resolvedUrl"
                title="Auron Suite Demo"
                frameborder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowfullscreen
                class="absolute inset-0 w-full h-full">
              </iframe>
            }
          </div>
        </div>

        <ng-template pTemplate="footer">
          <div class="flex flex-col sm:flex-row justify-between items-center w-full gap-3">
            <div class="flex gap-3">
              <p-button
                label="Cerrar"
                icon="pi pi-times"
                (onClick)="onClose()"
                severity="secondary"
                [outlined]="true"
                styleClass="!text-xs !px-4">
              </p-button>
              <button
                (click)="onClose(); openSalesModal.emit()"
                class="inline-flex items-center gap-2 px-4 py-2 text-xs font-medium text-slate-600 dark:text-slate-400 border border-slate-300 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors bg-transparent cursor-pointer">
                <i class="pi pi-envelope"></i>
                Hablar con ventas
              </button>
            </div>
            <p-button
              label="Comenzar Prueba Gratis"
              icon="pi pi-arrow-right"
              iconPos="right"
              (onClick)="startTrial()"
              styleClass="!bg-[var(--brand)] !border-0 !text-white !px-5 !py-2 !text-sm !font-semibold !shadow-lg !shadow-[var(--brand)]/25 hover:!bg-[var(--brand-400)] !transition-all !duration-300">
            </p-button>
          </div>
        </ng-template>
      }
    </p-dialog>
  `,
  styles: [`
    ::ng-deep .video-modal .p-dialog-content {
      padding: 0;
      overflow: hidden;
      border-radius: 1rem;
    }

    ::ng-deep .video-modal .p-dialog-header {
      display: none;
    }

    ::ng-deep .video-modal .p-dialog-footer {
      padding: 1rem 1.5rem;
      border-top: 1px solid var(--p-slate-200, #e2e8f0);
      background: white;
    }

    :host-context(.app-dark) ::ng-deep .video-modal .p-dialog-footer {
      border-color: var(--p-slate-800, #1e293b);
      background: #0f172a;
    }

    .animate-fade-in {
      animation: fadeInUp 0.4s ease-out both;
    }

    @keyframes fadeInUp {
      from {
        opacity: 0;
        transform: translateY(8px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    ::ng-deep .video-modal {
      border-radius: 1rem !important;
      overflow: hidden;
    }
  `]
})
export class VideoModal implements OnChanges {
  @Input() visible: boolean = false;
  @Input() videoUrlInput?: string;
  @Output() visibleChange = new EventEmitter<boolean>();
  @Output() openSalesModal = new EventEmitter<void>();

  resolvedUrl: SafeResourceUrl | null = null;
  isTutorial = false;
  private defaultVideoUrl = 'https://www.youtube.com/embed/GSVYJ1KByY0?autoplay=1&mute=1';

  items: ChecklistItem[] = [
    { id: 1, text: 'Registro de empleados con roles y permisos' },
    { id: 2, text: 'Catálogo de servicios con precios y duración' },
    { id: 3, text: 'Inventario de productos con alertas de stock' },
    {
      id: 4,
      text: 'Métodos de pago (efectivo, tarjeta, transferencia)',
      helperText: '¿No tienos los métodos de pago que buscas?',
      helperLink: { href: '#', text: 'Ver opciones disponibles' }
    },
    { id: 5, text: 'Configuración de comisiones por empleado' },
    { id: 6, text: 'Datos bancarios para pagos y nómina' }
  ];

  constructor(private sanitizer: DomSanitizer) {}

  ngOnChanges(changes: SimpleChanges) {
    if (changes['visible'] || changes['videoUrlInput']) {
      if (this.visible) {
        const raw = this.videoUrlInput || this.defaultVideoUrl;
        this.isTutorial = !!this.videoUrlInput;
        this.resolvedUrl = this.sanitizer.bypassSecurityTrustResourceUrl(
          toEmbedUrl(raw)
        );
      } else {
        this.resolvedUrl = null;
        this.isTutorial = false;
      }
    }
  }

  onClose() {
    this.visible = false;
    this.visibleChange.emit(false);
    this.resolvedUrl = null;
  }

  startTrial() {
    this.onClose();
    const pricingSection = document.getElementById('pricing');
    if (pricingSection) {
      pricingSection.scrollIntoView({ behavior: 'smooth' });
    }
  }
}
