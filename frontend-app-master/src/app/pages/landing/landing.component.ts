import {
    Component, OnInit, OnDestroy, AfterViewInit,
    HostListener, signal, computed, inject, PLATFORM_ID, ViewEncapsulation
} from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { RouterModule } from '@angular/router';
import { RevealDirective } from './directives/reveal.directive';
import { Meta, Title } from '@angular/platform-browser';
import { ThemeService } from '../../core/services/theme.service';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

interface Faq {
    question: string;
    answer: string;
    open: boolean;
}

interface Testimonial {
    quote: string;
    name: string;
    role: string;
    location: string;
    avatar: string;
}

@Component({
    selector: 'app-landing',
    standalone: true,
    imports: [CommonModule, RouterModule, RevealDirective, FormsModule],
    templateUrl: './landing.component.html',
    styleUrl: './landing.styles.css',
    encapsulation: ViewEncapsulation.None,
    styles: [`
        app-landing {
            display: block;
            background: var(--au-bg);
            color: var(--au-text);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            overflow-x: hidden;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            min-height: 100vh;
        }
    `]
})
export class LandingComponent implements OnInit, AfterViewInit, OnDestroy {
    private readonly meta = inject(Meta);
    private readonly titleService = inject(Title);
    private readonly platformId = inject(PLATFORM_ID);
    private readonly themeService = inject(ThemeService);
    private readonly http = inject(HttpClient);

    // Theme
    isDark = computed(() => this.themeService.isDarkMode());
    themeIcon = computed(() => this.isDark() ? 'moon' : 'sun');

    // Navbar
    navScrolled = signal(false);
    mobileMenuOpen = signal(false);
    heroVisible = signal(true);
    showDemoModal = signal(false);

    // Lead capture
    leadEmail = signal('');
    leadCaptureSent = signal(false);

    submitLeadCapture(): void {
        const email = this.leadEmail();
        if (!email) return;
        this.http.post('/api/settings/contact/presentation/', {
            name: '',
            email: email
        }).subscribe({
            next: () => this.leadCaptureSent.set(true),
            error: () => this.leadCaptureSent.set(true)
        });
    }

    // Counters
    counters = [
        { target: 1200, suffix: '+', label: 'Negocios activos', current: signal(0) },
        { target: 150, suffix: 'K+', label: 'Citas gestionadas', current: signal(0) },
        { target: 45, suffix: 'M+', label: 'RD$ procesados', current: signal(0) },
        { target: 4.9, suffix: '/5', label: 'Calificación', current: signal(0), decimal: true },
    ];
    countersAnimated = false;

    // Products
    products = [
        {
            id: 'pos',
            number: '01',
            title: 'Punto de Venta',
            description: 'Cobra en segundos. Descuentos, propinas, comisiones y métodos de pago — todo automático.',
            icon: 'shopping-cart',
            span: 2,
        },
        {
            id: 'agenda',
            number: '02',
            title: 'Agenda Inteligente',
            description: 'Reservas por WhatsApp. Recordatorios automáticos. Cero no-shows.',
            icon: 'calendar',
            span: 1,
        },
        {
            id: 'clients',
            number: '03',
            title: 'CRM de Clientes',
            description: 'Historial completo: visitas, servicios favoritos, notas y fidelización.',
            icon: 'users',
            span: 1,
        },
        {
            id: 'reports',
            number: '04',
            title: 'Reportes & Analytics',
            description: 'Sabe cuánto ganas, quién produce más y dónde pierdes dinero. Datos reales, decisiones reales.',
            icon: 'bar-chart-2',
            span: 2,
        },
    ];

    // Cómo funciona
    howItWorks = [
        {
            number: 1,
            title: 'Registra tu negocio',
            description: 'Crea tu cuenta en 2 minutos. Solo necesitas tu email y el nombre de tu negocio. Sin tarjeta, sin compromiso.',
        },
        {
            number: 2,
            title: 'Configura tu equipo',
            description: 'Agrega tu personal, servicios y horarios en unos clicks. Tan fácil como armar un perfil de redes sociales.',
        },
        {
            number: 3,
            title: 'Empieza a operar',
            description: 'POS, agenda, clientes, reportes e inventario — todo funcionando desde el primer día. En minutos, no en semanas.',
        },
    ];

