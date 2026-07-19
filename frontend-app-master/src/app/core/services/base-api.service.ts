import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_CONFIG } from '../config/api.config';

@Injectable({
  providedIn: 'root'
})
export class BaseApiService {
  protected baseUrl = API_CONFIG.BASE_URL;
  protected http = inject(HttpClient);

  constructor() {}

  protected get<T>(endpoint: string, params?: any, options?: { withCredentials?: boolean; [key: string]: any }): Observable<T> {
    const httpParams = this.buildParams(params);
    const requestOptions = { withCredentials: true, params: httpParams, ...options };
    return this.http.get<T>(`${this.baseUrl}${endpoint}`, requestOptions);
  }

  protected post<T>(endpoint: string, data?: any, options?: { withCredentials?: boolean; [key: string]: any }): Observable<T> {
    return this.http.post<T>(`${this.baseUrl}${endpoint}`, data, { withCredentials: true, ...options });
  }

  protected put<T>(endpoint: string, data?: any): Observable<T> {
    return this.http.put<T>(`${this.baseUrl}${endpoint}`, data, { withCredentials: true });
  }

  protected patch<T>(endpoint: string, data?: any): Observable<T> {
    return this.http.patch<T>(`${this.baseUrl}${endpoint}`, data, { withCredentials: true });
  }

  protected delete<T>(endpoint: string): Observable<T> {
    return this.http.delete<T>(`${this.baseUrl}${endpoint}`, { withCredentials: true });
  }

  protected postFormData<T>(endpoint: string, formData: FormData): Observable<T> {
    return this.http.post<T>(`${this.baseUrl}${endpoint}`, formData, { withCredentials: true });
  }

  protected putFormData<T>(endpoint: string, formData: FormData): Observable<T> {
    return this.http.put<T>(`${this.baseUrl}${endpoint}`, formData, { withCredentials: true });
  }

  private buildParams(params?: any): HttpParams {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== null && params[key] !== undefined) {
          httpParams = httpParams.set(key, params[key].toString());
        }
      });
    }
    return httpParams;
  }
}
