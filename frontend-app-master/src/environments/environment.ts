/**
 * Environment - Development
 * Apunta a localhost. Para conectar a staging usar:
 *   ng serve --configuration staging
 */
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api',
  wsUrl: 'ws://localhost:8000/ws',
  stripePublishableKey: '',
  appName: 'Auron-Suite (Dev)',
  appVersion: '1.0.0-dev',

  enableDebugMode: true,
  enableMockData: false,

  csrfCookieName: 'csrftoken',
  sessionCookieName: 'sessionid',

  whatsappNumber: '18096769729',
  facebookPixelId: '',
  googleAnalyticsId: '',
  tawktoWidgetId: '',

  logrocketAppId: '',
};
