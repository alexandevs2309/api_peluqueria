import { ChangeDetectorRef, OnDestroy, Pipe, PipeTransform } from '@angular/core';
import { Subscription } from 'rxjs';
import { LocaleService } from '../services/locale/locale.service';

@Pipe({
    name: 't',
    standalone: true,
    pure: false
})
export class I18nPipe implements PipeTransform, OnDestroy {
    private readonly subscription: Subscription;

    constructor(
        private readonly localeService: LocaleService,
        private readonly cdr: ChangeDetectorRef
    ) {
        let isFirst = true;
        this.subscription = this.localeService.languageChanged$.subscribe(() => {
            if (isFirst) {
                isFirst = false;
            } else {
                this.cdr.markForCheck();
            }
        });
    }

    transform(key: string, fallback?: string): string {
        const translated = this.localeService.t(key as any);
        if (translated === key && fallback) {
            return fallback;
        }
        return translated;
    }

    ngOnDestroy(): void {
        this.subscription.unsubscribe();
    }
}
