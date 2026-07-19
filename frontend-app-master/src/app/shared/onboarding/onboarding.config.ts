export type OnboardingShape = 'rounded' | 'circle';
export type OnboardingTooltipPlacement = 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';
export type OnboardingUserRole =
    | 'CLIENT_ADMIN'
    | 'ClientAdmin'
    | 'CLIENT_STAFF'
    | 'Estilista'
    | 'Manager'
    | 'Cajera'
    | 'SUPER_ADMIN'
    | 'SuperAdmin'
    | string;

/**
 * Opens the sidebar on mobile before a tour step highlights a sidebar menu item.
 * The sidebar is hidden via translateX(-100%) on small viewports, so we must
 * reveal it or the spotlight will target off-screen coordinates.
 */
export async function ensureSidebarOpen(): Promise<void> {
    if (window.innerWidth >= 992) return;
    const wrapper = document.querySelector('.layout-wrapper');
    if (!wrapper || wrapper.classList.contains('layout-mobile-active')) return;
    wrapper.classList.add('layout-mobile-active');
    await new Promise(resolve => setTimeout(resolve, 420));
}

export interface OnboardingStep {
    id: string;
    selector: string;
    title: string;
    description: string;
    shape?: OnboardingShape;
    titleKey?: string;
    descriptionKey?: string;
    placement?: OnboardingTooltipPlacement;
    spotlightPadding?: number;
    offsetX?: number;
    offsetY?: number;
    scrollBehavior?: ScrollBehavior;
    scrollBlock?: ScrollLogicalPosition;
    skipIf?: (ctx: OnboardingContext) => boolean;
    beforeEnter?: (ctx: OnboardingContext) => void | Promise<void>;
    nextRoute?: string;
}

export interface OnboardingContext {
    currentRole: string;
    currentUrl: string;
    hasEmployees: boolean;
    hasServices: boolean;
}

export interface OnboardingTourConfig {
    id: string;
    name: string;
    routeMatch: string;
    roles: OnboardingUserRole[];
    autoStart?: boolean;
    version?: number;
    context?: (ctx: OnboardingContext) => boolean;
    steps: OnboardingStep[];
}

