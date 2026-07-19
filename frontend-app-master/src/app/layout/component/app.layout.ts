import { Component, DestroyRef, Renderer2, ViewChild, OnInit, OnDestroy, AfterViewInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NavigationEnd, Router, RouterModule } from '@angular/router';
import { filter, Subscription } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ToastModule } from 'primeng/toast';
import { DialogModule } from 'primeng/dialog';
import { ButtonModule } from 'primeng/button';
import { MessageService } from 'primeng/api';
import { AppTopbar } from './app.topbar';
import { AppSidebar } from './app.sidebar';
import { AppFooter } from './app.footer';
import { LayoutService, layoutConfig } from '../service/layout.service';
import { OnboardingTourModule } from '../../shared/onboarding/onboarding-tour.module';
import { OnboardingTourService } from '../../shared/onboarding/onboarding-tour.service';
import { ErrorDialogService } from '../../core/services/error-dialog.service';
import { BarbershopSettingsService } from '../../shared/services/barbershop-settings.service';
import { AccessDeniedDialogService } from '../../core/services/access-denied-dialog.service';

@Component({
    selector: 'app-layout',
    standalone: true,
    imports: [CommonModule, AppTopbar, AppSidebar, RouterModule, AppFooter, ToastModule, DialogModule, ButtonModule, OnboardingTourModule],
    providers: [MessageService],
    template: `<div class="layout-wrapper" [ngClass]="containerClass">
        @if (showChangelogBanner) {
            <div class="changelog-banner animate-fadein">
                <span class="banner-badge text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full text-white">🚀 NOVEDAD</span>
                <span class="text-zinc-300">
                    Nueva versión <strong>{{ latestChangelogVersion }}</strong> disponible: <em>{{ latestChangelogTitle }}</em>
                </span>
                <a routerLink="/changelog" (click)="readChangelog()" class="text-blue-400 hover:text-blue-300 font-bold hover:underline ml-1">Ver cambios</a>
                <button (click)="dismissBanner($event)" class="banner-close-btn bg-transparent border-0 text-zinc-400 hover:text-white cursor-pointer ml-2 p-0 flex items-center justify-center" title="Descartar">
                    <i class="pi pi-times text-[10px]"></i>
                </button>
            </div>
        }
        <app-topbar></app-topbar>
        <app-sidebar></app-sidebar>
        <div class="layout-main-container">
            <main class="layout-main">
                <router-outlet></router-outlet>
            </main>
            <app-footer></app-footer>
        </div>
        <div class="layout-mask animate-fadein"></div>
        <p-toast></p-toast>
        <app-onboarding-tour-overlay></app-onboarding-tour-overlay>

        <p-dialog header="Error" [(visible)]="errorVisible" [modal]="true" [closable]="false" styleClass="mobile-dialog" [style]="{maxWidth:'95vw', width:'420px'}">
            <div class="flex flex-col gap-4">
                <div class="flex items-start gap-3 p-3 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-700">
                    <i class="pi pi-exclamation-circle text-2xl text-red-500 mt-1"></i>
                    <div>
                        <strong class="block text-surface-900 dark:text-surface-100">Ocurrió un error</strong>
                        <p class="text-sm text-surface-600 dark:text-surface-400 mt-1">{{ errorMessage }}</p>
                    </div>
                </div>
                <div class="flex justify-end gap-2">
                    <button pButton label="Ir al inicio" (click)="irAlInicio()" class="p-button-text"></button>
                    <button *ngIf="errorRetry" pButton label="Reintentar" (click)="reintentar()"></button>
                    <button pButton label="Cerrar" (click)="cerrarError()"></button>
                </div>
            </div>
        </p-dialog>

        <p-dialog [(visible)]="accessDeniedVisible" [modal]="true" [closable]="false" [showHeader]="false" styleClass="mobile-dialog access-denied-dialog" [style]="{maxWidth:'95vw', width:'400px'}">
            <div class="flex flex-col items-center p-3 text-center">
                <div [class]="'flex items-center justify-center w-14 h-14 rounded-full mb-4 ' + accessDeniedIconBg">
                    <i [class]="'pi ' + accessDeniedIcon + ' text-2xl ' + accessDeniedIconColor"></i>
                </div>
                
                <h3 class="text-xl font-bold text-surface-900 dark:text-surface-100 mb-2">
                    {{ accessDeniedTitle }}
                </h3>
                
                <p class="text-sm text-surface-600 dark:text-surface-400 mb-6 max-w-sm">
                    {{ accessDeniedMessage }}
                </p>
                
                <div class="flex items-center gap-3 w-full">
                    <button *ngIf="accessDeniedSecondaryLabel" 
                            pButton 
                            [label]="accessDeniedSecondaryLabel" 
                            (click)="executeAccessDeniedSecondaryAction()" 
                            class="p-button-outlined flex-1 py-2 justify-center">
                    </button>
                    <button pButton 
                            [label]="accessDeniedPrimaryLabel" 
                            (click)="executeAccessDeniedPrimaryAction()" 
                            class="flex-1 py-2 justify-center">
                    </button>
                </div>
            </div>
        </p-dialog>
    </div> `,
    styles: [`
        .changelog-banner {
            position: fixed;
            top: 5.5rem;
            left: 50%;
            transform: translateX(-50%);
            z-index: 1001;
            display: flex;
            align-items: center;
            gap: 0.85rem;
            background: linear-gradient(135deg, #1e1b4b 0%, #311042 100%);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(168, 85, 247, 0.45);
            box-shadow: 0 0 20px rgba(168, 85, 247, 0.25), 0 10px 30px rgba(0, 0, 0, 0.45);
            color: #ffffff;
            padding: 0.65rem 1.4rem;
            border-radius: 999px;
            font-size: 0.85rem;
            transition: all 0.3s ease;
        }
        :host-context(.app-dark) .changelog-banner {
            background: linear-gradient(135deg, #09090b 0%, #1e1b4b 100%);
            border-color: rgba(99, 102, 241, 0.45);
            box-shadow: 0 0 25px rgba(99, 102, 241, 0.3), 0 10px 30px rgba(0, 0, 0, 0.55);
        }
        .banner-badge {
            background: linear-gradient(90deg, #3b82f6 0%, #8b5cf6 100%);
            animation: pulse-glow 2s infinite alternate;
        }
        @keyframes pulse-glow {
            0% { box-shadow: 0 0 4px rgba(139, 92, 246, 0.4); }
            100% { box-shadow: 0 0 12px rgba(139, 92, 246, 0.8); }
        }
        .banner-close-btn {
            outline: none;
            transition: color 150ms ease;
        }
        .banner-close-btn:hover {
            color: #ffffff;
        }
    `]
})
export class AppLayout implements OnInit, OnDestroy, AfterViewInit {
    overlayMenuOpenSubscription: Subscription;
    configSubscription?: Subscription;
    showChangelogBanner = false;
    latestChangelogVersion = '';
    latestChangelogTitle = '';

