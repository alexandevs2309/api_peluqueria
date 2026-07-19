export interface PaymentDto {
  id: string;
  paid_at: string;
  gross_amount: number;
  net_amount: number;
  total_deductions: number;
  payment_method: string;
  period_display: string;
  payment_reference: string;
}

export interface PaymentMethodDto {
  payment_method: string;
  total: number;
}