export const ONBOARDING_TOURS: OnboardingTourConfig[] = [
    {
        id: 'onboarding-main',
        name: 'Onboarding Inicial',
        routeMatch: '/client/dashboard',
        version: 2,
        roles: ['CLIENT_ADMIN', 'ClientAdmin', 'owner'],
        autoStart: true,
        context: (ctx) => !ctx.hasEmployees || !ctx.hasServices,
        steps: [
            {
                id: 'welcome',
                selector: '#onb-dashboard-welcome',
                title: 'Bienvenida',
                description: 'Resumen de ventas del día, citas próximas, ingresos y accesos directos a las funciones que más usas.',
                titleKey: 'onboarding.main.welcome.title',
                descriptionKey: 'onboarding.main.welcome.description',
                shape: 'rounded',
                spotlightPadding: 14
            },
            {
                id: 'business-settings',
                selector: 'a[data-tour="menu-settings"]',
                title: 'Configuración del negocio',
                description: 'Registra los datos legales de tu negocio: nombre, RNC, moneda (DOP), contacto y comprobantes fiscales NCF.',
                titleKey: 'onboarding.main.business_settings.title',
                descriptionKey: 'onboarding.main.business_settings.description',
                shape: 'rounded',
                spotlightPadding: 12,
                beforeEnter: ensureSidebarOpen
            },
            {
                id: 'add-employee',
                selector: 'a[data-tour="menu-employees"]',
                title: 'Agregar empleado',
                description: 'Crea tu equipo de trabajo para habilitar agenda de citas, nómina con comisiones y la operación del día a día.',
                titleKey: 'onboarding.main.add_employee.title',
                descriptionKey: 'onboarding.main.add_employee.description',
                shape: 'rounded',
                spotlightPadding: 12,
                beforeEnter: ensureSidebarOpen
            },
            {
                id: 'create-service',
                selector: 'a[data-tour="menu-services"]',
                title: 'Crear servicio',
                description: 'Define qué servicios ofreces, su duración y precio. Sin servicios definidos no puedes vender ni asignar empleados.',
                titleKey: 'onboarding.main.create_service.title',
                descriptionKey: 'onboarding.main.create_service.description',
                shape: 'rounded',
                spotlightPadding: 12,
                beforeEnter: ensureSidebarOpen
            },
            {
                id: 'first-pos-sale',
                selector: 'a[data-tour="menu-pos"]',
                title: 'Registrar venta en POS',
                description: 'Abre la caja del día, selecciona servicios o productos, aplica promociones o cupones y cobra. El núcleo de tu operación diaria.',
                titleKey: 'onboarding.main.first_pos_sale.title',
                descriptionKey: 'onboarding.main.first_pos_sale.description',
                shape: 'rounded',
                spotlightPadding: 12,
                beforeEnter: ensureSidebarOpen
            }
        ]
    },
    {
        id: 'onboarding-dashboard-ops',
        name: 'Onboarding Operativo',
        routeMatch: '/client/dashboard',
        version: 2,
        roles: ['CLIENT_STAFF', 'Estilista', 'Manager', 'Cajera', 'professional', 'manager', 'frontdesk_cashier'],
        autoStart: true,
        steps: [
            {
                id: 'ops-welcome',
                selector: '#onb-dashboard-welcome',
                title: 'Panel principal',
                description: 'Revisa tus turnos del día, citas asignadas, ingresos generados y accede rápido al POS y demás herramientas.',
                titleKey: 'onboarding.ops.welcome.title',
                descriptionKey: 'onboarding.ops.welcome.description',
                shape: 'rounded',
                spotlightPadding: 14
            },
            {
                id: 'ops-pos',
                selector: 'a[data-tour="menu-pos"]',
                title: 'Ir al POS',
                description: 'Acceso directo al POS para registrar ventas, aplicar descuentos o promociones y cobrar de forma rápida.',
                titleKey: 'onboarding.ops.pos.title',
                descriptionKey: 'onboarding.ops.pos.description',
                shape: 'rounded',
                spotlightPadding: 12,
                beforeEnter: ensureSidebarOpen
            }
        ]
    },
    {
        id: 'onboarding-pos',
        name: 'Tour POS',
        routeMatch: '/client/pos',
        version: 2,
        roles: ['CLIENT_ADMIN', 'ClientAdmin', 'CLIENT_STAFF', 'Estilista', 'Manager', 'Cajera', 'owner', 'professional', 'manager', 'frontdesk_cashier'],
        autoStart: true,
        steps: [
            {
                id: 'pos-header',
                selector: '#pos-tour-header',
                title: 'Cabecera POS',
                description: 'Controla la caja del día: ábrela al empezar tu turno, ciérrala al finalizar y revisa el arqueo de discrepancias.',
                titleKey: 'onboarding.pos.header.title',
                descriptionKey: 'onboarding.pos.header.description',
                shape: 'rounded',
                spotlightPadding: 10
            },
            {
                id: 'pos-filters',
                selector: '#pos-tour-filters',
                title: 'Búsqueda y filtros',
                description: 'Busca y filtra servicios o productos por nombre o categoría para agregarlos al carrito de forma rápida.',
                titleKey: 'onboarding.pos.filters.title',
                descriptionKey: 'onboarding.pos.filters.description',
                shape: 'rounded',
                spotlightPadding: 10
            },
            {
                id: 'pos-summary',
                selector: '#pos-tour-summary',
                title: 'Resumen de venta',
                description: 'Revisa el carrito, selecciona el cliente, asigna el empleado que realizó el servicio y elige el método de pago.',
                titleKey: 'onboarding.pos.summary.title',
                descriptionKey: 'onboarding.pos.summary.description',
                shape: 'rounded',
                spotlightPadding: 12
            },
            {
                id: 'pos-process',
                selector: '#pos-tour-process-btn',
                title: 'Procesar venta',
                description: 'Presiona para cobrar. También puedes ingresar un cupón promocional antes de procesar. En móvil usa el botón flotante para alternar entre catálogo y carrito.',
                titleKey: 'onboarding.pos.process.title',
                descriptionKey: 'onboarding.pos.process.description',
                shape: 'rounded',
                spotlightPadding: 10
            }
        ]
    },
    {
        id: 'onboarding-earnings',
        name: 'Tour de Ganancias',
        routeMatch: '/client/payroll',
        version: 2,
        roles: ['CLIENT_ADMIN', 'ClientAdmin', 'Manager', 'owner', 'manager'],
        autoStart: true,
        steps: [
            {
                id: 'earnings-header',
                selector: '#onb-earnings-header',
                title: 'Módulo de ganancias',
                description: 'Gestiona los periodos de nómina: revisa las comisiones generadas por cada empleado, aprueba los montos y liquida los pagos.',
                titleKey: 'onboarding.earnings.header.title',
                descriptionKey: 'onboarding.earnings.header.description',
                shape: 'rounded',
                spotlightPadding: 12
            },
            {
                id: 'earnings-periods',
                selector: '#onb-earnings-periods-table',
                title: 'Períodos de nómina',
                description: 'Cada fila es un periodo de nómina. Revisa el total de comisiones, marca como pagado cuando liquides y exporta los reportes si lo necesitas.',
                titleKey: 'onboarding.earnings.periods.title',
                descriptionKey: 'onboarding.earnings.periods.description',
                shape: 'rounded',
                spotlightPadding: 12
            }
        ]
    }
];