    menuOutsideClickListener: any;

    private touchStartX = 0;
    private touchStartY = 0;
    private readonly SWIPE_THRESHOLD = 60;
    private readonly EDGE_THRESHOLD = 25;
    private swipeCleanups: (() => void)[] = [];

    @ViewChild(AppSidebar) appSidebar!: AppSidebar;

    @ViewChild(AppTopbar) appTopBar!: AppTopbar;

    // Global error dialog
    private errorDialogService = inject(ErrorDialogService);
    private barbershopSettings = inject(BarbershopSettingsService);
    errorVisible = false;
    errorMessage = '';
    errorRetry: (() => void) | null = null;

    // Access Denied dialog
    private accessDeniedDialogService = inject(AccessDeniedDialogService);
    accessDeniedVisible = false;
    accessDeniedTitle = '';
    accessDeniedMessage = '';
    accessDeniedIcon = 'pi-lock';
    accessDeniedIconColor = 'text-amber-500';
    accessDeniedIconBg = 'bg-amber-50 dark:bg-amber-950/20';
    accessDeniedPrimaryLabel = 'Entendido';
    accessDeniedSecondaryLabel = '';
    
    private accessDeniedPrimaryCallback: (() => void) | null = null;
    private accessDeniedSecondaryCallback: (() => void) | null = null;

    constructor(
        public layoutService: LayoutService,
        public renderer: Renderer2,
        public router: Router,
        private readonly onboardingTourService: OnboardingTourService,
        private readonly destroyRef: DestroyRef
    ) {
        this.overlayMenuOpenSubscription = this.layoutService.overlayOpen$.subscribe(() => {
            if (!this.menuOutsideClickListener) {
                this.menuOutsideClickListener = this.renderer.listen('document', 'click', (event) => {
                    if (this.isOutsideClicked(event)) {
                        this.hideMenu();
                    }
                });
            }

            if (this.layoutService.layoutState().staticMenuMobileActive) {
                this.blockBodyScroll();
            }
        });

        this.router.events.pipe(filter((event) => event instanceof NavigationEnd), takeUntilDestroyed(this.destroyRef)).subscribe(() => {
            this.hideMenu();
            setTimeout(() => this.onboardingTourService.maybeStartForCurrentRoute(), 300);
        });
    }