    // Demo modal features
    demoFeatures = [
        'POS táctil con cobro exprés',
        'Agenda con recordatorios WhatsApp',
        'CRM con historial de clientes',
        'Reportes de ingresos en tiempo real',
        'Inventario con alertas de stock',
        'Nómina y comisiones automáticas',
        'Multi-sucursal',
        'Soporte en español',
    ];

    // Why Auron
    whyCards = [
        {
            icon: 'layers',
            title: 'Todo en un solo lugar',
            description: 'Otros sistemas venden módulos por separado. AURON incluye todo desde el día uno: POS, agenda, CRM, reportes, inventario y nómina.',
        },
        {
            icon: 'globe',
            title: 'Hecho para Latinoamérica',
            description: 'Idioma, moneda, horarios y lógica de negocio pensados para cómo funcionan los salones en República Dominicana y toda LATAM.',
        },
        {
            icon: 'zap',
            title: 'Listo en 5 minutos',
            description: 'Registro gratuito, datos de demo incluidos, sin tarjeta. Tu negocio operando antes de que termine el café.',
        },
    ];

    // Features
    features = [
        {
            title: 'Reservas por WhatsApp',
            description: 'Tus clientes agendan directo desde WhatsApp. Sin apps, sin fricciones.',
            icon: 'message-circle',
            span: 2,
        },
        {
            title: 'POS Moderno',
            description: 'Interfaz optimizada para cobrar rápido. Touch-friendly, con escáner de código.',
            icon: 'monitor',
            span: 1,
        },
        {
            title: 'Dashboard Analítico',
            description: 'Gráficas en tiempo real de ventas, servicios y rendimiento del equipo.',
            icon: 'activity',
            span: 1,
        },
        {
            title: 'Nómina Automática',
            description: 'Comisiones calculadas al segundo. Sin Excel, sin errores manuales.',
            icon: 'dollar-sign',
            span: 1,
        },
        {
            title: 'Multi-sucursal',
            description: 'Gestiona múltiples ubicaciones desde un solo panel centralizado.',
            icon: 'map-pin',
            span: 1,
        },
        {
            title: 'Inventario Inteligente',
            description: 'Alertas automáticas de stock bajo. Control completo de entradas, salidas y costos.',
            icon: 'package',
            span: 2,
        },
    ];

    // Ecosystem nodes
    ecosystemNodes = [
        { name: 'POS', angle: 0 },
        { name: 'Agenda', angle: 51.4 },
        { name: 'CRM', angle: 102.8 },
        { name: 'Inventario', angle: 154.3 },
        { name: 'Reportes', angle: 205.7 },
        { name: 'Nómina', angle: 257.1 },
        { name: 'WhatsApp', angle: 308.6 },
    ];

    // Testimonials
    testimonials: Testimonial[] = [
        {
            quote: 'Desde que uso AURON dejé el cuaderno y la calculadora. Ahora sé exactamente cuánto gano cada mes y mis clientes no faltan a sus citas.',
            name: 'Carlos Medina',
            role: 'Dueño de barbería',
            location: 'Santo Domingo, RD',
            avatar: 'CM',
        },
        {
            quote: 'Lo que más me gusta es el POS. Puedo cobrar en 3 toques y las comisiones de mis estilistas se calculan solas. Nos ahorra horas cada semana.',
            name: 'María Gómez',
            role: 'Administradora de salón',
            location: 'Santiago, RD',
            avatar: 'MG',
        },
        {
            quote: 'Probé tres sistemas antes de AURON. Este es el único que realmente entiende cómo funciona una barbería en República Dominicana.',
            name: 'Pedro Almonte',
            role: 'Cadena de barberías (3 sucursales)',
            location: 'La Vega, RD',
            avatar: 'PA',
        },
    ];
    currentTestimonial = signal(0);
    private testimonialInterval?: ReturnType<typeof setInterval>;

