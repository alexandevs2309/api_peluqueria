/**
 * Environment - Production
 * 
 * SEGURIDAD: Ninguna clave sensible debe estar en este archivo.
 * Todas las variables runtime se inyectan via env-config.sh -> window.__env
 * Variables de build-time (no sensibles): appName, appVersion, feature flags.
 */
export const environment = {
  production: true,
  
  // URLs y claves desde runtime (nunca en bundle — sin fallback hardcodeado)
  apiUrl: (window as any).__env?.apiUrl || 'https://api.auronsuite.com/api',
  wsUrl: (window as any).__env?.wsUrl || 'wss://api.auronsuite.com/ws',
  stripePublishableKey: (window as any).__env?.stripePublishableKey || '',
  
  appName: 'Auron-Suite',
  appVersion: '1.0.0',
  
  enableDebugMode: false,
  enableMockData: false,
  
  csrfCookieName: 'csrftoken',
  sessionCookieName: 'sessionid',

  whatsappNumber: (window as any).__env?.whatsappNumber || '',
  facebookPixelId: (window as any).__env?.facebookPixelId || '',
  googleAnalyticsId: (window as any).__env?.googleAnalyticsId || '',
  tawktoWidgetId: (window as any).__env?.tawktoWidgetId || '',
  
  logrocketAppId: (window as any).__env?.logrocketAppId || '',
};
