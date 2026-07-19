import { CommonModule } from '@angular/common';
import { Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AppConfigService } from '../../core/services/app-config.service';

interface DocSection {
    id: string;
    title: string;
    icon: string;
    content: {
        subtitle: string;
        steps: { title: string; desc: string }[];
        tips?: string[];
    };
}

@Component({
    selector: 'app-docs',
    standalone: true,
    imports: [CommonModule, RouterLink],
    template: `
        <div class="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(26,86,219,0.08),_transparent_45%),linear-gradient(180deg,#f8fafc_0%,#eef2ff_100%)] px-4 py-10 text-slate-900 dark:bg-[radial-gradient(circle_at_top,_rgba(26,86,219,0.14),_transparent_40%),linear-gradient(180deg,#020617_0%,#0f172a_100%)] dark:text-slate-100">
            <div class="mx-auto max-w-6xl space-y-8">
                <!-- Back Link -->
                <a
                    routerLink="/"
                    class="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.3em] text-slate-500 transition hover:text-slate-950 dark:text-slate-400 dark:hover:text-white"
                >
                    <span class="h-2 w-2 rounded-full bg-[var(--brand)]"></span>
                    Volver a {{ appConfig.platformName() }}
                </a>

                <!-- Main Header -->
                <section class="rounded-[32px] border border-white/70 bg-white/90 p-8 shadow-[0_28px_90px_-50px_rgba(15,23,42,0.35)] backdrop-blur dark:border-slate-800/80 dark:bg-slate-950/75">
                    <div class="max-w-3xl">
                        <span class="text-xs font-bold uppercase tracking-[0.2em] text-[var(--brand)]">Soporte y Aprendizaje</span>
                        <h1 class="mt-4 text-4xl font-extrabold tracking-tight text-slate-900 dark:text-white sm:text-5xl">
                            Centro de Documentación
                        </h1>
                        <p class="mt-4 text-base leading-relaxed text-slate-600 dark:text-slate-300">
                            Aprende a configurar tu barbería o salón de belleza desde cero, automatizar la comunicación con tus clientes y gestionar tus finanzas sin complicaciones.
                        </p>
                    </div>
                </section>

                <!-- Navigation Tabs and Content Grid -->
                <div class="grid gap-8 lg:grid-cols-[280px,1fr]">
                    <!-- Sidebar Navigation -->
                    <aside class="space-y-2">
                        <button
                            *ngFor="let sec of sections"
                            (click)="activeSection.set(sec.id)"
                            class="w-full text-left px-5 py-3.5 rounded-2xl text-sm font-semibold transition-all duration-200 flex items-center gap-3"
                            [class]="activeSection() === sec.id
                                ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/25'
                                : 'bg-white/50 border border-slate-200/50 hover:bg-white dark:bg-slate-900/40 dark:border-slate-800/50 dark:hover:bg-slate-900 text-slate-600 dark:text-slate-300'"
                        >
                            <span class="text-lg">{{ sec.icon }}</span>
                            {{ sec.title }}
                        </button>
                    </aside>

                    <!-- Document Content -->
                    <main class="rounded-[32px] border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
                        <div *ngIf="getActiveSectionData() as secData" class="space-y-6">
                            <div>
                                <h2 class="text-2xl font-bold text-slate-900 dark:text-white">{{ secData.title }}</h2>
                                <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">{{ secData.content.subtitle }}</p>
                            </div>

                            <hr class="border-slate-100 dark:border-slate-800" />

                            <!-- Steps -->
                            <div class="space-y-8">
                                <div *ngFor="let step of secData.content.steps; let idx = index" class="relative pl-10">
                                    <!-- Bullet Number -->
                                    <div class="absolute left-0 top-0.5 w-7 h-7 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-xs font-bold text-blue-600 dark:text-blue-400">
                                        {{ idx + 1 }}
                                    </div>
                                    <h3 class="font-bold text-base text-slate-900 dark:text-white">{{ step.title }}</h3>
                                    <p class="mt-2 text-sm text-slate-600 dark:text-slate-300 leading-relaxed">{{ step.desc }}</p>
                                </div>
                            </div>

                            <!-- Tips -->
                            <div *ngIf="secData.content.tips && secData.content.tips.length" class="mt-8 p-6 rounded-2xl bg-amber-500/[0.04] border border-amber-500/20 text-slate-700 dark:text-slate-300">
                                <h4 class="font-bold text-sm text-amber-600 dark:text-amber-400 flex items-center gap-2 mb-2">
                                    💡 Consejos útiles e información importante
                                </h4>
                                <ul class="list-disc list-inside text-xs space-y-1.5 leading-relaxed">
                                    <li *ngFor="let tip of secData.content.tips">{{ tip }}</li>
                                </ul>
                            </div>
                        </div>
                    </main>
                </div>
            </div>
        </div>
    `
})
export class DocsComponent {
    activeSection = signal('primeros-pasos');

