import { Component, inject, signal, computed, OnInit, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AuSkeleton } from '../../../shared/components';
import { TutorialsService, TutorialDto, getYouTubeThumbnail } from '../../../core/services/tutorials/tutorials.service';
import { VideoModal } from './video-modal';

interface ModuleOption {
  value: string;
  label: string;
  icon: string;
  color: string;
}

@Component({
  selector: 'app-tutorials',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, AuSkeleton, VideoModal],
  template: `
    <nav class="tut-nav" [class.is-scrolled]="scrolled">
      <div class="tut-nav-inner">
        <a class="tut-nav-logo" routerLink="/landing">
          <img src="assets/logos/logo-final.png" alt="Auron" class="tut-nav-logo-img" />
          <span class="tut-nav-brand">Auron Suite</span>
        </a>
        <div class="tut-nav-links">
          <a routerLink="/landing" class="tut-nav-link">Inicio</a>
          <a routerLink="/tutorials" class="tut-nav-link is-active">Gu&iacute;as</a>
          <a routerLink="/support" class="tut-nav-link">Soporte</a>
        </div>
      </div>
    </nav>

    <header class="tut-hero">
      <div class="tut-hero-bg"></div>
      <div class="tut-hero-glow g1"></div>
      <div class="tut-hero-glow g2"></div>
      <div class="tut-hero-inner">
        <div class="tut-hero-badge">
          <i class="pi pi-play-circle"></i>
          Gu&iacute;as interactivas
        </div>
        <h1 class="tut-hero-title">Aprende a usar <br class="hide-sm" />Auron Suite</h1>
        <p class="tut-hero-sub">
          Videos cortos y pr&aacute;cticos para cada m&oacute;dulo.
          Tu equipo al d&iacute;a en minutos.
        </p>

        <div class="tut-hero-search">
          <i class="pi pi-search tut-hero-search-icon"></i>
          <input class="tut-hero-search-input" type="text" placeholder="Buscar tutoriales..."
                 [ngModel]="query()" (ngModelChange)="query.set($event)" />
          @if (query()) {
            <button class="tut-hero-search-clear" (click)="query.set('')">
              <i class="pi pi-times"></i>
            </button>
          }
        </div>

        <div class="tut-hero-pills">
          <button class="tut-pill"
                  [class.is-active]="!selectedModule()"
                  (click)="filterByModule('')">
            <i class="pi pi-th-large"></i>
            Todos
            @if (tutorials().length) {
              <span class="tut-pill-count">{{ tutorials().length }}</span>
            }
          </button>
          @for (m of modules | keyvalue; track m.key) {
            @if (moduleCount(m.key) > 0) {
              <button class="tut-pill"
                      [class.is-active]="selectedModule() === m.key"
                      (click)="filterByModule(m.key)">
                <span>{{ m.value.icon }}</span>
                {{ m.value.label }}
                <span class="tut-pill-count">{{ moduleCount(m.key) }}</span>
              </button>
            }
          }
        </div>
      </div>
      <div class="tut-hero-wave"></div>
    </header>

    <main class="tut-main">
      <div class="tut-main-bg" aria-hidden="true">
        <div class="tut-main-glow g1"></div>
        <div class="tut-main-glow g2"></div>
      </div>
      @if (loading()) {
        <div class="tut-skeleton-grid">
          @for (i of [1,2,3,4,5,6]; track i) {
            <div class="tut-skeleton-card">
              <au-skeleton height="180px" />
              <div class="p-3">
                <au-skeleton height="10px" width="35%" class="mb-2" />
                <au-skeleton height="16px" class="mb-1" />
                <au-skeleton height="16px" width="65%" />
              </div>
            </div>
          }
        </div>
      } @else {

        @if (filteredTutorials().length === 0) {
          <div class="tut-empty">
            @if (query() && selectedModule()) {
              <div class="tut-empty-icon"><i class="pi pi-search"></i></div>
              <h3 class="tut-empty-title">Sin resultados</h3>
              <p class="tut-empty-sub">No hay tutoriales en <strong>{{ getModuleLabel(selectedModule()) }}</strong> que coincidan con &laquo;{{ query() }}&raquo;</p>
            } @else if (query()) {
              <div class="tut-empty-icon"><i class="pi pi-search"></i></div>
              <h3 class="tut-empty-title">Sin resultados</h3>
              <p class="tut-empty-sub">No hay tutoriales que coincidan con &laquo;{{ query() }}&raquo;</p>
            } @else if (selectedModule()) {
              <div class="tut-empty-icon"><i class="pi pi-folder-open"></i></div>
              <h3 class="tut-empty-title">M&oacute;dulo sin tutoriales</h3>
              <p class="tut-empty-sub">{{ getModuleLabel(selectedModule()) }} a&uacute;n no tiene tutoriales.</p>
            } @else {
              <div class="tut-empty-icon"><i class="pi pi-video"></i></div>
              <h3 class="tut-empty-title">Sin tutoriales</h3>
              <p class="tut-empty-sub">No hay tutoriales disponibles. Vuelve pronto.</p>
            }
            <button class="tut-empty-btn" (click)="clearFilters()">
              <i class="pi pi-arrow-left"></i> Limpiar filtros
            </button>
          </div>
        } @else {

          @if (selectedModule()) {
            <div class="tut-content-card">
              <div class="tut-section-header">
                <span class="tut-section-header-icon">{{ getModuleIcon(selectedModule()) }}</span>
                <div>
                  <h2 class="tut-section-header-title">{{ getModuleLabel(selectedModule()) }}</h2>
                  <p class="tut-section-header-sub">{{ filteredTutorials().length }} tutorial{{ filteredTutorials().length !== 1 ? 'es' : '' }}</p>
                </div>
              </div>
              <div class="tut-grid">
                @for (t of filteredTutorials(); track t.id; let i = $index) {
                  <div class="tut-card" [style.animation-delay]="i * 60 + 'ms'" (click)="openTutorial(t)">
                    <div class="tut-card-thumb">
                      @if (t.thumbnail_url) {
                        <img [src]="t.thumbnail_url" [alt]="t.title" class="tut-card-img" loading="lazy" />
                      } @else {
                        <div class="tut-card-img-placeholder"><i class="pi pi-play-circle"></i></div>
                      }
                      <div class="tut-card-overlay"></div>
                      <div class="tut-card-play"><i class="pi pi-play"></i></div>
                      @if (t.duration) {
                        <span class="tut-card-duration"><i class="pi pi-clock"></i> {{ t.duration }}</span>
                      }
                    </div>
                    <div class="tut-card-body">
                      <span class="tut-card-module">{{ getModuleIcon(t.module) }} {{ t.module_label }}</span>
                      <h3 class="tut-card-title">{{ t.title }}</h3>
                      @if (t.description) {
                        <p class="tut-card-desc">{{ t.description }}</p>
                      }
                    </div>
                  </div>
                }
              </div>
            </div>
          } @else {
            <div class="tut-content-card">
              @for (section of groupedTutorials(); track section[0]) {
              <div class="tut-section">
                <div class="tut-section-header">
                  <span class="tut-section-header-icon">{{ getModuleIcon(section[0]) }}</span>
                  <div>
                    <h2 class="tut-section-header-title">{{ getModuleLabel(section[0]) }}</h2>
                    <p class="tut-section-header-sub">{{ section[1].length }} tutorial{{ section[1].length !== 1 ? 'es' : '' }}</p>
                  </div>
                </div>
                <div class="tut-strip">
                  @for (t of section[1]; track t.id; let i = $index) {
                  <div class="tut-card tut-card--strip"
                       [style.animation-delay]="i * 80 + 'ms'"
                       (click)="openTutorial(t)">
                    <div class="tut-card-thumb">
                      @if (t.thumbnail_url) {
                      <img [src]="t.thumbnail_url" [alt]="t.title" class="tut-card-img" loading="lazy" />
                      } @else {
                      <div class="tut-card-img-placeholder"><i class="pi pi-play-circle"></i></div>
                      }
                      <div class="tut-card-overlay"></div>
                      <div class="tut-card-play"><i class="pi pi-play"></i></div>
                      @if (t.duration) {
                      <span class="tut-card-duration"><i class="pi pi-clock"></i> {{ t.duration }}</span>
                      }
                    </div>
                    <div class="tut-card-body">
                      <h3 class="tut-card-title">{{ t.title }}</h3>
                      @if (t.description) {
                      <p class="tut-card-desc">{{ t.description }}</p>
                      }
                    </div>
                  </div>
                  }
                </div>
              </div>
              }
            </div>
          }

          <div class="tut-cta">
            <div class="tut-cta-icon"><i class="pi pi-headphones"></i></div>
            <h3 class="tut-cta-title">&iquest;No encuentras lo que buscas?</h3>
            <p class="tut-cta-sub">Nuestro equipo est&aacute; listo para ayudarte.</p>
            <a routerLink="/support" class="tut-cta-btn">
              <i class="pi pi-envelope"></i> Contactar soporte
            </a>
          </div>
        }
      }
    </main>

    <video-modal [(visible)]="showVideoModal" [videoUrlInput]="selectedVideoUrl" />
  `,
  styles: [`
    :host {
      --primary: #2563EB;
      --primary-light: #3B82F6;
      --primary-dark: #0055B0;
      --surface: #ffffff;
      --surface-2: #F5F7FA;
      --border: #E4E8F0;
      --text-1: #0A0F1E;
      --text-2: #4B5568;
      --text-3: #9CA3AF;
      --radius-sm: 12px;
      --radius-md: 16px;
      --radius-lg: 20px;
      --radius-full: 999px;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      display: block;
    }

    /* ══════════════════════════════════════════
       NAV
    ══════════════════════════════════════════ */
    .tut-nav {
      position: fixed; top: 0; left: 0; right: 0; z-index: 100;
      height: 56px;
      transition: background 0.35s ease, box-shadow 0.35s ease;
      border-bottom: 1px solid transparent;
    }
    .tut-nav { background: transparent; }
    .tut-nav.is-scrolled {
      background: rgba(255,255,255,0.88);
      backdrop-filter: blur(20px);
      border-bottom-color: rgba(0,0,0,0.08);
      box-shadow: 0 1px 20px rgba(0,0,0,0.06);
    }
    .tut-nav-inner {
      max-width: 1200px; margin: 0 auto; padding: 0 1.5rem;
      height: 100%; display: flex; align-items: center; gap: 1.5rem;
    }
    .tut-nav-logo {
      display: flex; align-items: center; gap: 0.6rem;
      text-decoration: none; flex-shrink: 0;
    }
    .tut-nav-logo-img {
      width: 30px; height: 30px; border-radius: 7px;
      object-fit: cover;
      border: 1px solid rgba(255,255,255,0.3);
      box-shadow: 0 2px 8px rgba(0,0,0,0.12);
    }
    .tut-nav-brand {
      font-size: 0.92rem; font-weight: 800;
      color: rgba(255,255,255,0.95);
      letter-spacing: -0.02em;
    }
    .tut-nav.is-scrolled .tut-nav-brand { color: var(--text-1); }
    .tut-nav-links {
      display: flex; align-items: center; gap: 1.5rem; flex: 1;
    }
    .tut-nav-link {
      font-size: 0.84rem; font-weight: 600;
      color: rgba(255,255,255,0.75);
      text-decoration: none; transition: color 0.2s ease;
    }
    .tut-nav-link:hover { color: #fff; }
    .tut-nav-link.is-active { color: #fff; }
    .tut-nav.is-scrolled .tut-nav-link { color: var(--text-2); }
    .tut-nav.is-scrolled .tut-nav-link:hover { color: var(--text-1); }
    .tut-nav.is-scrolled .tut-nav-link.is-active { color: var(--primary); }

    /* ══════════════════════════════════════════
       HERO
    ══════════════════════════════════════════ */
    .tut-hero {
      position: relative; overflow: hidden;
      background: linear-gradient(160deg, #001B3D 0%, #003D82 40%, #0066CC 100%);
      padding: 72px 0 0;
    }
    .tut-hero-bg {
      position: absolute; inset: 0;
      background-image: radial-gradient(rgba(255,255,255,0.06) 1px, transparent 1px);
      background-size: 24px 24px;
    }
    .tut-hero-glow {
      position: absolute; border-radius: 50%; pointer-events: none;
      filter: blur(70px);
      animation: tutFloat 8s ease-in-out infinite;
    }
    .tut-hero-glow.g1 {
      width: 500px; height: 500px;
      background: rgba(59,130,246,0.25);
      top: -200px; right: -100px;
      animation-delay: 0s;
    }
    .tut-hero-glow.g2 {
      width: 350px; height: 350px;
      background: rgba(167,139,250,0.15);
      bottom: -120px; left: 5%;
      animation-delay: -4s;
    }
    @keyframes tutFloat {
      0%, 100% { transform: translateY(0) scale(1); }
      50% { transform: translateY(-20px) scale(1.05); }
    }
    .tut-hero-inner {
      position: relative; z-index: 1;
      max-width: 800px; margin: 0 auto;
      padding: 4rem 1.5rem 3.5rem;
      text-align: center;
    }
    .tut-hero-badge {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 5px 14px; border-radius: var(--radius-full);
      background: rgba(255,255,255,0.1);
      border: 1px solid rgba(255,255,255,0.18);
      color: rgba(255,255,255,0.85);
      font-size: 0.72rem; font-weight: 600;
      letter-spacing: 0.06em; text-transform: uppercase;
      margin-bottom: 1.2rem;
      animation: tutPopIn 0.5s ease-out both;
    }
    .tut-hero-title {
      font-size: clamp(2.2rem, 5.5vw, 3.2rem);
      font-weight: 800; color: #fff;
      line-height: 1.1; letter-spacing: -0.03em;
      margin: 0 0 0.8rem;
      animation: tutPopIn 0.5s ease-out 0.1s both;
    }
    .tut-hero-sub {
      font-size: 1.02rem; color: rgba(255,255,255,0.65);
      line-height: 1.65; margin: 0 auto 1.5rem;
      max-width: 480px; font-weight: 400;
      animation: tutPopIn 0.5s ease-out 0.2s both;
    }
    .tut-hero-search {
      position: relative; max-width: 460px; margin: 0 auto 1.5rem;
      animation: tutPopIn 0.5s ease-out 0.3s both;
    }
    @keyframes tutPopIn {
      from { opacity: 0; transform: translateY(12px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .tut-hero-pills {
      display: flex; flex-wrap: wrap; justify-content: center; gap: 0.45rem;
      animation: tutPopIn 0.5s ease-out 0.4s both;
    }
    .tut-hero-search-icon {
      position: absolute; left: 16px; top: 50%; transform: translateY(-50%);
      font-size: 0.9rem; color: rgba(255,255,255,0.4); pointer-events: none;
    }
    .tut-hero-search-input {
      width: 100%; padding: 0.75rem 2.8rem 0.75rem 2.8rem;
      border-radius: var(--radius-full);
      border: 1.5px solid rgba(255,255,255,0.2);
      background: rgba(255,255,255,0.1);
      backdrop-filter: blur(12px);
      color: #fff; font-size: 0.92rem; outline: none;
      transition: border-color 0.25s ease, background 0.25s ease;
    }
    .tut-hero-search-input::placeholder { color: rgba(255,255,255,0.45); }
    .tut-hero-search-input:focus {
      border-color: rgba(255,255,255,0.4);
      background: rgba(255,255,255,0.15);
    }
    .tut-hero-search-clear {
      position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
      width: 28px; height: 28px; border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      border: none; background: rgba(255,255,255,0.12);
      color: rgba(255,255,255,0.6); cursor: pointer; font-size: 0.75rem;
      transition: background 0.2s ease;
    }
    .tut-hero-search-clear:hover { background: rgba(255,255,255,0.2); color: #fff; }

    .tut-pill {
      display: inline-flex; align-items: center; gap: 5px;
      padding: 0.45rem 1rem;
      border-radius: var(--radius-full);
      border: 1.5px solid rgba(255,255,255,0.15);
      background: rgba(255,255,255,0.06);
      color: rgba(255,255,255,0.7);
      font-size: 0.82rem; font-weight: 500;
      cursor: pointer; transition: all 0.2s ease;
      white-space: nowrap;
    }
    .tut-pill:hover {
      background: rgba(255,255,255,0.12);
      color: #fff;
      border-color: rgba(255,255,255,0.25);
    }
    .tut-pill.is-active {
      background: #fff;
      border-color: #fff;
      color: var(--primary);
      box-shadow: 0 3px 14px rgba(0,0,0,0.15);
    }
    .tut-pill-count {
      display: inline-flex; align-items: center; justify-content: center;
      min-width: 18px; height: 17px; padding: 0 5px;
      border-radius: var(--radius-full);
      font-size: 0.67rem; font-weight: 700;
      background: rgba(0,0,0,0.12);
    }
    .tut-pill.is-active .tut-pill-count {
      background: rgba(37,99,235,0.12);
    }
    .tut-hero-wave {
      position: absolute; bottom: -1px; left: 0; right: 0;
      height: 40px;
      background: var(--surface-2);
      border-radius: 28px 28px 0 0;
    }

    /* ══════════════════════════════════════════
       MAIN
    ══════════════════════════════════════════ */
    .tut-main {
      max-width: 1200px; margin: 0 auto;
      padding: 1.75rem 1.5rem 4rem;
      position: relative;
      z-index: 1;
      background: linear-gradient(
        180deg,
        rgba(37,99,235,0.02) 0%,
        transparent 120px
      );
    }

    .tut-main-bg {
      position: absolute; inset: 0;
      overflow: hidden; pointer-events: none;
      z-index: 0;
    }
    .tut-main-glow {
      position: absolute; border-radius: 50%; pointer-events: none;
      filter: blur(90px);
    }
    .tut-main-glow.g1 {
      width: 550px; height: 550px;
      background: radial-gradient(circle, rgba(37,99,235,0.12), transparent 70%);
      top: -200px; right: -120px;
    }
    .tut-main-glow.g2 {
      width: 400px; height: 400px;
      background: radial-gradient(circle, rgba(99,102,241,0.08), transparent 70%);
      bottom: -100px; left: 5%;
    }

    .tut-content-card {
      background: var(--surface);
      border-radius: var(--radius-lg);
      padding: 1.75rem 1.5rem;
      box-shadow: 0 8px 32px rgba(0,0,0,0.05), 0 0 0 1px rgba(0,0,0,0.02);
      position: relative;
      z-index: 2;
      margin-bottom: 1.5rem;
    }

    /* Section header */
    .tut-section-header {
      display: flex; align-items: center; gap: 0.75rem;
      margin-bottom: 1rem;
    }
    .tut-section-header-icon {
      width: 38px; height: 38px; border-radius: var(--radius-sm);
      background: var(--surface-2); border: 1.5px solid var(--border);
      display: flex; align-items: center; justify-content: center;
      font-size: 1.1rem; flex-shrink: 0;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .tut-section-header:hover .tut-section-header-icon {
      transform: scale(1.08);
      box-shadow: 0 3px 12px rgba(37,99,235,0.12);
    }
    .tut-section-header-title {
      font-size: 1.05rem; font-weight: 700; color: var(--text-1);
      margin: 0; line-height: 1.2;
    }
    .tut-section-header-sub {
      font-size: 0.78rem; color: var(--text-3); margin: 1px 0 0;
    }
    .tut-section {
      margin-bottom: 2rem;
      animation: tutFadeSection 0.5s ease-out both;
    }
    .tut-section:nth-child(2) { animation-delay: 0.1s; }
    .tut-section:nth-child(3) { animation-delay: 0.2s; }
    .tut-section:nth-child(4) { animation-delay: 0.3s; }
    @keyframes tutFadeSection {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* Strip */
    .tut-strip {
      display: flex; gap: 0.9rem; overflow-x: auto;
      padding-bottom: 0.6rem;
      scrollbar-width: thin; scrollbar-color: var(--border) transparent;
    }
    .tut-strip::-webkit-scrollbar { height: 4px; }
    .tut-strip::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }

    /* Grid */
    .tut-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 1rem;
    }

    /* Card */
    .tut-card {
      border-radius: var(--radius-md);
      overflow: hidden;
      background: var(--surface);
      border: 1.5px solid var(--border);
      box-shadow: 0 2px 10px rgba(0,0,0,0.04);
      cursor: pointer;
      animation: tutUp 0.35s ease-out both;
      transition: box-shadow 0.25s ease, transform 0.25s ease;
    }
    .tut-card:hover {
      box-shadow: 0 10px 30px rgba(0,0,0,0.08), 0 0 0 1.5px rgba(37,99,235,0.15);
      transform: translateY(-3px);
    }
    .tut-card--strip {
      flex-shrink: 0; width: 260px;
    }
    @keyframes tutUp {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .tut-card-thumb {
      position: relative; aspect-ratio: 16/9;
      overflow: hidden; background: #0A0F1E;
    }
    .tut-card-img { width: 100%; height: 100%; object-fit: cover; }
    .tut-card:hover .tut-card-img { transition: transform 0.5s ease; transform: scale(1.04); }
    .tut-card-img-placeholder {
      width: 100%; height: 100%;
      display: flex; align-items: center; justify-content: center;
      background: linear-gradient(135deg, rgba(37,99,235,0.08), rgba(59,130,246,0.1));
      font-size: 2rem; color: rgba(37,99,235,0.3);
    }
    .tut-card-overlay {
      position: absolute; inset: 0;
      background: linear-gradient(to top, rgba(0,0,0,0.5) 0%, transparent 55%);
      opacity: 0; transition: opacity 0.25s ease;
    }
    .tut-card:hover .tut-card-overlay { opacity: 1; }
    .tut-card-play {
      position: absolute; inset: 0;
      display: flex; align-items: center; justify-content: center;
      opacity: 0; transition: opacity 0.25s ease;
    }
    .tut-card:hover .tut-card-play { opacity: 1; }
    .tut-card-play i {
      width: 44px; height: 44px; border-radius: 50%;
      background: rgba(255,255,255,0.92);
      box-shadow: 0 4px 20px rgba(0,0,0,0.2);
      display: flex; align-items: center; justify-content: center;
      font-size: 0.95rem; color: var(--primary); padding-left: 3px;
    }
    .tut-card-duration {
      position: absolute; bottom: 8px; right: 8px;
      display: inline-flex; align-items: center; gap: 3px;
      padding: 2px 8px; border-radius: 5px;
      font-size: 0.68rem; font-weight: 600;
      background: rgba(0,0,0,0.6); color: #fff;
      backdrop-filter: blur(8px);
    }
    .tut-card-body {
      padding: 0.85rem 1rem 0.9rem;
      display: flex; flex-direction: column; gap: 0.25rem;
    }
    .tut-card-module {
      font-size: 0.68rem; font-weight: 600; color: var(--primary); opacity: 0.85;
    }
    .tut-card-title {
      font-size: 0.9rem; font-weight: 700; color: var(--text-1);
      line-height: 1.3; margin: 0;
      display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
    }
    .tut-card-desc {
      font-size: 0.78rem; color: var(--text-3); line-height: 1.5; margin: 0;
      display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
    }

    /* Skeleton */
    .tut-skeleton-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 1rem;
    }
    .tut-skeleton-card {
      border-radius: var(--radius-md); overflow: hidden;
      background: var(--surface); border: 1.5px solid var(--border);
    }

    /* Empty state */
    .tut-empty { text-align: center; padding: 4rem 1rem; }
    .tut-empty-icon {
      width: 68px; height: 68px; margin: 0 auto 1rem;
      border-radius: var(--radius-lg);
      background: var(--surface-2); border: 1.5px solid var(--border);
      display: flex; align-items: center; justify-content: center;
      font-size: 1.6rem; color: var(--text-3);
    }
    .tut-empty-title { font-size: 1.05rem; font-weight: 700; color: var(--text-2); margin: 0 0 0.3rem; }
    .tut-empty-sub { font-size: 0.85rem; color: var(--text-3); margin: 0 0 1.2rem; }
    .tut-empty-btn {
      display: inline-flex; align-items: center; gap: 5px;
      padding: 0.5rem 1.1rem; border-radius: var(--radius-full);
      background: var(--primary); color: #fff; font-size: 0.82rem; font-weight: 600;
      border: none; cursor: pointer; transition: background 0.2s ease;
    }
    .tut-empty-btn:hover { background: var(--primary-dark); }

    /* CTA */
    .tut-cta {
      margin-top: 2.5rem; padding: 2rem 1.5rem;
      border-radius: var(--radius-md);
      background: linear-gradient(135deg, rgba(37,99,235,0.04), rgba(59,130,246,0.06));
      border: 1.5px solid rgba(37,99,235,0.12);
      text-align: center;
    }
    .tut-cta-icon {
      width: 46px; height: 46px; margin: 0 auto 0.7rem;
      border-radius: var(--radius-sm);
      background: linear-gradient(135deg, var(--primary), var(--primary-light));
      display: flex; align-items: center; justify-content: center;
      font-size: 1.15rem; color: #fff;
      box-shadow: 0 5px 16px rgba(37,99,235,0.28);
      animation: tutCtaPulse 3s ease-in-out infinite;
    }
    @keyframes tutCtaPulse {
      0%, 100% { box-shadow: 0 5px 16px rgba(37,99,235,0.28); }
      50% { box-shadow: 0 8px 28px rgba(37,99,235,0.45), 0 0 0 4px rgba(37,99,235,0.08); }
    }
    .tut-cta-title { font-size: 1rem; font-weight: 700; color: var(--text-1); margin: 0 0 0.25rem; }
    .tut-cta-sub {
      font-size: 0.84rem; color: var(--text-2);
      max-width: 360px; margin: 0 auto 1rem; line-height: 1.5;
    }
    .tut-cta-btn {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 0.5rem 1.2rem; border-radius: var(--radius-full);
      background: var(--primary); color: #fff; font-size: 0.83rem; font-weight: 600;
      text-decoration: none; transition: background 0.2s ease;
      box-shadow: 0 3px 14px rgba(37,99,235,0.25);
    }
    .tut-cta-btn:hover { background: var(--primary-dark); }

    @media (max-width: 640px) {
      .tut-hero-inner { padding: 3rem 1rem 2.5rem; }
      .hide-sm { display: none; }
      .tut-hero-title br.hide-sm { display: none; }
    }

    :host-context(.app-dark) {
      --surface: #111827; --surface-2: #0D1117; --border: #1F2A3D;
      --text-1: #F0F4FF; --text-2: #94A3B8; --text-3: #475569;
    }
    :host-context(.app-dark) .tut-hero { background: linear-gradient(160deg, #000714 0%, #001B3D 50%, #002A5A 100%); }
    :host-context(.app-dark) .tut-hero-wave { background: var(--surface-2); }
    :host-context(.app-dark) .tut-nav.is-scrolled {
      background: rgba(10,15,30,0.9);
      border-bottom-color: rgba(255,255,255,0.06);
    }
    :host-context(.app-dark) .tut-nav.is-scrolled .tut-nav-brand { color: #F0F4FF; }
    :host-context(.app-dark) .tut-pill.is-active { background: var(--primary); color: #fff; border-color: var(--primary); }
    :host-context(.app-dark) .tut-pill.is-active .tut-pill-count { background: rgba(255,255,255,0.2); color: #fff; }
    :host-context(.app-dark) .tut-card:hover { box-shadow: 0 10px 30px rgba(0,0,0,0.4); }
    :host-context(.app-dark) .tut-content-card { box-shadow: 0 8px 32px rgba(0,0,0,0.2), 0 0 0 1px rgba(255,255,255,0.04); }
    :host-context(.app-dark) .tut-main { background: linear-gradient(180deg, rgba(37,99,235,0.06) 0%, transparent 120px); }
    :host-context(.app-dark) .tut-main-glow.g1 { background: radial-gradient(circle, rgba(59,130,246,0.2), transparent 70%); }
    :host-context(.app-dark) .tut-main-glow.g2 { background: radial-gradient(circle, rgba(99,102,241,0.15), transparent 70%); }
    :host-context(.app-dark) .tut-cta {
      background: rgba(37,99,235,0.06);
      border-color: rgba(37,99,235,0.2);
    }
  `]
})
export class TutorialsComponent implements OnInit {
  private readonly tutorialsService = inject(TutorialsService);

