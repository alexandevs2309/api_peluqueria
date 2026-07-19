import { Injectable, signal, computed, inject } from '@angular/core'
import { CartItem, DailyStats, Denomination, MixedPayment } from './pos.types'
import { LocaleService } from '../../../core/services/locale/locale.service'
import { OfflineService } from '../../../core/services/offline.service'

@Injectable({ providedIn: 'root' })
export class PosCart {
  private localeService = inject(LocaleService)
  private offlineService = inject(OfflineService)
  items = signal<CartItem[]>([])
  client = signal<any>(null)
  employee = signal<any>(null)
  paymentMethod = signal('')
  discount = signal(0)
  discountType = signal<'$' | '%'>('$')
  receivedAmount = signal<number | null>(null)
  mixedPayments = signal<MixedPayment[]>([])
  promoApplied = signal<any>(null)
  couponApplied = signal<any>(null)
  redeemPoints = signal(0)
  tempPaymentMethod = signal('')
  tempPaymentAmount = signal(0)

  // Cash register
  isOpen = signal(false)

  // Stats persisted to localStorage
  dailyStats = signal<DailyStats>(this.loadStats())
  userSalesCount = signal(this.loadUserStats().count)
  userSalesRevenue = signal(this.loadUserStats().revenue)
  cashSales = signal(0)
  cashStartAmount = signal(0)

  denominations = signal<Denomination[]>(
    [2000, 1000, 500, 200, 100, 50, 25, 10, 5].map(v => ({ valor: v, cantidad: 0, total: 0 }))
  )

  // Computed
  subtotal = computed(() => this.items().reduce((s, i) => s + (Number(i.subtotal) || 0), 0))

  discountValue = computed(() => {
    const d = Number(this.discount()) || 0
    return this.discountType() === '%' ? this.subtotal() * d / 100 : d
  })

  total = computed(() => Math.max(0, this.subtotal() - this.discountValue() - this.pointsDiscount()))

  pointsDiscount = computed(() => {
    const pts = Number(this.redeemPoints()) || 0
    if (!pts || !this.client()) return 0
    return Math.min(pts / 10, this.subtotal())
  })

  change = computed(() => Math.max(0, (Number(this.receivedAmount()) || 0) - this.total()))

  itemCount = computed(() => this.items().length)

  hasServices = computed(() => this.items().some(i => i.type === 'service'))

  canSell = computed(() =>
    this.items().length > 0 &&
    this.paymentMethod() !== '' &&
    this.isOpen() &&
    (!this.hasServices() || this.employee() !== null) &&
    this.total() > 0 &&
    !this.offlineService.isOffline()
  )

  validationMessage = computed(() => {
    if (this.items().length === 0) return this.localeService.t('pos.validation.add_items' as any)
    if (!this.isOpen()) return this.localeService.t('pos.validation.open_register' as any)
    if (!this.paymentMethod()) return this.localeService.t('pos.validation.select_payment' as any)
    if (this.hasServices() && !this.employee()) return this.localeService.t('pos.validation.select_employee' as any)
    if (this.total() <= 0) return this.localeService.t('pos.validation.total_greater_zero' as any)
    if (this.offlineService.isOffline()) return this.localeService.t('pos.validation.offline' as any)
    return ''
  })

  mixedTotal = computed(() => this.mixedPayments().reduce((s, p) => s + (Number(p.monto) || 0), 0))

  mixedValid = computed(() => this.mixedTotal() >= this.total())

  // Stock helpers
  stockInCart(itemId: number) {
    return this.items()
      .filter(i => i.item.id === itemId && i.type === 'product')
      .reduce((t, i) => t + i.quantity, 0)
  }

  availableStock(item: any) {
    if (!item.stock) return 999
    return Math.max(0, Number(item.stock) - this.stockInCart(item.id))
  }

  canAddMore(item: any) {
    return this.availableStock(item) > 0
  }

  // Cart operations
  addItem(item: any, type: 'service' | 'product') {
    const existing = this.items().find(i => i.item.id === item.id && i.type === type)
    if (existing) {
      this.updateQuantity(this.items().indexOf(existing), 1)
      return true
    }
    if (type === 'product' && (item.stock ?? 0) <= 0) return false

    const cartItem: CartItem = {
      id: `${type}-${item.id}-${Date.now()}`,
      type,
      item,
      quantity: 1,
      price: Number(item.price) || 0,
      subtotal: Number(item.price) || 0,
    }
    this.items.update(cart => [...cart, cartItem])
    return true
  }

  updateQuantity(index: number, delta: number) {
    this.items.update(cart => {
      const next = [...cart]
      const item = { ...next[index] }
      const newQty = item.quantity + delta
      if (newQty <= 0) return next.filter((_, i) => i !== index)
      if (item.type === 'product' && newQty > (item.item.stock ?? Infinity)) return cart
      item.quantity = newQty
      item.subtotal = item.price * item.quantity
      next[index] = item
      return next
    })
  }

  removeItem(index: number) {
    this.items.update(cart => cart.filter((_, i) => i !== index))
  }

