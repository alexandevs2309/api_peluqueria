import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../../core/services/auth/auth.service';
import { resolveBusinessRole } from '../../../core/utils/role-normalizer';
import { PeriodsListComponent } from '../payroll/components/periods-list/periods-list.component';
import { MyEarningsComponent } from '../my-earnings/my-earnings.component';
import { I18nPipe } from '../../../core/pipes/i18n.pipe';

@Component({
  selector: 'app-finanzas',
  standalone: true,
  imports: [CommonModule, PeriodsListComponent, MyEarningsComponent, I18nPipe],
  template: `
    @if (isOwnerManager()) {
      <!-- Owner/Manager: Payroll view -->
      <div class="min-h-screen surface-ground p-4 md:p-6 space-y-6">
        <section class="auron-surface-card p-6">
          <div class="flex items-center gap-3 mb-1">
            <div class="w-12 h-12 rounded-2xl bg-[rgba(26,86,219,0.10)] dark:bg-[rgba(26,86,219,0.18)] flex items-center justify-center">
              <i class="pi pi-money-bill text-[var(--brand)] dark:text-[var(--brand-400)] text-xl"></i>
            </div>
            <div>
              <h1 class="display-3 text-surface-900 dark:text-white">{{ 'menu.payroll' | t }}</h1>
              <p class="text-sm text-surface-500 dark:text-surface-400">{{ 'payroll.subtitle' | t }}</p>
            </div>
          </div>
        </section>

        <div class="flex-1 rounded-[1.75rem] border border-surface-200 bg-white shadow-sm dark:border-surface-700 dark:bg-surface-900">
          <app-periods-list></app-periods-list>
        </div>
      </div>
    } @else {
      <!-- Professional: My Earnings view -->
      <app-my-earnings></app-my-earnings>
    }
  `
})
export class FinanzasComponent implements OnInit {
  private authService = inject(AuthService);

  isOwnerManager = signal(false);

  ngOnInit() {
    const user = this.authService.getCurrentUser();
    if (user) {
      const businessRole = resolveBusinessRole(user.role, user.business_role);
      this.isOwnerManager.set(businessRole === 'owner' || businessRole === 'manager');
    }
  }
}
