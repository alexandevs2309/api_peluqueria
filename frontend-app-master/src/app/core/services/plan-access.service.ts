import { Injectable } from '@angular/core';

interface TenantPlanLike {
  name?: string;
  display_name?: string;
  max_users?: number;
  max_employees?: number;
  features?: Record<string, boolean> | null;
}

interface TenantLike {
  id?: number;
  name?: string;
  plan_type?: string;
  subscription_plan?: any;
  subscription_plan_details?: TenantPlanLike | null;
}

export interface PlanLimitStatus {
  reached: boolean;
  current: number;
  limit: number;
  unlimited: boolean;
  planName: string;
}

export interface UpgradeRecommendation {
  nextPlanName: string;
  reason: string;
  detail: string;
}

import { safeGetItem } from '../utils/storage';

@Injectable({
  providedIn: 'root'
})
export class PlanAccessService {
  getStoredTenant(): TenantLike | null {
    const raw = safeGetItem('tenant');
    if (!raw) return null;

    try {
      return JSON.parse(raw) as TenantLike;
    } catch {
      return null;
    }
  }

  getStoredPlan(): TenantPlanLike | null {
    const tenant = this.getStoredTenant();
    if (!tenant) return null;
    const plan = tenant.subscription_plan_details || tenant.subscription_plan;
    return typeof plan === 'object' ? plan as TenantPlanLike : null;
  }

  getPlanName(): string {
    const plan = this.getStoredPlan();
    const tenant = this.getStoredTenant();
    const planName = String(plan?.display_name || plan?.name || tenant?.plan_type || '');
    return planName || 'Trial';
  }

  hasFeature(featureName: string): boolean {
    const features = this.getStoredPlan()?.features;
    return !!features && !!features[featureName];
  }

  canAccessFeature(featureName: string): boolean {
    const plan = this.getStoredPlan();
    const features = plan?.features;

    if (features && typeof features === 'object' && featureName in features) {
      return !!features[featureName];
    }

    const currentPlan = this.getCurrentPlanKey();
    const featureMatrix: Record<string, string[]> = {
      basic: ['basic_reports', 'cash_register', 'client_history'],
      standard: ['basic_reports', 'cash_register', 'client_history', 'inventory', 'advanced_reports'],
      premium: ['basic_reports', 'cash_register', 'client_history', 'inventory', 'advanced_reports', 'multi_location', 'role_permissions', 'custom_branding'],
      enterprise: ['basic_reports', 'cash_register', 'client_history', 'inventory', 'advanced_reports', 'multi_location', 'role_permissions', 'custom_branding', 'export_reports', 'priority_support', 'whatsapp_notifications']
    };

    return (featureMatrix[currentPlan] || []).includes(featureName);
  }

  getUserLimitStatus(currentUsers: number): PlanLimitStatus {
    const plan = this.getStoredPlan();
    const limit = Number(plan?.max_users || 0);
    return this.buildLimitStatus(currentUsers, limit);
  }

  getEmployeeLimitStatus(currentEmployees: number): PlanLimitStatus {
    const plan = this.getStoredPlan();
    const limit = Number(plan?.max_employees || 0);
    return this.buildLimitStatus(currentEmployees, limit);
  }

  getUserLimitMessage(status: PlanLimitStatus): string {
    return `Has alcanzado el límite de usuarios de ${status.planName} (${status.current}/${status.limit}). Actualiza tu plan para seguir agregando usuarios.`;
  }

  getEmployeeLimitMessage(status: PlanLimitStatus): string {
    return `Has alcanzado el límite de usuarios activos de ${status.planName} (${status.current}/${status.limit}). Actualiza tu plan para seguir agregando personal.`;
  }

