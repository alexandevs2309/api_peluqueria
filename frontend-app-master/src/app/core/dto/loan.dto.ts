export interface LoanDto {
  id: number;
  loan_type: string;
  amount: number;
  status: string;
  installments: number;
  monthly_payment: number;
  remaining_balance: number;
  request_date: string;
  reason: string;
}

export interface LoanSummaryDto {
  total_loans: number;
  total_amount: number;
  remaining_balance: number;
  next_deduction: number;
  active_loans: number;
}

export interface CreateLoanDto {
  loan_type: string;
  amount: number;
  installments: number;
  reason: string;
}
