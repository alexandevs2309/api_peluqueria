import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { BaseApiService } from '../base-api.service';
import { API_CONFIG } from '../../config/api.config';

export interface Tutorial {
  id?: number;
  module: string;
  title: string;
  description: string;
  video_url: string;
  thumbnail_url: string;
  duration: string;
  order: number;
  is_published: boolean;
}

@Injectable({ providedIn: 'root' })
export class TutorialAdminService extends BaseApiService {
  private readonly endpoint = API_CONFIG.ENDPOINTS.TUTORIALS.ADMIN;

  getAll(): Observable<Tutorial[]> {
    return this.get<Tutorial[]>(this.endpoint);
  }

  getById(id: number): Observable<Tutorial> {
    return this.get<Tutorial>(`${this.endpoint}${id}/`);
  }

  create(data: Partial<Tutorial>): Observable<Tutorial> {
    return this.post<Tutorial>(this.endpoint, data);
  }

  update(id: number, data: Partial<Tutorial>): Observable<Tutorial> {
    return this.patch<Tutorial>(`${this.endpoint}${id}/`, data);
  }

  remove(id: number): Observable<any> {
    return this.delete(`${this.endpoint}${id}/`);
  }
}
