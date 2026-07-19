import { Component, OnInit, OnDestroy } from '@angular/core';
import { NgClass } from '@angular/common';
import { ButtonModule } from 'primeng/button';
import { Router } from '@angular/router';
import { TrialService, TrialStatus } from '../../core/services/trial.service';
import { SubscriptionService } from '../../core/services/subscription/subscription.service';
import { Subscription, firstValueFrom } from 'rxjs';

@Component({
  selector: 'app-trial-banner',
  standalone: true,
  imports: [NgClass, ButtonModule],
  template: `
    @if (shouldShowBanner) {
      <div class="trial-banner"
           [ngClass]="{
             'trial-warning': daysRemaining <= 3 && daysRemaining > 0 && !isGracePeriod,
             'trial-expired': daysRemaining <= 0 && !isGracePeriod,
             'trial-active': daysRemaining > 3 && !isGracePeriod,
             'grace-period': isGracePeriod
           }">

        @if (isGracePeriod && daysRemaining > 0) {
          <div class="banner-content">
            <div class="banner-icon"><i class="pi pi-exclamation-triangle animate-pulse"></i></div>
            <div class="banner-text">
              <span class="banner-title">⚠️ Período de Gracia Activo</span>
              <span class="banner-message">Tu suscripción expiró. Te quedan <strong>{{daysRemaining}} días</strong> para renovar.</span>
            </div>
            <button pButton type="button" label="Renovar Ahora" class="p-button-sm p-button-danger" (click)="upgradeNow()"></button>
          </div>
        }

        @if (!isGracePeriod && daysRemaining > 0) {
          <div class="banner-content">
            <div class="banner-icon">
              @if (daysRemaining > 3) {
                <i class="pi pi-clock"></i>
              } @else {
                <i class="pi pi-exclamation-triangle"></i>
              }
            </div>
            <div class="banner-text">
              <span class="banner-title">Prueba Gratuita</span>
              <span class="banner-message">Te quedan <strong>{{daysRemaining}} días</strong> de prueba gratuita</span>
            </div>
            <button pButton type="button" label="Actualizar Plan" class="p-button-sm" (click)="upgradeNow()"></button>
          </div>
        }

        @if (!isGracePeriod && daysRemaining <= 0) {
          <div class="banner-content">
            <div class="banner-icon"><i class="pi pi-times-circle"></i></div>
            <div class="banner-text">
              <span class="banner-title">Prueba Expirada</span>
              <span class="banner-message">Tu prueba gratuita ha terminado. Actualiza para continuar.</span>
            </div>
            <button pButton type="button" label="Actualizar Ahora" class="p-button-sm p-button-danger" (click)="upgradeNow()"></button>
          </div>
        }
      </div>
    }
  `,
  styles: [`
    .trial-banner {
      position: sticky;
      top: 0;
      z-index: 100;
      padding: 12px 20px;
      border-bottom: 1px solid var(--surface-200);
      transition: all 0.3s ease;
    }

    .trial-active {
      background: linear-gradient(135deg, var(--brand-50) 0%, var(--brand-100) 100%);
      color: var(--brand-700);
    }

    .trial-warning {
      background: linear-gradient(135deg, var(--warning-50) 0%, var(--warning-100) 100%);
      color: var(--warning-700);
    }

    .trial-expired {
      background: linear-gradient(135deg, var(--danger-50) 0%, var(--danger-100) 100%);
      color: var(--danger-700);
    }

    .grace-period {
      background: linear-gradient(135deg, var(--danger-100) 0%, var(--danger-500) 100%);
      color: #ffffff;
      animation: pulse 2s infinite;
    }

    @keyframes pulse {
      0% { opacity: 1; }
      50% { opacity: 0.8; }
      100% { opacity: 1; }
    }

    .animate-pulse {
      animation: pulse 1.5s infinite;
    }

    .banner-content {
      display: flex;
      align-items: center;
      justify-content: space-between;
      max-width: 1200px;
      margin: 0 auto;
    }

    .banner-icon {
      font-size: 1.2rem;
      margin-right: 12px;
    }

    .banner-text {
      flex: 1;
      display: flex;
      flex-direction: column;
    }

    .banner-title {
      font-weight: 600;
      font-size: 0.9rem;
    }

    .banner-message {
      font-size: 0.85rem;
      opacity: 0.9;
    }

    @media (max-width: 768px) {
      .banner-content {
        flex-direction: column;
        text-align: center;
        gap: 8px;
      }
      
      .banner-icon {
        margin-right: 0;
      }
    }
  `]
})
export class TrialBannerComponent implements OnInit, OnDestroy {
  trialStatus: TrialStatus | null = null;
  subscriptionStatus: any = null;
  daysRemaining: number = 0;
  shouldShowBanner: boolean = false;
  isGracePeriod: boolean = false;
  private subscription: Subscription = new Subscription();

  constructor(
    private trialService: TrialService,
    private subscriptionService: SubscriptionService,
    private router: Router
  ) {}

  ngOnInit() {
    this.subscription.add(
      this.trialService.trialStatus$.subscribe(status => {
        this.trialStatus = status;
        this.updateBannerState();
      })
    );

    // Cargar estado inicial
    this.trialService.loadTrialStatus();
    this.loadSubscriptionStatus();
  }

  ngOnDestroy() {
    this.subscription.unsubscribe();
  }

  private updateBannerState() {
    // Verificar período de gracia primero
    if (this.subscriptionStatus?.access_level === 'grace' && this.subscriptionStatus?.days_in_grace > 0) {
      this.isGracePeriod = true;
      this.daysRemaining = this.subscriptionStatus.days_in_grace;
      this.shouldShowBanner = true;
      return;
    }

    // Si no hay período de gracia, usar lógica de trial normal
    if (!this.trialStatus) {
      this.shouldShowBanner = false;
      return;
    }

    this.isGracePeriod = false;
    this.daysRemaining = this.trialStatus.trial_days_remaining || 0;
    
    // Mostrar banner si está en trial (con días > 0) O si expiró (días <= 0)
    this.shouldShowBanner = this.trialStatus.is_trial;
  }

  private async loadSubscriptionStatus() {
    try {
      this.subscriptionStatus = await firstValueFrom(this.subscriptionService.getSubscriptionStatus());
      this.updateBannerState();
    } catch (error) {
      }
  }

  upgradeNow() {
    this.router.navigate(['/client/payment']);
  }
}
