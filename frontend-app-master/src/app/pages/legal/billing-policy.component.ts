import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AppConfigService } from '../../core/services/app-config.service';
import { PublicPageTopbarComponent } from '../../shared/components/public-page-topbar.component';
import { PageTocComponent } from '../../shared/components/page-toc.component';

@Component({
    selector: 'app-billing-policy',
    standalone: true,
    imports: [CommonModule, RouterLink, PublicPageTopbarComponent, PageTocComponent],
    template: `
        <div class="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(139,92,246,0.12),_transparent_40%),linear-gradient(180deg,#f8fafc_0%,#eef2ff_100%)] px-4 py-10 text-slate-900 dark:bg-[radial-gradient(circle_at_top,_rgba(139,92,246,0.18),_transparent_35%),linear-gradient(180deg,#020617_0%,#0f172a_100%)] dark:text-slate-100">
            <app-public-page-topbar />
            <div class="mx-auto max-w-6xl">
                <section class="rounded-[32px] border border-white/70 bg-white/90 p-8 shadow-[0_28px_90px_-50px_rgba(15,23,42,0.35)] backdrop-blur dark:border-slate-800/80 dark:bg-slate-950/75">
                    <a
                        routerLink="/"
                        class="inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.3em] text-slate-500 transition hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
                    >
                        <span class="h-2 w-2 rounded-full bg-violet-500"></span>
                        {{ appConfig.platformName() }}
                    </a>
                    <h1 class="mt-5 text-4xl font-semibold tracking-tight text-slate-900 dark:text-white">
                        Política de Facturación y Suscripciones
                    </h1>
                    <p class="mt-4 max-w-3xl text-base leading-7 text-slate-600 dark:text-slate-300">
                        Esta política describe cómo se gestionan los planes, cobros, renovaciones, cambios de plan y situaciones de
                        impago dentro de {{ appConfig.platformName() }}.
                    </p>
                    <div class="mt-6 flex flex-wrap items-center gap-4 text-sm text-slate-500 dark:text-slate-400">
                        <span>Última actualización: {{ currentDate }}</span>
                        <span>Producto: {{ appConfig.platformName() }}</span>
                        <span *ngIf="appConfig.platformDomain()">Dominio: {{ appConfig.platformDomain() }}</span>
                        <span>Operador: Auron Technologies EIRL</span>
                    </div>
                    <div class="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                        <article
                            *ngFor="let card of summaryCards"
                            class="rounded-3xl border border-violet-100 bg-violet-50/80 p-5 shadow-[0_20px_50px_-40px_rgba(139,92,246,0.45)] dark:border-violet-500/20 dark:bg-violet-500/10"
                        >
                            <p class="text-xs font-semibold uppercase tracking-[0.24em] text-violet-700 dark:text-violet-300">Resumen</p>
                            <h2 class="mt-3 text-lg font-semibold text-slate-900 dark:text-white">{{ card.title }}</h2>
                            <p class="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{{ card.description }}</p>
                        </article>
                    </div>
                </section>

                <div class="flex gap-8 mt-8">
                    <div class="flex-1 space-y-8">
                        <section class="grid gap-6 lg:grid-cols-[1.35fr,0.95fr]">
                            <article class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                                <p class="text-sm font-semibold uppercase tracking-[0.26em] text-violet-600 dark:text-violet-300">En términos simples</p>
                                <h2 class="mt-3 text-3xl font-semibold text-slate-900 dark:text-white">La suscripción se factura por ciclos y exige un método de pago válido</h2>
                                <div class="mt-6 space-y-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                                    <p>El acceso a {{ appConfig.platformName() }} puede depender del plan contratado, de sus límites vigentes y del estado de pago de la cuenta.</p>
                                    <p>Los cobros recurrentes, reintentos, cambios de plan y efectos de cancelación se rigen por esta política junto con los términos del servicio.</p>
                                    <p>La plataforma puede restringir funciones o suspender acceso si la cuenta entra en mora, disputa de pago o riesgo comercial relevante.</p>
                                </div>
                            </article>
                            <article class="rounded-3xl border border-slate-200 bg-slate-950 p-8 text-slate-100 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.55)] dark:border-slate-700">
                                <p class="text-sm font-semibold uppercase tracking-[0.26em] text-violet-300">Checklist financiera</p>
                                <ul class="mt-5 space-y-3 text-sm leading-6 text-slate-300">
                                    <li>Los precios pueden cambiar para renovaciones futuras con comunicación razonable.</li>
                                    <li>La cancelación evita cobros futuros, pero no deshace períodos ya devengados salvo excepción aplicable.</li>
                                    <li>Los chargebacks o fraudes pueden generar investigación, bloqueo preventivo o restricción del servicio.</li>
                                    <li>Los impuestos, tasas y cargos regulatorios pueden añadirse cuando corresponda.</li>
                                </ul>
                            </article>
                        </section>

                        <section id="toc-planes" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                            <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">1. Planes de suscripción</h2>
                            <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                                Auron-Suite, operado por Auron Technologies EIRL, ofrece planes con ciclos mensuales, trimestrales y anuales.
                                Cada plan puede incluir límites de usuarios, empleados, sucursales y funcionalidades según la oferta vigente
                                al momento de la contratación o renovación.
                            </p>
                            <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                                Los límites funcionales, beneficios incluidos, promociones y condiciones de elegibilidad pueden variar por
                                plan, fecha de contratación, canal comercial o configuración técnica vigente en la plataforma de cobro.
                            </p>
                        </section>

                        <section id="toc-cobro" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                            <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">2. Cobro y renovación automática</h2>
                            <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                                Las suscripciones se cobran por adelantado mediante Stripe y, salvo indicación contraria, se renuevan
                                automáticamente al final de cada ciclo por un período equivalente. El cliente autoriza el cobro recurrente con
                                el método de pago registrado mientras la suscripción permanezca activa.
                            </p>
                            <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                                La fecha efectiva de renovación puede depender del alta original, de la configuración del checkout o de ajustes
                                posteriores sobre la suscripción. El cliente es responsable de mantener actualizada y válida la información de
                                pago asociada a la cuenta.
                            </p>
                        </section>

                        <section id="toc-cancelaciones" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                            <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">3. Cancelaciones y cambios de plan</h2>
                            <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                                El cliente puede cancelar la renovación automática desde la sección "Facturación" del panel de administración
                                o contactando a soporte@auronsuite.com antes del siguiente vencimiento. La cancelación evita cobros futuros
                                y el cliente mantendrá el acceso completo hasta el final del período ya pagado. Los cambios de plan pueden
                                generar ajustes prorrateados o aplicarse al siguiente ciclo, según la configuración comercial y técnica
                                utilizada en Stripe.
                            </p>
                            <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                                Un upgrade puede habilitar beneficios o límites superiores de forma inmediata o diferida; un downgrade puede
                                posponerse hasta el siguiente ciclo o implicar restricciones funcionales al cierre del período vigente.
                            </p>
                        </section>

                        <section id="toc-reembolsos" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                            <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">4. Reembolsos</h2>
                            <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                                Salvo obligación legal aplicable, error de cobro comprobado o decisión comercial expresa de Auron Technologies
                                EIRL, los pagos realizados no son reembolsables y no generan devoluciones proporcionales por períodos
                                parcialmente utilizados.
                            </p>
                            <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                                Las promociones, descuentos, onboarding, tiempo ya consumido, costos transaccionales o habilitación técnica de
                                la suscripción pueden considerarse al evaluar cualquier excepción comercial.
                            </p>
                        </section>

                        <section id="toc-pagos" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                            <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">5. Pagos fallidos, reintentos y período de gracia</h2>
                            <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                                Cuando un cobro no pueda completarse, Stripe o la configuración de facturación asociada podrá realizar hasta 3
                                reintentos automáticos de cobro en los 7 días siguientes. Durante un período de gracia de 7 días calendario,
                                el cliente podrá actualizar su método de pago y regularizar la cuenta sin perder inmediatamente el acceso, salvo que existan riesgos de fraude
                                o incumplimientos graves adicionales.
                            </p>
                            <div class="mt-5 rounded-2xl border border-violet-100 bg-violet-50/80 p-5 dark:border-violet-500/20 dark:bg-violet-500/10">
                                <p class="text-sm font-semibold uppercase tracking-[0.22em] text-violet-700 dark:text-violet-300">Posibles efectos durante mora</p>
                                <ul class="mt-4 space-y-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                                    <li>Recordatorios de cobro o actualización de medio de pago.</li>
                                    <li>Reintentos automáticos según la configuración de facturación.</li>
                                    <li>Restricción temporal de funciones no críticas o del acceso completo.</li>
                                    <li>Suspensión o cancelación si no hay regularización razonable.</li>
                                </ul>
                            </div>
                        </section>

                        <section id="toc-suspension" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                            <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">6. Suspensión por impago</h2>
                            <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                                Si el cliente no regulariza el pago dentro del período de gracia o tras los reintentos razonables de cobro,
                                Auron Technologies EIRL podrá restringir funciones, suspender temporalmente la cuenta o desactivar el acceso
                                hasta que la situación de pago sea resuelta.
                            </p>
                            <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                                La suspensión por impago no elimina automáticamente obligaciones pendientes ni garantiza conservación indefinida
                                de datos si la cuenta permanece inactiva o irregular durante un plazo prolongado.
                            </p>
                        </section>

                        <section id="toc-impuestos" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                            <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">7. Impuestos y disputas de pago</h2>
                            <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                                Los importes pueden estar sujetos a impuestos, tasas o cargos aplicables. En caso de chargeback, fraude,
                                reversión o disputa de pago, Auron Technologies EIRL podrá investigar el incidente, suspender temporalmente el
                                servicio y adoptar las medidas necesarias para proteger la cuenta y la operación del sistema.
                            </p>
                            <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                                El cliente colaborará razonablemente con la investigación de disputas y reconoce que un chargeback injustificado
                                puede tratarse como incumplimiento material de la relación comercial.
                            </p>
                        </section>

                        <section id="toc-contacto" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                            <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">8. Contacto</h2>
                            <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                                Para consultas sobre planes, cobros, renovaciones o incidencias de facturación, puede escribir a
                                <a
                                    [attr.href]="'mailto:' + appConfig.supportEmail()"
                                    class="font-semibold text-violet-600 transition hover:text-violet-500 dark:text-violet-400 dark:hover:text-violet-300"
                                >
                                    {{ appConfig.supportEmail() }}
                                </a>.
                                Auron-Suite es operado por Auron Technologies EIRL desde Santo Domingo, República Dominicana.
                            </p>
                        </section>
                    </div>
                    <app-page-toc [sections]="tocSections" />
                </div>
            </div>
        </div>
    `
})
export class BillingPolicyComponent {
    readonly currentDate = new Intl.DateTimeFormat('es-DO', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
    }).format(new Date());

    readonly tocSections = [
        { id: 'toc-planes', label: '1. Planes de suscripción' },
        { id: 'toc-cobro', label: '2. Cobro y renovación' },
        { id: 'toc-cancelaciones', label: '3. Cancelaciones' },
        { id: 'toc-reembolsos', label: '4. Reembolsos' },
        { id: 'toc-pagos', label: '5. Pagos fallidos' },
        { id: 'toc-suspension', label: '6. Suspensión por impago' },
        { id: 'toc-impuestos', label: '7. Impuestos y disputas' },
        { id: 'toc-contacto', label: '8. Contacto' },
    ];

    readonly summaryCards = [
        {
            title: 'Cobro anticipado',
            description: 'Las suscripciones se facturan por adelantado y, salvo indicacion contraria, se renuevan automaticamente.'
        },
        {
            title: 'Cambios de plan',
            description: 'Los upgrades, downgrades o ajustes pueden aplicarse con prorrateo o al siguiente ciclo segun la configuracion comercial.'
        },
        {
            title: 'Impago y gracia',
            description: 'Un fallo de cobro puede activar reintentos, periodo de regularizacion y luego suspension o restriccion de acceso.'
        },
        {
            title: 'Reembolsos',
            description: 'No hay devolucion general automatica salvo obligacion legal, error comprobado de cobro o decision comercial expresa.'
        }
    ];

    constructor(public appConfig: AppConfigService) {}
}
