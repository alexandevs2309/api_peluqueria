import { Component, Input } from '@angular/core';
import { NgClass } from '@angular/common';

@Component({
  selector: 'app-metric-card',
  standalone: true,
  imports: [NgClass],
  template: `
    <div class="surface-card shadow-2 p-3 border-1 border-round">
      <div class="flex justify-content-between mb-3">
        <div>
          <span class="block text-color-secondary font-medium mb-3">{{ title }}</span>
          <div class="text-color font-medium text-xl">{{ formattedValue }}</div>
        </div>
        <div class="flex align-items-center justify-content-center border-round" 
             [ngClass]="iconBackgroundClass" 
             style="width:2.5rem;height:2.5rem">
          <i [ngClass]="iconClass" class="text-xl"></i>
        </div>
      </div>
      @if (subtitle) {
        <div class="text-color-secondary text-sm">{{ subtitle }}</div>
      }
    </div>
  `,
  styles: [`
    .icon-success {
      color: var(--success-color) !important;
    }
    .icon-danger {
      color: var(--danger-color) !important;
    }
    .icon-warning {
      color: var(--warning-color) !important;
    }
    .icon-info {
      color: var(--primary-color) !important;
    }
    .bg-success {
      background-color: color-mix(in srgb, var(--success-color) 15%, transparent) !important;
    }
    .bg-danger {
      background-color: color-mix(in srgb, var(--danger-color) 15%, transparent) !important;
    }
    .bg-warning {
      background-color: color-mix(in srgb, var(--warning-color) 15%, transparent) !important;
    }
    .bg-info {
      background-color: color-mix(in srgb, var(--primary-color) 15%, transparent) !important;
    }
  `]
})
export class MetricCardComponent {
  @Input() title: string = '';
  @Input() value: number | string = 0;
  @Input() icon: string = 'pi-info-circle';
  @Input() severity: 'success' | 'danger' | 'warning' | 'info' = 'info';
  @Input() format: 'number' | 'currency' | 'percentage' | 'text' = 'number';
  @Input() subtitle?: string;

  // Backward compatibility
  @Input() set color(value: 'blue' | 'green' | 'orange' | 'purple' | 'red') {
    const colorToSeverityMap = {
      'green': 'success',
      'red': 'danger',
      'orange': 'warning',
      'blue': 'info',
      'purple': 'info'
    } as const;
    this.severity = colorToSeverityMap[value] || 'info';
  }

  get formattedValue(): string {
    if (typeof this.value === 'string') return this.value;
    
    switch (this.format) {
      case 'currency':
        return `$${this.value.toLocaleString()}`;
      case 'percentage':
        return `${this.value}%`;
      case 'text':
        return this.value.toString();
      default:
        return this.value.toLocaleString();
    }
  }

  get iconClass(): string {
    return `pi ${this.icon} icon-${this.severity}`;
  }

  get iconBackgroundClass(): string {
    return `bg-${this.severity}`;
  }
}