import { environment } from '../../../environments/environment';

export const API_CONFIG = {
  BASE_URL: environment.apiUrl,
  WS_URL: environment.wsUrl,
  ENDPOINTS: {
    // Auth
    AUTH: {
      LOGIN: '/auth/login/',
      LOGOUT: '/auth/logout/',
      REGISTER: '/auth/register/',
      CHANGE_PASSWORD: '/auth/change-password/',
      RESET_PASSWORD: '/auth/reset-password/',
      RESET_PASSWORD_CONFIRM: '/auth/reset-password-confirm/',
      ACTIVE_SESSIONS: '/auth/active-sessions/',
      TERMINATE_SESSION: '/auth/session/',
      VERIFY_EMAIL: '/auth/verify-email/',
      MFA_SETUP: '/auth/mfa/setup/',
      MFA_VERIFY: '/auth/mfa/verify/',
      MFA_DISABLE: '/auth/mfa/disable/',
      MFA_LOGIN_VERIFY: '/auth/mfa/login-verify/',
      PERMISSIONS: '/auth/permissions/',
      USERS: '/auth/users/'
    },
    
    // Tenants
    TENANTS: '/tenants/',
    ADMIN_USERS: '/tenants/admin/users/',
    
    // Subscriptions
    SUBSCRIPTIONS: {
      BASE: '/subscriptions/',
      PLANS: '/subscriptions/plans/',
      USER_SUBSCRIPTIONS: '/subscriptions/user-subscriptions/',
      AUDIT_LOGS: '/subscriptions/audit-logs/',
      MY_ACTIVE: '/subscriptions/me/active/',
      MY_ENTITLEMENTS: '/subscriptions/me/entitlements/',
      REGISTER: '/subscriptions/register/',
      ONBOARD: '/subscriptions/onboard/',
      PROMOTIONAL_CREDITS: '/subscriptions/promotional-credits/',
      RENEW: '/subscriptions/renew/'
    },
    
    // Employees
    EMPLOYEES: {
      BASE: '/employees/employees/',
      SCHEDULES: '/employees/schedules/',
      ATTENDANCE: '/employees/attendance/'
    },
    
    // Appointments
    APPOINTMENTS: {
      BASE: '/appointments/appointments/',
      TEST: '/appointments/test/'
    },
    
    // Clients
    CLIENTS: '/clients/clients/',
    
    // Services
    SERVICES: '/services/services/',
    
    // POS
    POS: {
      SALES: '/pos/sales/',
      CASH_REGISTERS: '/pos/cashregisters/',
      PROMOTIONS: '/pos/promotions/',
      CONFIGURATION: '/pos/configuration/',
      DAILY_SUMMARY: '/pos/summary/daily/',
      DASHBOARD_STATS: '/pos/dashboard/stats/',
      ACTIVE_PROMOTIONS: '/pos/promotions/active/',
      CATEGORIES: '/pos/categories/',
      CONFIG: '/pos/config/',
      SEARCH_SALES: '/pos/sales/search_sales/',
      PRINT_RECEIPT: '/pos/sales/{id}/print_receipt/',
      CASH_COUNT: '/pos/cashregisters/{id}/cash_count/',
      COUPONS: '/pos/coupons/',
      NCF_SEQUENCES: '/pos/ncf-sequences/'
    },
    
    // Inventory
    INVENTORY: {
      PRODUCTS: '/inventory/products/',
      SUPPLIERS: '/inventory/suppliers/',
      STOCK_MOVEMENTS: '/inventory/stock-movements/',
      LOW_STOCK_ALERTS: '/inventory/alerts/low-stock/',
      CATEGORIES: '/inventory/categories/',
      LOW_STOCK_PRODUCTS: '/inventory/products/low-stock/',
      SEARCH_BY_BARCODE: '/inventory/products/search_by_barcode/'
    },
    
    // Reports
    REPORTS: {
      BASE: '/reports/',
      DASHBOARD: '/reports/dashboard/',
      SALES: '/reports/sales/',
      EMPLOYEES: '/reports/employees/',
      BY_TYPE: '/reports/',
      ADMIN: '/reports/admin/'
    },
    
    // Billing
    BILLING: '/billing/',
    BILLING_ADMIN_STATS: '/billing/admin/stats/',
    
    // Payments
    PAYMENTS: '/payments/',
    
    // Settings
    SETTINGS: {
      BASE: '/settings/',
      SYSTEM: '/system-settings/',
      SYSTEM_RESET: '/system-settings/reset/',
      PUBLIC_BRANDING: '/settings/public-branding/',
      TEST_EMAIL: '/settings/test-email/',
      TEST_PAYMENT: '/settings/test-payment/',
      
      // SuperAdmin endpoints
      ADMIN_METRICS: '/settings/admin/metrics/',
      ADMIN_SYSTEM_MONITOR: '/settings/admin/system-monitor/',
      ADMIN_TEST_SERVICE: '/settings/admin/test-service/'
    },
    
    // Roles
    ROLES: '/roles/',
    
    // Audit
    AUDIT: '/audit/',
    
    // Notifications
    NOTIFICATIONS: '/notifications/',
    
    // Compatibility endpoints
    COMPATIBILITY: {
      USERS_AVAILABLE_FOR_EMPLOYEE: '/users/available-for-employee/',
      PRODUCTS_LOW_STOCK: '/inventory/products/low-stock/'
    },
    
    // Tutorials
    TUTORIALS: {
      BASE: '/tutorials/tutorials/',
      ADMIN: '/tutorials/admin/tutorials/'
    },


    // System
    SYSTEM: {
      HEALTH: '/healthz/',
      SENTRY_TEST: '/sentry-test/',
      SCHEMA: '/schema/',
      DOCS: '/docs/'
    }
  }
};

export const HTTP_CONFIG = {
  TIMEOUT: 30000,
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000
};