  tutorials = signal<TutorialDto[]>([]);
  loading = signal(true);
  selectedModule = signal('');
  query = signal('');
  scrolled = false;

  showVideoModal = false;
  selectedVideoUrl = '';

  readonly modules: Record<string, ModuleOption> = {
    appointments:  { value: 'appointments',  label: 'Citas',          icon: '📅', color: '#6366F1' },
    employees:     { value: 'employees',     label: 'Empleados',      icon: '👥', color: '#0EA5E9' },
    pos:           { value: 'pos',           label: 'POS',            icon: '💳', color: '#10B981' },
    inventory:     { value: 'inventory',     label: 'Inventario',     icon: '📦', color: '#F59E0B' },
    services:      { value: 'services',      label: 'Servicios',      icon: '✂️', color: '#EF4444' },
    clients:       { value: 'clients',       label: 'Clientes',       icon: '👤', color: '#8B5CF6' },
    reports:       { value: 'reports',       label: 'Reportes',       icon: '📊', color: '#14B8A6' },
    settings:      { value: 'settings',      label: 'Configuración',  icon: '⚙️', color: '#6B7280' },
    payroll:       { value: 'payroll',       label: 'Nómina',         icon: '💰', color: '#F97316' },
    subscriptions: { value: 'subscriptions', label: 'Suscripciones',  icon: '🔒', color: '#3B82F6' },
  };

