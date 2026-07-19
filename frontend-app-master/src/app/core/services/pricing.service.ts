import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface PricingPlan {
  id: string;
  name: string;
  price: number;
  features: string[];
  popular?: boolean;
  description: string;
}

@Injectable({
  providedIn: 'root'
})
export class PricingService {
  private apiUrl = `${environment.apiUrl}/subscriptions/plans`;

  constructor(private http: HttpClient) {}

  getPublicPlans(): Observable<PricingPlan[]> {
    return this.http.get<PricingPlan[]>(`${this.apiUrl}/public-catalog/`);
  }

  getLandingPlans(): Observable<PricingPlan[]> {
    // Usar el endpoint de subscriptions que ya existe
    return this.http.get<PricingPlan[]>(`${environment.apiUrl}/subscriptions/plans/`);
  }
}
