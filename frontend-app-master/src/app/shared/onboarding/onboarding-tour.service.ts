import { Injectable } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { BehaviorSubject, firstValueFrom } from 'rxjs';
import { filter } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/services/auth/auth.service';
import { EmployeeService } from '../../core/services/employee/employee.service';
import { ServiceService } from '../../core/services/service/service.service';
import { LocaleService } from '../../core/services/locale/locale.service';
import { normalizeRole } from '../../core/utils/role-normalizer';
import { safeGetItem } from '../../core/utils/storage';
import { ONBOARDING_TOURS, OnboardingContext, OnboardingStep, OnboardingTourConfig, OnboardingTooltipPlacement, OnboardingUserRole } from './onboarding.config';

export interface OnboardingRuntimeState {
    active: boolean;
    tourId: string;
    tourName: string;
    title: string;
    description: string;
    stepIndex: number;
    totalSteps: number;
    placement: OnboardingTooltipPlacement;
    spotlightRect: { top: number; left: number; width: number; height: number; shape: 'rounded' | 'circle' } | null;
    selector: string;
}

@Injectable({ providedIn: 'root' })
export class OnboardingTourService {
    private readonly stateSubject = new BehaviorSubject<OnboardingRuntimeState>({
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
    });
    readonly state$ = this.stateSubject.asObservable();

    private activeTour: OnboardingTourConfig | null = null;
    private activeSteps: OnboardingStep[] = [];
    private stepIndex = 0;
    private renderToken = 0;
    private maybeStartInFlight = false;
    private lastUserId: number | null = null;
    private contextCache: { hasEmployees: boolean; hasServices: boolean; ts: number } | null = null;
    private pendingManualTourId: string | null = null;

    constructor(
        private readonly router: Router,
        private readonly authService: AuthService,
        private readonly employeeService: EmployeeService,
        private readonly serviceService: ServiceService,
        private readonly localeService: LocaleService
    ) {
        this.router.events.pipe(filter((e) => e instanceof NavigationEnd)).subscribe(() => {
            this.trace('router.navigation_end', { url: this.router.url });
            this.maybeStartForCurrentRoute();
        });

        this.authService.currentUser$.subscribe((user) => {
            if (!user || this.activeTour) {
                this.trace('auth.current_user_skip', { hasUser: !!user, activeTour: !!this.activeTour });
                return;
            }
            this.trace('auth.current_user_ready', { userId: user.id, role: user.role, url: this.router.url });
            setTimeout(() => this.maybeStartForCurrentRoute(), 120);
        });
    }

    async maybeStartForCurrentRoute(): Promise<void> {
        if (this.maybeStartInFlight) {
            this.trace('maybe_start.skip_inflight', { url: this.router.url });
            return;
        }
        this.maybeStartInFlight = true;
        try {
        const user = this.authService.getCurrentUser();
        this.trace('maybe_start.enter', { hasUser: !!user, activeTour: !!this.activeTour, url: this.router.url });
        if (!user || this.activeTour) {
            this.trace('maybe_start.exit_guard', { reason: !user ? 'no_user' : 'active_tour' });
            return;
        }
        if (this.lastUserId !== user.id) {
            this.contextCache = null;
            this.lastUserId = user.id;
            this.trace('maybe_start.user_changed', { userId: user.id, role: user.role });
        }

        const currentUrl = this.router.url;
        const role = user.role;

        // Prioridad: si el usuario pidió tour manual, iniciarlo aunque ya esté completado.
        if (this.pendingManualTourId) {
            const manualTour = ONBOARDING_TOURS.find(
                (tour) =>
                    tour.id === this.pendingManualTourId &&
                    currentUrl.includes(tour.routeMatch) &&
                    this.roleMatches(tour.roles, role)
            );
            if (manualTour) {
                this.pendingManualTourId = null;
                this.trace('maybe_start.pending_manual_match', { tourId: manualTour.id, url: currentUrl, role });
                this.startTour(manualTour, true);
                return;
            }
            this.trace('maybe_start.pending_manual_no_match', { pendingManualTourId: this.pendingManualTourId, url: currentUrl, role });
        }

        const candidate = ONBOARDING_TOURS.find((tour) => tour.autoStart && currentUrl.includes(tour.routeMatch) && tour.roles.includes(role));
        if (!candidate) {
            this.trace('maybe_start.no_candidate', { url: currentUrl, role });
            return;
        }

        if (this.isCompleted(candidate.id)) {
            this.trace('maybe_start.already_completed', { tourId: candidate.id, role });
            return;
        }

        const context = await this.resolveContext(role, currentUrl);
        if (candidate.context && !candidate.context(context)) {
            this.trace('maybe_start.context_blocked', {
                tourId: candidate.id,
                role,
                hasEmployees: context.hasEmployees,
                hasServices: context.hasServices
            });
            return;
        }

        this.trace('maybe_start.starting', { tourId: candidate.id, role, url: currentUrl });
        this.startTour(candidate);
        } finally {
            this.maybeStartInFlight = false;
        }
    }

