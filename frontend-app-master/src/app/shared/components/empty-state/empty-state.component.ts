import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ButtonModule } from 'primeng/button';
import { I18nPipe } from '../../../core/pipes/i18n.pipe';

@Component({
  selector: 'app-empty-state',
  standalone: true,
  imports: [CommonModule, ButtonModule, I18nPipe],
  template: `
    <div class="flex flex-col items-center justify-center p-8 text-center bg-surface-card rounded-2xl border border-surface-200 dark:border-surface-800 shadow-sm max-w-lg mx-auto my-6 animate-fade-in">
      <!-- Ilustración SVG Abstracta de Software/Datos -->
      <div class="mb-6 flex justify-center items-center w-24 h-24 rounded-full bg-[#FAF8F6] dark:bg-[#2A2724] border border-[#EBE6E0] dark:border-[#3E3A36]">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <!-- Fondo de tarjeta superior -->
          <rect x="3" y="4" width="18" height="14" rx="2" fill="var(--surface-50, #FAF8F6)" stroke="#C8674A" stroke-width="1.5" />
          <!-- Líneas de datos simulando una tabla o lista vacía -->
          <line x1="6" y1="8" x2="14" y2="8" stroke="#D4A84B" stroke-width="1.5" stroke-linecap="round" />
          <line x1="6" y1="11" x2="18" y2="11" stroke="#EBE6E0" stroke-width="1.5" stroke-linecap="round" />
          <line x1="6" y1="14" x2="11" y2="14" stroke="#EBE6E0" stroke-width="1.5" stroke-linecap="round" />
          
          <!-- Elemento decorativo circular (simula un gráfico o indicador) -->
          <circle cx="16" cy="14" r="2.5" fill="none" stroke="#C8674A" stroke-width="1.5" />
          <!-- Indicador de estado vacío central -->
          <path d="M11 18H13" stroke="#C8674A" stroke-width="1.5" stroke-linecap="round" />
        </svg>
      </div>

      <!-- Título de Estado Vacío -->
      <h3 class="font-display text-xl font-semibold text-surface-900 dark:text-surface-50 mb-2">
        {{ title | t }}
      </h3>

      <!-- Descripción Contextual -->
      <p class="text-sm text-surface-500 dark:text-surface-400 max-w-sm mb-6 leading-relaxed">
        {{ description | t }}
      </p>

      <!-- Botón de Acción Principal (CTA) -->
      @if (actionLabel) {
        <button 
          pButton 
          type="button" 
          [label]="actionLabel | t" 
          icon="pi pi-plus" 
          class="p-button-primary px-5 py-2.5 rounded-xl font-medium shadow-sm transition-all duration-200 hover:-translate-y-0.5" 
          (click)="onAction()">
        </button>
      }
    </div>
  `,
  styles: [`
    .animate-fade-in {
      animation: fadeIn 0.4s ease-out;
    }
    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: translateY(10px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
  `]
})
export class EmptyStateComponent {
  @Input() title: string = '';
  @Input() description: string = '';
  @Input() actionLabel?: string;
  @Output() actionClicked = new EventEmitter<void>();

  onAction(): void {
    this.actionClicked.emit();
  }
}