    sections: DocSection[] = [
        {
            id: 'primeros-pasos',
            title: 'Configuración Inicial',
            icon: '🚀',
            content: {
                subtitle: 'Configura la base de tu salón en menos de 5 minutos.',
                steps: [
                    {
                        title: 'Añadir los detalles del Negocio',
                        desc: 'Ve a Ajustes > Perfil de Negocio. Sube tu logotipo, define el nombre comercial, el número de contacto principal y la moneda predeterminada.'
                    },
                    {
                        title: 'Crear Sucursales (Multi-sucursal)',
                        desc: 'Si cuentas con más de un establecimiento, puedes registrar cada sucursal en el panel de Sucursales. Cada una mantendrá su inventario, caja y personal de forma independiente.'
                    },
                    {
                        title: 'Establecer Horarios y Días Laborables',
                        desc: 'Define las horas de apertura y cierre generales, así como los descansos programados. Esto evitará que los clientes agenden citas fuera de horario.'
                    }
                ],
                tips: [
                    'Asegúrate de que la zona horaria del negocio esté configurada correctamente para evitar desfasamientos en los recordatorios.',
                    'El logotipo del negocio se utilizará automáticamente en tus comprobantes de pago del POS.'
                ]
            }
        },
        {
            id: 'agenda-citas',
            title: 'Calendario y Citas',
            icon: '📅',
            content: {
                subtitle: 'Gestiona la ocupación de tus colaboradores con facilidad.',
                steps: [
                    {
                        title: 'Crear Categorías y Servicios',
                        desc: 'Registra los servicios que ofreces (ej. Corte, Tintura, Manicura) especificando su precio, duración estimada y el personal capacitado para realizarlo.'
                    },
                    {
                        title: 'Agendar una Cita desde el Calendario',
                        desc: 'Haz clic en cualquier celda de tiempo vacía en el calendario. Selecciona al cliente, el servicio y el especialista. Guarda para bloquear la agenda.'
                    },
                    {
                        title: 'Control de Estatus de Cita',
                        desc: 'Actualiza el estado de las citas en tiempo real (Pendiente, En Proceso, Completado, Ausente o Cancelado) para mantener la visibilidad operativa.'
                    }
                ],
                tips: [
                    'Puedes arrastrar y soltar las citas en el calendario para cambiar rápidamente su hora o el especialista asignado.',
                    'Las citas marcadas como "Completadas" pueden enviarse al POS con un solo clic para realizar el cobro.'
                ]
            }
        },
        {
            id: 'pos-ventas',
            title: 'Punto de Venta (POS)',
            icon: '💵',
            content: {
                subtitle: 'Realiza transacciones rápidas y mantén el control de tu caja.',
                steps: [
                    {
                        title: 'Apertura de Caja Diaria',
                        desc: 'Al iniciar la jornada, ingresa el monto del fondo base de caja (dinero en efectivo disponible para dar cambio) para abrir la sesión.'
                    },
                    {
                        title: 'Registrar Ventas y Cobros',
                        desc: 'Selecciona servicios de la agenda o productos físicos de tu inventario. El sistema calculará impuestos, descuentos y el total a pagar.'
                    },
                    {
                        title: 'Cierre y Conciliación de Caja',
                        desc: 'Al finalizar el día, realiza el arqueo ingresando el dinero físico en efectivo. El sistema comparará el balance real con el teórico y reportará cualquier descuadre.'
                    }
                ],
                tips: [
                    'El sistema soporta métodos de pago divididos (ej. mitad tarjeta, mitad efectivo).',
                    'Puedes registrar salidas de caja (gastos rápidos) directamente desde el menú del POS para mantener el balance final cuadrado.'
                ]
            }
        },
        {
            id: 'nominas',
            title: 'Nómina y Comisiones',
            icon: '💰',
            content: {
                subtitle: 'Automatiza el cálculo de pagos y comisiones para tus colaboradores.',
                steps: [
                    {
                        title: 'Configurar Reglas de Comisión',
                        desc: 'Asigna a cada empleado su tasa de comisión para servicios (ej. 40%) y para venta de productos (ej. 10%).'
                    },
                    {
                        title: 'Trazabilidad de Comisiones',
                        desc: 'Cada vez que se cobra un servicio en el POS, el sistema calcula y adjudica de forma automática la comisión al profesional que lo realizó.'
                    },
                    {
                        title: 'Cierre de Período y Pago de Nómina',
                        desc: 'Accede al módulo de Nómina, selecciona el período deseado y visualiza el reporte consolidado que detalla el salario base, comisiones acumuladas, adelantos deducidos y el total neto a transferir.'
                    }
                ],
                tips: [
                    'Puedes registrar adelantos de salario o bonos extra de forma manual para que se incluyan automáticamente en la liquidación del período.',
                    'El reporte de nómina se puede exportar en formato PDF o Excel para facilitar el pago bancario.'
                ]
            }
        },
        {
            id: 'whatsapp',
            title: 'Integración WhatsApp',
            icon: '💬',
            content: {
                subtitle: 'Reduce hasta un 80% las inasistencias de tus clientes.',
                steps: [
                    {
                        title: 'Activar el Canal de Notificaciones',
                        desc: 'Ve a Configuración > WhatsApp. Activa la integración para permitir que el sistema realice envíos automáticos.'
                    },
                    {
                        title: 'Personalizar Plantillas de Mensajes',
                        desc: 'Configura las variables y textos que se enviarán en la confirmación de la cita, en el recordatorio (24 horas antes) y en el mensaje de agradecimiento.'
                    },
                    {
                        title: 'Monitoreo de Envíos',
                        desc: 'Visualiza la bitácora de mensajes para verificar que las alertas se hayan entregado correctamente en los números telefónicos correspondientes.'
                    }
                ],
                tips: [
                    'Asegúrate de registrar los números telefónicos de tus clientes con su código de área internacional (ej. +1 para República Dominicana, +57 para Colombia).',
                    'Los recordatorios automatizados se envían de forma asíncrona a través de colas de tareas, por lo que no ralentizan la navegación de la plataforma.'
                ]
            }
        }
    ];

    constructor(public appConfig: AppConfigService) {}

    getActiveSectionData(): DocSection | undefined {
        return this.sections.find(sec => sec.id === this.activeSection());
    }
}
