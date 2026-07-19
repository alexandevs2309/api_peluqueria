import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { BaseApiService } from '../base-api.service';
import { API_CONFIG } from '../../config/api.config';

export interface Tenant {
  id: number;
  name: string;
  subdomain: string;
  owner: any;
  contact_email: string;
  contact_phone: string;
  address: string;
  country: string;
  plan_type: string;
  subscription_plan: any;
  subscription_status: string;
  is_active: boolean;
  created_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class TenantService extends BaseApiService {
  private readonly tenantStorageKey = 'tenant';
  private readonly tenantSubdomainStorageKey = 'tenant_subdomain';

  getTenantById(id: number): Observable<Tenant> {
    return this.get(`${API_CONFIG.ENDPOINTS.TENANTS}${id}/`);
  }

  getTenant(): string | null {
    const queryTenant = this.getTenantFromQueryParams();
    if (queryTenant) {
      localStorage.setItem(this.tenantSubdomainStorageKey, queryTenant);
      return queryTenant;
    }

    const storedSubdomain = localStorage.getItem(this.tenantSubdomainStorageKey);
    if (storedSubdomain?.trim()) {
      return storedSubdomain.trim().toLowerCase();
    }

    const storedTenant = this.getStoredTenant();
    return storedTenant?.subdomain?.trim().toLowerCase() || null;
  }

  // Tenant CRUD (SuperAdmin)
  getTenants(params?: any): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.TENANTS, params);
  }


  createTenant(tenant: Partial<Tenant>): Observable<Tenant> {
    return this.post(API_CONFIG.ENDPOINTS.TENANTS, tenant);
  }

  updateTenant(id: number, tenant: Partial<Tenant>): Observable<Tenant> {
    return this.patch(`${API_CONFIG.ENDPOINTS.TENANTS}${id}/`, tenant);
  }

  deleteTenant(id: number): Observable<any> {
    return this.delete(`${API_CONFIG.ENDPOINTS.TENANTS}${id}/`);
  }

  // Tenant specific actions
  activateTenant(id: number): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.TENANTS}${id}/activate/`, {});
  }

  deactivateTenant(id: number): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.TENANTS}${id}/deactivate/`, {});
  }

  suspendTenant(id: number, reason: string): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.TENANTS}${id}/suspend/`, { reason });
  }

  resumeTenant(id: number): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.TENANTS}${id}/resume/`, {});
  }

  extendSubscription(id: number, days: number, reason: string): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.TENANTS}${id}/extend_subscription/`, { days, reason });
  }

  // Tenant stats and analytics (SuperAdmin)
  getTenantStats(id: number): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.TENANTS}${id}/stats/`);
  }

  getTenantUsers(id: number): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.ADMIN_USERS, { tenant: id });
  }

  getTenantSubscription(id: number): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.SUBSCRIPTIONS.USER_SUBSCRIPTIONS, {
      tenant: id,
      is_active: true,
      page_size: 1
    }).pipe(
      map((response: any) => {
        const items = Array.isArray(response) ? response : response?.results || [];
        return items[0] || null;
      })
    );
  }

  // Bulk operations (SuperAdmin)
  bulkActivate(tenantIds: number[]): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.TENANTS}bulk_activate/`, { tenant_ids: tenantIds });
  }

  bulkDeactivate(tenantIds: number[]): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.TENANTS}bulk_deactivate/`, { tenant_ids: tenantIds });
  }

  bulkDelete(tenantIds: number[]): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.TENANTS}bulk_delete/`, { tenant_ids: tenantIds });
  }

  // Current tenant info (for logged user)
  getCurrentTenant(): Observable<Tenant> {
    return this.get(`${API_CONFIG.ENDPOINTS.TENANTS}current/`);
  }

  updateCurrentTenant(data: Partial<Tenant>): Observable<Tenant> {
    return this.patch(`${API_CONFIG.ENDPOINTS.TENANTS}current/`, data);
  }

  private getStoredTenant(): Partial<Tenant> | null {
    try {
      return JSON.parse(localStorage.getItem(this.tenantStorageKey) || 'null');
    } catch {
      return null;
    }
  }

  private getTenantFromQueryParams(): string | null {
    if (typeof window === 'undefined') {
      return null;
    }

    const params = new URLSearchParams(window.location.search);
    const tenant = params.get('tenant_subdomain') || params.get('tenant') || params.get('subdomain');
    return tenant?.trim().toLowerCase() || null;
  }
}
