import { Pipe, PipeTransform, inject } from '@angular/core';
import { SettingsService } from '../services/settings/settings.service';

@Pipe({
  name: 'appCurrency',
  standalone: true,
  pure: false
})
export class AppCurrencyPipe implements PipeTransform {
  private settingsService = inject(SettingsService);

  transform(value: number | null | undefined, decimals: string = '1.0-0'): string {
    if (value === null || value === undefined) {
      value = 0;
    }

    const currency = this.settingsService.getCurrency();
    const locale = this.settingsService.getCurrencyLocale();

    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: parseInt(decimals.split('-')[0].split('.')[1]),
      maximumFractionDigits: parseInt(decimals.split('-')[1])
    }).format(value);
  }
}
