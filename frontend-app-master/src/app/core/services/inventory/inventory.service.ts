import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { BaseApiService } from '../base-api.service';
import { API_CONFIG } from '../../config/api.config';

export interface Product {
  id: number;
  name: string;
  sku: string;
  description: string;
  price: number;
  cost?: number;
  stock: number;
  min_stock: number;
  category: number | null;
  category_name?: string;
  supplier?: any;
  unit?: string;
  is_active: boolean;
  tenant: number;
  image?: string;
  barcode?: string;
}

export interface Supplier {
  id: number;
  name: string;
  contact_person: string;
  email: string;
  phone: string;
  address: string;
  is_active: boolean;
  tenant: number;
}

export interface StockMovement {
  id: number;
  product: any;
  movement_type: string;
  quantity: number;
  reason: string;
  user: any;
  date: string;
}

@Injectable({
  providedIn: 'root'
})
export class InventoryService extends BaseApiService {

  // Products
  getProducts(params?: any): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.INVENTORY.PRODUCTS, params);
  }

  getProduct(id: number): Observable<Product> {
    return this.get(`${API_CONFIG.ENDPOINTS.INVENTORY.PRODUCTS}${id}/`);
  }

  createProduct(product: Partial<Product>): Observable<Product> {
    return this.post(API_CONFIG.ENDPOINTS.INVENTORY.PRODUCTS, product);
  }

  createProductWithImage(formData: FormData): Observable<Product> {
    return this.postFormData(API_CONFIG.ENDPOINTS.INVENTORY.PRODUCTS, formData);
  }

  updateProduct(id: number, product: Partial<Product>): Observable<Product> {
    return this.patch(`${API_CONFIG.ENDPOINTS.INVENTORY.PRODUCTS}${id}/`, product);
  }

  updateProductWithImage(id: number, formData: FormData): Observable<Product> {
    return this.putFormData(`${API_CONFIG.ENDPOINTS.INVENTORY.PRODUCTS}${id}/`, formData);
  }

  deleteProduct(id: number): Observable<any> {
    return this.delete(`${API_CONFIG.ENDPOINTS.INVENTORY.PRODUCTS}${id}/`);
  }

  // Suppliers
  getSuppliers(params?: any): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.INVENTORY.SUPPLIERS, params);
  }

  getSupplier(id: number): Observable<Supplier> {
    return this.get(`${API_CONFIG.ENDPOINTS.INVENTORY.SUPPLIERS}${id}/`);
  }

  createSupplier(supplier: Partial<Supplier>): Observable<Supplier> {
    return this.post(API_CONFIG.ENDPOINTS.INVENTORY.SUPPLIERS, supplier);
  }

  updateSupplier(id: number, supplier: Partial<Supplier>): Observable<Supplier> {
    return this.put(`${API_CONFIG.ENDPOINTS.INVENTORY.SUPPLIERS}${id}/`, supplier);
  }

  deleteSupplier(id: number): Observable<any> {
    return this.delete(`${API_CONFIG.ENDPOINTS.INVENTORY.SUPPLIERS}${id}/`);
  }

  // Stock Movements
  getStockMovements(params?: any): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.INVENTORY.STOCK_MOVEMENTS, params);
  }

  createStockMovement(movement: Partial<StockMovement>): Observable<StockMovement> {
    return this.post(API_CONFIG.ENDPOINTS.INVENTORY.STOCK_MOVEMENTS, movement);
  }

  // Inventory specific actions
  getLowStockAlerts(): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.INVENTORY.LOW_STOCK_ALERTS);
  }

  getLowStockProducts(): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.INVENTORY.LOW_STOCK_PRODUCTS);
  }

  getCategories(): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.INVENTORY.CATEGORIES);
  }

  // Stock operations
  adjustStock(productId: number, quantity: number, reason: string): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.INVENTORY.PRODUCTS}${productId}/adjust_stock/`, {
      quantity,
      reason
    });
  }

  transferStock(fromProductId: number, toProductId: number, quantity: number): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.INVENTORY.PRODUCTS}transfer_stock/`, {
      from_product: fromProductId,
      to_product: toProductId,
      quantity
    });
  }

  bulkUpdateStock(updates: { id: number; stock: number }[]): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.INVENTORY.PRODUCTS}bulk_update_stock/`, { updates });
  }

  // Reports
  getInventoryReport(params?: any): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.INVENTORY.PRODUCTS}report/`, params);
  }

  getStockMovementReport(params?: any): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.INVENTORY.STOCK_MOVEMENTS}report/`, params);
  }
}
