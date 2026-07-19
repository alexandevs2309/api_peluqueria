import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { shareReplay, tap } from 'rxjs/operators';
import { environment } from '../../../../environments/environment';

export interface AppSettings {
  currency: string;
  currency_symbol: string;
  name?: string;
}

export interface BarbershopSettingsResponse extends AppSettings {
  logo?: string | null;
  brand_colors?: {
    primary: string;
    secondary: string;
    accent: string;
  };
  pos_config?: {
    business_name?: string;
    rnc?: string;
    address?: string;
    phone?: string;
    email?: string;
    website?: string;
  } | null;
  service_discount_limit?: number | null;
  business_hours?: Record<string, { open: string; close: string; closed: boolean }>;
  contact?: {
    phone: string;
    email: string;
    address: string;
  };
  currency_locked?: boolean;
  currency_lock_reason?: string;
}

@Injectable({
  providedIn: 'root'
})
export class SettingsService {
  private settingsSubject = new BehaviorSubject<AppSettings>({
    currency: 'DOP',
    currency_symbol: 'RD$'
  });

  public settings$ = this.settingsSubject.asObservable();
  public settings = signal<AppSettings>({ currency: 'DOP', currency_symbol: 'RD$' });
  private settingsRequest$?: Observable<BarbershopSettingsResponse>;

  constructor(private http: HttpClient) {
    this.loadSettings().subscribe({
      error: () => {
        // Mantener fallback local si el endpoint no responde.
      }
    });
  }

  loadSettings(): Observable<BarbershopSettingsResponse> {
    return this.getBarbershopSettings();
  }

  getBarbershopSettings(forceRefresh = false): Observable<BarbershopSettingsResponse> {
    if (!forceRefresh && this.settingsRequest$) {
      return this.settingsRequest$;
    }

    this.settingsRequest$ = this.http.get<BarbershopSettingsResponse>(`${environment.apiUrl}/settings/barbershop/`).pipe(
      tap((data: BarbershopSettingsResponse) => {
        const settings: AppSettings = {
          currency: data.currency || 'DOP',
          currency_symbol: data.currency_symbol || 'RD$',
          name: data.name
        };
        this.settingsSubject.next(settings);
        this.settings.set(settings);
      }),
      shareReplay({ bufferSize: 1, refCount: true })
    );

    return this.settingsRequest$;
  }

  getBarbershopAdminSettings(): Observable<BarbershopSettingsResponse> {
    return this.http.get<BarbershopSettingsResponse>(`${environment.apiUrl}/settings/barbershop/admin_settings/`);
  }

  updateBarbershopSettings(payload: unknown): Observable<any> {
    this.settingsRequest$ = undefined;
    return this.http.post(`${environment.apiUrl}/settings/barbershop/`, payload);
  }

  uploadBarbershopLogo(formData: FormData): Observable<{ logo_url: string }> {
    this.settingsRequest$ = undefined;
    return this.http.post<{ logo_url: string }>(`${environment.apiUrl}/settings/barbershop/upload_logo/`, formData);
  }

  getCurrency(): string {
    return this.settings().currency;
  }

  getCurrencySymbol(): string {
    return this.settings().currency_symbol;
  }

  getCurrencyLocale(): string {
    const currency = this.getCurrency();
    const localeMap: Record<string, string> = {
      DOP: 'es-DO',
      COP: 'es-CO',
      USD: 'en-US',
      EUR: 'es-ES'
    };
    return localeMap[currency] || 'es-DO';
  }

  getWhatsAppStatus(): Observable<any> {
    return this.http.get(`${environment.apiUrl}/settings/barbershop/whatsapp_status/`);
  }

  connectWhatsApp(): Observable<any> {
    return this.http.post(`${environment.apiUrl}/settings/barbershop/whatsapp_connect/`, {});
  }

  disconnectWhatsApp(): Observable<any> {
    return this.http.post(`${environment.apiUrl}/settings/barbershop/whatsapp_disconnect/`, {});
  }
}

