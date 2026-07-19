import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { BaseApiService } from '../base-api.service';
import { API_CONFIG } from '../../config/api.config';

export interface AuditLog {
  id: number;
  user: {
    id: number;
    email: string;
    full_name: string;
  } | null;
  action: string;
  description: string;
  content_type?: number;
  content_type_name?: string;
  object_id?: number;
  object_repr?: string;
  ip_address?: string;
  user_agent?: string;
  extra_data?: any;
  timestamp: string;
  source: string;
}

export interface AuditLogResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: AuditLog[];
}

export interface AuditSummaryBreakdown {
  action?: string;
  source?: string;
  count: number;
}

export interface AuditSummaryResponse {
  recent_activity: AuditLog[];
  total_logs: number;
  error_logs: number;
  warning_logs: number;
  last_24h: number;
  actions_breakdown: AuditSummaryBreakdown[];
  sources_breakdown: AuditSummaryBreakdown[];
}

@Injectable({
  providedIn: 'root'
})
export class ActivityLogService extends BaseApiService {
  
  getAuditLogs(params?: any): Observable<AuditLogResponse> {
    return this.get(`${API_CONFIG.ENDPOINTS.AUDIT}logs/`, params);
  }

  getActions(): Observable<{value: string, label: string}[]> {
    return this.get(`${API_CONFIG.ENDPOINTS.AUDIT}logs/actions/`);
  }

  getSources(): Observable<{value: string, label: string}[]> {
    return this.get(`${API_CONFIG.ENDPOINTS.AUDIT}logs/sources/`);
  }

  getSummary(): Observable<AuditSummaryResponse> {
    return this.get<AuditSummaryResponse>(`${API_CONFIG.ENDPOINTS.AUDIT}logs/summary/`);
  }
}
