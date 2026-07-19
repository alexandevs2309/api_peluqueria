import { TenantService } from '../../../core/services/tenant/tenant.service';

export interface TenantActionTarget {
    id?: number | null;
    is_active?: boolean | null;
    subscription_status?: string | null;
}

export function toggleTenantActive(
    tenantService: TenantService,
    tenant: TenantActionTarget,
    onSuccess: (message: string) => void,
    onError: (message: string, error?: unknown) => void
): void {
    if (!tenant.id) return;

    const action$ = tenant.is_active
        ? tenantService.deactivateTenant(tenant.id)
        : tenantService.activateTenant(tenant.id);

    action$.subscribe({
        next: () => onSuccess(tenant.is_active ? 'Tenant desactivado' : 'Tenant activado'),
        error: (error) => onError('No se pudo cambiar estado activo del tenant', error)
    });
}

export function toggleTenantSuspension(
    tenantService: TenantService,
    tenant: TenantActionTarget,
    onSuccess: (message: string) => void,
    onError: (message: string, error?: unknown) => void,
    promptMessage = 'Razón de suspensión:'
): void {
    if (!tenant.id) return;

    if (tenant.subscription_status === 'suspended') {
        tenantService.resumeTenant(tenant.id).subscribe({
            next: () => onSuccess('Suscripción reanudada'),
            error: (error) => onError('No se pudo reanudar suscripción', error)
        });
        return;
    }

    const reason = window.prompt(promptMessage) || 'Suspensión administrativa';
    tenantService.suspendTenant(tenant.id, reason).subscribe({
        next: () => onSuccess('Suscripción suspendida'),
        error: (error) => onError('No se pudo suspender suscripción', error)
    });
}
