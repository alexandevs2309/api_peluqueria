import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { BaseApiService } from '../base-api.service';
import { API_CONFIG } from '../../config/api.config';
import { NotificationService } from '../notification/notification.service';

export interface Appointment {
  id: number;
  client: number;
  stylist: number;
  service?: number;
  date_time: string;
  status: 'scheduled' | 'completed' | 'cancelled' | 'no_show';
  description?: string;
  created_at: string;
  updated_at: string;
  sale?: number;
  stylist_info?: any;
}

export interface AppointmentWithDetails extends Appointment {
  client_name?: string;
  stylist_name?: string;
  service_name?: string;
  service_price?: number;
  service_duration?: number;
  client_phone?: string;
  branch?: number;
}

@Injectable({
  providedIn: 'root'
})
export class AppointmentService extends BaseApiService {
  private notificationService = inject(NotificationService);

  getAppointments(params?: any): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.APPOINTMENTS.BASE, params);
  }

  getAppointment(id: number): Observable<Appointment> {
    return this.get(`${API_CONFIG.ENDPOINTS.APPOINTMENTS.BASE}${id}/`);
  }

  createAppointment(appointment: Partial<Appointment>): Observable<Appointment> {
    return this.post<Appointment>(API_CONFIG.ENDPOINTS.APPOINTMENTS.BASE, appointment).pipe(
      tap(() => {
        // ✅ Actualizar notificaciones inmediatamente después de crear cita
        setTimeout(() => this.notificationService.refresh(), 500);
      })
    );
  }

  updateAppointment(id: number, appointment: Partial<Appointment>): Observable<Appointment> {
    return this.put(`${API_CONFIG.ENDPOINTS.APPOINTMENTS.BASE}${id}/`, appointment);
  }

  deleteAppointment(id: number): Observable<any> {
    return this.delete(`${API_CONFIG.ENDPOINTS.APPOINTMENTS.BASE}${id}/`);
  }

  // Appointment actions
  confirmAppointment(id: number): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.APPOINTMENTS.BASE}${id}/confirm/`, {});
  }

  cancelAppointment(id: number, reason?: string): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.APPOINTMENTS.BASE}${id}/cancel/`, { reason });
  }

  completeAppointment(id: number): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.APPOINTMENTS.BASE}${id}/complete/`, {});
  }

  rescheduleAppointment(id: number, newDateTime: string): Observable<any> {
    return this.post(`${API_CONFIG.ENDPOINTS.APPOINTMENTS.BASE}${id}/reschedule/`, { 
      new_date_time: newDateTime 
    });
  }

  // Calendar views
  getCalendarAppointments(start: string, end: string): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.APPOINTMENTS.BASE, { start, end });
  }

  getDayAppointments(date: string): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.APPOINTMENTS.BASE, { date });
  }

  // Availability
  checkAvailability(stylistId: number, date: string, duration: number): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.APPOINTMENTS.BASE}check_availability/`, {
      stylist_id: stylistId,
      date,
      duration
    });
  }

  getAvailableSlots(stylistId: number, date: string): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.APPOINTMENTS.BASE}available_slots/`, {
      stylist_id: stylistId,
      date
    });
  }

  // Backend specific methods
  getAvailability(stylistId: number, date: string, excludeId?: number): Observable<any> {
    const params: any = { stylist_id: stylistId, date };
    if (excludeId) {
      params.exclude_id = excludeId;
    }
    return this.get(`${API_CONFIG.ENDPOINTS.APPOINTMENTS.BASE}availability/`, params);
  }

  getTodayAppointments(): Observable<any> {
    return this.get(`${API_CONFIG.ENDPOINTS.APPOINTMENTS.BASE}today/`);
  }

  // Test endpoint
  testAppointment(): Observable<any> {
    return this.get(API_CONFIG.ENDPOINTS.APPOINTMENTS.TEST);
  }
}
