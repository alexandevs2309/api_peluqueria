import { Injectable, signal, computed, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { CashRegisterState } from '../interfaces/employee.interface';
import { catchError, EMPTY } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class CashRegisterStateService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/pos/cashregisters/`;

  currentRegister = signal<CashRegisterState | null>(null);
  
  isOpen = computed(() => this.currentRegister()?.is_open ?? false);
  currentAmount = computed(() => this.currentRegister()?.current_amount ?? 0);

  loadCurrentRegister() {
    this.http.get<CashRegisterState[]>(`${this.apiUrl}`)
      .pipe(catchError(() => EMPTY))
      .subscribe(data => {
        // Get the first (current) cash register from array
        const current = Array.isArray(data) && data.length > 0 ? data[0] : null;
        this.currentRegister.set(current);
      });
  }

  syncWithEarnings() {
    // Notificar cambios a módulos dependientes
    this.loadCurrentRegister();
  }
}