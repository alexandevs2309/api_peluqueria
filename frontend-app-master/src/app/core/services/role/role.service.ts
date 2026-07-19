import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { BaseApiService } from '../base-api.service';
import { API_CONFIG } from '../../config/api.config';

export interface Role {
  id: number;
  name: string;
  description: string;
  scope: string;
  module?: string;
}

@Injectable({
  providedIn: 'root'
})
export class RoleService extends BaseApiService {
  getRoles(): Observable<Role[]> {
    return this.get<Role[]>(API_CONFIG.ENDPOINTS.ROLES);
  }
}
