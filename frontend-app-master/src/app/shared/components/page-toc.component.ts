import { Component, Input, signal, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-page-toc',
  standalone: true,
  imports: [CommonModule],
  template: `
    <aside class="hidden xl:block sticky top-24 self-start shrink-0 w-64">
      <div class="rounded-2xl border border-slate-200 bg-white/90 dark:border-slate-700 dark:bg-slate-900/90 p-4 shadow-sm">
        <div class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500 dark:text-slate-400 mb-3">En esta página</div>
        <nav class="space-y-1">
          <a
            *ngFor="let section of sections"
            (click)="scrollTo(section.id)"
            class="block text-sm leading-relaxed cursor-pointer transition px-2 py-1.5 rounded-lg"
            [class.text-violet-700!]="activeSection() === section.id"
            [class.bg-violet-50!]="activeSection() === section.id"
            [class.dark:text-violet-300!]="activeSection() === section.id"
            [class.dark:bg-violet-500/10!]="activeSection() === section.id"
            [class.text-slate-600]="activeSection() !== section.id"
            [class.dark:text-slate-300]="activeSection() !== section.id"
            [class.hover:bg-slate-100]="activeSection() !== section.id"
            [class.dark:hover:bg-slate-800]="activeSection() !== section.id"
          >
            {{ section.label }}
          </a>
        </nav>
      </div>

      <button
        (click)="scrollToTop()"
        *ngIf="showScrollTop()"
        type="button"
        class="mt-3 w-full inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400 dark:hover:border-slate-600 dark:hover:text-white"
      >
        <i class="pi pi-arrow-up text-xs"></i>
        Volver arriba
      </button>
    </aside>

    <button
      (click)="scrollToTop()"
      *ngIf="showScrollTop()"
      type="button"
      class="xl:hidden fixed bottom-6 right-6 z-50 flex h-12 w-12 items-center justify-center rounded-full border border-slate-200 bg-white shadow-lg transition hover:border-slate-300 hover:shadow-xl dark:border-slate-700 dark:bg-slate-900 dark:hover:border-slate-600"
      [style]="{ 'box-shadow': '0 8px 32px -8px rgba(0,0,0,0.15)' }"
    >
      <i class="pi pi-arrow-up text-sm text-slate-600 dark:text-slate-300"></i>
    </button>
  `
})
export class PageTocComponent {
  @Input() sections: { id: string; label: string }[] = [];

  protected activeSection = signal('');
  protected showScrollTop = signal(false);

  @HostListener('window:scroll')
  onScroll() {
    this.showScrollTop.set(window.scrollY > 400);
    for (const section of this.sections) {
      const el = document.getElementById(section.id);
      if (el) {
        const rect = el.getBoundingClientRect();
        if (rect.top <= 120) {
          this.activeSection.set(section.id);
        }
      }
    }
  }

  scrollTo(id: string) {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}
