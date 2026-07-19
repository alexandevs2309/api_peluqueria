/**
 * Environment - Staging
 * Conecta a la API de staging con datos de prueba.
 * Activar con: ng serve --configuration staging
 */
export const environment = {
  production: false,
  apiUrl: (window as any).__env?.apiUrl || 'https://staging-api.auronsuite.com/api',
  wsUrl: (window as any).__env?.wsUrl || 'wss://staging-api.auronsuite.com/ws',
  stripePublishableKey: (window as any).__env?.stripePublishableKey || '',
  appName: 'Auron-Suite (Staging)',
  appVersion: '1.0.0-staging',
  enableDebugMode: true,
  enableMockData: false,
  csrfCookieName: 'csrftoken',
  sessionCookieName: 'sessionid',

  whatsappNumber: (window as any).__env?.whatsappNumber || '',
  facebookPixelId: (window as any).__env?.facebookPixelId || '',
  googleAnalyticsId: (window as any).__env?.googleAnalyticsId || '',
  tawktoWidgetId: (window as any).__env?.tawktoWidgetId || '',

  logrocketAppId: (window as any).__env?.logrocketAppId || '',
};
