import { Component, OnInit } from '@angular/core';
import { NgClass } from '@angular/common';
import { ButtonModule } from 'primeng/button';
import { Router } from '@angular/router';
import { SubscriptionService } from '../../core/services/subscription/subscription.service';

@Component({
  selector: 'app-subscription-status',
  standalone: true,
  imports: [NgClass, ButtonModule],
  template: `
    @if (subscriptionInfo && !isSuperAdmin()) {
    <div class="subscription-status" [ngClass]="getStatusClass()">
      <div class="status-content">
        <div class="status-info">
          <span class="plan-name">{{ subscriptionInfo.plan_display }}</span>
          <span class="status-text">{{ getStatusText() }}</span>
        </div>
        @if (shouldShowUpgrade()) {
          <button pButton label="Renovar" size="small" class="p-button-sm" (click)="upgrade()"></button>
        }
      </div>
    </div>
    }
  `,
  styles: [`
    .subscription-status {
      padding: 8px 16px;
      border-radius: 6px;
      margin-bottom: 1rem;
      border-left: 4px solid;
    }
    
    .status-content {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .status-info {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    
    .plan-name {
      font-weight: 600;
      font-size: 0.9rem;
    }
    
    .status-text {
      font-size: 0.8rem;
      opacity: 0.9;
    }
    
    .status-active {
background: #f5f3ff;
border-color: #8B5CF6;
      color: #0c4a6e;
    }
    
    .status-expiring {
      background: #fefce8;
      border-color: #eab308;
      color: #713f12;
    }
    
    .status-expired {
      background: #fef2f2;
      border-color: #ef4444;
      color: #7f1d1d;
    }
  `]
})
export class SubscriptionStatusComponent implements OnInit {
  subscriptionInfo: any = null;

  constructor(
    private subscriptionService: SubscriptionService,
    private router: Router
  ) {}

  ngOnInit() {
    this.loadSubscriptionInfo();
  }

  loadSubscriptionInfo() {
    this.subscriptionService.getSubscriptionStatus().subscribe({
      next: (info) => {
        this.subscriptionInfo = info;
      },
      error: () => {
        this.subscriptionInfo = null;
      }
    });
  }

  getStatusClass(): string {
    if (!this.subscriptionInfo) return '';
    
    const status = this.subscriptionInfo.current_status;
    const daysInGrace = this.subscriptionInfo.days_in_grace || 0;
    
    if (status === 'active') return 'status-active';
    if (status === 'grace' || daysInGrace > 0) return 'status-expired';
    if (status === 'trial') return 'status-expiring';
    
    return 'status-expired';
  }

  getStatusText(): string {
    if (!this.subscriptionInfo) return '';
    
    const status = this.subscriptionInfo.current_status;
    const daysInGrace = this.subscriptionInfo.days_in_grace || 0;
    
    if (status === 'active') return 'Suscripción activa';
    if (daysInGrace > 0) return `${daysInGrace} días para renovar`;
    if (status === 'trial') return 'Período de prueba';
    
    return 'Suscripción expirada';
  }

  shouldShowUpgrade(): boolean {
    if (!this.subscriptionInfo) return false;
    
    const status = this.subscriptionInfo.current_status;
    const daysInGrace = this.subscriptionInfo.days_in_grace || 0;
    
    return status !== 'active' || daysInGrace > 0;
  }

  isSuperAdmin(): boolean {
    return this.subscriptionInfo?.is_superadmin === true;
  }

  upgrade() {
    this.router.navigate(['/client/payment']);
  }
}