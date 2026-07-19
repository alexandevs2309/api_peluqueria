import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { BaseApiService } from '../base-api.service';
import { API_CONFIG } from '../../config/api.config';

export interface Employee {
  id: number;
  user: any;
  user_id_read?: number;
  tenant: number;
  branch?: number | null;
  profession?: string;
  profession_display?: string;
  phone?: string;
  hire_date?: string;
  is_active: boolean;
  service_ids?: number[];
  services_count?: number;
  created_at?: string;
  updated_at?: string;
}

export interface CreateEmployeeRequest {
  user_id: number;
  branch?: number | null;
  profession?: string;
  phone?: string;
  hire_date?: string;
  is_active: boolean;
}

export interface UpdateEmployeeRequest {
  branch?: number | null;
  profession?: string;
  phone?: string;
  hire_date?: string;
  is_active: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class EmployeeService extends BaseApiService {

  // Employee CRUD
  getEmployees(params?: any): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.EMPLOYEES.BASE, params);
  }

  getEmployee(id: number): Observable<Employee> {
    return this.get(`${API_CONFIG.ENDPOINTS.EMPLOYEES.BASE}${id}/`);
  }

  getEmployeeByUserId(userId: number): Observable<Employee> {
    return this.get(`${API_CONFIG.ENDPOINTS.EMPLOYEES.BASE}by-user/${userId}/`);
  }

  createEmployee(employee: Partial<Employee>): Observable<Employee> {
    return this.post(API_CONFIG.ENDPOINTS.EMPLOYEES.BASE, employee);
  }

  updateEmployee(id: number, employee: UpdateEmployeeRequest): Observable<Employee> {
    return this.put(`${API_CONFIG.ENDPOINTS.EMPLOYEES.BASE}${id}/`, employee);
  }

  patchEmployee(id: number, employee: Partial<UpdateEmployeeRequest>): Observable<Employee> {
    return this.patch(`${API_CONFIG.ENDPOINTS.EMPLOYEES.BASE}${id}/`, employee);
  }

  deleteEmployee(id: number): Observable<any> {
    return this.delete(`${API_CONFIG.ENDPOINTS.EMPLOYEES.BASE}${id}/`);
  }

  // Schedules
  getSchedules(params?: any): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.EMPLOYEES.SCHEDULES, params);
  }

  createSchedule(schedule: any): Observable<any> {
    return this.post(API_CONFIG.ENDPOINTS.EMPLOYEES.SCHEDULES, schedule);
  }

  updateSchedule(id: number, schedule: any): Observable<any> {
    return this.put(`${API_CONFIG.ENDPOINTS.EMPLOYEES.SCHEDULES}${id}/`, schedule);
  }

  deleteSchedule(id: number): Observable<any> {
    return this.delete(`${API_CONFIG.ENDPOINTS.EMPLOYEES.SCHEDULES}${id}/`);
  }

  // Attendance
  getAttendance(params?: any): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.EMPLOYEES.ATTENDANCE, params);
  }

  checkIn(employee?: number): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.EMPLOYEES.ATTENDANCE}check_in/`, employee ? { employee } : {});
  }

  checkOut(employee?: number): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.EMPLOYEES.ATTENDANCE}check_out/`, employee ? { employee } : {});
  }

  justifyAttendance(id: number, reason: string): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.EMPLOYEES.ATTENDANCE}${id}/justify/`, { reason });
  }

  // Employee specific actions
  assignServices(employeeId: number, serviceIds: number[]): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.EMPLOYEES.BASE}${employeeId}/assign_services/`, {
      service_ids: serviceIds
    });
  }

  getEmployeeServices(employeeId: number): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.EMPLOYEES.BASE}${employeeId}/services/`);
  }

  getEmployeeSchedule(employeeId: number): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.EMPLOYEES.BASE}${employeeId}/schedule/`);
  }

  setEmployeeSchedule(employeeId: number, schedules: any[]): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.EMPLOYEES.BASE}${employeeId}/set_schedule/`, {
      schedules
    });
  }

  getEmployeeStats(employeeId: number): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.EMPLOYEES.BASE}${employeeId}/stats/`);
  }

  // Payroll methods
  getPayrollConfig(employeeId: number): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.EMPLOYEES.BASE}${employeeId}/payroll_config/`);
  }

  updatePayrollConfig(employeeId: number, config: any): Observable<any> {
    return this.put(`${API_CONFIG.ENDPOINTS.EMPLOYEES.BASE}${employeeId}/payroll_config/`, config);
  }

  getPaymentHistory(employeeId: number): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.EMPLOYEES.BASE}${employeeId}/payment_history/`);
  }

  getPaymentStats(employeeId: number): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.EMPLOYEES.BASE}${employeeId}/payment_stats/`);
  }

  getPaymentReceipt(paymentId: string): Observable<any> {
    return this.get(`/payroll/client/payroll/payments/${paymentId}/receipt/`);
  }

  // Loans methods
  getLoans(employeeId: number): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.EMPLOYEES.BASE}${employeeId}/loans/`);
  }

  getLoansSummary(employeeId: number): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.EMPLOYEES.BASE}${employeeId}/loans_summary/`);
  }

  createLoan(employeeId: number, loanData: any): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.EMPLOYEES.BASE}${employeeId}/loans/`, loanData);
  }
}