    async startManualTour(tourId?: string): Promise<boolean> {
        const role = this.authService.getCurrentUserRole();
        this.trace('manual_start.enter', { role, tourId: tourId || null, url: this.router.url });
        if (!role) {
            this.trace('manual_start.exit_guard', { reason: 'no_role' });
            return false;
        }

        const currentUrl = this.router.url;

        // Si se pide un tour específico, se puede navegar a su ruta.
        if (tourId) {
            const targetTour = ONBOARDING_TOURS.find((tour) => tour.id === tourId && tour.roles.includes(role));
            if (!targetTour) {
                this.trace('manual_start.no_target_tour', { role, tourId });
                return false;
            }

            if (!currentUrl.includes(targetTour.routeMatch)) {
                this.pendingManualTourId = targetTour.id;
                this.trace('manual_start.navigate_to_target', { tourId: targetTour.id, routeMatch: targetTour.routeMatch });
                await this.router.navigateByUrl(targetTour.routeMatch);
                return true;
            }

            this.trace('manual_start.start_current_target', { tourId: targetTour.id });
            this.startTour(targetTour, true);
            return true;
        }

        // Botón global (sin tourId): intentar módulo actual.
        const onCurrentRoute = ONBOARDING_TOURS.find((tour) => currentUrl.includes(tour.routeMatch) && this.roleMatches(tour.roles, role));
        if (onCurrentRoute) {
            this.trace('manual_start.start_current_route', { tourId: onCurrentRoute.id, role, url: currentUrl });
            this.startTour(onCurrentRoute, true);
            return true;
        }

        // Si no hay tour en la ruta actual, intentar fallback por rol con navegación validada.
        const fallbackTours = this.resolveManualFallbacks(role);
        if (!fallbackTours.length) {
            this.trace('manual_start.no_fallback', { role, url: currentUrl });
            return false;
        }

        for (const fallbackTour of fallbackTours) {
            if (currentUrl.includes(fallbackTour.routeMatch)) {
                this.trace('manual_start.start_fallback_current', { tourId: fallbackTour.id, role, url: currentUrl });
                this.startTour(fallbackTour, true);
                return true;
            }

            this.pendingManualTourId = fallbackTour.id;
            this.trace('manual_start.navigate_fallback', { tourId: fallbackTour.id, routeMatch: fallbackTour.routeMatch, role });
            const navigated = await this.router.navigateByUrl(fallbackTour.routeMatch);
            if (navigated) {
                this.trace('manual_start.navigate_fallback_ok', { tourId: fallbackTour.id, routeMatch: fallbackTour.routeMatch });
                return true;
            }
            this.pendingManualTourId = null;
            this.trace('manual_start.navigate_fallback_failed', { tourId: fallbackTour.id, routeMatch: fallbackTour.routeMatch });
        }

        this.trace('manual_start.exit_no_result', { role, url: currentUrl });
        return false;
    }

    next(): void {
        if (!this.activeTour) {
            return;
        }

        const currentStep = this.activeSteps[this.stepIndex];

        if (currentStep?.nextRoute) {
            this.markCompleted(this.activeTour.id);
            this.resetState();
            this.router.navigateByUrl(currentStep.nextRoute);
            return;
        }

        this.stepIndex += 1;
        if (this.stepIndex >= this.activeSteps.length) {
            this.complete();
            return;
        }
        void this.renderCurrentStep();
    }

    previous(): void {
        if (!this.activeTour) {
            return;
        }
        this.stepIndex = Math.max(0, this.stepIndex - 1);
        void this.renderCurrentStep();
    }

    goToStep(step: number): void {
        if (!this.activeTour) return;
        if (step < 1 || step > this.activeSteps.length) return;
        this.stepIndex = step - 1;
        void this.renderCurrentStep();
    }

    skip(): void {
        // Si el usuario salta el tour manualmente, marcarlo como completado
        // para no mostrarlo de forma automática nuevamente.
        if (this.activeTour) {
            this.markCompleted(this.activeTour.id);
        }
        this.resetState();
    }

