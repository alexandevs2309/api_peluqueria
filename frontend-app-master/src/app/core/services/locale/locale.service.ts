import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { TRANSLATIONS, TranslationKey, SupportedLanguage, SUPPORTED_LANGUAGES } from './translations';
import { AppConfigService } from '../app-config.service';

export interface TenantLocaleConfig {
  locale: string;
  currency: string;
  dateFormat: string;
  timeZone: string;
}

export interface LanguageOption {
  code: SupportedLanguage;
  label: string;
  nativeLabel: string;
  shortLabel: string;
  region: string;
  locale: string;
  icon: string;
}

@Injectable({
  providedIn: 'root'
})
export class LocaleService {
  private readonly relativeTimeFormatters = new Map<string, Intl.RelativeTimeFormat>();
  private readonly languageOptions: LanguageOption[] = [
    { code: 'es', label: 'Spanish', nativeLabel: 'Español', shortLabel: 'ES', region: 'Latam y Caribe', locale: 'es-DO', icon: '🇩🇴' },
    { code: 'en', label: 'English', nativeLabel: 'English', shortLabel: 'EN', region: 'Global', locale: 'en-US', icon: '🇺🇸' },
    { code: 'fr', label: 'French', nativeLabel: 'Français', shortLabel: 'FR', region: 'Europa y Canadá', locale: 'fr-FR', icon: '🇫🇷' },
    { code: 'pt', label: 'Portuguese', nativeLabel: 'Português', shortLabel: 'PT', region: 'Brasil y Portugal', locale: 'pt-BR', icon: '🇧🇷' },
    { code: 'de', label: 'German', nativeLabel: 'Deutsch', shortLabel: 'DE', region: 'Alemania y DACH', locale: 'de-DE', icon: '🇩🇪' }
  ];

  private currentLocale = signal<TenantLocaleConfig>({
    locale: 'es-DO',
    currency: 'DOP',
    dateFormat: 'dd/MM/yyyy',
    timeZone: 'America/Santo_Domingo'
  });

  private currentLanguage = signal<SupportedLanguage>('es');
  public languageChanged$ = new BehaviorSubject<SupportedLanguage>('es');

  private readonly http = inject(HttpClient);
  private readonly appConfig = inject(AppConfigService);

  constructor() {
    const savedLang = localStorage.getItem('language');
    const lang = savedLang ? this.toSupportedLanguage(savedLang) : null;
    if (lang) {
      this.currentLanguage.set(lang);
      this.languageChanged$.next(lang);
    }
  }

  loadTenantLocaleFromBackend(tenantId?: number) {
    return this.http.get<TenantLocaleConfig>(`${environment.apiUrl}/tenants/locale/`, { withCredentials: true });
  }

  getCurrentLocale() {
    return this.currentLocale();
  }

  getCurrentLanguage(): SupportedLanguage {
    return this.currentLanguage();
  }

  setLanguage(lang: SupportedLanguage) {
    if (!this.getSupportedLanguageCodes().includes(lang)) {
      return;
    }

    if (this.currentLanguage() === lang) {
      return;
    }

    this.currentLanguage.set(lang);
    localStorage.setItem('language', lang);
    this.languageChanged$.next(lang);
  }

  getLanguageOptions(): LanguageOption[] {
    const allowed = this.getSupportedLanguageCodes();
    const filtered = this.languageOptions.filter((option) => allowed.includes(option.code));
    return filtered.length > 0 ? filtered : this.languageOptions;
  }

  getCurrentLanguageOption(): LanguageOption {
    const options = this.getLanguageOptions();
    return options.find((option) => option.code === this.currentLanguage()) || options[0];
  }

  getCurrentAppLocale(): string {
    return this.getCurrentLanguageOption().locale;
  }

  formatDate(value: Date | string | number, options?: Intl.DateTimeFormatOptions): string {
    const date = new Date(value);
    return new Intl.DateTimeFormat(this.getCurrentAppLocale(), options).format(date);
  }

  formatTime(value: Date | string | number, options?: Intl.DateTimeFormatOptions): string {
    const date = new Date(value);
    return new Intl.DateTimeFormat(this.getCurrentAppLocale(), {
      hour: '2-digit',
      minute: '2-digit',
      ...(options || {})
    }).format(date);
  }

  formatRelativeTime(value: Date | string | number): string {
    const date = new Date(value);
    const diffMs = date.getTime() - Date.now();
    const diffMinutes = Math.round(diffMs / 60000);
    const absMinutes = Math.abs(diffMinutes);

    let unit: Intl.RelativeTimeFormatUnit = 'minute';
    let valueToFormat = diffMinutes;

    if (absMinutes >= 1440) {
      unit = 'day';
      valueToFormat = Math.round(diffMinutes / 1440);
    } else if (absMinutes >= 60) {
      unit = 'hour';
      valueToFormat = Math.round(diffMinutes / 60);
    }

    const locale = this.getCurrentAppLocale();
    if (!this.relativeTimeFormatters.has(locale)) {
      this.relativeTimeFormatters.set(locale, new Intl.RelativeTimeFormat(locale, { numeric: 'auto' }));
    }

    return this.relativeTimeFormatters.get(locale)!.format(valueToFormat, unit);
  }

  getLanguageLabel(): string {
    return this.getCurrentLanguageOption().nativeLabel;
  }

  getLanguageShortLabel(): string {
    return this.getCurrentLanguageOption().shortLabel;
  }

  getLanguageIcon(): string {
    return this.getCurrentLanguageOption().icon;
  }

  translate(key: TranslationKey): string {
    const lang = this.currentLanguage();
    return TRANSLATIONS[lang][key] || TRANSLATIONS.es[key] || key;
  }

  t(key: TranslationKey): string {
    return this.translate(key);
  }

  setTenantLocale(tenantId: number) {
    // Deprecated: Configuration now loaded from backend
  }

  getDateFormat(): string {
    return this.currentLocale().dateFormat;
  }

  getCurrency(): string {
    return this.currentLocale().currency;
  }

  private getSupportedLanguageCodes(): SupportedLanguage[] {
    const configured = this.appConfig.supportedLanguages()
      .map((lang: string) => String(lang).trim().toLowerCase())
      .filter((lang: string): lang is SupportedLanguage => this.isSupportedLanguage(lang));

    return configured.length > 0 ? configured : this.languageOptions.map((option) => option.code);
  }

  private toSupportedLanguage(lang: string): SupportedLanguage | null {
    const normalized = lang.trim().toLowerCase();
    return this.isSupportedLanguage(normalized) ? normalized : null;
  }

  private isSupportedLanguage(lang: string): lang is SupportedLanguage {
    return SUPPORTED_LANGUAGES.includes(lang as SupportedLanguage);
  }
}