    // Integrations
    pagosComunicacion = [
        { name: 'Efectivo', desc: 'Cobro en mostrador con registro automático' },
        { name: 'Tarjetas', desc: 'VISA, MasterCard y más con Stripe' },
        { name: 'Transferencias', desc: 'Depósitos y pagos electrónicos' },
        { name: 'Link de pago', desc: 'Cobra desde cualquier lugar sin equipo extra' },
        { name: 'WhatsApp', desc: 'Recordatorios y confirmaciones automáticas' },
        { name: 'Email', desc: 'Facturas digitales, promociones y acuses' },
    ];

    // Trust
    trustBadges = [
        { icon: 'lock', label: 'SSL/TLS', desc: 'Conexión encriptada' },
        { icon: 'shield', label: 'RBAC', desc: 'Control de acceso por rol' },
        { icon: 'activity', label: '99.9%', desc: 'Uptime garantizado' },
        { icon: 'key', label: 'JWT Auth', desc: 'Autenticación segura' },
        { icon: 'database', label: 'Backups', desc: 'Respaldos diarios' },
        { icon: 'eye-off', label: 'Privacidad', desc: 'Datos protegidos' },
    ];

    // FAQ
    faqs: Faq[] = [
        { question: '¿Cuánto cuesta AURON?', answer: 'AURON tiene planes desde $29.99/mes. Incluimos 7 días de prueba gratuita sin necesidad de tarjeta de crédito. Todos los planes incluyen todas las funcionalidades — no vendemos módulos por separado.', open: false },
        { question: '¿Puedo probarlo gratis?', answer: 'Sí. Al registrarte obtienes 7 días de acceso completo sin necesidad de ingresar datos de pago. Incluimos datos de demostración para que puedas explorar todas las funcionalidades desde el primer minuto.', open: false },
        { question: '¿Funciona sin internet?', answer: 'AURON es una aplicación web progresiva (PWA). Puedes instalarla en tu dispositivo y acceder a datos en caché cuando pierdas conexión. Las operaciones se sincronizan automáticamente cuando se restablece el internet.', open: false },
        { question: '¿Se conecta con WhatsApp?', answer: 'Sí. AURON se integra con WhatsApp Business para enviar confirmaciones de citas, recordatorios automáticos y permitir que tus clientes reserven directamente desde una conversación de WhatsApp.', open: false },
        { question: '¿Puedo migrar mis datos?', answer: 'Nuestro equipo de soporte te ayuda a migrar tus datos de clientes, servicios y productos desde Excel u otros sistemas. El proceso típico toma menos de 24 horas.', open: false },
        { question: '¿Funciona para cadenas?', answer: 'Sí. AURON soporta gestión multi-sucursal. Puedes administrar todas tus ubicaciones desde un solo panel, con reportes consolidados y gestión de personal por sucursal.', open: false },
        { question: '¿Tienen soporte en español?', answer: 'Por supuesto. AURON fue creado en República Dominicana. Todo nuestro equipo de soporte habla español. Respondemos en menos de 2 horas durante horario laboral.', open: false },
        { question: '¿Qué pasa con mis datos si cancelo?', answer: 'Tus datos te pertenecen. Si cancelas tu suscripción, puedes exportar toda tu información en formato estándar. Mantenemos tus datos por 90 días adicionales por si deseas regresar.', open: false },
    ];

    // Pricing
    billingAnnual = signal(false);
    plans = [
        {
            name: 'Basic',
            monthly: 29.99,
            annual: 24.99,
            description: 'Entrada seria para barberías pequeñas',
            popular: false,
            features: [
                'POS y agenda de citas',
                'CRM de clientes',
                'Reportes básicos',
                'Hasta 5 empleados',
                'Soporte por email',
            ],
            cta: 'Probar 7 días',
            link: '/auth/register',
        },
        {
            name: 'Pro',
            monthly: 69.99,
            annual: 58.32,
            description: 'Para negocios en crecimiento',
            popular: true,
            features: [
                'Todo Basic +',
                'Inventario completo',
                'Reportes avanzados',
                'Hasta 15 empleados',
                'WhatsApp integrado',
                'Soporte prioritario',
            ],
            cta: 'Probar 7 días',
            link: '/auth/register',
        },
        {
            name: 'Business',
            monthly: 129.99,
            annual: 108.32,
            description: 'Para equipos grandes y cadenas',
            popular: false,
            features: [
                'Todo Pro +',
                'Multi-sucursal',
                'Roles y permisos',
                'Branding personalizado',
                'Hasta 50 empleados',
                'Soporte 24/7',
            ],
            cta: 'Probar 7 días',
            link: '/auth/register',
        },
    ];