    private startTour(definition: OnboardingTourConfig, force = false): void {
        if (!force && this.isCompleted(definition)) {
            this.trace('start_tour.skip_completed', { tourId: definition.id, force });
            return;
        }
        try {
            localStorage.setItem('onboarding:last_active_tour', definition.id);
            localStorage.setItem('onboarding:last_started_at', new Date().toISOString());
        } catch {
            // noop
        }
        this.trace('start_tour.ok', { tourId: definition.id, force, stepCount: definition.steps.length, url: this.router.url });
        this.activeTour = definition;
        this.activeSteps = definition.steps;
        this.stepIndex = 0;
        setTimeout(() => void this.renderCurrentStep(), 180);
    }

    private async renderCurrentStep(): Promise<void> {
        if (!this.activeTour) {
            return;
        }

        const role = this.authService.getCurrentUserRole() || '';
        const context = await this.resolveContext(role, this.router.url);
        let step = this.activeSteps[this.stepIndex];
        while (step && step.skipIf && step.skipIf(context)) {
            this.stepIndex += 1;
            step = this.activeSteps[this.stepIndex];
        }

        if (!step) {
            this.trace('render_step.no_step_complete', { stepIndex: this.stepIndex, totalSteps: this.activeSteps.length });
            this.complete();
            return;
        }

        if (step.beforeEnter) {
            await step.beforeEnter(context);
        }

        const currentToken = ++this.renderToken;
        const element = document.querySelector(step.selector) as HTMLElement | null;

        if (element) {
            element.scrollIntoView({
                behavior: 'instant',
                block: step.scrollBlock || 'center',
                inline: 'nearest'
            });
        } else {
            this.trace('render_step.selector_not_found', { selector: step.selector, stepId: step.id, stepIndex: this.stepIndex + 1 });
        }

        this.pushState(step, element);

        // Recalcular tras estabilizar el DOM (instant scroll + spotlight CSS transition)
        setTimeout(() => {
            if (!this.activeTour || currentToken !== this.renderToken) {
                return;
            }
            const refreshed = document.querySelector(step.selector) as HTMLElement | null;
            this.pushState(step, refreshed);
        }, 50);
    }

    private complete(): void {
        if (this.activeTour) {
            this.markCompleted(this.activeTour.id);
            this.trace('tour.complete', { tourId: this.activeTour.id });
        }
        this.resetState();
    }

    private resetState(): void {
        this.renderToken += 1;
        this.trace('tour.reset', { hadActiveTour: !!this.activeTour });
        this.activeTour = null;
        this.activeSteps = [];
        this.stepIndex = 0;
        this.stateSubject.next({
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
        });
    }

    private pushState(step: OnboardingStep, element: HTMLElement | null): void {
        const rect = element?.getBoundingClientRect();
        const padding = step.spotlightPadding ?? 10;
        const offsetX = step.offsetX ?? 0;
        const offsetY = step.offsetY ?? 0;
        const spotlightRect =
            rect && rect.width > 0 && rect.height > 0
                ? {
                      top: Math.max(rect.top - padding + offsetY, 8),
                      left: Math.max(rect.left - padding + offsetX, 8),
                      width: rect.width + padding * 2,
                      height: rect.height + padding * 2,
                      shape: step.shape || 'rounded'
                  }
                : null;

        this.stateSubject.next({
            active: true,
            tourId: this.activeTour?.id || '',
            tourName: this.resolveText(undefined, this.activeTour?.name || 'Recorrido guiado'),
            title: this.resolveText(step.titleKey, step.title),
            description: this.resolveText(step.descriptionKey, step.description),
            stepIndex: this.stepIndex + 1,
            totalSteps: this.activeSteps.length,
            placement: step.placement || 'bottom-right',
            spotlightRect,
            selector: step.selector
        });
    }

    private resolveText(key: string | undefined, fallback: string): string {
        if (!key) {
            return fallback;
        }
        const translated = this.localeService.t(key as any);
        return translated === key ? fallback : translated;
    }

    private completionKey(tourId: string, version = 1): string {
        const userKey = this.resolveStableUserKey();
        return `onboarding:${tourId}:v:${version}:user:${userKey}:done`;
    }

    private resolveStableUserKey(): string {
        const current = this.authService.getCurrentUser();
        if (current?.id) {
            return String(current.id);
        }

        try {
            const raw = safeGetItem('user');
            if (raw) {
                const parsed = JSON.parse(raw);
                if (parsed?.id) {
                    return String(parsed.id);
                }
                if (parsed?.email) {
                    return String(parsed.email).toLowerCase();
                }
            }
        } catch {
            // noop
        }

        return 'anon';
    }

