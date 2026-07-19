import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';

@Component({
  selector: 'auron-pagination',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (totalRecords > pageSize) {
      <div class="flex flex-col gap-3 border-t border-surface-100 px-4 py-3 text-sm dark:border-surface-800 sm:flex-row sm:items-center sm:justify-between">
        <div class="flex items-center gap-2 text-surface-500 dark:text-surface-400">
          <span>{{ showingLabel }}</span>
          <select
            [value]="pageSize"
            (change)="onPageSizeChange($event)"
            class="rounded-md border border-surface-200 bg-surface-0 px-2 py-1 text-sm dark:border-surface-700 dark:bg-surface-800"
          >
            @for (size of pageSizeOptions; track size) {
              <option [value]="size">{{ size }}</option>
            }
          </select>
        </div>

        <div class="flex items-center gap-3">
          <span class="text-surface-500 dark:text-surface-400">{{ pageLabel }}</span>
          <button
            type="button"
            (click)="pageChange.emit(currentPage - 1)"
            [disabled]="currentPage === 0"
            class="inline-flex items-center rounded-lg border border-surface-200 bg-surface-0 px-3 py-1.5 text-sm font-medium text-surface-700 shadow-sm hover:bg-surface-50 disabled:opacity-50 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:hover:bg-surface-700"
          >
            Anterior
          </button>
          <button
            type="button"
            (click)="pageChange.emit(currentPage + 1)"
            [disabled]="currentPage >= totalPages - 1"
            class="inline-flex items-center rounded-lg border border-surface-200 bg-surface-0 px-3 py-1.5 text-sm font-medium text-surface-700 shadow-sm hover:bg-surface-50 disabled:opacity-50 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:hover:bg-surface-700"
          >
            Siguiente
          </button>
        </div>
      </div>
    }
  `,
})
export class AuronPaginationComponent {
  @Input({ required: true }) currentPage = 0;
  @Input({ required: true }) totalPages = 1;
  @Input({ required: true }) pageSize = 10;
  @Input({ required: true }) totalRecords = 0;
  @Input() firstRecord = 0;
  @Input() lastRecord = 0;
  @Input() showingLabel = '';
  @Input() pageLabel = '';
  @Input() pageSizeOptions: number[] = [10, 25, 50];

  @Output() pageChange = new EventEmitter<number>();
  @Output() pageSizeChange = new EventEmitter<number>();

  onPageSizeChange(event: Event): void {
    this.pageSizeChange.emit(Number((event.target as HTMLSelectElement).value));
  }
}
