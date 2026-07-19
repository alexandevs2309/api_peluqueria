import { Injectable, inject, signal } from '@angular/core'
import { firstValueFrom } from 'rxjs'
import { ServiceService } from '../../../core/services/service/service.service'
import { InventoryService } from '../../../core/services/inventory/inventory.service'
import { ClientService } from '../../../core/services/client/client.service'
import { EmployeeService } from '../../../core/services/employee/employee.service'
import { PosApi } from './pos.api'
import { CatalogItem, PosConfig, Promotion } from './pos.types'
import { BranchService } from '../../../core/services/branch/branch.service'
import { PlanAccessService } from '../../../core/services/plan-access.service'

const TTL = 5 * 60 * 1000

@Injectable({ providedIn: 'root' })
export class PosRepo {
  private servicesSvc = inject(ServiceService)
  private inventorySvc = inject(InventoryService)
  private clientsSvc = inject(ClientService)
  private employeesSvc = inject(EmployeeService)
  private api = inject(PosApi)
  private branchService = inject(BranchService)
  private planAccess = inject(PlanAccessService)

  services = signal<CatalogItem[]>([])
  products = signal<CatalogItem[]>([])
  clients = signal<Record<string, unknown>[]>([])
  employees = signal<Record<string, unknown>[]>([])
  categories = signal<{ name: string; value: string }[]>([])
  promotions = signal<Promotion[]>([])
  posConfig = signal<PosConfig>({})
  loading = signal(false)

  private timestamps: Record<string, number> = {}

  private isStale(key: string) {
    return !this.timestamps[key] || Date.now() - this.timestamps[key] > TTL
  }

  private touch(key: string) {
    this.timestamps[key] = Date.now()
  }

  private extractResults(resp: Record<string, unknown>) {
    return ((resp?.results ?? resp) ?? []) as Record<string, unknown>[]
  }

  async loadAll(force = false) {
    if (this.loading() && !force) return
    this.loading.set(true)
    try {
      await Promise.all([
        this.loadServices(force),
        this.loadProducts(force),
        this.loadClients(force),
        this.loadEmployees(force),
        this.loadCategories(force),
        this.loadPromotions(force),
        this.loadConfig(force),
      ])
    } finally {
      this.loading.set(false)
    }
  }

  async loadServices(force = false) {
    if (!force && !this.isStale('services')) return
    const params: any = { is_active: true }
    const activeBranchId = this.branchService.activeBranchId()
    if (activeBranchId) {
      params.branch_id = activeBranchId
    }
    const resp = await firstValueFrom(this.servicesSvc.getServices(params))
    this.services.set((this.extractResults(resp) as unknown as CatalogItem[]).filter(s => s.is_active !== false))
    this.touch('services')
  }

  async loadProducts(force = false) {
    if (!force && !this.isStale('products')) return
    if (!this.planAccess.hasFeature('inventory')) {
      this.products.set([])
      return
    }
    try {
      const params: any = {}
      const activeBranchId = this.branchService.activeBranchId()
      if (activeBranchId) {
        params.branch_id = activeBranchId
      }
      const resp = await firstValueFrom(this.inventorySvc.getProducts(params))
      this.products.set(
        (this.extractResults(resp) as unknown as CatalogItem[]).filter(p => p.is_active && (p.stock ?? 0) > 0)
      )
    } catch {
      this.products.set([])
    }
    this.touch('products')
  }

  async loadClients(force = false) {
    if (!force && !this.isStale('clients')) return
    const resp = await firstValueFrom(this.clientsSvc.getClients())
    this.clients.set(this.extractResults(resp).filter(c => c.is_active !== false))
    this.touch('clients')
  }

  async loadEmployees(force = false) {
    if (!force && !this.isStale('employees')) return
    try {
      const params: any = {}
      const activeBranchId = this.branchService.activeBranchId()
      if (activeBranchId) {
        params.branch_id = activeBranchId
      }
      const resp = await firstValueFrom(this.employeesSvc.getEmployees(params))
      const all = this.extractResults(resp).filter(e => e.is_active)
      this.employees.set(all.map(e => ({
        ...e,
        displayName: `${(e.user as Record<string, string>)?.full_name || (e.user as Record<string, string>)?.email || 'Sin nombre'} (${(e.user as Record<string, string>)?.role || 'Sin rol'})`,
      })))
    } catch {
      this.employees.set([])
    }
    this.touch('employees')
  }

  async loadCategories(force = false) {
    if (!force && !this.isStale('categories')) return
    try {
      const resp = await this.api.getCategories()
      const cats = [{ name: 'Todas las categorías', value: '' }]
      const raw = this.extractResults(resp)
      if (raw.length) cats.push(...raw.map(c => ({ name: (c.name || c) as string, value: (c.value || c) as string })))
      this.categories.set(cats)
    } catch {
      this.categories.set([{ name: 'Todas las categorías', value: '' }])
    }
    this.touch('categories')
  }

  async loadPromotions(force = false) {
    if (!force && !this.isStale('promotions')) return
    try {
      const resp = await this.api.getPromotions()
      this.promotions.set(this.extractResults(resp) as unknown as Promotion[])
    } catch {
      this.promotions.set([])
    }
    this.touch('promotions')
  }

  async loadConfig(force = false) {
    if (!force && !this.isStale('config')) return
    try {
      const resp = await this.api.getPosConfiguration()
      this.posConfig.set((resp?.results?.[0] || {}) as PosConfig)
    } catch {
      this.posConfig.set({})
    }
    this.touch('config')
  }

  getFrequentClients() {
    return this.clients().filter(c => (c.total_purchases as number || 0) > 5)
  }

  isFrequentClient(client: Record<string, unknown>) {
    return this.getFrequentClients().some(c => c.id === client.id)
  }
}
