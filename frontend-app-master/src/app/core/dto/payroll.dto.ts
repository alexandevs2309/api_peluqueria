export interface PayrollConfigDto {
  salary_type: string;
  payment_frequency: string;
  commission_percentage: number;
  commission_payment_mode: string;
  contractual_monthly_salary: number;
  apply_afp: boolean;
  apply_sfs: boolean;
  apply_isr: boolean;
}

export interface PaymentStatsDto {
  employee_name: string;
  all_time: {
    total_payments: number;
    total_net: number;
    average_payment: number;
  };
  last_payment: {
    date: string;
    amount: number;
    method: string;
  } | null;
}

export interface PaymentReceiptDto {
  payment_id: string;
  employee: {
    name: string;
    email: string;
  };
  period: {
    display: string;
    start_date: string;
    end_date: string;
  };
  amounts: {
    gross_amount: number;
    deductions: {
      afp: number;
      sfs: number;
      isr: number;
      loans: number;
      total: number;
    };
    net_amount: number;
  };
  payment_info: {
    method: string;
    reference: string;
    paid_at: string;
    paid_by: string;
  };
  company: {
    name: string;
    address: string;
    phone: string;
  };
}
