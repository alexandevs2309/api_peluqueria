import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { BehaviorSubject } from 'rxjs';
import { roleKey } from '../../core/utils/role-normalizer';
import { safeGetItem } from '../../core/utils/storage';

export interface BarbershopSettings {
  name: string;
  logo?: string;
  brand_colors?: {
    primary: string;
    secondary: string;
    accent: string;
  };
  currency: string;
  currency_symbol: string;
  business_hours: {
    [key: string]: {
      open: string;
      close: string;
      closed: boolean;
    };
  };
  contact: {
    phone: string;
    email: string;
    address: string;
  };
}

@Injectable({
  providedIn: 'root'
})
export class BarbershopSettingsService {
  private http = inject(HttpClient);
  
  private settingsSubject = new BehaviorSubject<BarbershopSettings>({
    name: '',
    brand_colors: {
      primary: '#2563EB',
      secondary: '#4F46E5',
      accent: '#059669',
    },
    currency: 'COP',
    currency_symbol: '$',
    business_hours: {
      monday: { open: '08:00', close: '18:00', closed: false },
      tuesday: { open: '08:00', close: '18:00', closed: false },
      wednesday: { open: '08:00', close: '18:00', closed: false },
      thursday: { open: '08:00', close: '18:00', closed: false },
      friday: { open: '08:00', close: '18:00', closed: false },
      saturday: { open: '08:00', close: '16:00', closed: false },
      sunday: { open: '10:00', close: '14:00', closed: true }
    },
    contact: {
      phone: '',
      email: '',
      address: ''
    }
  });

  settings$ = this.settingsSubject.asObservable();
  settings = signal<BarbershopSettings>(this.settingsSubject.value);

  constructor() {
    // Solo cargar si no es SUPER_ADMIN
    const userStr = safeGetItem('user');
    if (userStr) {
      const user = JSON.parse(userStr);
      if (roleKey(user.role) !== 'SUPER_ADMIN') {
        this.loadSettings();
      }
    }
  }

  loadSettings() {
    this.http.get<BarbershopSettings>(`${environment.apiUrl}/settings/barbershop/`)
      .subscribe({
        next: (settings) => {
          if (settings.logo) {
            settings.logo = this.toAbsoluteUrl(settings.logo);
          }
          this.settingsSubject.next(settings);
          this.settings.set(settings);
        },
        error: () => {
          // Keep default settings
        }
      });
  }

  formatCurrency(amount: number): string {
    const settings = this.settings();
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: settings.currency,
      minimumFractionDigits: 0
    }).format(amount);
  }

  getCurrencySymbol(): string {
    return this.settings().currency_symbol;
  }

  getLogo(): string | null {
    const logo = this.settings().logo || null;
    if (!logo) return null;
    return this.toAbsoluteUrl(logo);
  }

  updateBusinessHours(day: string, field: 'open' | 'close' | 'closed', value: any) {
    this.settings.update(settings => ({
      ...settings,
      business_hours: {
        ...settings.business_hours,
        [day]: {
          ...settings.business_hours[day],
          [field]: value
        }
      }
    }));
  }

  getBusinessHour(day: string, field: 'open' | 'close' | 'closed'): any {
    return this.settings().business_hours[day]?.[field];
  }

  private toAbsoluteUrl(url: string): string {
    if (!url) return url;
    if (/^https?:\/\//i.test(url)) return url;
    const apiOrigin = new URL(environment.apiUrl).origin;
    return url.startsWith('/') ? `${apiOrigin}${url}` : `${apiOrigin}/${url}`;
  }
}
