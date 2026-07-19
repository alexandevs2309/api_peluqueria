import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { BaseApiService } from '../base-api.service';

export interface SupportTicket {
  id: number;
  subject: string;
  description: string;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  status: 'open' | 'in_progress' | 'resolved' | 'closed';
  created_by: number;
  created_by_name: string;
  created_by_email: string;
  tenant_name?: string;
  admin_reply?: string | null;
  replied_at?: string | null;
  created_at: string;
  updated_at: string;
}

@Injectable({ providedIn: 'root' })
export class SupportTicketService extends BaseApiService {
  getMyTickets(): Observable<SupportTicket[]> {
    return this.get<SupportTicket[]>('/support/tickets/');
  }

  getTicket(id: number): Observable<SupportTicket> {
    return this.get<SupportTicket>(`/support/tickets/${id}/`);
  }

  createTicket(data: Partial<SupportTicket>): Observable<SupportTicket> {
    return this.post<SupportTicket>('/support/tickets/', data);
  }

  closeTicket(id: number): Observable<{ status: string }> {
    return this.post<{ status: string }>(`/support/tickets/${id}/close/`, {});
  }

  updateTicketStatus(id: number, status: string): Observable<SupportTicket> {
    return this.patch<SupportTicket>(`/support/tickets/${id}/`, { status });
  }

  replyTicket(id: number, reply: string): Observable<SupportTicket> {
    return this.post<SupportTicket>(`/support/tickets/${id}/reply/`, { reply });
  }
}
