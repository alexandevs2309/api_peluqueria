import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app.config';
import { AppComponent } from './app.component';
import {registerLocaleData} from '@angular/common';
import localeEsDO from '@angular/common/locales/es-DO';
import { environment } from './environments/environment';
import LogRocket from 'logrocket';

registerLocaleData(localeEsDO);

// LogRocket — session replay & observability (production only)
if (environment.production && environment.logrocketAppId) {
  LogRocket.init(environment.logrocketAppId, {
    dom: {
      inputSanitizer: true,
      textSanitizer: true,
    },
    release: environment.appVersion,
  });
}

// Keep browser console clean across environments without affecting app flow.
// To re-enable verbose logs temporarily in dev, set localStorage.DEBUG_CONSOLE = '1'.
const debugConsoleEnabled = !environment.production && localStorage.getItem('DEBUG_CONSOLE') === '1';
if (!debugConsoleEnabled) {
    const noop = () => {};
    console.log = noop;
    console.info = noop;
    console.debug = noop;
    console.trace = noop;
}

bootstrapApplication(AppComponent, appConfig).catch((err) => console.error(err));
