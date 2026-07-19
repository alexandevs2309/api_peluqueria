import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AppConfigService } from '../../core/services/app-config.service';

@Component({
    selector: 'app-cookies',
    standalone: true,
    imports: [CommonModule, RouterLink],
    template: `
        <div class="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(26,86,219,0.10),_transparent_40%),linear-gradient(180deg,#f8fafc_0%,#eef2ff_100%)] px-4 py-10 text-slate-900 dark:bg-[radial-gradient(circle_at_top,_rgba(26,86,219,0.16),_transparent_35%),linear-gradient(180deg,#020617_0%,#0f172a_100%)] dark:text-slate-100">
            <div class="mx-auto max-w-6xl space-y-8">
                <a
                    routerLink="/"
                    class="inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.3em] text-slate-500 transition hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
                >
                    <span class="h-2 w-2 rounded-full bg-[var(--brand)]"></span>
                    {{ appConfig.platformName() }}
                </a>

                <section class="rounded-[32px] border border-white/70 bg-white/90 p-8 shadow-[0_28px_90px_-50px_rgba(15,23,42,0.35)] backdrop-blur dark:border-slate-800/80 dark:bg-slate-950/75">
                    <h1 class="mt-5 text-4xl font-semibold tracking-tight text-slate-900 dark:text-white">
                        Política de Cookies
                    </h1>
                    <p class="mt-4 max-w-3xl text-base leading-7 text-slate-600 dark:text-slate-300">
                        Esta política describe el uso de cookies y tecnologías similares en el sitio público y en el panel
                        autenticado de {{ appConfig.platformName() }}.
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
                            class="rounded-3xl border border-[var(--brand)]/20 bg-[var(--brand)]/5 p-5 shadow-[0_20px_50px_-40px_rgba(26,86,219,0.45)]"
                        >
                            <p class="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--brand)]">Resumen</p>
                            <h2 class="mt-3 text-lg font-semibold text-slate-900 dark:text-white">{{ card.title }}</h2>
                            <p class="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{{ card.description }}</p>
                        </article>
                    </div>
                </section>

                <section class="grid gap-6 lg:grid-cols-[1.3fr,1fr]">
                    <article class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                        <p class="text-sm font-semibold uppercase tracking-[0.26em] text-[var(--brand)]">En una frase</p>
                        <h2 class="mt-3 text-3xl font-semibold text-slate-900 dark:text-white">Usamos principalmente cookies e identificadores tecnicos, no marketing invasivo</h2>
                        <div class="mt-6 space-y-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                            <p>La plataforma depende de cookies e identificadores de sesión para autenticar usuarios, mantener seguridad y operar el contexto del negocio autenticado.</p>
                            <p>También existen preferencias guardadas localmente, como idioma o recordar el email de acceso, que no son imprescindibles para el servicio.</p>
                            <p>Si en el futuro se habilitan herramientas analíticas o de marketing no esenciales, esta política y los mecanismos de consentimiento deberán actualizarse de forma expresa.</p>
                        </div>
                    </article>
                    <article class="rounded-3xl border border-slate-200 bg-slate-950 p-8 text-slate-100 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.55)] dark:border-slate-700">
                        <p class="text-sm font-semibold uppercase tracking-[0.26em] text-[var(--brand)]">Consecuencia práctica</p>
                        <ul class="mt-5 space-y-3 text-sm leading-6 text-slate-300">
                            <li>Bloquear cookies esenciales puede impedir el acceso, la renovación de sesión o acciones protegidas.</li>
                            <li>Las preferencias locales mejoran la experiencia, pero no sustituyen controles de autenticación del backend.</li>
                            <li>Los servicios externos, como pagos, pueden usar sus propios identificadores dentro de sus flujos técnicos.</li>
                        </ul>
                    </article>
                </section>

                <section id="toc-que-son" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                    <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">1. Qué son las cookies</h2>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Las cookies son pequeños archivos o identificadores que pueden almacenarse en el navegador o en el entorno de
                        la sesión para facilitar autenticación, seguridad, continuidad de navegación, preferencias o medición técnica
                        del funcionamiento del servicio.
                    </p>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        En este documento, el término “cookies” también incluye otros identificadores equivalentes utilizados por el
                        navegador o por el front-end para recordar estado local, siempre que cumplan una función similar.
                    </p>
                </section>

                <section id="toc-sitio" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                    <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">2. Sitio público y panel autenticado</h2>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        El sitio público puede utilizar cookies técnicas para navegación básica, preferencias o funcionamiento del
                        banner de consentimiento. El panel autenticado puede utilizar cookies o identificadores de sesión necesarios
                        para autenticación, seguridad de cuenta, persistencia de sesión y continuidad operativa del servicio.
                    </p>
                    <div class="mt-5 overflow-hidden rounded-2xl border border-[var(--brand)]/20 bg-[var(--brand)]/5">
                        <table class="min-w-full divide-y divide-[var(--brand)]/10 text-sm">
                            <thead class="bg-white/60 dark:bg-slate-900/40">
                                <tr class="text-left text-slate-600 dark:text-slate-300">
                                    <th class="px-4 py-3 font-semibold">Identificador</th>
                                    <th class="px-4 py-3 font-semibold">Uso principal</th>
                                    <th class="px-4 py-3 font-semibold">Tipo</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-[var(--brand)]/10 text-slate-600 dark:text-slate-300">
                                <tr>
                                    <td class="px-4 py-3 font-medium text-slate-900 dark:text-white">access_token</td>
                                    <td class="px-4 py-3">Mantener la autenticación del panel y autorizar requests protegidos.</td>
                                    <td class="px-4 py-3">Cookie esencial de sesión</td>
                                </tr>
                                <tr>
                                    <td class="px-4 py-3 font-medium text-slate-900 dark:text-white">refresh_token</td>
                                    <td class="px-4 py-3">Renovar la sesión autenticada sin pedir reingreso inmediato.</td>
                                    <td class="px-4 py-3">Cookie esencial persistente</td>
                                </tr>
                                <tr>
                                    <td class="px-4 py-3 font-medium text-slate-900 dark:text-white">tenant_id</td>
                                    <td class="px-4 py-3">Soportar el contexto operativo del negocio autenticado.</td>
                                    <td class="px-4 py-3">Cookie técnica funcional</td>
                                </tr>
                                <tr>
                                    <td class="px-4 py-3 font-medium text-slate-900 dark:text-white">csrftoken</td>
                                    <td class="px-4 py-3">Mitigar ataques CSRF en formularios o requests con estado.</td>
                                    <td class="px-4 py-3">Cookie de seguridad</td>
                                </tr>
                                <tr>
                                    <td class="px-4 py-3 font-medium text-slate-900 dark:text-white">language / rememberedEmail / rememberMe</td>
                                    <td class="px-4 py-3">Recordar idioma y, si el usuario lo activa, preferencias del formulario de acceso.</td>
                                    <td class="px-4 py-3">Preferencias locales del navegador</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        La presencia de un identificador en esta lista responde al estado funcional actual del producto y puede variar
                        si cambian los mecanismos de autenticación, seguridad o preferencias ofrecidas por la app.
                    </p>
                </section>

                <section id="toc-esenciales" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                    <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">3. Cookies esenciales y funcionales</h2>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Son aquellas necesarias para autenticación, prevención de fraude, mantenimiento de sesión, seguridad,
                        enrutamiento o funcionamiento básico de la plataforma. Estas cookies o identificadores forman parte esencial
                        del servicio y no pueden desactivarse si desea utilizar funciones críticas de la aplicación.
                    </p>
                    <div class="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-5 dark:border-slate-700 dark:bg-slate-950/60">
                        <p class="text-sm font-semibold uppercase tracking-[0.22em] text-slate-500 dark:text-slate-400">Incluye, por ejemplo</p>
                        <ul class="mt-4 space-y-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                            <li>Autenticación del usuario y continuidad de sesión.</li>
                            <li>Protección CSRF y otras medidas defensivas de requests con estado.</li>
                            <li>Contexto operativo del tenant o negocio autenticado.</li>
                            <li>Persistencia mínima necesaria para navegación segura en el panel.</li>
                        </ul>
                    </div>
                </section>

                <section id="toc-analiticas" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                    <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">4. Cookies analíticas</h2>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        A la fecha de esta versión, Auron-Suite no utiliza cookies analíticas propias activas como parte esencial del
                        servicio público descrito en esta política. Si en el futuro se activan herramientas analíticas o de medición
                        no esenciales, esta política y el mecanismo de consentimiento correspondiente serán actualizados de forma
                        consistente.
                    </p>
                </section>

                <section id="toc-terceros" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                    <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">5. Cookies o tecnologías de terceros</h2>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Determinados servicios de terceros integrados al producto pueden utilizar identificadores técnicos en sus
                        propios flujos, como puede ocurrir con Stripe en el procesamiento de pagos o validaciones asociadas. El uso de
                        dichos mecanismos depende de la interacción real del usuario con esos servicios y se encuentra además sujeto a
                        las políticas del proveedor correspondiente.
                    </p>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Esta política no sustituye los términos o avisos de dichos proveedores. Cuando un flujo delega parte de la
                        operación a un tercero, ese tercero puede instalar o leer identificadores conforme a su propio marco legal y
                        técnico.
                    </p>
                </section>

                <section id="toc-duracion" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                    <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">6. Duración y gestión</h2>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Algunas cookies o identificadores son de sesión y se eliminan al cerrar el navegador; otras pueden conservarse
                        temporalmente para recordar preferencias o mantener continuidad operativa. Puede gestionar o bloquear cookies
                        desde la configuración de su navegador, aunque ello podría afectar el funcionamiento de determinadas áreas del
                        servicio.
                    </p>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Si bloquea cookies esenciales como <span class="font-semibold text-slate-900 dark:text-white">access_token</span>,
                        <span class="font-semibold text-slate-900 dark:text-white">refresh_token</span> o
                        <span class="font-semibold text-slate-900 dark:text-white">csrftoken</span>, el acceso al panel, la continuidad
                        de sesión y varias acciones protegidas pueden dejar de funcionar con normalidad.
                    </p>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        La eliminación manual de cookies o almacenamiento local puede cerrar sesiones activas, borrar preferencias
                        recordadas y exigir nueva autenticación para continuar utilizando el producto.
                    </p>
                </section>

                <section id="toc-cambios" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                    <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">7. Cambios y contacto</h2>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Esta política podrá actualizarse para reflejar cambios tecnológicos, operativos o regulatorios. Para
                        consultas, puede escribir a
                        <a
                            [attr.href]="'mailto:' + appConfig.supportEmail()"
                            class="font-semibold text-[var(--brand)] transition hover:opacity-80"
                        >
                            {{ appConfig.supportEmail() }}
                        </a>.
                        Auron-Suite es operado por Auron Technologies EIRL desde Santo Domingo, República Dominicana.
                    </p>
                </section>
            </div>
        </div>
    `
})
export class CookiesComponent {
    readonly currentDate = new Intl.DateTimeFormat('es-DO', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
    }).format(new Date());

    readonly summaryCards = [
        {
            title: 'Esenciales',
            description: 'Sin ellas no funciona correctamente el login, la continuidad de sesión ni varias acciones protegidas del panel.'
        },
        {
            title: 'Seguridad',
            description: 'Se usan identificadores y tokens para autenticación, protección CSRF, trazabilidad operativa y prevención de abuso.'
        },
        {
            title: 'Preferencias',
            description: 'Algunas claves locales recuerdan idioma y preferencias del formulario de acceso cuando el usuario así lo decide.'
        },
        {
            title: 'Terceros',
            description: 'Las integraciones de pago o servicios externos pueden desplegar sus propios identificadores técnicos en flujos concretos.'
        }
    ];

    constructor(public appConfig: AppConfigService) {}
}
