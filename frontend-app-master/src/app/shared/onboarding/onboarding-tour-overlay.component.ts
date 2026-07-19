import { Component, ElementRef, HostBinding, HostListener, OnDestroy, OnInit, Renderer2 } from '@angular/core';
import { DecimalPipe, NgStyle } from '@angular/common';
import { Subscription } from 'rxjs';
import { OnboardingRuntimeState, OnboardingTourService } from './onboarding-tour.service';
import { I18nPipe } from '../../core/pipes/i18n.pipe';
import { OnboardingTooltipPlacement } from './onboarding.config';

@Component({
    selector: 'app-onboarding-tour-overlay',
    standalone: true,
    imports: [DecimalPipe, I18nPipe, NgStyle],
    styleUrl: './onboarding.styles.scss',
    host: {
        style: 'position: fixed; inset: 0; z-index: 2147483000;'
    },
    template: `
        @if (showWelcomeModal) {
        <div class="onboarding-welcome-modal" (click)="closeWelcomeModal()">
            <div class="onboarding-welcome-card" (click)="$event.stopPropagation()">
                <div class="onboarding-welcome-icon"><i class="pi pi-sparkles"></i></div>
                <h2 class="onboarding-welcome-title">{{ 'onboarding.welcome.title' | t : '¡Bienvenido a Auron Suite!' }}</h2>
                <p class="onboarding-welcome-subtitle">{{ 'onboarding.welcome.subtitle' | t : 'Te guiaremos en un recorrido rápido para que arranques con el pie derecho.' }}</p>
                <div class="onboarding-welcome-features">
                    <div class="onboarding-welcome-feature">
                        <div class="onboarding-welcome-feature-icon main"><i class="pi pi-cog"></i></div>
                        <div class="onboarding-welcome-feature-text"><strong>{{ 'onboarding.welcome.feature.main.title' | t : 'Configuración' }}</strong><span>{{ 'onboarding.welcome.feature.main.desc' | t : 'Datos del negocio, moneda y contactos' }}</span></div>
                    </div>
                    <div class="onboarding-welcome-feature">
                        <div class="onboarding-welcome-feature-icon ops"><i class="pi pi-users"></i></div>
                        <div class="onboarding-welcome-feature-text"><strong>{{ 'onboarding.welcome.feature.ops.title' | t : 'Equipo' }}</strong><span>{{ 'onboarding.welcome.feature.ops.desc' | t : 'Agrega empleados y roles' }}</span></div>
                    </div>
                    <div class="onboarding-welcome-feature">
                        <div class="onboarding-welcome-feature-icon pos"><i class="pi pi-shopping-cart"></i></div>
                        <div class="onboarding-welcome-feature-text"><strong>{{ 'onboarding.welcome.feature.pos.title' | t : 'Ventas' }}</strong><span>{{ 'onboarding.welcome.feature.pos.desc' | t : 'POS, citas y cobro rápido' }}</span></div>
                    </div>
                </div>
                <div class="onboarding-welcome-actions">
                    <button class="onboarding-welcome-btn secondary" (click)="closeWelcomeModal()">{{ 'onboarding.welcome.skip' | t : 'Saltar' }}</button>
                    <button class="onboarding-welcome-btn primary" (click)="startWelcomeTour()">{{ 'onboarding.welcome.start' | t : 'Empezar tour' }}</button>
                </div>
            </div>
        </div>
        }

        @if (state.active) {
        <div class="onboarding-backdrop" [class.with-spotlight]="!!computedSpotlightRect"></div>
        }

        @if (state.active && computedSpotlightRect) {
        <div class="onboarding-spotlight"
            [style.top.px]="computedSpotlightRect.top"
            [style.left.px]="computedSpotlightRect.left"
            [style.width.px]="computedSpotlightRect.width"
            [style.height.px]="computedSpotlightRect.height"
            [class.spotlight-circle]="computedSpotlightRect.shape === 'circle'"
            [class.enter-left]="tooltipEnterDir === 'left'"
            [class.enter-right]="tooltipEnterDir === 'right'"
            [class.enter-top]="tooltipEnterDir === 'top'"
            [class.enter-bottom]="tooltipEnterDir === 'bottom'">
            <span class="onboarding-spotlight-step">{{ state.stepIndex }}</span>
            <div class="onboarding-spotlight-arrow" [attr.dir]="spotlightArrowDir"></div>
        </div>
        }

        @if (state.active) {
        <aside class="onboarding-tooltip" [class.mobile]="isMobile" [class]="tourVisual.className" [ngStyle]="tooltipStyle"
            [class.enter-left]="tooltipEnterDir === 'left'"
            [class.enter-right]="tooltipEnterDir === 'right'"
            [class.enter-top]="tooltipEnterDir === 'top'"
            [class.enter-bottom]="tooltipEnterDir === 'bottom'">
            <header class="onboarding-tooltip-header">
                <div>
                    <div class="onboarding-tooltip-kicker">
                        <i [class]="tourVisual.icon"></i>
                        <span>{{ tourVisual.eyebrowKey | t : tourVisual.eyebrow }}</span>
                    </div>
                    <div class="onboarding-tooltip-tour-name">{{ state.tourName }}</div>
                    <div class="onboarding-tooltip-step-meta">{{ 'onboarding.overlay.step' | t : 'Paso' }} {{ state.stepIndex }} {{ 'onboarding.overlay.of' | t : 'de' }} {{ state.totalSteps }}</div>
                </div>
                <div class="onboarding-tooltip-header-actions">
                    <span class="onboarding-step-pill">{{ progressPercent | number: '1.0-0' }}%</span>
                    <button type="button" class="onboarding-close" (click)="skip()" aria-label="Cerrar recorrido">
                        <i class="pi pi-times"></i>
                    </button>
                </div>
            </header>
            <div class="onboarding-step-indicators" role="tablist" aria-label="Pasos del recorrido">
                @for (step of stepIndicators; track step.index; let i = $index) {
                    <button type="button"
                        class="onboarding-step-dot"
                        [class.active]="i + 1 === state.stepIndex"
                        [class.completed]="i + 1 < state.stepIndex"
                        (click)="goToStep(i + 1)"
                        [attr.aria-label]="'Paso ' + (i + 1) + (i + 1 === state.stepIndex ? ' (actual)' : '')"
                        [attr.aria-current]="i + 1 === state.stepIndex ? 'step' : null">
                    </button>
                }
            </div>
            <h3 class="onboarding-tooltip-title">{{ state.title }}</h3>
            <p class="onboarding-tooltip-description">{{ state.description }}</p>
            <div class="onboarding-tour-hint">{{ tourVisual.hintKey | t : tourVisual.hint }}</div>
            <div class="onboarding-progress-meta">
                <div class="onboarding-progress-track" aria-hidden="true">
                    <div class="onboarding-progress-fill" [style.width.%]="progressPercent"></div>
                </div>
                <span class="onboarding-progress-label">{{ state.stepIndex }}/{{ state.totalSteps }}</span>
            </div>
            <footer class="onboarding-tooltip-actions">
                <button type="button" class="onboarding-btn ghost" (click)="previous()" [disabled]="state.stepIndex <= 1">{{ 'onboarding.overlay.previous' | t : 'Anterior' }}</button>
                <button type="button" class="onboarding-btn primary" (click)="next()">
                    {{ state.stepIndex === state.totalSteps ? ('onboarding.overlay.finish' | t : 'Finalizar') : ('onboarding.overlay.next' | t : 'Siguiente') }}
                </button>
                <button type="button" class="onboarding-btn skip-link" (click)="skip()">{{ 'onboarding.overlay.skip' | t : 'Saltar tour' }}</button>
            </footer>
            <div class="onboarding-shortcuts">
                <span><kbd>Enter</kbd> avanzar</span>
                <span><kbd>Esc</kbd> cerrar</span>
                <span><kbd>←</kbd><kbd>→</kbd> navegar</span>
            </div>
        </aside>
        }
    `
})
export class OnboardingTourOverlayComponent implements OnInit, OnDestroy {
    state: OnboardingRuntimeState = {
        active: false,
        tourId: '',
        tourName: '',
        title: '',
        description: '',
        stepIndex: 0,
        totalSteps: 0,
        placement: 'bottom-right',
        spotlightRect: null,
        selector: ''
    };
    computedSpotlightRect: { top: number; left: number; width: number; height: number; shape: 'rounded' | 'circle' } | null = null;
    isMobile = false;
    tooltipStyle: Record<string, string> = {};
    tooltipEnterDir: 'left' | 'right' | 'top' | 'bottom' = 'right';
    spotlightArrowDir: 'top' | 'bottom' | 'left' | 'right' = 'top';
    stepIndicators: { index: number }[] = [];
    showWelcomeModal = false;
    private readonly subscription = new Subscription();
    private scrollUnlisten: VoidFunction | null = null;
    private readonly scrollThrottleToken = { id: 0 };
    private prevStepIndex = 0;
    @HostBinding('style.pointer-events') get hostPointerEvents(): string {
        return this.state.active ? 'auto' : 'none';
    }

