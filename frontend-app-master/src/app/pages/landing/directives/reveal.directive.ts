import { Directive, ElementRef, Input, AfterViewInit, OnDestroy, inject } from '@angular/core';

@Directive({
    selector: '[auReveal]',
    standalone: true,
})
export class RevealDirective implements AfterViewInit, OnDestroy {
    @Input() auRevealDelay = 0;
    @Input() auRevealThreshold = 0.12;

    private readonly el = inject(ElementRef);
    private observer?: IntersectionObserver;

    ngAfterViewInit(): void {
        const element = this.el.nativeElement as HTMLElement;

        if (typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            element.classList.add('au-revealed');
            return;
        }

        if (!element.classList.contains('au-reveal') &&
            !element.classList.contains('au-reveal-left') &&
            !element.classList.contains('au-reveal-scale')) {
            element.classList.add('au-reveal');
        }

        this.observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting) {
                    setTimeout(() => {
                        element.classList.add('au-revealed');
                    }, this.auRevealDelay);
                    this.observer?.disconnect();
                }
            },
            {
                threshold: this.auRevealThreshold,
                rootMargin: '0px 0px -50px 0px',
            }
        );

        this.observer.observe(element);
    }

    ngOnDestroy(): void {
        this.observer?.disconnect();
    }
}
