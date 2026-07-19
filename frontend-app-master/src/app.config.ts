import { provideHttpClient, withInterceptorsFromDi, HTTP_INTERCEPTORS } from '@angular/common/http';
import { ApplicationConfig, APP_INITIALIZER, ErrorHandler, LOCALE_ID, isDevMode } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideRouter, withEnabledBlockingInitialNavigation, withInMemoryScrolling, withPreloading } from '@angular/router';
import { provideServiceWorker } from '@angular/service-worker';
import { providePrimeNG } from 'primeng/config';
import { AuronPreset } from './theme/auron-preset';
import { MessageService } from 'primeng/api';
import { appRoutes } from './app.routes';
import { AuthInterceptor, ErrorInterceptor } from './app/core/interceptors';
import { MaintenanceInterceptor } from './app/core/interceptors/maintenance.interceptor';
import { EmployeeErrorInterceptor } from './app/core/interceptors/employee-error.interceptor';
import { RuntimeConfigValidatorService } from './app/core/config/runtime-config-validator.service';
import { LocaleService } from './app/core/services/locale/locale.service';
import { GlobalErrorHandlerService } from './app/core/services/global-error-handler.service';
import { RoleBasedPreloadingStrategy } from './app/core/services/role-based-preloading.strategy';

function validateRuntimeConfigFactory(validator: RuntimeConfigValidatorService) {
    return () => validator.assertValidRuntimeConfig();
}

export const appConfig: ApplicationConfig = {
    providers: [
        provideRouter(
            appRoutes,
            withInMemoryScrolling({ anchorScrolling: 'enabled', scrollPositionRestoration: 'enabled' }),
            withEnabledBlockingInitialNavigation(),
            withPreloading(RoleBasedPreloadingStrategy)
        ),
        provideHttpClient(withInterceptorsFromDi()),
        provideAnimationsAsync(),
        providePrimeNG({ theme: { preset: AuronPreset, options: { darkModeSelector: '.app-dark' } } }),
        provideServiceWorker('ngsw-worker.js', {
            enabled: !isDevMode(),
            registrationStrategy: 'registerWhenStable:30000'
        }),
        MessageService,
        
        // HTTP Interceptors
        {
            provide: HTTP_INTERCEPTORS,
            useClass: AuthInterceptor,
            multi: true
        },
        {
            provide: HTTP_INTERCEPTORS,
            useClass: ErrorInterceptor,
            multi: true
        },
        {
            provide: HTTP_INTERCEPTORS,
            useClass: MaintenanceInterceptor,
            multi: true
        },
        {
            provide: HTTP_INTERCEPTORS,
            useClass: EmployeeErrorInterceptor,
            multi: true
        },
        {
            provide: LOCALE_ID,
            useFactory: (localeService: LocaleService) => {
                try {
                    return localeService.getCurrentAppLocale();
                } catch (e) {
                    return 'es-DO';
                }
            },
            deps: [LocaleService]
        },
        {
            provide: APP_INITIALIZER,
            useFactory: validateRuntimeConfigFactory,
            deps: [RuntimeConfigValidatorService],
            multi: true
        },
        {
            provide: ErrorHandler,
            useClass: GlobalErrorHandlerService
        }
    ]
};