    constructor(
        private readonly onboardingTourService: OnboardingTourService,
        private readonly elementRef: ElementRef<HTMLElement>,
        private readonly renderer: Renderer2
    ) {}

    ngOnInit(): void {
        const host = this.elementRef.nativeElement;
        if (host.parentElement !== document.body) {
            this.renderer.appendChild(document.body, host);
        }
        this.isMobile = window.innerWidth < 900;
        this.subscription.add(this.onboardingTourService.state$.subscribe((state) => {
            // Close sidebar when tour ends (skip/complete/error)
            if (this.state.active && !state.active) {
                this.closeSidebarOnMobile();
            }

            const wasInactive = !this.state.active && state.active;
            if (wasInactive && !this.showWelcomeModal) {
                this.showWelcomeModal = true;
            }
            const directionChanged = this.state.active && state.active && state.stepIndex !== this.state.stepIndex;
            if (directionChanged) {
                this.tooltipEnterDir = this.computeTooltipEnterDir(this.state.stepIndex, state.stepIndex);
                this.spotlightArrowDir = this.computeSpotlightArrowDir(state.placement);
            }
            this.prevStepIndex = this.state.stepIndex;
            this.state = state;
            this.computedSpotlightRect = state.spotlightRect;
            this.stepIndicators = Array.from({ length: state.totalSteps }, (_, i) => ({ index: i }));
            this.updatePositioning();
            this.toggleScrollListener(state.active);
        }));
    }