    private isCompleted(tour: OnboardingTourConfig | string): boolean {
        const definition = typeof tour === 'string' ? this.findTourById(tour) : tour;
        const tourId = typeof tour === 'string' ? tour : tour.id;
        const version = definition?.version ?? 1;
        const scoped = localStorage.getItem(this.completionKey(tourId, version)) === '1';
        const legacyScoped = localStorage.getItem(`onboarding:${tourId}:user:${this.resolveStableUserKey()}:done`) === '1';
        const legacy = localStorage.getItem(`onboarding:${tourId}:done`) === '1';
        return scoped || legacyScoped || legacy;
    }

    private markCompleted(tourId: string): void {
        const definition = this.findTourById(tourId);
        const version = definition?.version ?? 1;
        localStorage.setItem(this.completionKey(tourId, version), '1');
        localStorage.setItem(`onboarding:${tourId}:user:${this.resolveStableUserKey()}:done`, '1');
        localStorage.setItem(`onboarding:${tourId}:done`, '1');
        this.trace('tour.mark_completed', { tourId, completionKey: this.completionKey(tourId, version), version });
    }

    private resolveManualFallbacks(role: string): OnboardingTourConfig[] {
        // Prioridades prácticas por rol (operación real) ⚠️ MIGRACIÓN RBAC: business roles mapeados a legacy
        const normalized = normalizeRole(role);
        const preferredIdsByRole: Record<string, string[]> = {
            CAJERA: ['onboarding-dashboard-ops', 'onboarding-pos'],
            MANAGER: ['onboarding-dashboard-ops', 'onboarding-pos', 'onboarding-earnings'],
            CLIENT_ADMIN: ['onboarding-main', 'onboarding-pos', 'onboarding-earnings'],
            CLIENT_STAFF: ['onboarding-dashboard-ops', 'onboarding-pos'],
            ESTILISTA: ['onboarding-dashboard-ops', 'onboarding-pos']
        };

        const preferredIds = preferredIdsByRole[normalized] || [];
        const resolved: OnboardingTourConfig[] = [];

        for (const tourId of preferredIds) {
            const found = ONBOARDING_TOURS.find((tour) => tour.id === tourId && this.roleMatches(tour.roles, role));
            if (found) {
                resolved.push(found);
            }
        }

        const remaining = ONBOARDING_TOURS.filter((tour) => this.roleMatches(tour.roles, role) && !resolved.some((item) => item.id === tour.id));
        return [...resolved, ...remaining];
    }

    private async resolveContext(currentRole: string, currentUrl: string): Promise<OnboardingContext> {
        const now = Date.now();
        if (!this.contextCache || now - this.contextCache.ts > 120000) {
            const [hasEmployees, hasServices] = await Promise.all([this.fetchHasEmployees(), this.fetchHasServices()]);
            this.contextCache = { hasEmployees, hasServices, ts: now };
        }
        return {
            currentRole,
            currentUrl,
            hasEmployees: this.contextCache.hasEmployees,
            hasServices: this.contextCache.hasServices
        };
    }

    private async fetchHasEmployees(): Promise<boolean> {
        try {
            const result = await firstValueFrom(this.employeeService.getEmployees({ page_size: 1 }));
            const total = Number((result as any)?.count ?? (Array.isArray(result) ? result.length : 0));
            return total > 0;
        } catch {
            return false;
        }
    }

    private async fetchHasServices(): Promise<boolean> {
        try {
            const result = await firstValueFrom(this.serviceService.getServices({ page_size: 1 }));
            const total = Number((result as any)?.count ?? (Array.isArray(result) ? result.length : 0));
            return total > 0;
        } catch {
            return false;
        }
    }

    private roleMatches(tourRoles: OnboardingUserRole[], userRole: string): boolean {
        const normalized = normalizeRole(userRole);
        return tourRoles.some((r) => normalizeRole(r) === normalized);
    }

    private findTourById(tourId: string): OnboardingTourConfig | undefined {
        return ONBOARDING_TOURS.find((tour) => tour.id === tourId);
    }

    private trace(event: string, data?: Record<string, unknown>): void {
        if (environment.production) return;
        try {
            const key = 'onboarding:debug:events';
            const raw = localStorage.getItem(key);
            const current = raw ? (JSON.parse(raw) as Array<Record<string, unknown>>) : [];
            const next = [
                ...current.slice(-79),
                {
                    ts: new Date().toISOString(),
                    event,
                    ...(data || {})
                }
            ];
            localStorage.setItem(key, JSON.stringify(next));
            localStorage.setItem('onboarding:debug:last', JSON.stringify(next[next.length - 1]));
        } catch {
            // noop
        }
    }
}
