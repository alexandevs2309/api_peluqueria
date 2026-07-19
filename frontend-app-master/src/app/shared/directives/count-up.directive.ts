import { Directive, ElementRef, Input, AfterViewInit, OnDestroy } from '@angular/core';

@Directive({
    selector: '[appCountUp]',
    standalone: true
})
export class CountUpDirective implements AfterViewInit, OnDestroy {
    @Input({ required: true }) appCountUp: number = 0;
    @Input() duration: number = 1500;

    private observer: IntersectionObserver | null = null;

    constructor(private el: ElementRef<HTMLElement>) {}

    ngAfterViewInit() {
        if (typeof IntersectionObserver === 'undefined') {
            this.setFinal();
            return;
        }
        this.observer = new IntersectionObserver(([entry]) => {
            if (entry.isIntersecting) {
                this.animate();
                this.observer?.unobserve(this.el.nativeElement);
            }
        }, { threshold: 0.3 });
        this.observer.observe(this.el.nativeElement);
    }

    private animate() {
        const start = performance.now();
        const target = this.appCountUp;
        const isFloat = target % 1 !== 0;
        const duration = this.duration;

        const tick = (now: number) => {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = eased * target;
            this.el.nativeElement.textContent = isFloat
                ? current.toFixed(1)
                : Math.round(current).toString();
            if (progress < 1) {
                requestAnimationFrame(tick);
            }
        };
        requestAnimationFrame(tick);
    }

    private setFinal() {
        this.el.nativeElement.textContent = this.appCountUp.toString();
    }

    ngOnDestroy() {
        this.observer?.disconnect();
    }
}
