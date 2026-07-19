export interface SaleDto {
  id: number;
  client?: number;
  employee_id?: number;
  payment_method: 'cash' | 'card' | 'transfer' | 'mixed';
  discount: number;
  total: number;
  paid: number;
  date_time: string;
}

export interface SaleWithDetailsDto extends SaleDto {
  details: any[];
  payments: any[];
  client_name?: string;
  employee_name?: string;
  user_name?: string;
  cashier_name?: string;
  fiscal_requested?: boolean;
  fiscal_voucher_type?: string;
  fiscal_name?: string;
  fiscal_document?: string;
}

export interface CreateSaleDto {
  client?: number;
  employee_id?: number;
  payment_method: 'cash' | 'card' | 'transfer' | 'mixed';
  discount: number;
  discount_reason?: string;
  total: number;
  paid: number;
  details: any[];
  payments: any[];
}