    ngOnInit() {
        this.loadChangelogInfo();
        // Aplicar clase dark al body para overlays de PrimeNG
        const isDark = this.layoutService.layoutConfig().darkTheme === true;
        if (isDark) {
            document.body.classList.add('dark');
        }
        
        // Observar cambios de tema
        this.configSubscription = this.layoutService.configUpdate$.subscribe((config: layoutConfig) => {
            if (config.darkTheme === true) {
                document.body.classList.add('dark');
            } else {
                document.body.classList.remove('dark');
            }
        });
        
        setTimeout(() => this.onboardingTourService.maybeStartForCurrentRoute(), 500);
        // Cambiar a overlay solo en POS
        this.router.events.pipe(filter((event) => event instanceof NavigationEnd), takeUntilDestroyed(this.destroyRef)).subscribe((event: NavigationEnd) => {
            if (event.url.includes('/pos')) {
                this.layoutService.layoutConfig.update(config => ({ ...config, menuMode: 'overlay' }));
            } else if (this.layoutService.layoutConfig().menuMode === 'overlay') {
                this.layoutService.layoutConfig.update(config => ({ ...config, menuMode: 'static' }));
            }
        });

        // Global error dialog
        this.errorDialogService.error$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(info => {
            if (info) {
                this.errorMessage = info.message;
                this.errorRetry = info.retry ?? null;
                this.errorVisible = true;
            } else {
                this.errorVisible = false;
            }
        });

        // Access denied dialog
        this.accessDeniedDialogService.dialog$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(info => {
            if (info) {
                this.accessDeniedTitle = info.title;
                this.accessDeniedMessage = info.message;
                this.accessDeniedIcon = info.icon || 'pi-lock';
                this.accessDeniedIconColor = info.iconColor || 'text-amber-500';
                this.accessDeniedIconBg = info.iconBgColor || 'bg-amber-50 dark:bg-amber-950/20';
                this.accessDeniedPrimaryLabel = info.primaryButtonLabel || 'Entendido';
                this.accessDeniedSecondaryLabel = info.secondaryButtonLabel || '';
                this.accessDeniedPrimaryCallback = info.primaryButtonAction ?? null;
                this.accessDeniedSecondaryCallback = info.secondaryButtonAction ?? null;
                this.accessDeniedVisible = true;
            } else {
                this.accessDeniedVisible = false;
            }
        });

        // Apply brand colors as CSS custom properties
        this.barbershopSettings.settings$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(settings => {
            const root = document.documentElement;
            if (settings?.brand_colors) {
                root.style.setProperty('--brand-primary', settings.brand_colors.primary);
                root.style.setProperty('--brand-secondary', settings.brand_colors.secondary);
                root.style.setProperty('--brand-accent', settings.brand_colors.accent);
            }
        });
    }

    cerrarError() {
        this.errorDialogService.dismiss();
    }

    loadChangelogInfo() {
        fetch('assets/changelog.json')
            .then(res => res.json())
            .then(data => {
                if (data && data.length > 0) {
                    const latest = data[0];
                    this.latestChangelogVersion = latest.version;
                    this.latestChangelogTitle = latest.title;
                    const lastRead = localStorage.getItem('last_read_changelog_version');
                    const dismissedVersion = localStorage.getItem('dismissed_changelog_version');
                    
                    if (lastRead !== this.latestChangelogVersion && dismissedVersion !== this.latestChangelogVersion) {
                        this.showChangelogBanner = true;
                    }
                }
            })
            .catch(err => console.error('Error al cargar changelog en layout', err));
    }

    readChangelog() {
        localStorage.setItem('last_read_changelog_version', this.latestChangelogVersion);
        this.showChangelogBanner = false;
    }

    dismissBanner(event: Event) {
        event.stopPropagation();
        localStorage.setItem('dismissed_changelog_version', this.latestChangelogVersion);
        this.showChangelogBanner = false;
    }

    executeAccessDeniedPrimaryAction() {
        this.accessDeniedDialogService.dismiss();
        if (this.accessDeniedPrimaryCallback) {
            this.accessDeniedPrimaryCallback();
        } else {
            const currentUrl = this.router.url;
            if (currentUrl.startsWith('/admin')) {
                this.router.navigate(['/admin/dashboard']);
            } else {
                this.router.navigate(['/client/dashboard']);
            }
        }
    }

    executeAccessDeniedSecondaryAction() {
        this.accessDeniedDialogService.dismiss();
        if (this.accessDeniedSecondaryCallback) {
            this.accessDeniedSecondaryCallback();
        }
    }

    irAlInicio() {
        this.errorDialogService.dismiss();
        const currentUrl = this.router.url;
        if (currentUrl.startsWith('/admin')) {
            this.router.navigate(['/admin/dashboard']);
        } else if (currentUrl.startsWith('/client')) {
            this.router.navigate(['/client/dashboard']);
        } else {
            this.router.navigate(['/landing']);
        }
    }