  clear() {
    this.items.set([])
    this.client.set(null)
    this.employee.set(null)
    this.paymentMethod.set('')
    this.discount.set(0)
    this.discountType.set('$')
    this.receivedAmount.set(null)
    this.mixedPayments.set([])
    this.promoApplied.set(null)
    this.couponApplied.set(null)
    this.redeemPoints.set(0)
  }

  resetPayment() {
    this.receivedAmount.set(0)
    this.mixedPayments.set([])
    this.promoApplied.set(null)
    this.couponApplied.set(null)
  }

  toggleDiscountType() {
    this.discountType.update(t => t === '$' ? '%' : '$')
    this.discount.set(0)
  }

  addMixedPayment(metodo: string, monto: number) {
    if (!metodo || !monto || monto <= 0) return false
    this.mixedPayments.update(p => [...p, { metodo, monto: Number(monto) }])
    return true
  }

  removeMixedPayment(index: number) {
    this.mixedPayments.update(p => p.filter((_, i) => i !== index))
  }

  applyPromotion(promo: any) {
    this.promoApplied.set(promo)
    const validatedDiscount = Number(promo.validatedDiscount ?? promo.discount_value) || 0
    this.discount.set(validatedDiscount)
    this.discountType.set('$')
    this.couponApplied.set(null)
  }

  applyCoupon(coupon: any) {
    this.couponApplied.set(coupon)
    const validatedDiscount = Number(coupon.discount) || 0
    this.discount.set(validatedDiscount)
    this.discountType.set('$')
    this.promoApplied.set(null)
  }

  // Stats
  recordSale(amount: number, method: string) {
    const s = this.dailyStats()
    const newVentas = s.ventas + 1
    const newIngresos = s.ingresos + amount
    this.dailyStats.set({ ventas: newVentas, ingresos: newIngresos, ticketPromedio: newIngresos / newVentas })
    if (method === 'cash') this.cashSales.update(v => v + amount)
    this.userSalesCount.update(v => v + 1)
    this.userSalesRevenue.update(v => v + amount)
    this.saveStats()
    this.saveUserStats()
  }

  resetDailyStats() {
    this.dailyStats.set({ ventas: 0, ingresos: 0, ticketPromedio: 0 })
    this.userSalesCount.set(0)
    this.userSalesRevenue.set(0)
    this.cashSales.set(0)
    this.cashStartAmount.set(0)
    this.saveStats()
    this.saveUserStats()
  }

  private statsKey(): string {
    const today = new Date().toISOString().split('T')[0]
    return `pos_stats_${today}`
  }

  private userStatsKey(): string {
    const today = new Date().toISOString().split('T')[0]
    return `pos_user_stats_${today}`
  }

  setStatsFromApi(ventas: number, ingresos: number) {
    const avg = ventas > 0 ? ingresos / ventas : 0
    this.dailyStats.set({ ventas, ingresos, ticketPromedio: avg })
    this.saveStats()
  }

  setUserStatsFromApi(count: number, revenue: number) {
    this.userSalesCount.set(count)
    this.userSalesRevenue.set(revenue)
    this.saveUserStats()
  }

  private saveStats() {
    try {
      localStorage.setItem(this.statsKey(), JSON.stringify(this.dailyStats()))
      this.cleanOldStats()
    } catch {}
  }

  private cleanOldStats() {
    try {
      const cutoff = Date.now() - 30 * 24 * 60 * 60 * 1000
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i)
        if (!key) continue
        if (key.startsWith('pos_stats_') || key.startsWith('pos_user_stats_')) {
          const dateStr = key.replace('pos_stats_', '').replace('pos_user_stats_', '')
          if (new Date(dateStr).getTime() < cutoff) {
            localStorage.removeItem(key)
            i--
          }
        }
      }
    } catch {}
  }

  private loadStats(): DailyStats {
    try {
      const raw = localStorage.getItem(this.statsKey())
      return raw ? JSON.parse(raw) : { ventas: 0, ingresos: 0, ticketPromedio: 0 }
    } catch {
      return { ventas: 0, ingresos: 0, ticketPromedio: 0 }
    }
  }

  private saveUserStats() {
    try {
      localStorage.setItem(this.userStatsKey(), JSON.stringify({
        count: this.userSalesCount(),
        revenue: this.userSalesRevenue(),
      }))
    } catch {}
  }

  private loadUserStats(): { count: number; revenue: number } {
    try {
      const raw = localStorage.getItem(this.userStatsKey())
      return raw ? JSON.parse(raw) : { count: 0, revenue: 0 }
    } catch {
      return { count: 0, revenue: 0 }
    }
  }

  // Cash count
  expectedCash() {
    return this.cashStartAmount() + this.cashSales()
  }

  countTotal() {
    return this.denominations().reduce((t, d) => {
      d.total = d.valor * d.cantidad
      return t + d.total
    }, 0)
  }

  countDifference() {
    return this.countTotal() - this.expectedCash()
  }

  resetCount() {
    this.denominations().forEach(d => { d.cantidad = 0; d.total = 0 })
  }
}
