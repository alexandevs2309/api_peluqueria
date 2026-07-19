import { Injectable, signal, effect } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  private readonly THEME_KEY = 'app-theme';
  
  isDarkMode = signal<boolean>(false);
  
  constructor() {
    this.initializeTheme();
    
    // Effect para aplicar cambios automáticamente
    effect(() => {
      this.applyTheme(this.isDarkMode());
    });
  }
  
  private initializeTheme(): void {
    const savedTheme = localStorage.getItem(this.THEME_KEY);
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    const isDark = savedTheme === 'dark' || (!savedTheme && prefersDark);
    this.isDarkMode.set(isDark);
  }
  
  toggleTheme(): void {
    this.isDarkMode.update(current => !current);
  }
  
  setTheme(isDark: boolean): void {
    this.isDarkMode.set(isDark);
  }
  
  private applyTheme(isDark: boolean): void {
    const root = document.documentElement;
    
    if (isDark) {
      root.classList.add('app-dark');
      localStorage.setItem(this.THEME_KEY, 'dark');
    } else {
      root.classList.remove('app-dark');
      localStorage.setItem(this.THEME_KEY, 'light');
    }
  }
  
  getCurrentTheme(): 'light' | 'dark' {
    return this.isDarkMode() ? 'dark' : 'light';
  }
  
  get isLight(): boolean {
    return !this.isDarkMode();
  }
  
  getThemeClass(lightClass: string, darkClass: string): string {
    return this.isDarkMode() ? darkClass : lightClass;
  }
}