  getUpgradeRecommendation(limitType: 'users' | 'employees', contextText?: string): UpgradeRecommendation | null {
    const currentPlan = this.getCurrentPlanKey(contextText);

    if (currentPlan === 'basic') {
      return {
        nextPlanName: 'Pro',
        reason: limitType === 'employees'
          ? 'Necesitas más usuarios activos para seguir sumando personal.'
          : 'Necesitas más capacidad para seguir sumando usuarios internos.',
        detail: 'Pro te lleva a 15 empleados y 30 usuarios, ademas de inventario y reportes avanzados.'
      };
    }

    if (currentPlan === 'standard') {
      return {
        nextPlanName: 'Business',
        reason: limitType === 'employees'
          ? 'Tu operación ya pide más usuarios activos sin topes fijos para seguir creciendo.'
          : 'Tu operación ya pide más usuarios y una capa más premium.',
        detail: 'Business te lleva a 50 empleados, 100 usuarios, multi-sucursal, permisos avanzados y branding.'
      };
    }

    if (currentPlan === 'premium') {
      return {
        nextPlanName: 'Enterprise',
        reason: 'Has llegado al limite del plan Business.',
        detail: 'Enterprise te ofrece empleados y usuarios ilimitados, exportacion de reportes y soporte prioritario.'
      };
    }

    return null;
  }

  getFeatureUpgradeRecommendation(featureName: string): UpgradeRecommendation | null {
    const currentPlan = this.getCurrentPlanKey();

      if (featureName === 'inventory' || featureName === 'advanced_reports') {
      if (currentPlan === 'basic') {
        return {
          nextPlanName: 'Pro',
          reason: 'Tu plan actual no incluye esta funcionalidad operativa.',
          detail: 'Pro habilita inventario y reportes avanzados para crecer con mas control.'
        };
      }
    }

    if (featureName === 'multi_location' || featureName === 'custom_branding' || featureName === 'role_permissions') {
      if (currentPlan === 'standard') {
        return {
          nextPlanName: 'Business',
          reason: 'Esta funcionalidad esta disponible desde el plan Business.',
          detail: 'Business agrega multi-sucursal, permisos avanzados y branding personalizado.'
        };
      }
    }

    if (featureName === 'export_reports' || featureName === 'priority_support' || featureName === 'whatsapp_notifications') {
      return {
        nextPlanName: 'Enterprise',
        reason: 'Esta funcionalidad es exclusiva del plan Enterprise.',
        detail: 'Enterprise incluye exportacion de reportes, notificaciones por WhatsApp y soporte prioritario.'
      };
    }

    return null;
  }

  private getCurrentPlanKey(contextText?: string): string {
    const tenant = this.getStoredTenant();
    const rawPlan =
      tenant?.subscription_plan?.name ||
      tenant?.subscription_plan?.display_name ||
      tenant?.plan_type ||
      this.inferPlanFromText(contextText) ||
      '';

    const normalized = String(rawPlan).trim().toLowerCase();

    if (['basic', 'professional', 'profesional', 'esencial'].includes(normalized)) {
      return 'basic';
    }

    if (['standard', 'pro', 'crecimiento'].includes(normalized)) {
      return 'standard';
    }

    if (['premium', 'business', 'escala'].includes(normalized)) {
      return 'premium';
    }

    if (['enterprise'].includes(normalized)) {
      return 'enterprise';
    }

    return '';
  }

  private inferPlanFromText(contextText?: string): string {
    const normalized = String(contextText || '').trim().toLowerCase();

    if (!normalized) {
      return '';
    }

    if (normalized.includes('plan basic') || normalized.includes('professional') || normalized.includes('profesional') || normalized.includes('esencial')) {
      return 'basic';
    }

    if (normalized.includes('plan standard') || normalized.includes('pro') || normalized.includes('crecimiento')) {
      return 'standard';
    }

    if (normalized.includes('premium') || normalized.includes('business') || normalized.includes('escala')) {
      return 'premium';
    }

    if (normalized.includes('enterprise')) {
      return 'enterprise';
    }

    return '';
  }

  private buildLimitStatus(current: number, limit: number): PlanLimitStatus {
    const unlimited = limit === 0;
    return {
      reached: !unlimited && current >= limit,
      current,
      limit,
      unlimited,
      planName: this.getPlanName()
    };
  }
}