    reintentar() {
        this.errorDialogService.dismiss();
        this.errorRetry?.();
    }

    isOutsideClicked(event: MouseEvent) {
        const sidebarEl = document.querySelector('.layout-sidebar');
        const topbarEl = document.querySelector('.layout-menu-button');
        const eventTarget = event.target as Node;

        return !(sidebarEl?.isSameNode(eventTarget) || sidebarEl?.contains(eventTarget) || topbarEl?.isSameNode(eventTarget) || topbarEl?.contains(eventTarget));
    }

    hideMenu() {
        this.layoutService.layoutState.update((prev) => ({ ...prev, overlayMenuActive: false, staticMenuMobileActive: false, menuHoverActive: false }));
        if (this.menuOutsideClickListener) {
            this.menuOutsideClickListener();
            this.menuOutsideClickListener = null;
        }
        this.unblockBodyScroll();
    }

    blockBodyScroll(): void {
        if (document.body.classList) {
            document.body.classList.add('blocked-scroll');
        } else {
            document.body.className += ' blocked-scroll';
        }
    }

    unblockBodyScroll(): void {
        if (document.body.classList) {
            document.body.classList.remove('blocked-scroll');
        } else {
            document.body.className = document.body.className.replace(new RegExp('(^|\\b)' + 'blocked-scroll'.split(' ').join('|') + '(\\b|$)', 'gi'), ' ');
        }
    }

    get containerClass() {
        return {
            'layout-overlay': this.layoutService.layoutConfig().menuMode === 'overlay',
            'layout-static': this.layoutService.layoutConfig().menuMode === 'static',
            'layout-static-inactive': this.layoutService.layoutState().staticMenuDesktopInactive && this.layoutService.layoutConfig().menuMode === 'static',
            'layout-overlay-active': this.layoutService.layoutState().overlayMenuActive,
            'layout-mobile-active': this.layoutService.layoutState().staticMenuMobileActive
        };
    }

    ngAfterViewInit() {
        this.setupSwipeGestures();
    }

    private setupSwipeGestures() {
        const sidebar = this.appSidebar?.el?.nativeElement;
        if (!sidebar) return;

        const onSidebarTouchStart = (e: TouchEvent) => {
            this.touchStartX = e.touches[0].clientX;
            this.touchStartY = e.touches[0].clientY;
        };
        sidebar.addEventListener('touchstart', onSidebarTouchStart, { passive: true });

        const onSidebarTouchEnd = (e: TouchEvent) => {
            const dx = e.changedTouches[0].clientX - this.touchStartX;
            const dy = Math.abs(e.changedTouches[0].clientY - this.touchStartY);
            if (Math.abs(dx) > this.SWIPE_THRESHOLD && Math.abs(dx) > dy * 1.5 && dx < 0) {
                this.layoutService.isMobile() && this.hideMenu();
            }
        };
        sidebar.addEventListener('touchend', onSidebarTouchEnd, { passive: true });

        const onDocTouchStart = (e: TouchEvent) => {
            if (this.layoutService.layoutState().staticMenuMobileActive) return;
            if (e.touches[0].clientX < this.EDGE_THRESHOLD) {
                this.touchStartX = e.touches[0].clientX;
                this.touchStartY = e.touches[0].clientY;
            } else {
                this.touchStartX = -1;
            }
        };
        document.addEventListener('touchstart', onDocTouchStart, { passive: true });

        const onDocTouchEnd = (e: TouchEvent) => {
            if (this.touchStartX < 0) return;
            if (this.layoutService.layoutState().staticMenuMobileActive) return;
            const dx = e.changedTouches[0].clientX - this.touchStartX;
            const dy = Math.abs(e.changedTouches[0].clientY - this.touchStartY);
            if (dx > this.SWIPE_THRESHOLD && dx > dy * 1.5) {
                this.layoutService.onMenuToggle();
            }
            this.touchStartX = -1;
        };
        document.addEventListener('touchend', onDocTouchEnd, { passive: true });

        this.swipeCleanups = [
            () => sidebar.removeEventListener('touchstart', onSidebarTouchStart),
            () => sidebar.removeEventListener('touchend', onSidebarTouchEnd),
            () => document.removeEventListener('touchstart', onDocTouchStart),
            () => document.removeEventListener('touchend', onDocTouchEnd),
        ];
    }

    ngOnDestroy() {
        document.body.classList.remove('dark');

        if (this.configSubscription) {
            this.configSubscription.unsubscribe();
        }
        
        if (this.overlayMenuOpenSubscription) {
            this.overlayMenuOpenSubscription.unsubscribe();
        }

        if (this.menuOutsideClickListener) {
            this.menuOutsideClickListener();
        }

        this.swipeCleanups.forEach(fn => fn());
    }
}
