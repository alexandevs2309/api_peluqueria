import { Component, inject, OnInit, OnDestroy, HostListener } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { SwUpdate, VersionReadyEvent } from '@angular/service-worker';
import { filter, Subject, takeUntil, defer, firstValueFrom } from 'rxjs';
import { PaypalReturnRecoveryService } from './app/core/services/paypal-return-recovery.service';
import { OfflineService } from './app/core/services';
import { DialogModule } from 'primeng/dialog';
import { ButtonModule } from 'primeng/button';
import { PosCart } from './app/pages/client/pos/pos.cart';

@Component({
    selector: 'app-root',
    standalone: true,
    imports: [RouterModule, DialogModule, ButtonModule],
    template: `
        @if (offlineService.isOffline()) {
            <div class="fixed top-0 left-0 right-0 z-[9999] bg-red-600 text-white text-xs font-semibold py-2.5 px-4 shadow-lg flex items-center justify-center gap-2 border-b border-red-500/20 backdrop-blur-xs">
                <i class="pi pi-exclamation-triangle text-sm animate-pulse"></i>
                <span>Sin conexión a Internet. Operando en modo de lectura/caché local.</span>
            </div>
        }
        @if (showInstallPrompt) {
            <div class="fixed bottom-4 left-4 right-4 z-[9998] bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-lg p-4 shadow-lg flex flex-col sm:flex-row items-center justify-between gap-3">
                <div class="flex items-center gap-3">
                    <i class="pi pi-mobile text-2xl text-primary"></i>
                    <div>
                        <div class="font-semibold">Instalar Auron Suite</div>
                        <div class="text-xs text-surface-600 dark:text-surface-400">Accede rápidamente desde tu pantalla de inicio</div>
                    </div>
                </div>
                <div class="flex gap-2 w-full sm:w-auto">
                    <button pButton (click)="dismissInstallPrompt()" label="Ahora no" class="p-button-text p-button-sm"></button>
                    <button pButton (click)="installApp()" label="Instalar" class="p-button-sm"></button>
                </div>
            </div>
        }
        <router-outlet></router-outlet>
        
        @if (updateNotificationVisible) {
            <div class="fixed bottom-4 right-4 z-[9997] max-w-sm w-[calc(100vw-2rem)] bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-xl p-4 shadow-2xl flex flex-col gap-3 transition-all duration-300 transform hover:scale-[1.01] backdrop-blur-md bg-opacity-95 dark:bg-opacity-95">
                <div class="flex items-start gap-3">
                    <div class="p-2 bg-primary-100 dark:bg-primary-950/50 rounded-lg text-primary">
                        <i class="pi pi-rocket text-xl animate-bounce"></i>
                    </div>
                    <div class="flex-1">
                        <div class="font-semibold text-sm text-surface-900 dark:text-surface-50">🚀 ¡Mejoras listas en AURON!</div>
                        <div class="text-xs text-surface-600 dark:text-surface-400 mt-1">Hay una nueva versión disponible con mejoras de rendimiento y estabilidad. Puedes actualizar ahora o esperar a que termines tu trabajo actual.</div>
                    </div>
                </div>
                <div class="flex justify-end gap-2 border-t border-surface-100 dark:border-surface-800 pt-3">
                    <button pButton (click)="snoozeUpdate()" label="En 15 min" class="p-button-text p-button-sm p-button-secondary"></button>
                    <button pButton (click)="reloadApp()" label="Actualizar ahora" class="p-button-sm p-button-primary"></button>
                </div>
            </div>
        }
    `
})
export class AppComponent implements OnInit, OnDestroy {
    protected readonly offlineService = inject(OfflineService);
    private readonly swUpdate = inject(SwUpdate);
    private readonly router = inject(Router);
    private readonly posCart = inject(PosCart, { optional: true });
    private destroy$ = new Subject<void>();
    showInstallPrompt = false;
    private deferredPrompt: any = null;
    
    hasUpdateReady = false;
    updateNotificationVisible = false;
    private updateCheckedInterval: any = null;

    constructor(private paypalReturnRecoveryService: PaypalReturnRecoveryService) {
        this.paypalReturnRecoveryService.init();
    }

    ngOnInit(): void {
        if (this.swUpdate.isEnabled) {
            this.swUpdate.versionUpdates
                .pipe(
                    filter((evt): evt is VersionReadyEvent => evt.type === 'VERSION_READY'),
                    takeUntil(this.destroy$)
                )
                .subscribe(() => {
                    this.hasUpdateReady = true;
                    this.showUpdateDialog();
                });
        }
        this.setupInstallPrompt();
    }

    private setupInstallPrompt(): void {
        this.showInstallPrompt = this.canShowInstallPrompt();
        window.addEventListener('beforeinstallprompt', (e: Event) => {
            e.preventDefault();
            this.deferredPrompt = e;
            this.showInstallPrompt = true;
        });
        window.addEventListener('appinstalled', () => {
            this.deferredPrompt = null;
            this.showInstallPrompt = false;
        });
    }

    canShowInstallPrompt(): boolean {
        if (!this.deferredPrompt) return false;
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
        const isInstalled = (window.navigator as any).standalone === true;
        return isMobile && !isStandalone && !isInstalled;
    }

    installApp(): void {
        if (this.deferredPrompt) {
            this.deferredPrompt.prompt();
            this.deferredPrompt.userChoice.then((choiceResult: any) => {
                if (choiceResult.outcome === 'dismissed') {
                }
                this.deferredPrompt = null;
                this.showInstallPrompt = false;
            });
        }
    }

    dismissInstallPrompt(): void {
        this.showInstallPrompt = false;
        localStorage.setItem('installPromptDismissed', Date.now().toString());
    }

    private showUpdateDialog(): void {
        if (this.checkIfSafeToUpdate()) {
            this.updateNotificationVisible = true;
            if (this.updateCheckedInterval) {
                clearInterval(this.updateCheckedInterval);
                this.updateCheckedInterval = null;
            }
        } else {
            this.scheduleUpdateNotification();
        }
    }

    private checkIfSafeToUpdate(): boolean {
        // No molestar al usuario si está cobrando (POS con items en el carrito)
        if (this.router.url.includes('/pos') && this.posCart?.items().length) {
            return false;
        }
        return true;
    }

    private scheduleUpdateNotification(): void {
        if (this.updateCheckedInterval) return;
        
        this.updateCheckedInterval = setInterval(() => {
            if (this.hasUpdateReady && this.checkIfSafeToUpdate()) {
                this.updateNotificationVisible = true;
                clearInterval(this.updateCheckedInterval);
                this.updateCheckedInterval = null;
            }
        }, 15000); // Comprobar cada 15 segundos
    }

    snoozeUpdate(): void {
        this.updateNotificationVisible = false;
        // Volver a comprobar en 15 minutos
        setTimeout(() => {
            if (this.hasUpdateReady) {
                this.showUpdateDialog();
            }
        }, 15 * 60 * 1000);
    }

    public reloadApp(): void {
        document.location.reload();
    }

    ngOnDestroy(): void {
        if (this.updateCheckedInterval) {
            clearInterval(this.updateCheckedInterval);
        }
        this.destroy$.next();
        this.destroy$.complete();
    }
}
