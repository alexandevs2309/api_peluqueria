import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class OptimizedAnimationService {
  private observer: IntersectionObserver | null = null;
  private animatedElements = new Set<Element>();

  init() {
    if (this.observer) return;

    this.observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        const element = entry.target as HTMLElement;
        if (entry.isIntersecting && !this.animatedElements.has(element)) {
          const direction = element.getAttribute('data-direction') || 'bottom';
          element.style.opacity = '1';
          element.style.transform = 'translateX(0) translateY(0) scale(1)';
          element.style.transition = 'all 0.6s ease';
          this.animatedElements.add(element);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -20px 0px' });

    document.querySelectorAll('.animate-on-scroll').forEach(el => {
      this.observer?.observe(el);
    });
  }

  destroy() {
    this.observer?.disconnect();
    this.observer = null;
    this.animatedElements.clear();
  }
}