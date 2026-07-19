import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { TrialService } from '../services/trial.service';

export const TrialGuard: CanActivateFn = (route, state) => {
  const trialService = inject(TrialService);
  const router = inject(Router);

  return trialService.getSubscriptionStatus().pipe(
    map((status) => {
      if (status === 'expired' || status === 'payment_required') {
        void router.navigate(['/client/payment']);
        return false;
      }
      return true;
    }),
    catchError(() => {
      void router.navigate(['/client/payment']);
      return of(false);
    }),
  );
};