    ngOnDestroy(): void {
        this.subscription.unsubscribe();
        this.scrollUnlisten?.();
    }

    private toggleScrollListener(active: boolean): void {
        if (active && !this.scrollUnlisten) {
            this.scrollUnlisten = this.renderer.listen('window', 'scroll', () => {
                const token = ++this.scrollThrottleToken.id;
                requestAnimationFrame(() => {
                    if (token !== this.scrollThrottleToken.id || !this.state.active) {
                        return;
                    }
                    this.updatePositioning();
                });
            });
        } else if (!active && this.scrollUnlisten) {
            this.scrollUnlisten();
            this.scrollUnlisten = null;
        }
    }

    get progressPercent(): number {
        if (!this.state.totalSteps) {
            return 0;
        }
        return (this.state.stepIndex / this.state.totalSteps) * 100;
    }

    get tourVisual(): { icon: string; eyebrow: string; eyebrowKey: string; className: string; hint: string; hintKey: string } {
        if (this.state.tourId.includes('pos')) {
            return {
                icon: 'pi pi-shopping-cart',
                eyebrow: 'Flujo de venta',
                eyebrowKey: 'onboarding.visual.pos.eyebrow',
                className: 'tour-pos',
                hint: 'Validaremos caja, venta y cierre sin perder el hilo operativo.',
                hintKey: 'onboarding.visual.pos.hint'
            };
        }

        if (this.state.tourId.includes('earnings')) {
            return {
                icon: 'pi pi-wallet',
                eyebrow: 'Gestion de pagos',
                eyebrowKey: 'onboarding.visual.earnings.eyebrow',
                className: 'tour-earnings',
                hint: 'Este recorrido te orienta en periodos, aprobacion y pagos.',
                hintKey: 'onboarding.visual.earnings.hint'
            };
        }

        if (this.state.tourId.includes('ops')) {
            return {
                icon: 'pi pi-compass',
                eyebrow: 'Operacion diaria',
                eyebrowKey: 'onboarding.visual.ops.eyebrow',
                className: 'tour-ops',
                hint: 'Usa este tour para moverte mas rapido por las tareas del dia.',
                hintKey: 'onboarding.visual.ops.hint'
            };
        }

        return {
            icon: 'pi pi-sparkles',
            eyebrow: 'Configuracion inicial',
            eyebrowKey: 'onboarding.visual.main.eyebrow',
            className: 'tour-main',
            hint: 'Te guiaremos por el orden correcto para arrancar mejor.',
            hintKey: 'onboarding.visual.main.hint'
        };
    }

    @HostListener('window:resize')
    onResize(): void {
        this.isMobile = window.innerWidth < 900;
        this.updatePositioning();
    }

