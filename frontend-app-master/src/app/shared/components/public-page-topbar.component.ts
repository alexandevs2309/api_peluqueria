import { CommonModule, Location } from '@angular/common';
import { Component, inject } from '@angular/core';
import { RouterModule, Router } from '@angular/router';
import { AppConfigService } from '../../core/services/app-config.service';
import { LayoutService } from '../../layout/service/layout.service';

@Component({
    selector: 'app-public-page-topbar',
    standalone: true,
    imports: [CommonModule, RouterModule],
    template: `
        <section class="mb-6 border-b border-slate-200/80 bg-white/82 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/82">
            <div class="mx-auto flex max-w-6xl flex-col gap-3 px-6 py-4 sm:flex-row sm:items-center sm:justify-between lg:px-8">
                <div class="flex items-center gap-3">
                    <button
                        type="button"
                        (click)="goBack()"
                        class="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:text-slate-950 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:border-slate-600 dark:hover:text-white"
                    >
                        <span class="h-2 w-2 rounded-full bg-violet-500"></span>
                        Atrás
                    </button>

                    <a
                        routerLink="/"
                        class="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:text-slate-950 dark:border-slate-700 dark:bg-slate-900/70 dark:text-slate-200 dark:hover:border-slate-600 dark:hover:text-white"
                    >
                        Landing
                    </a>
                </div>

                <div class="flex items-center gap-3">
                    <span class="truncate text-sm font-semibold uppercase tracking-[0.22em] text-slate-500 dark:text-slate-400">
                        {{ appConfig.platformName() }}
                    </span>

                    <button
                        type="button"
                        (click)="layout.toggleTheme()"
                        [attr.aria-label]="layout.isDarkTheme() ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'"
                        [title]="layout.isDarkTheme() ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'"
                        class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-700 transition hover:border-slate-300 hover:text-slate-950 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:border-slate-600 dark:hover:text-white"
                    >
                        <i
                            [ngClass]="{
                                'pi': true,
                                'pi-moon': layout.isDarkTheme(),
                                'pi-sun': !layout.isDarkTheme()
                            }"
                        ></i>
                    </button>
                </div>
            </div>
        </section>
    `
})
export class PublicPageTopbarComponent {
    readonly appConfig = inject(AppConfigService);
    readonly layout = inject(LayoutService);
    private readonly location = inject(Location);
    private readonly router = inject(Router);

    goBack(): void {
        if (typeof window !== 'undefined' && window.history.length > 1) {
            this.location.back();
            return;
        }

        void this.router.navigateByUrl('/');
    }
}
