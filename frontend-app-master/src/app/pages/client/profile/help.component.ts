import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CardModule } from 'primeng/card';
import { AccordionModule } from 'primeng/accordion';
import { FormsModule } from '@angular/forms';
import { InputTextModule } from 'primeng/inputtext';
import { ButtonModule } from 'primeng/button';
import { Router } from '@angular/router';
import { BarbershopSettingsService } from '../../../shared/services/barbershop-settings.service';
import { AppConfigService } from '../../../core/services/app-config.service';
import { LocaleService } from '../../../core/services/locale/locale.service';
import { I18nPipe } from '../../../core/pipes/i18n.pipe';
import { AuBtn } from '../../../shared/components';

@Component({
    selector: 'app-help',
    standalone: true,
    imports: [CommonModule, FormsModule, AuBtn, CardModule, AccordionModule, InputTextModule, ButtonModule, I18nPipe],
    template: `
        <div class="help-page p-4 md:p-6">
            <section class="help-hero mb-6">
                <div class="flex items-center gap-4">
                    <div class="hero-icon">
                        <i class="pi pi-question-circle text-white text-2xl"></i>
                    </div>
                    <div>
                        <h1 class="display-3 mb-1">{{ 'help.title' | t }}</h1>
                        <p class="hero-subtitle">{{ 'help.subtitle' | t }}</p>
                    </div>
                </div>
            </section>

            <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
                <div class="xl:col-span-2">
                    <p-card>
                        <div class="space-y-4">
                            <div>
                                <h2 class="section-title">{{ 'help.faqs_title' | t }}</h2>
                                <p class="section-subtitle">{{ 'help.faqs_subtitle' | t }}</p>
                            </div>

                            <div>
                                <input
                                    pInputText
                                    type="text"
                                    class="w-full"
                                    [placeholder]="'help.search_placeholder' | t"
                                    [(ngModel)]="searchTerm"
                                />
                            </div>

                            @if (filteredFaqs().length > 0) {
                                <p-accordion>
                                    @for (faq of filteredFaqs(); track faq.title; let i = $index) {
                                        <p-accordion-panel [value]="i.toString()">
                                            <p-accordion-header>{{ faq.title }}</p-accordion-header>
                                            <p-accordion-content>
                                                <p class="m-0">{{ faq.content }}</p>
                                            </p-accordion-content>
                                        </p-accordion-panel>
                                    }
                                </p-accordion>
                            } @else {
                                <div class="auron-empty-state">
                                    <div class="auron-empty-icon"><i class="pi pi-search"></i></div>
                                    <div class="auron-empty-title">{{ 'help.no_results' | t }}</div>
                                    <p class="m-0">{{ ('help.no_results' | t).replace('{searchTerm}', searchTerm) }}</p>
                                </div>
                            }
                        </div>
                    </p-card>
                </div>

                <div class="space-y-6">
                    <p-card>
                        <div class="space-y-3">
                            <h3 class="section-title !mb-0">{{ 'help.quick_access' | t }}</h3>
                            <button au-btn variant="secondary" class="w-full" [icon]="'pi pi-shopping-cart'" (click)="go('/client/pos')">{{ 'help.go_pos' | t }}</button>
                            <button au-btn variant="secondary" class="w-full" [icon]="'pi pi-calendar'" (click)="go('/client/appointments')">{{ 'help.go_appointments' | t }}</button>
                            <button au-btn variant="secondary" class="w-full" [icon]="'pi pi-cog'" (click)="go('/client/settings')">{{ 'help.go_settings' | t }}</button>
                        </div>
                    </p-card>

                    <p-card>
                        <div class="space-y-3">
                            <h3 class="section-title !mb-0">{{ 'help.support' | t }}</h3>
                            <p class="section-subtitle">{{ 'help.support_subtitle' | t }}</p>
                            <div class="support-item">
                                <i class="pi pi-envelope"></i>
                                <span>{{ supportEmail() }}</span>
                            </div>
                            <div class="support-item">
                                <i class="pi pi-clock"></i>
                                <span>{{ 'help.support_hours' | t }}</span>
                            </div>
                        </div>
                    </p-card>
                </div>
            </div>
        </div>
    `,
    styles: [`
        .help-page {
            background: linear-gradient(180deg, rgba(26,86,219,0.08) 0%, rgba(26,86,219,0.02) 35%, transparent 100%);
            min-height: calc(100vh - 7rem);
            border-radius: 1rem;
        }

        .help-hero {
            border: 1px solid var(--surface-border);
            background: var(--surface-card);
            border-radius: 1rem;
            padding: 1.25rem;
        }

        .hero-icon {
            width: 3rem;
            height: 3rem;
            border-radius: 0.75rem;
            background: linear-gradient(135deg, var(--brand), var(--brand-400));
            display: grid;
            place-items: center;
        }

        .hero-subtitle {
            margin: 0;
            color: var(--text-color-secondary);
        }

        .section-title {
            margin: 0 0 0.25rem;
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text-color);
        }

        .section-subtitle {
            margin: 0;
            color: var(--text-color-secondary);
            font-size: 0.92rem;
        }

        .empty-state {
            border: 1px dashed var(--surface-border);
            border-radius: 0.75rem;
            padding: 1rem;
            display: flex;
            gap: 0.75rem;
            align-items: center;
            color: var(--text-color-secondary);
        }

        .support-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: var(--text-color);
            font-size: 0.92rem;
        }
    `]
})
export class HelpComponent {
    searchTerm = '';
    private appConfig = inject(AppConfigService);
    protected localeService = inject(LocaleService);

    t(key: string): string {
        return this.localeService.t(key as any);
    }

    get faqs() {
        return [
            {
                title: this.t('help.faq1.title'),
                content: this.t('help.faq1.content')
            },
            {
                title: this.t('help.faq2.title'),
                content: this.t('help.faq2.content')
            },
            {
                title: this.t('help.faq3.title'),
                content: this.t('help.faq3.content')
            },
            {
                title: this.t('help.faq4.title'),
                content: this.t('help.faq4.content')
            },
            {
                title: this.t('help.faq5.title'),
                content: this.t('help.faq5.content')
            },
            {
                title: this.t('help.faq6.title'),
                content: this.t('help.faq6.content')
            },
            {
                title: this.t('help.faq7.title'),
                content: this.t('help.faq7.content')
            },
            {
                title: this.t('help.faq8.title'),
                content: this.t('help.faq8.content')
            }
        ];
    }

    constructor(
        private router: Router,
        private barbershopSettings: BarbershopSettingsService
    ) {}

    filteredFaqs() {
        const term = this.searchTerm.trim().toLowerCase();
        if (!term) return this.faqs;
        return this.faqs.filter(
            (faq) => faq.title.toLowerCase().includes(term) || faq.content.toLowerCase().includes(term)
        );
    }

    go(route: string): void {
        this.router.navigate([route]);
    }

    supportEmail(): string {
        return this.appConfig.supportEmail() || 'soporte@auronsuite.com';
    }
}
