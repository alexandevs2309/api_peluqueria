import { Injectable, inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivate, Router } from '@angular/router';
import { of } from 'rxjs';
import { PlanAccessService } from '../services/plan-access.service';
import { MessageService } from 'primeng/api';
import { AccessDeniedDialogService } from '../services/access-denied-dialog.service';

@Injectable({
  providedIn: 'root'
})
export class FeatureAccessGuard implements CanActivate {
  private readonly router = inject(Router);
  private readonly planAccessService = inject(PlanAccessService);
  private readonly messageService = inject(MessageService);
  private readonly accessDeniedDialog = inject(AccessDeniedDialogService);

  canActivate(route: ActivatedRouteSnapshot) {
    const requiredFeature = String(route.data?.['requiredFeature'] || '').trim();
    if (!requiredFeature || this.planAccessService.canAccessFeature(requiredFeature)) {
      return of(true);
    }

    const recommendation = this.planAccessService.getFeatureUpgradeRecommendation(requiredFeature);
    const detail = recommendation
      ? `${recommendation.reason} ${recommendation.detail}`
      : 'Tu plan actual no incluye esta funcionalidad.';

    this.router.navigate(['/client/dashboard']).then(() => {
      this.accessDeniedDialog.show({
        title: recommendation ? 'Mejora de Plan Requerida' : 'Funcionalidad Limitada',
        message: detail,
        primaryButtonLabel: recommendation ? 'Ver Planes' : 'Entendido',
        primaryButtonAction: () => {
          if (recommendation) {
            this.router.navigate(['/client/payment']);
          } else {
            this.router.navigate(['/client/dashboard']);
          }
        },
        secondaryButtonLabel: recommendation ? 'Ir al Dashboard' : '',
        secondaryButtonAction: () => {
          this.router.navigate(['/client/dashboard']);
        },
        icon: recommendation ? 'pi-sparkles' : 'pi-lock',
        iconColor: 'text-violet-600 dark:text-violet-400',
        iconBgColor: 'bg-violet-50 dark:bg-violet-950/20'
      });
    });
    return of(false);
  }
}
