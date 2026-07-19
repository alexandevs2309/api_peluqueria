import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { BaseApiService } from './base-api.service';

export interface SystemSettings {
  platform_name: string;
  platform_domain: string;
  support_email: string;
  max_tenants: number;
  trial_days: number;
  default_currency: string;
  supported_languages: string[];
  platform_commission_rate: number;
  basic_plan_max_employees: number;
  premium_plan_max_employees: number;
  enterprise_plan_max_employees: number;
  stripe_enabled: boolean;
  paypal_enabled: boolean;
  twilio_enabled: boolean;
  sendgrid_enabled: boolean;
  aws_s3_enabled: boolean;
  maintenance_mode: boolean;
  email_notifications: boolean;
  auto_suspend_expired: boolean;
  smtp_host?: string;
  smtp_port?: number;
  smtp_username?: string;
  smtp_password?: string;
  from_email?: string;
  from_name?: string;
  stripe_public_key?: string;
  stripe_secret_key?: string;
  webhook_secret?: string;
  paypal_client_id?: string;
  paypal_client_secret?: string;
  paypal_sandbox?: boolean;
  twilio_account_sid?: string;
  twilio_auth_token?: string;
  twilio_phone_number?: string;
  jwt_expiry_minutes?: number;
  max_login_attempts?: number;
  login_lockout_minutes?: number;
  password_min_length?: number;
  require_email_verification?: boolean;
  enable_mfa?: boolean;
  auto_upgrade_limits?: boolean;
}

export interface PublicBrandingSettings {
  platform_name: string;
  support_email: string;
  platform_domain: string;
  public_site_url: string;
  supported_languages: string[];
  maintenance_mode: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class SettingsService extends BaseApiService {

  getSettings(): Observable<SystemSettings> {
    return this.get<SystemSettings>('/system-settings/');
  }

  getPublicBranding(): Observable<PublicBrandingSettings> {
    return this.get<PublicBrandingSettings>('/settings/public-branding/');
  }

  updateSettings(settings: Partial<SystemSettings>): Observable<SystemSettings> {
        return this.patch<SystemSettings>('/system-settings/', settings);
  }

  testEmailConnection(emailConfig: any): Observable<any> {
    return this.post<any>('/settings/integrations/test/', { type: 'sendgrid', ...emailConfig });
  }

  testPaymentConnection(paymentConfig: any): Observable<any> {
    return this.post<any>('/settings/integrations/test/', { type: 'stripe', ...paymentConfig });
  }

  testPaypalConnection(paypalConfig: any): Observable<any> {
    return this.post<any>('/settings/integrations/test/', { type: 'paypal', ...paypalConfig });
  }

  testTwilioConnection(twilioConfig: any): Observable<any> {
    return this.post<any>('/settings/integrations/test/', { type: 'twilio', ...twilioConfig });
  }
}
