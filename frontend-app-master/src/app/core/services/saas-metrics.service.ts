import { Injectable } from '@angular/core';
import { Observable, combineLatest, map } from 'rxjs';
import { BaseApiService } from './base-api.service';
import { API_CONFIG } from '../config/api.config';

export interface SaasMetrics {
  mrr: number;
  total_tenants: number;
  active_tenants: number;
  trial_tenants?: number;
  expiring_trials_7d?: number;
  trial_conversion_rate?: number;
  churn_rate: number;
  growth_rate: number;
  revenue_by_plan: {
    plan_name: string;
    revenue: number;
    tenant_count: number;
  }[];
  recent_signups: {
    tenant_name: string;
    plan: string;
    created_at: string;
    subscription_status?: string;
    trial_days_remaining?: number;
  }[];
}

@Injectable({
  providedIn: 'root'
})
export class SaasMetricsService extends BaseApiService {

  getSaasMetrics(): Observable<SaasMetrics> {
    // Usar el nuevo endpoint SuperAdmin
    return this.get<SaasMetrics>(`${API_CONFIG.ENDPOINTS.SETTINGS.ADMIN_METRICS}`);
  }
}
