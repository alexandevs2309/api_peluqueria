import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { BaseApiService } from '../base-api.service';
import { API_CONFIG } from '../../config/api.config';

export interface Sale {
  id: number;
  client: any;
  employee: any;
  services: any[];
  products: any[];
  total: number;
  payment_method: string;
  date_time: string;
  status: string;
}

export interface CashRegister {
  id: number;
  user: any;
  user_name?: string;
  opened_at: string;
  closed_at?: string;
  initial_cash: number;
  final_cash?: number;
  is_open: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class PosService extends BaseApiService {

  // Sales
  getSales(params?: any): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.POS.SALES, params);
  }

  getSale(id: number): Observable<Sale> {
    return this.get(`${API_CONFIG.ENDPOINTS.POS.SALES}${id}/`);
  }

  createSale(sale: Partial<Sale>): Observable<Sale> {
    return this.post(API_CONFIG.ENDPOINTS.POS.SALES, sale);
  }

  updateSale(id: number, sale: Partial<Sale>): Observable<Sale> {
    return this.put(`${API_CONFIG.ENDPOINTS.POS.SALES}${id}/`, sale);
  }

  deleteSale(id: number): Observable<any> {
    return this.delete(`${API_CONFIG.ENDPOINTS.POS.SALES}${id}/`);
  }

  // Cash Registers
  getCashRegisters(params?: any): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.POS.CASH_REGISTERS, params);
  }

  getCashRegister(id: number): Observable<CashRegister> {
    return this.get(`${API_CONFIG.ENDPOINTS.POS.CASH_REGISTERS}${id}/`);
  }

  openCashRegister(data: { initial_cash: number }): Observable<CashRegister> {
    return this.post(API_CONFIG.ENDPOINTS.POS.CASH_REGISTERS, data);
  }

  getCurrentCashRegister(params?: any): Observable<CashRegister> {
    return this.get(`${API_CONFIG.ENDPOINTS.POS.CASH_REGISTERS}current/`, params);
  }

  closeCashRegister(id: number, data: { final_cash: number }): Observable<CashRegister> {
    return this.post(`${API_CONFIG.ENDPOINTS.POS.CASH_REGISTERS}${id}/close/`, data);
  }

  // Dashboard & Stats
  getDashboardStats(params?: Record<string, string>): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.POS.DASHBOARD_STATS, params);
  }

  getDailySummary(date?: string): Observable<any> {
    const params = date ? { date } : {};
    return this.get(API_CONFIG.ENDPOINTS.POS.DAILY_SUMMARY, params);
  }

  // Promotions
  getActivePromotions(): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.POS.ACTIVE_PROMOTIONS);
  }

  // Categories
  getCategories(): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.POS.CATEGORIES);
  }

  // Config
  getPosConfig(): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.POS.CONFIG);
  }

  // Nuevas funcionalidades
  searchSales(params: any): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.POS.SEARCH_SALES, params);
  }

  cashCount(registerId: number, counts: any[]): Observable<any> {
    return this.post(API_CONFIG.ENDPOINTS.POS.CASH_COUNT.replace('{id}', registerId.toString()), { counts });
  }

  // Promociones
  getPromotions(): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.POS.PROMOTIONS);
  }

  applyPromotion(promotionId: number, cartTotal: number): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.POS.PROMOTIONS}${promotionId}/apply_promotion/`, { cart_total: cartTotal });
  }

  createPromotion(promotion: any): Observable<any> {
    return this.post(API_CONFIG.ENDPOINTS.POS.PROMOTIONS, promotion);
  }

  updatePromotion(id: number, promotion: any): Observable<any> {
    return this.put(`${API_CONFIG.ENDPOINTS.POS.PROMOTIONS}${id}/`, promotion);
  }

  deletePromotion(id: number): Observable<any> {
    return this.delete(`${API_CONFIG.ENDPOINTS.POS.PROMOTIONS}${id}/`);
  }

  // Configuración
  getPosConfiguration(): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.POS.CONFIGURATION);
  }

  updatePosConfiguration(config: any): Observable<any> {
    return this.put(`${API_CONFIG.ENDPOINTS.POS.CONFIGURATION}1/`, config);
  }

  // Búsqueda por código de barras
  searchByBarcode(barcode: string): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.INVENTORY.SEARCH_BY_BARCODE, { barcode });
  }

  // Sale specific actions
  processPayment(saleId: number, paymentData: any): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.POS.SALES}${saleId}/process_payment/`, paymentData);
  }

  refundSale(saleId: number, refundData: any): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.POS.SALES}${saleId}/refund/`, refundData);
  }

  printReceipt(saleId: number): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.POS.SALES}${saleId}/print_receipt/`);
  }

  generateCashRegisterReport(registerId: number): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.POS.CASH_REGISTERS}${registerId}/report/`);
  }

  // Card payment provider for POS (Stripe / CardNET según el país del tenant)
  chargeCard(amount: number, currency: string = 'DOP'): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.POS.SALES}charge_card/`, { amount, currency });
  }

  // Validar stock en tiempo real
  validateStock(items: any[]): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.POS.SALES}validate_stock/`, { items });
  }

  // NCF Sequences
  getNcfSequences(): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.POS.NCF_SEQUENCES);
  }

  getNcfSequence(id: number): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.POS.NCF_SEQUENCES}${id}/`);
  }

  createNcfSequence(data: any): Observable<any> {
    return this.post(API_CONFIG.ENDPOINTS.POS.NCF_SEQUENCES, data);
  }

  updateNcfSequence(id: number, data: any): Observable<any> {
    return this.put(`${API_CONFIG.ENDPOINTS.POS.NCF_SEQUENCES}${id}/`, data);
  }

  deleteNcfSequence(id: number): Observable<any> {
    return this.delete(`${API_CONFIG.ENDPOINTS.POS.NCF_SEQUENCES}${id}/`);
  }

  // Coupons
  validateCoupon(code: string, cartTotal: number): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.POS.COUPONS}validate/`, { code, cart_total: cartTotal });
  }
}