    @HostListener('window:keydown', ['$event'])
    onKeydown(event: KeyboardEvent): void {
        if (!this.state.active) return;

        if (event.key === 'Escape') {
            event.preventDefault();
            this.skip();
        } else if (event.key === 'ArrowRight' || event.key === 'Enter') {
            event.preventDefault();
            this.next();
        } else if (event.key === 'ArrowLeft') {
            event.preventDefault();
            this.previous();
        }
    }

    next(): void {
        this.onboardingTourService.next();
    }

    previous(): void {
        this.onboardingTourService.previous();
    }

    skip(): void {
        this.onboardingTourService.skip();
    }

    goToStep(step: number): void {
        if (step === this.state.stepIndex || step < 1 || step > this.state.totalSteps) return;
        this.onboardingTourService.goToStep(step);
    }

    closeWelcomeModal(): void {
        this.showWelcomeModal = false;
        this.onboardingTourService.skip();
    }

    startWelcomeTour(): void {
        this.showWelcomeModal = false;
    }

    private computeTooltipEnterDir(prevStep: number, nextStep: number): 'left' | 'right' | 'top' | 'bottom' {
        if (nextStep > prevStep) {
            return 'right';
        }
        return 'left';
    }

    private computeSpotlightArrowDir(placement: string): 'top' | 'bottom' | 'left' | 'right' {
        switch (placement) {
            case 'top-left':
            case 'top-right':
                return 'bottom';
            case 'bottom-left':
            case 'bottom-right':
                return 'top';
            default:
                return 'top';
        }
    }

    private updatePositioning(): void {
        if (!this.state.active) {
            return;
        }

        if (this.state.selector) {
            const element = document.querySelector(this.state.selector) as HTMLElement | null;
            if (element) {
                const rect = element.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    const padding = this.state.tourId.includes('main') ? 12 : 10;
                    this.computedSpotlightRect = {
                        top: Math.max(rect.top - padding, 8),
                        left: Math.max(rect.left - padding, 8),
                        width: rect.width + padding * 2,
                        height: rect.height + padding * 2,
                        shape: this.state.spotlightRect?.shape || 'rounded'
                    };
                } else {
                    this.computedSpotlightRect = null;
                }
            } else {
                this.computedSpotlightRect = null;
            }
        } else {
            this.computedSpotlightRect = null;
        }

        this.tooltipStyle = this.computeTooltipStyle(this.state);
    }

    private computeTooltipStyle(state: OnboardingRuntimeState): Record<string, string> {
        if (!state.active || this.isMobile || !this.computedSpotlightRect) {
            return {};
        }

        const rect = this.computedSpotlightRect;
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        const panelWidth = Math.min(420, vw - 32);
        const panelHeight = 360;
        const gap = 18;

        let top = vh - panelHeight - 20;
        let left = vw - panelWidth - 20;

        let placement = state.placement as OnboardingTooltipPlacement;

        // Smart Flipping logic
        if (placement.startsWith('bottom')) {
            const bottomSpace = vh - (rect.top + rect.height + gap);
            if (bottomSpace < panelHeight && rect.top > panelHeight + gap) {
                placement = placement.replace('bottom', 'top') as OnboardingTooltipPlacement;
            }
        } else if (placement.startsWith('top')) {
            const topSpace = rect.top - gap;
            if (topSpace < panelHeight && (vh - (rect.top + rect.height + gap)) > panelHeight) {
                placement = placement.replace('top', 'bottom') as OnboardingTooltipPlacement;
            }
        }

        this.spotlightArrowDir = this.computeSpotlightArrowDir(placement);

        switch (placement) {
            case 'top-left':
                top = rect.top - panelHeight - gap;
                left = rect.left;
                break;
            case 'top-right':
                top = rect.top - panelHeight - gap;
                left = rect.left + rect.width - panelWidth;
                break;
            case 'bottom-left':
                top = rect.top + rect.height + gap;
                left = rect.left;
                break;
            case 'bottom-right':
            default:
                top = rect.top + rect.height + gap;
                left = rect.left + rect.width - panelWidth;
                break;
        }

        top = Math.max(16, Math.min(top, vh - panelHeight - 16));
        left = Math.max(16, Math.min(left, vw - panelWidth - 16));

        return {
            top: `${top}px`,
            left: `${left}px`,
            right: 'auto',
            bottom: 'auto',
            width: `${panelWidth}px`
        };
    }

    private closeSidebarOnMobile(): void {
        if (window.innerWidth >= 992) return;
        const wrapper = document.querySelector('.layout-wrapper');
        if (!wrapper) return;
        wrapper.classList.remove('layout-mobile-active');
    }
}