  readonly filteredTutorials = computed(() => {
    let result = this.tutorials();
    const mod = this.selectedModule();
    const q = this.query().toLowerCase().trim();
    if (mod) result = result.filter(t => t.module === mod);
    if (q) result = result.filter(t => t.title.toLowerCase().includes(q) || (t.description && t.description.toLowerCase().includes(q)));
    return result;
  });

  readonly groupedTutorials = computed(() => {
    const map = new Map<string, TutorialDto[]>();
    for (const t of this.filteredTutorials()) {
      const list = map.get(t.module);
      if (list) list.push(t);
      else map.set(t.module, [t]);
    }
    return Array.from(map.entries());
  });

  @HostListener('window:scroll')
  onScroll() { this.scrolled = window.scrollY > 20; }

  ngOnInit() { this.loadTutorials(); }

  loadTutorials() {
    this.loading.set(true);
    this.tutorialsService.getAll().subscribe({
      next: (data) => {
        this.tutorials.set((data ?? []).map(t => ({
          ...t,
          thumbnail_url: getYouTubeThumbnail(t.thumbnail_url) ?? t.thumbnail_url
        })));
      },
      error: () => { this.loading.set(false); this.tutorials.set([]); },
      complete: () => this.loading.set(false),
    });
  }

  moduleCount(module: string): number {
    return this.tutorials().filter(t => t.module === module).length;
  }

  filterByModule(module: string) {
    this.selectedModule.set(this.selectedModule() === module ? '' : module);
  }

  clearFilters() {
    this.selectedModule.set('');
    this.query.set('');
  }

  getModuleIcon(module: string): string {
    return this.modules[module]?.icon ?? '🎬';
  }

  getModuleLabel(module: string): string {
    return this.modules[module]?.label ?? module;
  }

  openTutorial(tutorial: TutorialDto) {
    this.selectedVideoUrl = tutorial.video_url;
    this.showVideoModal = true;
  }
}
