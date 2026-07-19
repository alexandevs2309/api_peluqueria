import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AppConfigService } from '../../core/services/app-config.service';

@Component({
    selector: 'app-privacy',
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
                        Política de Privacidad
                    </h1>
                    <p class="mt-4 max-w-3xl text-base leading-7 text-slate-600 dark:text-slate-300">
                        Esta política explica cómo Auron Technologies EIRL recopila, utiliza, conserva y protege datos personales
                        relacionados con el uso de {{ appConfig.platformName() }}.
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
                            <p class="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--brand)]">Clave</p>
                            <h2 class="mt-3 text-lg font-semibold text-slate-900 dark:text-white">{{ card.title }}</h2>
                            <p class="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{{ card.description }}</p>
                        </article>
                    </div>
                </section>

                <section class="grid gap-6 lg:grid-cols-[1.35fr,0.95fr]">
                    <article class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                        <p class="text-sm font-semibold uppercase tracking-[0.26em] text-[var(--brand)]">Resumen ejecutivo</p>
                        <h2 class="mt-3 text-3xl font-semibold text-slate-900 dark:text-white">Tratamos lo necesario para operar la plataforma y protegerla</h2>
                        <div class="mt-6 space-y-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                            <p>{{ appConfig.platformName() }} necesita tratar datos de cuenta, negocio, operaciones, auditoría y seguridad para prestar el servicio de forma estable.</p>
                            <p>No todo dato tiene el mismo rol legal: algunos tratamientos son responsabilidad directa de Auron y otros se ejecutan por cuenta del negocio cliente.</p>
                            <p>El objetivo de esta política es dejar claro qué se recopila, por qué se usa, cuánto tiempo puede permanecer y cómo se canalizan solicitudes o incidentes.</p>
                        </div>
                    </article>
                    <article class="rounded-3xl border border-slate-200 bg-slate-950 p-8 text-slate-100 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.55)] dark:border-slate-700">
                        <p class="text-sm font-semibold uppercase tracking-[0.26em] text-[var(--brand)]">En particular</p>
                        <ul class="mt-5 space-y-3 text-sm leading-6 text-slate-300">
                            <li>Los eventos de login, errores, IP, user-agent y auditoría pueden tratarse con fines de seguridad y trazabilidad.</li>
                            <li>Las integraciones con pagos, email, SMS o almacenamiento se limitan a la finalidad técnica de cada flujo.</li>
                            <li>Las copias de respaldo y los registros de actividad pueden conservarse más allá de la vida activa de una sesión o cuenta.</li>
                            <li>Las solicitudes sobre datos operativos del negocio deben canalizarse prioritariamente por el propio negocio cliente.</li>
                        </ul>
                    </article>
                </section>

                <section id="toc-alcance" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                    <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">1. Alcance y categorías de interesados</h2>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Esta política aplica al tratamiento de datos relacionado con el sitio público, el registro de cuentas, el uso
                        operativo de Auron-Suite y las comunicaciones de soporte o preventa. En el contexto del servicio pueden
                        existir dos categorías principales de interesados: usuarios del negocio cliente, que acceden y operan la
                        plataforma, y clientes finales del negocio, cuyos datos son gestionados por el propio negocio dentro del
                        sistema. Esta política se rige por lo dispuesto en la Ley 172-13 sobre Protección de Datos Personales de
                        la República Dominicana y su reglamento de aplicación.
                    </p>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Dependiendo del flujo, también pueden verse involucrados prospectos comerciales, contactos de facturación,
                        solicitantes de soporte, usuarios temporales de prueba e incluso representantes del cliente con facultades
                        administrativas sobre la cuenta corporativa.
                    </p>
                </section>

                <section id="toc-datos" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                    <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">2. Datos recopilados</h2>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Podemos tratar datos de identificación y contacto de titulares de cuenta, usuarios autorizados, empleados,
                        clientes finales, datos operativos de citas, ventas, reportes, inventario, logs técnicos, información de
                        soporte, datos de facturación y referencias necesarias para pagos procesados por Stripe.
                    </p>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Entre los datos técnicos pueden incluirse dirección IP, agente de usuario, marcas temporales de acceso,
                        eventos de auditoría, identificadores de tenant, registros de error y metadatos mínimos necesarios para
                        proteger cuentas, investigar incidentes y mantener la trazabilidad del servicio.
                    </p>
                    <div class="mt-5 rounded-2xl border border-[var(--brand)]/20 bg-[var(--brand)]/5 p-5">
                        <p class="text-sm font-semibold uppercase tracking-[0.22em] text-[var(--brand)]">Ejemplos de datos</p>
                        <ul class="mt-4 grid gap-3 text-sm leading-6 text-slate-600 dark:text-slate-300 md:grid-cols-2">
                            <li>Cuenta: nombre, email, rol, tenant, estado de acceso.</li>
                            <li>Operación: citas, clientes, ventas, servicios, inventario, reportes.</li>
                            <li>Seguridad: IP, user-agent, cookies de sesión, eventos de auditoría.</li>
                            <li>Soporte y comercial: tickets, correos, historial de contacto, datos de suscripción.</li>
                        </ul>
                    </div>
                </section>

                <section id="toc-finalidades" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                    <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">3. Finalidades y bases de tratamiento</h2>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Los datos se utilizan para prestar el servicio, autenticar usuarios, gestionar suscripciones, procesar pagos,
                        enviar notificaciones operativas por email, responder solicitudes de soporte, mejorar seguridad y rendimiento,
                        así como cumplir obligaciones contractuales y legítimas derivadas de la operación del SaaS.
                    </p>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Cuando la base jurídica aplicable lo exija, el tratamiento se apoya en la ejecución del contrato, el interés
                        legítimo en seguridad, soporte, prevención de fraude y continuidad operativa, el cumplimiento de obligaciones
                        legales y, en su caso, el consentimiento para comunicaciones o tecnologías no esenciales.
                    </p>
                </section>

                <section id="toc-roles" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                    <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">4. Roles sobre los datos</h2>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Respecto de los datos de usuarios del negocio cliente y de sus clientes finales cargados en la plataforma, el
                        negocio cliente actúa como responsable de dichos datos dentro de su operación y Auron Technologies EIRL actúa
                        como proveedor tecnológico y Data Processor en la medida prevista por el DPA. Respecto de datos de contacto,
                        suscripción, soporte o preventa recabados directamente por la operadora, Auron Technologies EIRL actúa como
                        responsable del tratamiento.
                    </p>
                </section>

                <section id="toc-conservacion" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                    <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">5. Conservación de datos</h2>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Los datos de cuenta y suscripción se conservarán mientras exista una relación activa y por el tiempo razonable
                        posterior necesario para soporte, auditoría, defensa contractual o cumplimiento de obligaciones. Los datos
                        operativos del cliente permanecerán disponibles mientras el servicio esté activo o hasta que el cliente
                        solicite su eliminación, sujeto a tiempos razonables de exportación, cierre y depuración. Los logs técnicos y
                        registros de seguridad podrán conservarse por períodos adicionales compatibles con necesidades legítimas de
                        estabilidad, trazabilidad y prevención de fraude. Las copias de respaldo podrán persistir temporalmente y ser
                        eliminadas de forma diferida en ciclos internos de backup.
                    </p>
                    <div class="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-5 dark:border-slate-700 dark:bg-slate-950/60">
                        <p class="text-sm font-semibold uppercase tracking-[0.22em] text-slate-500 dark:text-slate-400">Matriz orientativa</p>
                        <ul class="mt-4 space-y-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                            <li>Datos de cuenta y facturación: durante la relación activa y por un plazo razonable posterior.</li>
                            <li>Datos operativos del cliente: mientras el servicio siga activo o hasta solicitud de cierre/eliminación.</li>
                            <li>Logs y auditoría: por el tiempo necesario para seguridad, investigación y trazabilidad.</li>
                            <li>Backups: conservación temporal y eliminación diferida según ciclos internos del servicio.</li>
                        </ul>
                    </div>
                </section>

                <section id="toc-proveedores" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                    <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">6. Proveedores y transferencias internacionales</h2>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Auron Technologies EIRL puede utilizar proveedores de infraestructura, correo electrónico, pagos, monitoreo o
                        seguridad para operar el servicio. Estos proveedores se encuentran mayoritariamente en Estados Unidos, lo que
                        implica transferencias internacionales de datos. Para todas las transferencias internacionales, la operadora
                        implementa Cláusulas Contractuales Tipo (SCCs) adoptadas por la Comisión Europea, así como las salvaguardas
                        exigidas por la Ley 172-13 sobre Protección de Datos Personales de la República Dominicana y su reglamento,
                        garantizando un nivel adecuado de protección para los datos transferidos.
                    </p>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        En la operación del producto esto puede incluir, según la configuración activa del entorno, proveedores para
                        procesamiento de pagos, correo transaccional, mensajería SMS, almacenamiento de archivos o infraestructura
                        cloud. Cada integración se limita a la finalidad técnica correspondiente y no habilita un uso indiscriminado
                        de la información.
                    </p>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Cuando la transferencia internacional involucre países que no ofrezcan un nivel de protección de datos
                        adecuado según la normativa aplicable, Auron Technologies EIRL implementará Cláusulas Contractuales
                        Tipo (SCCs) adoptadas por la Comisión Europea u otros mecanismos equivalentes reconocidos por la
                        legislación dominicana y los marcos internacionales aplicables, garantizando salvaguardas suficientes
                        para la protección de los datos transferidos.
                    </p>
                </section>

                <section id="toc-seguridad" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                    <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">7. Seguridad de la información</h2>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Se aplican medidas técnicas y organizativas razonables, incluyendo autenticación, control de acceso,
                        segregación lógica por cliente, monitoreo de actividad y medidas proporcionadas al riesgo para proteger la
                        confidencialidad, integridad y disponibilidad de la información tratada.
                    </p>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Estas medidas pueden abarcar uso de credenciales protegidas, cookies seguras de autenticación, registros de
                        auditoría, permisos por rol, separación lógica por tenant, copias de respaldo y controles para detectar
                        actividad anómala o errores operativos relevantes.
                    </p>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Ninguna medida de seguridad puede garantizar riesgo cero; sin embargo, la plataforma procura una postura
                        razonable y evolutiva de seguridad compatible con un entorno SaaS multi-tenant y con integraciones externas.
                    </p>
                </section>

                <section id="toc-derechos" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                    <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">8. Derechos y solicitudes</h2>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Los titulares pueden solicitar acceso, actualización, corrección o eliminación de sus datos cuando corresponda.
                        Cuando la solicitud se refiera a datos gestionados por un negocio cliente dentro de su operación, la misma
                        deberá ser canalizada principalmente a través de dicho negocio, sin perjuicio de la asistencia razonable que
                        pueda brindar Auron Technologies EIRL en su calidad de proveedor tecnológico.
                    </p>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Las solicitudes pueden enviarse a
                        <a
                            [attr.href]="'mailto:' + appConfig.supportEmail()"
                            class="font-semibold text-[var(--brand)] transition hover:opacity-80"
                        >
                            {{ appConfig.supportEmail() }}
                        </a>
                        e idealmente deberán identificar el negocio, la cuenta o el contexto del tratamiento para facilitar la
                        verificación y la respuesta.
                    </p>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Cuando sea técnicamente factible, los titulares también podrán solicitar la portabilidad de sus datos
                        a otro responsable del tratamiento. Auron Technologies EIRL facilitará dicha transferencia en un formato
                        estructurado, de uso común y lectura mecánica, sin entorpecer el derecho del titular ni las obligaciones
                        del responsable.
                    </p>
                </section>

                <section id="toc-menores" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                    <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">9. Datos de menores y cambios</h2>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Auron-Suite no está diseñado específicamente para menores de edad. Si un negocio cliente gestiona datos de
                        menores dentro de su propia operación, será responsable de contar con la legitimación correspondiente. Esta
                        política podrá actualizarse para reflejar cambios legales, operativos o técnicos relevantes.
                    </p>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Cuando se publiquen cambios materiales, estos podrán comunicarse mediante el sitio, el panel, correo
                        operativo u otros medios razonables que permitan al cliente conocer la versión vigente.
                    </p>
                </section>

                <section id="toc-contacto" class="rounded-3xl border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.28)] dark:border-slate-800 dark:bg-slate-900/85">
                    <h2 class="text-2xl font-semibold text-slate-900 dark:text-white">10. Contacto</h2>
                    <p class="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
                        Auron-Suite es operado por Auron Technologies EIRL desde Santo Domingo, República Dominicana. Para consultas de
                        privacidad o tratamiento de datos, puede escribir a
                        <a
                            [attr.href]="'mailto:' + appConfig.supportEmail()"
                            class="font-semibold text-[var(--brand)] transition hover:opacity-80"
                        >
                            {{ appConfig.supportEmail() }}
                        </a>.
                    </p>
                </section>
        </div>
    `
})
export class PrivacyComponent {
    readonly currentDate = new Intl.DateTimeFormat('es-DO', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
    }).format(new Date());

    readonly summaryCards = [
        {
            title: 'Quién decide',
            description: 'Auron actua como responsable para cuenta, facturacion, soporte y preventa, y como processor respecto de los datos operativos cargados por el negocio cliente.'
        },
        {
            title: 'Qué se trata',
            description: 'Datos de cuenta, operaciones, logs tecnicos, auditoria, seguridad, soporte y referencias necesarias para pagos e integraciones activadas.'
        },
        {
            title: 'Por qué se trata',
            description: 'Prestacion del SaaS, autenticacion, continuidad operativa, cumplimiento legal, prevencion de fraude y soporte del servicio.'
        },
        {
            title: 'Cómo se protege',
            description: 'Permisos por rol, segregacion por tenant, credenciales protegidas, auditoria, backups y controles razonables de seguridad.'
        }
    ];

    constructor(public appConfig: AppConfigService) {}
}