    // Nav items
    navItems = [
        { label: 'Productos', fragment: 'productos' },
        { label: 'Precios', fragment: 'precios' },
        { label: 'Características', fragment: 'caracteristicas' },
    ];

    ngOnInit(): void {
        this.titleService.setTitle('AURON Suite — El sistema operativo para tu negocio de belleza');
        this.meta.updateTag({ name: 'description', content: 'Gestiona tu barbería, salón o spa desde un solo lugar. Agenda, POS, CRM, reportes, inventario y nómina. Hecho en RD para toda Latinoamérica.' });
        this.meta.updateTag({ property: 'og:title', content: 'AURON Suite — El sistema operativo para tu negocio de belleza' });
        this.meta.updateTag({ property: 'og:description', content: 'Gestiona tu barbería, salón o spa desde un solo lugar. Agenda, POS, CRM, reportes, inventario y nómina.' });
        this.meta.updateTag({ property: 'og:type', content: 'website' });
        this.meta.updateTag({ name: 'twitter:card', content: 'summary_large_image' });

        if (isPlatformBrowser(this.platformId)) {
            this.startTestimonialAutoplay();
        }
    }

    ngAfterViewInit(): void {
        if (!isPlatformBrowser(this.platformId)) return;

        // Observe counter section
        const counterSection = document.getElementById('social-proof');
        if (counterSection) {
            const obs = new IntersectionObserver(([entry]) => {
                if (entry.isIntersecting && !this.countersAnimated) {
                    this.countersAnimated = true;
                    this.animateCounters();
                    obs.disconnect();
                }
            }, { threshold: 0.3 });
            obs.observe(counterSection);
        }
    }

    @HostListener('window:scroll')
    onScroll(): void {
        if (!isPlatformBrowser(this.platformId)) return;
        this.navScrolled.set(window.scrollY > 50);
    }

    toggleTheme(): void {
        this.themeService.toggleTheme();
    }

    toggleMobileMenu(): void {
        this.mobileMenuOpen.update(v => !v);
    }

    scrollTo(id: string): void {
        this.mobileMenuOpen.set(false);
        const el = document.getElementById(id);
        if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    toggleFaq(faq: Faq): void {
        faq.open = !faq.open;
    }

    nextTestimonial(): void {
        this.currentTestimonial.update(v =>
            (v + 1) % this.testimonials.length
        );
        this.resetTestimonialAutoplay();
    }

    prevTestimonial(): void {
        this.currentTestimonial.update(v =>
            v === 0 ? this.testimonials.length - 1 : v - 1
        );
        this.resetTestimonialAutoplay();
    }

    goToTestimonial(index: number): void {
        this.currentTestimonial.set(index);
        this.resetTestimonialAutoplay();
    }

    private startTestimonialAutoplay(): void {
        this.testimonialInterval = setInterval(() => {
            this.currentTestimonial.update(v =>
                (v + 1) % this.testimonials.length
            );
        }, 6000);
    }

    private resetTestimonialAutoplay(): void {
        if (this.testimonialInterval) {
            clearInterval(this.testimonialInterval);
        }
        this.startTestimonialAutoplay();
    }

    private animateCounters(): void {
        const duration = 2000;
        const start = performance.now();

        const step = (now: number) => {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);

            this.counters.forEach(c => {
                if (c.decimal) {
                    c.current.set(Math.round(eased * c.target * 10) / 10);
                } else {
                    c.current.set(Math.floor(eased * c.target));
                }
            });

            if (progress < 1) {
                requestAnimationFrame(step);
            }
        };

        requestAnimationFrame(step);
    }

    getEcosystemPosition(angle: number, radius: number): { x: number; y: number } {
        const rad = (angle - 90) * (Math.PI / 180);
        return {
            x: Math.cos(rad) * radius + 50,
            y: Math.sin(rad) * radius + 50,
        };
    }

    ngOnDestroy(): void {
        if (this.testimonialInterval) {
            clearInterval(this.testimonialInterval);
        }
    }
}
