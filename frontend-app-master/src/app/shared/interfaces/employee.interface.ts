export interface BaseEmployee {
  id: number;
  user_id: number;
  full_name: string;
  email: string;
  role: 'stylist' | 'assistant' | 'manager';
  is_active: boolean;
}

export interface CashRegisterState {
  id: number;
  is_open: boolean;
  current_amount: number;
  initial_amount: number;
  opened_at: string;
}