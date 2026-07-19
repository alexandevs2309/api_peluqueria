import { Injectable, inject, signal } from '@angular/core'
import { firstValueFrom } from 'rxjs'
import { PosService } from '../../../core/services/pos/pos.service'
import { SalePayload } from './pos.types'

@Injectable({ providedIn: 'root' })
export class PosApi {
  private pos = inject(PosService)

  loading = signal(false)

  private async request<T>(fn: () => Promise<T>): Promise<T> {
    this.loading.set(true)
    try { return await fn() }
    finally { this.loading.set(false) }
  }

  // Sales
  getSales(params?: any) {
    return this.request(() => firstValueFrom(this.pos.getSales(params)))
  }

  getSale(id: number) {
    return this.request(() => firstValueFrom(this.pos.getSale(id)))
  }

  createSale(sale: SalePayload) {
    return this.request(() => firstValueFrom(this.pos.createSale(sale)))
  }

  deleteSale(id: number) {
    return this.request(() => firstValueFrom(this.pos.deleteSale(id)))
  }

  refundSale(saleId: number, data?: any) {
    return this.request(() => firstValueFrom(this.pos.refundSale(saleId, data ?? {})))
  }

  printReceipt(saleId: number) {
    return this.request(() => firstValueFrom(this.pos.printReceipt(saleId)))
  }

  searchSales(params: any) {
    return this.request(() => firstValueFrom(this.pos.searchSales(params)))
  }

  validateStock(items: any[]) {
    return this.request(() => firstValueFrom(this.pos.validateStock(items)))
  }

  // Cash registers
  getCashRegisters(params?: any) {
    return this.request(() => firstValueFrom(this.pos.getCashRegisters(params)))
  }

  getCurrentCashRegister(params?: any) {
    return this.request(() => firstValueFrom(this.pos.getCurrentCashRegister(params)))
  }

  openCashRegister(data: { initial_cash: number; branch?: number | null }) {
    return this.request(() => firstValueFrom(this.pos.openCashRegister(data)))
  }

  closeCashRegister(id: number, data: { final_cash: number }) {
    return this.request(() => firstValueFrom(this.pos.closeCashRegister(id, data)))
  }

  cashCount(registerId: number, counts: any[]) {
    return this.request(() => firstValueFrom(this.pos.cashCount(registerId, counts)))
  }

  // Dashboard
  getDailySummary(date?: string) {
    return this.request(() => firstValueFrom(this.pos.getDailySummary(date)))
  }

  getDashboardStats(params?: Record<string, string>) {
    return this.request(() => firstValueFrom(this.pos.getDashboardStats(params)))
  }

  // Promotions
  getPromotions() {
    return this.request(() => firstValueFrom(this.pos.getPromotions()))
  }

  getActivePromotions() {
    return this.request(() => firstValueFrom(this.pos.getActivePromotions()))
  }

  applyPromotion(promotionId: number, cartTotal: number) {
    return this.request(() => firstValueFrom(this.pos.applyPromotion(promotionId, cartTotal)))
  }

  // Config
  getPosConfig() {
    return this.request(() => firstValueFrom(this.pos.getPosConfig()))
  }

  getPosConfiguration() {
    return this.request(() => firstValueFrom(this.pos.getPosConfiguration()))
  }

  getCategories() {
    return this.request(() => firstValueFrom(this.pos.getCategories()))
  }

  // Barcode
  searchByBarcode(barcode: string) {
    return this.request(() => firstValueFrom(this.pos.searchByBarcode(barcode)))
  }

  // Charge card via provider (Stripe / CardNET según el país del tenant)
  chargeCard(amount: number, currency = 'DOP') {
    return this.request(() => firstValueFrom(this.pos.chargeCard(amount, currency)))
  }

  // Coupons
  validateCoupon(code: string, cartTotal: number) {
    return this.request(() => firstValueFrom(this.pos.validateCoupon(code, cartTotal)))
  }
}
