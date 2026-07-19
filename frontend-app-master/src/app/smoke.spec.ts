import { clientRoutes } from './routes/client.routes'
import { adminRoutes } from './routes/admin.routes'

const AUTH_PATHS = ['login', 'register', 'forgot-password', 'reset-password/:uid/:token', 'access', 'error', 'registration-success']
const CLIENT_PATHS = ['dashboard', 'payment', 'checkout', 'employees', 'schedules', 'appointments', 'pos', 'payroll', 'services', 'clients', 'products', 'reports', 'settings', 'profile', 'change-password', 'help']
const ADMIN_PATHS = ['dashboard', 'tenants', 'users', 'plans', 'settings', 'audit-logs', 'billing', 'reports', 'support', 'monitor']

function getChildPaths(routes: any[] | undefined): (string | undefined)[] {
  return (routes || []).map(r => r.path)
}

function getLazyLoads(routes: any[] | undefined): string[] {
  return (routes || []).filter(r => r.loadComponent || r.loadChildren).map(r => r.path || '(root)')
}

describe('Route Smoke Tests', () => {
  describe('client routes', () => {
    const clientRoot = clientRoutes.find(r => r.path === '')
    const childPaths = getChildPaths(clientRoot?.children)

    CLIENT_PATHS.forEach(path => {
      it(`exposes /client/${path}`, () => {
        expect(childPaths).toContain(path)
      })
    })

    it('guards with roles for all children', () => {
      clientRoot?.children?.forEach(r => {
        if (r.path && !['', '**'].includes(r.path)) {
          expect(r.canActivate).toContain(jasmine.any(Function))
        }
      })
    })

    it('all client routes are lazy-loaded', () => {
      getLazyLoads(clientRoot?.children || []).forEach(p => {
        expect(p).toBeDefined()
      })
    })
  })

  describe('admin routes', () => {
    const adminRoot = adminRoutes.find(r => r.path === '')
    const childPaths = getChildPaths(adminRoot?.children)

    ADMIN_PATHS.forEach(path => {
      it(`exposes /admin/${path}`, () => {
        expect(childPaths).toContain(path)
      })
    })

    it('all admin routes are lazy-loaded', () => {
      getLazyLoads(adminRoot?.children || []).forEach(p => {
        expect(p).toBeDefined()
      })
    })
  })
})
