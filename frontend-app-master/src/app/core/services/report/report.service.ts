import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { BaseApiService } from '../base-api.service';
import { API_CONFIG } from '../../config/api.config';

export interface ReportParams {
  start_date?: string;
  end_date?: string;
  employee_id?: number;
  service_id?: number;
  client_id?: number;
  format?: 'json' | 'csv' | 'pdf';
}

export interface AdminReportResponse {
  period: string;
  total_revenue: number;
  commission_rate?: number;
  platform_commission_amount?: number;
  net_revenue?: number;
  pending_payments: number;
  overdue_invoices: number;
  revenue_trend: Array<{
    label?: string;
    month?: string;
    revenue: number;
    commission_amount?: number;
    net_revenue?: number;
  }>;
  top_tenants: Array<{
    tenant_name: string;
    revenue: number;
    commission_amount?: number;
    net_revenue?: number;
    plan: string;
  }>;
  summary: {
    total_invoices: number;
    paid_invoices: number;
    average_invoice: number;
  };
}

@Injectable({
  providedIn: 'root'
})
export class ReportService extends BaseApiService {

  // General reports
  getReports(params?: any): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.REPORTS.BASE, params);
  }

  // Sales reports
  getSalesReport(params?: ReportParams): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.REPORTS.SALES, params);
  }

  getDailySalesReport(date: string): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.REPORTS.SALES, { date });
  }

  getMonthlySalesReport(year: number, month: number): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.REPORTS.SALES, { year, month });
  }

  // Employee reports
  getEmployeeReport(params?: ReportParams): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.REPORTS.EMPLOYEES, params);
  }

  getEmployeePerformanceReport(employeeId: number, params: ReportParams): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.REPORTS.EMPLOYEES, { ...params, employee_id: employeeId });
  }

  // Appointment reports
  getAppointmentReport(params: ReportParams): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.REPORTS.BY_TYPE, { ...params, type: 'appointments' });
  }

  getAppointmentStatusReport(params: ReportParams): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.REPORTS.BY_TYPE, { ...params, type: 'appointments', group_by: 'status' });
  }

  // Client reports
  getClientReport(params: ReportParams): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.REPORTS.BASE}client-analytics/`, params);
  }

  getClientRetentionReport(params: ReportParams): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.REPORTS.BASE}client-analytics/`, { ...params, mode: 'retention' });
  }

  // Service reports
  getServiceReport(params: ReportParams): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.REPORTS.BASE}services-performance/`, params);
  }

  getPopularServicesReport(params: ReportParams): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.REPORTS.BASE}services-performance/`, { ...params, sort: 'popular' });
  }

  // Inventory reports
  getInventoryReport(params: ReportParams): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.INVENTORY.PRODUCTS, params);
  }

  getLowStockReport(): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.INVENTORY.LOW_STOCK_PRODUCTS);
  }

  // Financial reports
  getFinancialReport(params: ReportParams): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.REPORTS.BASE}kpi/`, params);
  }

  getProfitLossReport(params: ReportParams): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.REPORTS.BASE}kpi/`, { ...params, mode: 'profit_loss' });
  }

  // Dashboard reports
  getDashboardStats(period?: string): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.REPORTS.DASHBOARD, { period });
  }

  getKPIReport(): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.REPORTS.BASE}kpi/`);
  }

  // SuperAdmin reports
  getAdminReport(params?: { period?: string; start_date?: string; end_date?: string }): Observable<AdminReportResponse> {
    return this.get<AdminReportResponse>(API_CONFIG.ENDPOINTS.REPORTS.ADMIN, params);
  }

  // Export functions
  exportReport(reportType: string, params: ReportParams): Observable<Blob> {
    return this.get(`${API_CONFIG.ENDPOINTS.REPORTS.BASE}${reportType}/export/`, params);
  }

  downloadReport(reportType: string, params: ReportParams): void {
    this.exportReport(reportType, params).subscribe(blob => {
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${reportType}-report.${params.format || 'pdf'}`;
      link.click();
      window.URL.revokeObjectURL(url);
    });
  }
}
