import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { BaseApiService } from '../base-api.service';
import { API_CONFIG } from '../../config/api.config';

export interface Client {
  id: number;
  full_name: string;
  email: string;
  phone: string;
  address?: string;
  birthday?: string;
  date_of_birth?: string;
  gender: string;
  notes: string;
  is_active: boolean;
  created_at: string;
  tenant: number;
  loyalty_points?: number;
  last_visit?: string;
  preferred_stylist?: number;
  source?: string;
  user?: number;
  created_by?: number;
  updated_at?: string;
}

@Injectable({
  providedIn: 'root'
})
export class ClientService extends BaseApiService {

  getClients(params?: any): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.CLIENTS, params);
  }

  getClient(id: number): Observable<Client> {
    return this.get(`${API_CONFIG.ENDPOINTS.CLIENTS}${id}/`);
  }

  createClient(client: Partial<Client>): Observable<Client> {
    return this.post(API_CONFIG.ENDPOINTS.CLIENTS, client);
  }

  updateClient(id: number, client: Partial<Client>): Observable<Client> {
    return this.put(`${API_CONFIG.ENDPOINTS.CLIENTS}${id}/`, client);
  }

  deleteClient(id: number): Observable<any> {
    return this.delete(`${API_CONFIG.ENDPOINTS.CLIENTS}${id}/`);
  }

  // Client specific actions
  getClientHistory(id: number): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.CLIENTS}${id}/history/`);
  }

  getClientAppointments(id: number): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.CLIENTS}${id}/appointments/`);
  }

  getClientStats(id: number): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.CLIENTS}${id}/stats/`);
  }

  searchClients(query: string): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.CLIENTS, { search: query });
  }

  getActiveClients(): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.CLIENTS, { is_active: true });
  }

  // Métodos para sistema de cumpleaños
  getBirthdaysThisMonth(): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.CLIENTS}birthdays_this_month/`);
  }

  getBirthdaysToday(): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.CLIENTS}birthdays_today/`);
  }

  getUpcomingBirthdays(): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.CLIENTS}upcoming_birthdays/`);
  }
}
