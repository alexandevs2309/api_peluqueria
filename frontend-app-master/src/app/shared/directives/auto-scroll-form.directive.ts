import { Directive, HostListener, ElementRef } from '@angular/core';

@Directive({
    selector: 'form[appAutoScroll]',
    standalone: true
})
export class AutoScrollFormDirective {
    constructor(private el: ElementRef<HTMLFormElement>) {}

    @HostListener('ngSubmit')
    scrollToFirstError(): void {
        setTimeout(() => {
            const form = this.el.nativeElement;
            const invalid = form.querySelector<HTMLElement>('.ng-invalid');
            if (invalid) {
                const target = invalid.closest<HTMLElement>('[formGroupName], [formArrayName], .p-field, .field, .mb-3, [style*="flex"], p-select, p-inputnumber, p-inputmask') || invalid;
                target.scrollIntoView({ behavior: 'smooth', block: 'center' });
                const input = target.querySelector('input, textarea, select, [role="combobox"]') as HTMLElement | null;
                input?.focus({ preventScroll: true });
            }
        }, 100);
    }
}
