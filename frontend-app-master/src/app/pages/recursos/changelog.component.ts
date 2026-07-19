import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AppConfigService } from '../../core/services/app-config.service';
import { HttpClient } from '@angular/common/http';

interface ChangelogEntry {
    version: string;
    date: string;
    title: string;
    description: string;
    type: 'feat' | 'fix' | 'security' | 'perf';
    changes: string[];
}

@Component({
    selector: 'app-changelog',
    standalone: true,
    imports: [CommonModule, RouterLink],
    template: `
        <div class="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(26,86,219,0.08),_transparent_45%),linear-gradient(180deg,#f8fafc_0%,#eef2ff_100%)] px-4 py-10 text-slate-900 dark:bg-[radial-gradient(circle_at_top,_rgba(26,86,219,0.14),_transparent_40%),linear-gradient(180deg,#020617_0%,#0f172a_100%)] dark:text-slate-100">
            <div class="mx-auto max-w-4xl space-y-8">
                <!-- Back Link -->
                <a
                    routerLink="/"
                    class="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.3em] text-slate-500 transition hover:text-slate-950 dark:text-slate-400 dark:hover:text-white"
                >
                    <span class="h-2 w-2 rounded-full bg-[var(--brand)]"></span>
                    Volver a {{ appConfig.platformName() }}
                </a>

                <!-- Header Banner -->
                <section class="rounded-[32px] border border-white/70 bg-white/90 p-8 shadow-[0_28px_90px_-50px_rgba(15,23,42,0.35)] backdrop-blur dark:border-slate-800/80 dark:bg-slate-950/75">
                    <h1 class="mt-5 text-4xl font-extrabold tracking-tight text-slate-900 dark:text-white">
                        Historial de Versiones (Changelog)
                    </h1>
                    <p class="mt-4 max-w-3xl text-base leading-relaxed text-slate-600 dark:text-slate-300">
                        Entérate de las últimas mejoras, correcciones y nuevas funcionalidades que hemos implementado en la plataforma {{ appConfig.platformName() }}.
                    </p>
                </section>

                <!-- Changelog Timeline -->
                <div class="relative border-l border-slate-200 dark:border-slate-800 pl-8 ml-4 space-y-12">
                    <article *ngFor="let item of changelog()" class="relative">
                        <!-- Bullet point timeline icon -->
                        <div
                            class="absolute -left-[41px] top-1 h-6 w-6 rounded-full border-4 border-slate-50 dark:border-slate-950 flex items-center justify-center shadow-sm"
                            [class]="item.type === 'feat' ? 'bg-blue-500' : item.type === 'fix' ? 'bg-amber-500' : item.type === 'security' ? 'bg-rose-500' : 'bg-emerald-500'"
                        ></div>

                        <!-- Date and version -->
                        <div class="flex items-center gap-3">
                            <span class="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">{{ item.date }}</span>
                            <span
                                class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider"
                                [class]="item.type === 'feat' ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400' : item.type === 'fix' ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400' : item.type === 'security' ? 'bg-rose-500/10 text-rose-600 dark:text-rose-400' : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'"
                            >
                                {{ item.type === 'feat' ? 'Nueva Feature' : item.type === 'fix' ? 'Corrección' : item.type === 'security' ? 'Seguridad' : 'Rendimiento' }}
                            </span>
                            <span class="text-xs font-bold text-slate-500 dark:text-slate-400">{{ item.version }}</span>
                        </div>

                        <!-- Title and details -->
                        <h3 class="mt-3 text-xl font-bold text-slate-900 dark:text-white">{{ item.title }}</h3>
                        <p class="mt-2 text-sm text-slate-600 dark:text-slate-300 leading-relaxed">{{ item.description }}</p>

                        <!-- Change bullets -->
                        <ul class="mt-4 space-y-2 list-disc list-inside text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                            <li *ngFor="let change of item.changes">{{ change }}</li>
                        </ul>
                    </article>
                </div>
            </div>
        </div>
    `
})
export class ChangelogComponent implements OnInit {
    private readonly http = inject(HttpClient);
    changelog = signal<ChangelogEntry[]>([]);

    constructor(public appConfig: AppConfigService) {}

    ngOnInit(): void {
        this.http.get<ChangelogEntry[]>('assets/changelog.json').subscribe({
            next: (data) => this.changelog.set(data),
            error: (err) => console.error('Error al cargar changelog', err)
        });
    }
}
