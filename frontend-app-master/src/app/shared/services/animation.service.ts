import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class AnimationService {
  private observer: IntersectionObserver | null = null;

  initScrollAnimations() {
    if (this.observer) {
      this.observer.disconnect();
    }

    this.observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        const element = entry.target as HTMLElement;
        
        if (entry.isIntersecting) {
          const direction = element.getAttribute('data-direction') || 'bottom';
          
          // Remover clases anteriores
          element.classList.remove('animate-slide-in-left', 'animate-slide-in-right', 'animate-slide-in-top', 'animate-slide-in-bottom');
          
          // Aplicar animación según dirección
          setTimeout(() => {
            switch(direction) {
              case 'left':
                element.classList.add('animate-slide-in-left');
                break;
              case 'right':
                element.classList.add('animate-slide-in-right');
                break;
              case 'top':
                element.classList.add('animate-slide-in-top');
                break;
              case 'bottom':
                element.classList.add('animate-slide-in-bottom');
                break;
            }
          }, 50);
        } else {
          // Resetear cuando sale de vista para repetir animación
          element.classList.remove('animate-slide-in-left', 'animate-slide-in-right', 'animate-slide-in-top', 'animate-slide-in-bottom');
        }
      });
    }, {
      threshold: 0.2,
      rootMargin: '0px 0px -50px 0px'
    });

    // Observar elementos con clase animate-on-scroll
    setTimeout(() => {
      const elements = document.querySelectorAll('.animate-on-scroll');
      elements.forEach(element => {
        this.observer?.observe(element);
      });
    }, 100);
  }

  destroy() {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }
  }
}