import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AppConfigService } from '../../core/services/app-config.service';

interface ServiceStatus {
    name: string;
    description: string;
    uptime: string;
    status: 'operational' | 'degraded' | 'down';
    history: number[]; // 1 for ok, 2 for degraded, 3 for down
}

@Component({
    selector: 'app-status',
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

                <!-- Main Status Banner -->
                <section class="rounded-[32px] border border-white/70 bg-white/90 p-8 shadow-[0_28px_90px_-50px_rgba(15,23,42,0.35)] backdrop-blur dark:border-slate-800/80 dark:bg-slate-950/75">
                    <div class="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
                        <div>
                            <span class="text-xs font-bold uppercase tracking-[0.2em] text-emerald-500">Monitoreo de Infraestructura</span>
                            <h1 class="mt-2 text-4xl font-extrabold tracking-tight text-slate-900 dark:text-white">
                                Estado del Sistema
                            </h1>
                            <p class="mt-2 text-sm text-slate-600 dark:text-slate-300">
                                Estado operativo de los servicios principales de {{ appConfig.platformName() }}.
                            </p>
                        </div>
                        <div class="inline-flex items-center gap-2.5 px-4 py-2.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-sm font-bold shadow-sm shrink-0">
                            <span class="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
                            Todos los sistemas operativos
                        </div>
                    </div>
                </section>

                <!-- Detailed Services list -->
                <div class="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900/80 space-y-8">
                    <h2 class="text-xl font-bold text-slate-900 dark:text-white">Estado por Componente</h2>

                    <div class="space-y-6">
                        <div *ngFor="let svc of services" class="space-y-3">
                            <!-- Service Info Header -->
                            <div class="flex items-center justify-between">
                                <div>
                                    <h4 class="font-bold text-sm text-slate-900 dark:text-white">{{ svc.name }}</h4>
                                    <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{{ svc.description }}</p>
                                </div>
                                <div class="flex items-center gap-2">
                                    <span class="text-xs font-semibold text-slate-400 dark:text-slate-500 mr-2">Uptime: {{ svc.uptime }}</span>
                                    <span
                                        class="px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider"
                                        [class]="svc.status === 'operational'
                                            ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                                            : svc.status === 'degraded'
                                                ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                                                : 'bg-rose-500/10 text-rose-600 dark:text-rose-400'"
                                    >
                                        {{ svc.status === 'operational' ? 'Operativo' : svc.status === 'degraded' ? 'Degradado' : 'Caído' }}
                                    </span>
                                </div>
                            </div>

                            <!-- 90 Days Uptime Bars Visualization (Statuspage style) -->
                            <div class="flex items-center gap-0.5 h-6">
                                <div
                                    *ngFor="let statusVal of svc.history"
                                    class="flex-1 h-full rounded-sm transition-all duration-200 hover:scale-y-125"
                                    [class]="statusVal === 1
                                        ? 'bg-emerald-500/85 hover:bg-emerald-400'
                                        : statusVal === 2
                                            ? 'bg-amber-500 hover:bg-amber-400'
                                            : 'bg-rose-500 hover:bg-rose-400'"
                                    [attr.title]="statusVal === 1 ? 'Sin incidencias' : statusVal === 2 ? 'Rendimiento degradado' : 'Interrupción del servicio'"
                                ></div>
                            </div>

                            <!-- Timeline markers -->
                            <div class="flex items-center justify-between text-[10px] text-slate-400 dark:text-slate-500">
                                <span>Hace 90 días</span>
                                <span class="w-16 h-px bg-slate-200 dark:bg-slate-800"></span>
                                <span>100% operativo hoy</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Incident History -->
                <section class="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
                    <h2 class="text-xl font-bold text-slate-900 dark:text-white mb-4">Historial de Incidentes</h2>
                    <div class="space-y-4">
                        <div class="border-l-2 border-emerald-500 pl-4 py-1">
                            <span class="text-xs text-slate-500 dark:text-slate-400 font-semibold">10 de Julio, 2026</span>
                            <h4 class="font-bold text-sm text-slate-900 dark:text-white mt-1">Mantenimiento de Servidores Planificado</h4>
                            <p class="text-xs text-slate-600 dark:text-slate-300 mt-1 leading-relaxed">
                                Se aplicaron optimizaciones en los motores de base de datos Postgres y optimizaciones en la indexación de búsqueda rápida de inquilinos. El mantenimiento duró 8 minutos y no reportó interrupción.
                            </p>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    `
})
export class StatusComponent {
    services: ServiceStatus[] = [
        {
            name: 'Plataforma Web (Frontend)',
            description: 'Acceso a la interfaz de usuario en producción y componentes de carga estática.',
            uptime: '99.98%',
            status: 'operational',
            history: this.generateHistory(1)
        },
        {
            name: 'Servidor de API Core',
            description: 'Servicio encargado de procesar solicitudes REST de clientes, agendas y transacciones.',
            uptime: '99.95%',
            status: 'operational',
            history: this.generateHistory(2)
        },
        {
            name: 'Base de Datos Principal',
            description: 'Instancia PostgreSQL dedicada con aislamiento multi-inquilino.',
            uptime: '100.00%',
            status: 'operational',
            history: this.generateHistory(0) // 100% operational
        },
        {
            name: 'Motor de Notificaciones',
            description: 'Procesamiento y colas de entrega de recordatorios automáticos y correos transaccionales.',
            uptime: '99.91%',
            status: 'operational',
            history: this.generateHistory(3)
        }
    ];

    constructor(public appConfig: AppConfigService) {}

    // Generates a mock history of 90 days. 
    // faultLevel controls how many warnings/alerts to seed: 
    // 0 = perfect, 1 = slight warning, 2 = warning + small downtime, 3 = more warnings.
    generateHistory(faultLevel: number): number[] {
        const history: number[] = [];
        for (let i = 0; i < 90; i++) {
            let val = 1; // Operational
            const rand = Math.random();
            if (faultLevel === 1 && i === 45) {
                val = 2; // Degradado
            } else if (faultLevel === 2) {
                if (i === 12) val = 3; // Down
                else if (i === 13 || i === 45) val = 2; // Degraded
            } else if (faultLevel === 3) {
                if (i === 5 || i === 70) val = 3;
                else if (i === 6 || i === 71 || i === 30) val = 2;
            }
            history.push(val);
        }
        return history;
    }
}
