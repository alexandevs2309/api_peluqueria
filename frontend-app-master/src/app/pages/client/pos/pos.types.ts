export interface CatalogItem {
  id: number
  name: string
  description?: string
  price: number
  category?: string
  stock?: number
  is_active?: boolean
  image?: string
  duration?: number
  user?: { id: number; full_name?: string; email?: string; role?: string }
}

export interface CartItem {
  id: string
  type: 'service' | 'product'
  item: CatalogItem
  employee?: CatalogItem
  quantity: number
  price: number
  subtotal: number
}

export interface SaleData {
  id: number
  client: { id: number; full_name?: string; phone?: string }
  employee?: { id: number; user?: { full_name?: string; email?: string } }
  date_time: string
  total: number
  discount: number
  paid: number
  payment_method: string
  status: string
  details: SaleDetailPayload[]
  payments?: SalePaymentPayload[]
  points_earned?: number
  points_redeemed?: number
  cashier_name?: string
  ncf?: string
  ncf_type?: string
  rnc?: string
  company_name?: string
  coupon_code?: string
  coupon_id?: number
}

export interface DashboardData {
  today: DailyStats
  by_type: { services: number; products: number }
  top_products: { name: string; sold: number }[]
  top_services: { name: string; sold: number; revenue: number }[]
  weekly_revenue: { day: string; revenue: number }[]
  payment_methods: { payment_method: string; total: number }[]
  monthly_revenue: { month: string; revenue: number }[]
  revenue_today?: number
  sales_today_count?: number
  average_ticket?: number
  daily_revenue?: { day: string; revenue: number }[]
  payment_breakdown?: { payment_method: string; total: number }[]
}

export interface TicketItem {
  item?: { name: string }
  name?: string
  type?: string
  quantity?: number
  price?: number
  subtotal?: number
  content_type?: string
  object_id?: number
}

export interface TicketData {
  id?: number
  items: TicketItem[]
  cliente: Record<string, unknown> | null
  empleado: Record<string, unknown> | null
  cajero?: string
  subtotal: number
  descuento: number
  total: number
  metodoPago: string
  status?: string
  date_time?: string
  paid?: number
  payment_method?: string
  points_earned?: number
  points_redeemed?: number
  ncf?: string
  ncf_type?: string
  rnc?: string
  company_name?: string
  coupon_code?: string
  coupon_id?: number
}

export interface CashCloseData {
  fecha: string
  hora: string
  montoInicial: number
  ventasEfectivo: number
  montoEsperado: number
  montoContado: number
  diferencia: number
  denominaciones?: Denomination[]
  totalEsperado?: number
  totalReal?: number
  estadisticas?: Record<string, unknown>
}

export interface Promotion {
  id: number
  name: string
  description?: string
  type: string
  discount_value: number
  min_amount?: number
  start_date?: string
  end_date?: string
  is_active: boolean
}

export interface SalePayload {
  client: number | null
  employee_id: number | null
  payment_method: string
  discount: number
  total: number
  paid: number
  details: SaleDetailPayload[]
  payments: SalePaymentPayload[]
  promotion_id?: number | null
  coupon_id?: number | null
  cash_register?: number | null
}

export interface SaleDetailPayload {
  content_type: string
  object_id: number
  name: string
  quantity: number
  price: number
}

export interface SalePaymentPayload {
  method: string
  amount: number
}

export interface CashRegister {
  id: number
  user: any
  user_name?: string
  opened_at: string
  closed_at?: string
  initial_cash: number
  final_cash?: number
  is_open: boolean
  current_amount?: number
  sales_amount?: number
}

export interface DailyStats {
  ventas: number
  ingresos: number
  ticketPromedio: number
}

export interface Denomination {
  valor: number
  cantidad: number
  total: number
}

export interface MixedPayment {
  metodo: string
  monto: number
}

export interface Category {
  name: string
  value: string
}

export interface PosConfig {
  business_name?: string
  address?: string
  phone?: string
  email?: string
  rnc?: string
  currency_symbol?: string
  tax_rate?: number
  receipt_footer?: string
}
