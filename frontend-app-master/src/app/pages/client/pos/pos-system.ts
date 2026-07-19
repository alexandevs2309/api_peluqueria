import { Component, OnInit, inject, signal, computed, HostListener, ViewChild, ElementRef } from '@angular/core'
import { CommonModule } from '@angular/common'
import { FormsModule } from '@angular/forms'
import { Router } from '@angular/router'
import { firstValueFrom } from 'rxjs'
import { BrowserMultiFormatReader, IScannerControls } from '@zxing/browser'
import { ButtonModule } from 'primeng/button'
import { InputTextModule } from 'primeng/inputtext'
import { SelectModule } from 'primeng/select'
import { TableModule } from 'primeng/table'
import { CardModule } from 'primeng/card'
import { DividerModule } from 'primeng/divider'
import { ToastModule } from 'primeng/toast'
import { DialogModule } from 'primeng/dialog'
import { InputNumberModule } from 'primeng/inputnumber'
import { TooltipModule } from 'primeng/tooltip'
import { ChartModule } from 'primeng/chart'
import { TextareaModule } from 'primeng/textarea'
import { MessageService, ConfirmationService } from 'primeng/api'
import { ConfirmDialogModule } from 'primeng/confirmdialog'
import { BarbershopSettingsService } from '../../../shared/services/barbershop-settings.service'
import { OfflineService } from '../../../core/services/offline.service'
import { loadStripe, Stripe, StripeElements, StripeCardElement } from '@stripe/stripe-js'
import { environment } from '../../../../environments/environment'
import { PosRepo } from './pos.repo'
import { PosApi } from './pos.api'
import { PosCart } from './pos.cart'
import { PosSound } from './pos.sound'
import { CatalogItem, DashboardData, PosConfig, Promotion, SaleData, Denomination, TicketData, TicketItem, CashCloseData, CashRegister } from './pos.types'
import { AuthService } from '../../../core/services/auth/auth.service'
import { TrialService } from '../../../core/services/trial.service'
import { LocaleService } from '../../../core/services/locale/locale.service'
import { BranchService, Branch } from '../../../core/services/branch/branch.service'
import { PlanAccessService } from '../../../core/services/plan-access.service'
import { AuBtn, AuSkeleton } from '../../../shared/components'

@Component({
  selector: 'app-pos-system',
  standalone: true,
  imports: [
    CommonModule, FormsModule, ButtonModule, InputTextModule, SelectModule,
    TableModule, CardModule, DividerModule, ToastModule, DialogModule,
    InputNumberModule,     TooltipModule,
    ChartModule,
    TextareaModule,
    ConfirmDialogModule,
    AuBtn,
    AuSkeleton,
  ],
  providers: [MessageService, ConfirmationService],
  templateUrl: './pos-system.html',
  styleUrl: './pos-system.scss',
})
export class PosSystem implements OnInit {
  protected repo = inject(PosRepo)
  protected api = inject(PosApi)
  cart = inject(PosCart)
  private sound = inject(PosSound)
  private messageService = inject(MessageService)
  private confirmationService = inject(ConfirmationService)
  private authService = inject(AuthService)
  private trialService = inject(TrialService)
  protected barbershopSettings = inject(BarbershopSettingsService)
  private branchService = inject(BranchService)
  private router = inject(Router)
  protected localeService = inject(LocaleService)
  private planAccessService = inject(PlanAccessService)
  protected offlineService = inject(OfflineService)

  t(key: string): string {
    return this.localeService.t(key as any)
  }

  Math = Math

  // Catalog UI state
  activeMobileView = signal<'catalog' | 'cart'>('catalog')
  tipoActivo: 'services' | 'products' = 'services'
  categoriaSeleccionada = ''
  busqueda = ''
  codigoBarras = ''
  modoScanner = false
  mostarCamara = signal(false)
  @ViewChild('scannerVideo') scannerVideoRef!: ElementRef<HTMLVideoElement>
  private scannerControls: IScannerControls | null = null

  toggleMobileView() {
    this.activeMobileView.update(view => view === 'catalog' ? 'cart' : 'catalog')
  }

  // Inventory feature
  tieneInventario = true
  inventoryCheckDone = false

  // Branch management
  branches = signal<Branch[]>([])
  selectedBranch = signal<Branch | null>(null)

  // Dialog visibility
  mostrarDialogoAbrirCaja = false
  mostrarDialogoCerrarCaja = false
  mostrarDialogoPago = false
  mostrarDialogoArqueo = false
  mostrarDialogoHistorial = false
  mostrarDialogoPromociones = false
  mostrarticket = false
  mostrarDialogoFirma = false
  mostrarDialogoSinInventario = false

  // Cash register dialog state
  activeRegisterId: number | null = null
  closingRegister = false
  montoInicialCaja: number | null = null
  montoFinalCaja: number | null = null
  montoEsperado = 0
  ventasEfectivoHoy = 0
  diferenciaCaja = 0

  // Ticket
  ventaActual: TicketData | null = null
  firmaCliente = ''

  // History
  historialVentas: SaleData[] = []
  cargandoHistorial = false

  // Payment
  get metodosPago() {
    const t = this.t.bind(this)
    return [
      { label: t('pos.cash'), value: 'cash' },
      { label: t('pos.card'), value: 'card' },
      { label: t('pos.transfer'), value: 'transfer' },
      { label: t('pos.mixed'), value: 'mixed' },
    ]
  }

  // Al hacer focus en inputs numéricos, seleccionar todo para escribir encima
  selectOnFocus(event: Event) {
    const input = event.target as HTMLInputElement
    setTimeout(() => input.select())
  }

  // Selecciona el método de pago
  selectPaymentMethod(method: string) {
    this.cart.paymentMethod.set(method)
  }

  // Dashboard
  mostrarDashboard = false
  dashboardData: DashboardData | null = null
  dashboardLoading = false
  chartRevenue: unknown = null
  chartOptions: unknown = null
  chartPayment: unknown = null
  chartMonthly: unknown = null

  // Reembolso guiado
  mostrarDialogoReembolso = false
  ventaAReembolsar: SaleData | null = null
  motivoReembolso = ''
  reembolsando = false

  // Stripe
  mostrarDialogoTarjeta = false
  stripe: Stripe | null = null
  stripeElements: StripeElements | null = null
  stripeCard: StripeCardElement | null = null
  stripeLoading = false
  stripeError = ''

  // NCF (Comprobante Fiscal RD)
  get ncfTypes() {
    const t = this.t.bind(this)
    return [
      { label: t('pos.ncf_sin_comprobante'), value: '' },
      { label: t('pos.ncf_consumidor_final'), value: '02' },
      { label: t('pos.ncf_credito_fiscal'), value: '01' },
      { label: t('pos.ncf_regimenes_especiales'), value: '14' },
      { label: t('pos.ncf_gubernamentales'), value: '15' },
    ]
  }
  
  getNcfTypeLabel(type: string): string {
    const t = this.t.bind(this)
    switch(type) {
      case '': return t('pos.ncf_sin_comprobante')
      case '01': return t('pos.ncf_credito_fiscal')
      case '02': return t('pos.ncf_consumidor_final')
      case '14': return t('pos.ncf_regimenes_especiales')
      case '15': return t('pos.ncf_gubernamentales')
      default: return type
    }
  }

  selectedNcfType = ''
  ncfRnc = ''
  ncfCompanyName = ''

  couponCode = ''
  aplicandoCupon = false

  // Firma canvas
  firmando = false

  @ViewChild('firmaCanvas') firmaCanvas!: ElementRef<HTMLCanvasElement>


  // Expose signals for template
  get servicios() { return this.repo.services() }
  get productos() { return this.repo.products() }
  get clientes() { return this.repo.clients() }
  get empleados() { return this.repo.employees() }
  get categorias() { return this.repo.categories() }
  get promociones() { return this.repo.promotions() }
  get configuracionPos() { return this.repo.posConfig() }
  get itemsFiltrados() { return this.filteredItems() }

  empleadosFiltrados = computed(() => {
    const all = this.repo.employees()
    const items = this.cart.items()
    const serviceIds = items.filter(i => i.type === 'service').map(i => i.item?.id).filter(Boolean) as number[]
    if (serviceIds.length === 0) return all
    return all.filter((e: any) => {
      const ids: number[] = e.service_ids || []
      return ids.some(id => serviceIds.includes(id))
    })
  })

  ngOnInit() {
    this.repo.loadAll()
    this.checkInventoryFeature()
    this.loadBranches()
    this.verificarEstadoCaja()
    this.cargarStatsDelDia()
  }

  private loadBranches(): void {
    this.branchService.getAll().subscribe({
      next: (data) => {
        this.branches.set(data)
        const active = this.branchService.activeBranch()
        const fallback = data.find(b => b.is_main) || data[0] || null
        this.selectedBranch.set(active || fallback)
        this.verificarEstadoCaja()
      },
    })
  }

  get showBranchSelector(): boolean {
    const user = this.authService.getCurrentUser()
    if (!user) return false
    const role = (user.role || '').trim().toUpperCase()
    const isClientAdmin = role === 'CLIENT_ADMIN' || role === 'CLIENT-ADMIN'
    const hasMultiLocation = this.planAccessService.canAccessFeature('multi_location')
    return isClientAdmin && hasMultiLocation && this.branches().length > 1
  }

  onBranchChange(branch: Branch | null) {
    this.selectedBranch.set(branch)
    this.branchService.selectBranch(branch)
    this.cart.clear()
    this.repo.loadAll(true)
    this.verificarEstadoCaja()
    this.cargarStatsDelDia()
  }

  statsLoading = signal(false)

  private async cargarStatsDelDia() {
    this.statsLoading.set(true)
    try {
      const branchId = this.selectedBranch()?.id
      const params: Record<string, string> = {}
      if (branchId) params['branch_id'] = String(branchId)
      const data = await this.api.getDashboardStats(params) as Record<string, unknown>
      const ventas = Number(data.sales_today_count) || 0
      const ingresos = Number(data.revenue_today) || 0
      this.cart.setStatsFromApi(ventas, ingresos)
      const userCount = Number(data.user_sales_today_count) || 0
      const userRevenue = Number(data.user_sales_today_revenue) || 0
      this.cart.setUserStatsFromApi(userCount, userRevenue)
    } catch {
      // keep existing stats from localStorage
    } finally {
      this.statsLoading.set(false)
    }
  }

  private async checkInventoryFeature() {
    try {
      const status = this.trialService.getCurrentTrialStatus()
      if (status?.features) {
        this.tieneInventario = !!(status.features as Record<string, unknown>)['inventory']
      } else {
        const entitlements = await firstValueFrom(this.trialService.getEntitlements())
        this.tieneInventario = !!(entitlements.features as Record<string, unknown>)?.['inventory']
      }
    } catch {
      this.tieneInventario = true
    }
    this.inventoryCheckDone = true
  }

  seleccionarTipo(tipo: 'services' | 'products') {
    if (tipo === 'products' && !this.tieneInventario) {
      this.mostrarDialogoSinInventario = true
      return
    }
    this.tipoActivo = tipo
    this.filterItems()
  }

  irAPlanes() {
    this.mostrarDialogoSinInventario = false
    this.router.navigate(['/client/checkout'])
  }

  // Filtering
  private filteredItems() {
    let items = this.tipoActivo === 'services' ? this.servicios : this.productos
    if (this.categoriaSeleccionada) {
      items = items.filter(i => (i.category || 'General') === this.categoriaSeleccionada)
    }
    if (this.busqueda.trim()) {
      const q = this.busqueda.toLowerCase().trim()
      items = items.filter(i =>
        i.name.toLowerCase().includes(q) || (i.description?.toLowerCase().includes(q))
      )
    }
    if (this.tipoActivo === 'products') {
      items = items.filter(i => (i.stock ?? 0) > 0)
    }
    return items
  }

  filterItems() {
    this.filteredItems()
  }

  // Cart actions
  agregarAlCarrito(item: CatalogItem) {
    if (!this.cart.isOpen()) {
      this.mostrarDialogoAbrirCaja = true
      return
    }
    if (this.cart.addItem(item, this.tipoActivo === 'services' ? 'service' : 'product')) {
      this.sound.playAdd()
      this.messageService.add({ severity: 'success', summary: this.t('pos.alert.added'), detail: this.t('pos.alert.added_to_cart').replace('{name}', item.name) })
    }
  }

  // Cash register
  async verificarEstadoCaja() {
    try {
      const branchId = this.selectedBranch()?.id
      const resp = await this.api.getCurrentCashRegister({ branch: branchId }) as unknown as CashRegister | null
      const isOpen = resp?.is_open ?? false
      this.cart.isOpen.set(isOpen)
      if (isOpen && resp) {
        this.activeRegisterId = resp.id ?? null
        this.cart.cashStartAmount.set(Number(resp.initial_cash) || 0)
        this.cart.cashSales.set(Number(resp.sales_amount) || 0)
      } else {
        this.activeRegisterId = null
        this.cart.cashStartAmount.set(0)
        this.cart.cashSales.set(0)
      }
    } catch {
      this.activeRegisterId = null
      this.cart.isOpen.set(false)
      this.cart.cashStartAmount.set(0)
      this.cart.cashSales.set(0)
    }
  }

  async abrirCaja() {
    if ((this.montoInicialCaja ?? 0) < 0) {
      this.messageService.add({ severity: 'error', summary: this.t('pos.alert.error_title'), detail: this.t('pos.alert.no_negative_amount') })
      return
    }
    try {
      const resp = await this.api.openCashRegister({
        initial_cash: this.montoInicialCaja ?? 0,
        branch: this.selectedBranch()?.id || null,
      }) as unknown as CashRegister | null
      this.activeRegisterId = resp?.id ?? null
      this.cart.isOpen.set(true)
      this.cart.cashStartAmount.set(this.montoInicialCaja ?? 0)
      this.mostrarDialogoAbrirCaja = false
      this.sound.playOpen()
      this.messageService.add({
        severity: 'success',
        summary: this.t('pos.alert.register_opened'),
        detail: !this.montoInicialCaja 
          ? this.t('pos.alert.register_opened_no_cash') 
          : this.t('pos.alert.register_opened_with_cash').replace('{amount}', this.formatearMoneda(this.montoInicialCaja)),
      })
    } catch {
      this.messageService.add({ severity: 'error', summary: this.t('pos.alert.error_title'), detail: this.t('pos.alert.open_register_error') })
    }
  }

  async prepararCierreCaja() {
    try {
      const branchId = this.selectedBranch()?.id
      const currentUser = this.authService.getCurrentUser()
      const params: any = { is_open: true, branch: branchId }
      if (currentUser?.id) {
        params.user = currentUser.id
      }
      const resp = await this.api.getCashRegisters(params)
      const cajas = resp?.results as CashRegister[] | undefined
      if (!cajas || cajas.length === 0) {
        this.messageService.add({ severity: 'error', summary: this.t('pos.alert.error_title'), detail: this.t('pos.alert.no_open_register_to_close') })
        return
      }
      const activeCaja = cajas[0]
      this.activeRegisterId = activeCaja.id
      this.ventasEfectivoHoy = Number(activeCaja.sales_amount) || 0
      const initialCash = Number(activeCaja.initial_cash) || 0
      this.montoEsperado = initialCash + this.ventasEfectivoHoy
      
      this.cart.cashStartAmount.set(initialCash)
      this.cart.cashSales.set(this.ventasEfectivoHoy)

      this.montoFinalCaja = 0
      this.diferenciaCaja = 0
      this.mostrarDialogoCerrarCaja = true
    } catch {
      this.messageService.add({ severity: 'error', summary: this.t('pos.alert.error_title'), detail: this.t('pos.alert.prepare_close_error') })
    }
  }

  calcularDiferencia() {
    this.diferenciaCaja = (Number(this.montoFinalCaja) || 0) - (Number(this.montoEsperado) || 0)
  }

  cerrarCaja() {
    if (this.montoFinalCaja === null || this.montoFinalCaja === undefined || this.montoFinalCaja < 0) {
      this.messageService.add({ severity: 'error', summary: this.t('pos.alert.error_title'), detail: this.t('pos.alert.final_amount_required') })
      return
    }

    if ((this.montoFinalCaja ?? 0) === 0 && this.montoEsperado > 0) {
      this.confirmationService.confirm({
        message: this.t('pos.confirm.critical_diff_msg').replace(/\${expected}/g, this.montoEsperado.toFixed(2)),
        header: this.t('pos.confirm.critical_diff_header'),
        icon: 'pi pi-exclamation-triangle text-red-500 text-3xl',
        acceptLabel: this.t('pos.confirm.yes_close_zero'),
        rejectLabel: this.t('pos.confirm.cancel'),
        acceptButtonStyleClass: 'p-button-danger p-button-raised',
        rejectButtonStyleClass: 'p-button-text p-button-secondary',
        accept: () => this.ejecutarCierreCaja()
      })
    } else if (Math.abs(this.diferenciaCaja) > 5) {
      this.confirmationService.confirm({
        message: this.t('pos.confirm.box_diff_msg').replace('{diff}', `$${this.diferenciaCaja.toFixed(2)}`),
        header: this.t('pos.confirm.box_diff_header'),
        icon: 'pi pi-info-circle text-amber-500 text-3xl',
        acceptLabel: this.t('pos.confirm.yes_close_diff'),
        rejectLabel: this.t('pos.confirm.cancel'),
        acceptButtonStyleClass: 'p-button-warning p-button-raised',
        rejectButtonStyleClass: 'p-button-text p-button-secondary',
        accept: () => this.ejecutarCierreCaja()
      })
    } else {
      this.ejecutarCierreCaja()
    }
  }

  async ejecutarCierreCaja() {
    if (this.closingRegister) return
    this.closingRegister = true
    try {
      const cajaId = this.activeRegisterId
      if (!cajaId) {
        this.messageService.add({ severity: 'error', summary: this.t('pos.alert.error_title'), detail: this.t('pos.alert.no_open_register_to_close') })
        this.closingRegister = false
        return
      }
      await this.api.closeCashRegister(cajaId, { final_cash: this.montoFinalCaja ?? 0 })
      this.generarPDFCuadre({
        fecha: new Date().toLocaleDateString('es-ES'),
        hora: new Date().toLocaleTimeString('es-ES'),
        montoInicial: this.cart.cashStartAmount(),
        ventasEfectivo: this.ventasEfectivoHoy,
        montoEsperado: this.montoEsperado,
        montoContado: this.montoFinalCaja ?? 0,
        diferencia: this.diferenciaCaja,
        estadisticas: this.cart.dailyStats() as unknown as Record<string, unknown>,
      })
      this.cart.isOpen.set(false)
      this.mostrarDialogoCerrarCaja = false
      this.activeRegisterId = null
      this.closingRegister = false
      this.sound.playClose()
      this.messageService.add({ severity: 'success', summary: this.t('pos.alert.register_closed_title'), detail: this.t('pos.alert.register_closed_success') })
    } catch (err: any) {
      this.closingRegister = false
      const detail = err?.error?.detail || err?.error?.final_cash?.[0] || this.t('pos.alert.close_register_error')
      this.messageService.add({ severity: 'error', summary: this.t('pos.alert.error_title'), detail })
    }
  }

  // Sale processing
  async procesarVenta() {
    if (!this.cart.canSell()) {
      this.messageService.add({ severity: 'error', summary: this.t('pos.alert.invalid_sale'), detail: this.cart.validationMessage() })
      return
    }
    if (this.cart.paymentMethod() === 'cash' || this.cart.paymentMethod() === 'mixed') {
      this.mostrarDialogoPago = true
      return
    }
    if (this.cart.paymentMethod() === 'card') {
      await this.iniciarPagoTarjeta()
      return
    }
    if (this.cart.total() > 500) {
      this.mostrarDialogoFirma = true
      return
    }
    await this.confirmarVenta()
  }

  async confirmarVenta() {
    if (this.api.loading()) return
    const payload = {
      branch: this.selectedBranch()?.id || null,
      client: this.cart.client()?.id || null,
      employee_id: this.cart.employee()?.id || null,
      payment_method: this.cart.paymentMethod(),
      discount: Number(this.cart.discount()) || 0,
      total: this.cart.total(),
      paid: this.cart.total(),
      details: this.cart.items().map(item => ({
        content_type: item.type === 'service' ? 'service' : 'product',
        object_id: item.item?.id ?? 0,
        name: item.item.name,
        quantity: item.quantity,
        price: item.price,
      })),
      payments: [{
        method: this.cart.paymentMethod(),
        amount: this.cart.total(),
      }],
      cash_register: this.activeRegisterId,
      promotion: this.cart.promoApplied()?.id || null,
      coupon_id: this.cart.couponApplied()?.coupon_id || null,
      redeem_points: this.cart.redeemPoints() || 0,
      cashier_name: this.obtenerUsuarioActual(),
      ncf_type: this.selectedNcfType,
      rnc: this.ncfRnc,
      company_name: this.ncfCompanyName,
    }
    try {
      const venta = await this.api.createSale(payload) as unknown as Record<string, unknown>
      const saleData: SaleData = {
        id: (venta?.id as number) ?? 0,
        client: venta.client as SaleData['client'],
        employee: venta.employee as SaleData['employee'],
        date_time: venta.date_time as string,
        total: Number(venta.total) || 0,
        discount: Number(venta.discount ?? payload.discount),
        paid: Number(venta.paid ?? payload.total),
        payment_method: (venta.payment_method || payload.payment_method) as string,
        status: (venta.status || 'completed') as string,
        details: (venta.details || payload.details) as SaleData['details'],
        payments: venta.payments as SaleData['payments'],
        points_earned: venta.points_earned as number | undefined,
        points_redeemed: venta.points_redeemed as number | undefined,
        ncf: venta.ncf as string | undefined,
        ncf_type: venta.ncf_type as string | undefined,
        rnc: venta.rnc as string | undefined,
        company_name: venta.company_name as string | undefined,
      }
      this.sound.playSuccess()
      this.sound.vibrate([50, 50, 50])
      this.mostrarTicket(saleData, payload)
      this.cart.recordSale(payload.total, payload.payment_method)
      this.cart.clear()
      this.cart.resetPayment()
      this.resetNcfFields()
      this.mostrarDialogoPago = false
      this.messageService.add({ severity: 'success', summary: this.t('pos.alert.sale_processed'), detail: this.t('pos.alert.sale_success') })
    } catch (err: unknown) {
      this.sound.playError()
      this.messageService.add({ severity: 'error', summary: this.t('pos.alert.error_title'), detail: this.getErrorMessage(err) })
    }
  }

  private resetNcfFields() {
    this.selectedNcfType = '02'
    this.ncfRnc = ''
    this.ncfCompanyName = ''
  }

  onNcfTypeChange() {
    if (this.selectedNcfType !== '01') {
      this.ncfRnc = ''
      this.ncfCompanyName = ''
    }
  }

  private getErrorMessage(err: unknown): string {
    const e = err as { error?: { detail?: string; error?: string }; detail?: string } | undefined
    return e?.error?.detail || e?.error?.error || e?.detail || this.t('pos.alert.generic_error')
  }

  // Ticket
  mostrarTicket(venta: SaleData, payload?: Record<string, unknown>) {
    const rawItems = (payload?.details || venta.details || []) as TicketItem[]
    const items: TicketItem[] = rawItems.map(i => ({
      ...i,
      type: i.type || i.content_type || 'product',
      subtotal: i.subtotal ?? (i.quantity ?? 0) * (i.price ?? 0),
    }))
    this.ventaActual = {
      ...venta,
      items,
      cliente: this.cart.client() as Record<string, unknown> | null,
      empleado: this.cart.employee() as Record<string, unknown> | null,
      cajero: venta.cashier_name || this.obtenerUsuarioActual(),
      subtotal: this.cart.subtotal(),
      descuento: this.cart.discountValue(),
      total: this.cart.total(),
      metodoPago: this.cart.paymentMethod() as string,
      coupon_code: venta.coupon_code || this.cart.couponApplied()?.code,
    }
    this.mostrarticket = true
    setTimeout(() => this.autoPrintAfterSale(), 400)
  }

  private async autoPrintAfterSale() {
    const serial = (navigator as { serial?: any }).serial
    if (serial && localStorage.getItem('pos_thermal_connected') === 'true') {
      try {
        const ports = await serial.getPorts()
        if (ports.length > 0) {
          await this.imprimirTermicaConPuerto(ports[0])
          return
        }
      } catch {
        // Fall through to browser print
      }
    }
    await this.imprimirTicketNavegador()
  }

  async reimprimirTicket() {
    await this.autoPrintAfterSale()
  }

  async imprimirTicket() {
    await this.imprimirTicketNavegador()
  }

  async conectarImpresionTermica() {
    const serial = (navigator as { serial?: any }).serial
    if (!serial) {
      this.messageService.add({
        severity: 'warn',
        summary: this.t('pos.alert.error_title'),
        detail: 'Tu navegador no soporta Web Serial API. Usa Chrome desktop.'
      })
      return
    }
    try {
      await this.imprimirTermica(serial)
      localStorage.setItem('pos_thermal_connected', 'true')
    } catch (e) {
      if (!environment.production) console.error('[POS] Thermal Serial error:', e)
      this.messageService.add({
        severity: 'error',
        summary: this.t('pos.alert.error_title'),
        detail: 'No se pudo conectar. Verifica el driver Virtual COM o que la impresora esté encendida.'
      })
    }
  }

  private async imprimirTermicaConPuerto(port: any) {
    try {
      await this._escribirTermica(port)
    } catch {
      await this.imprimirTicketNavegador()
    }
  }

  private buildThermalLines(v: any): string[] {
    const lines: string[] = [
      '\x1B\x40',
      '\x1B\x61\x01',
      `${this.configuracionPos.business_name || this.t('pos.recibo_brand_default')}\n`,
      `${this.t('pos.recibo_venta_sub')}\n`,
      '\x1B\x61\x00',
      '='.repeat(32) + '\n\n',
      `${this.t('pos.recibo_fecha')}: ${new Date().toLocaleString()}\n`,
      `${this.t('pos.recibo_recibo')}: #${this.getTicketId(v.id)}\n`,
      '\n',
    ]
    if (v.cliente) {
      const c = v.cliente as { full_name?: string }
      lines.push(`${this.t('pos.recibo_cliente')}:  ${c.full_name || ''}\n`)
    }
    if (v.empleado) {
      lines.push(`${this.t('pos.recibo_barbero')}:  ${this.getEmpleadoDisplayName(v.empleado)}\n`)
    }
    lines.push(`${this.t('pos.recibo_atendio')}:  ${v.cajero || ''}\n`)
    lines.push(`${this.t('pos.recibo_pago')}:     ${this.getPaymentMethodName(v.metodoPago)}\n`)
    lines.push('-'.repeat(32) + '\n\n')
    const descH = this.t('pos.recibo_desc').toUpperCase()
    const cantH = this.t('pos.recibo_cant').toUpperCase()
    const totalH = this.t('pos.recibo_total').toUpperCase()
    lines.push(`  ${descH.padEnd(18).slice(0, 18)}  ${cantH.padStart(3)}  ${totalH}\n`)
    for (const item of v.items) {
      const name = (item.item?.name || item.name || '').padEnd(18).slice(0, 18)
      const qty = String(item.quantity ?? 1).padStart(3)
      const total = this.formatearMoneda(this.getItemTotal(item))
      lines.push(`  ${name}  ${qty}  ${total}\n`)
    }
    lines.push(`\n${'-'.repeat(32)}\n`)
    lines.push(`\x1B\x61\x01`)
    lines.push(`${this.t('pos.subtotal')}:         ${this.formatearMoneda(v.subtotal)}\n`)
    if (v.descuento > 0) {
      lines.push(`${this.t('pos.discount')}:        -${this.formatearMoneda(v.descuento)}\n`)
    }
    lines.push(`\x1D\x21\x11`)
    lines.push(`${this.t('pos.total')}:            ${this.formatearMoneda(v.total)}\n`)
    lines.push(`\x1D\x21\x00`)
    lines.push(`${this.t('pos.recibo_pago')}:  ${this.getPaymentMethodName(v.metodoPago)}\n\n`)
    lines.push(`\x1B\x61\x00`)
    if (v.ncf) {
      lines.push(`NCF: ${v.ncf}\n`)
      if (v.rnc) lines.push(`RNC: ${v.rnc}\n`)
    }
    if (v.coupon_code) {
      lines.push(`${this.t('pos.coupon')}: ${v.coupon_code}\n`)
    }
    lines.push(`\n${this.t('pos.recibo_gracias')}\n\n`)
    lines.push('\x1D\x56\x00')
    return lines
  }

  private imprimirTicketNavegador(): void {
    const v = this.ventaActual
    if (!v) return

    const w = window.open('', '_blank')
    if (!w) {
      this.messageService.add({ severity: 'warn', summary: this.t('pos.alert.popup_blocked'), detail: this.t('pos.alert.enable_popups') })
      return
    }

    const negocio = this.configuracionPos.business_name || 'BARBERÍA APP'
    const rnc = this.configuracionPos.rnc || ''
    const direccion = this.configuracionPos.address || ''
    const telefono = this.configuracionPos.phone || ''
    const metodoPago = this.getPaymentMethodName(v.metodoPago)
    const reciboId = this.getTicketId(v.id)
    const fecha = this.getCurrentDateTime()

    const itemRows = v.items.map(item => {
      const name = (item.item?.name || item.name || '')
      const qty = item.quantity ?? 1
      const total = this.getItemTotal(item)
      return `<tr><td class="item-name">${this.escapeHtml(name)}</td><td class="item-qty">${qty}</td><td class="item-total">${this.formatearMoneda(total)}</td></tr>`
    }).join('')

    const html = `<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><title>${this.t('pos.recibo_venta_sub')}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #f4f4f5;
    font-family: 'Courier New', 'Lucida Console', monospace;
    padding: 20px;
  }
  .receipt {
    width: 100%;
    max-width: 320px;
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.12);
    padding: 24px 20px;
  }
  .center { text-align: center; }
  .negocio { font-size: 16px; font-weight: 800; margin-bottom: 2px; letter-spacing: 0.3px; color: #111; }
  .info-line { font-size: 10px; color: #52525b; margin-bottom: 1px; }
  .titulo { font-size: 11px; color: #52525b; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 16px; }
  .sep { border: none; border-top: 1px dashed #d4d4d8; margin: 10px 0; }
  .sep-solid { border: none; border-top: 1px solid #a1a1aa; margin: 10px 0; }
  .meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 12px; font-size: 12px; }
  .meta-grid .label { color: #52525b; }
  .meta-grid .value { text-align: right; font-weight: 600; color: #111; }
  .meta-full { grid-column: 1 / -1; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  thead th { text-align: left; padding-bottom: 6px; border-bottom: 1px solid #d4d4d8; color: #52525b; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
  thead th:last-child, thead th:nth-last-child(2) { text-align: right; }
  td { padding: 4px 0; vertical-align: top; }
  .item-name { width: 55%; word-break: break-word; }
  .item-qty { width: 15%; text-align: right; color: #52525b; }
  .item-total { width: 30%; text-align: right; font-weight: 600; }
  .summary { width: 100%; margin-top: 4px; }
  .summary td { padding: 2px 0; }
  .summary td:last-child { text-align: right; }
  .total td { font-size: 14px; font-weight: 800; padding-top: 6px; }
  .total td:last-child { font-size: 18px; }
  .metodo-pago {
    text-align: center;
    margin: 10px 0 0;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #111;
    background: #f4f4f5;
    padding: 6px 12px;
    border-radius: 20px;
    display: inline-block;
  }
  .puntos { text-align: center; font-size: 11px; color: #52525b; margin-top: 8px; }
  .footer { text-align: center; margin-top: 12px; font-size: 11px; color: #52525b; }
  .footer-thanks { font-size: 13px; font-weight: 700; color: #111; margin-bottom: 4px; }
  .actions { display: none; }

  @media print {
    body { background: #fff; padding: 0; min-height: auto; display: block; }
    .receipt { max-width: none; width: 72mm; padding: 2mm 3mm; box-shadow: none; border-radius: 0; font-size: 9px; }
    .negocio { font-size: 13px; }
    .titulo { font-size: 9px; margin-bottom: 8px; }
    .info-line { font-size: 7px; }
    .meta-grid { font-size: 8px; gap: 3px 8px; }
    table { font-size: 8px; }
    thead th { font-size: 7px; padding-bottom: 3px; }
    td { padding: 2px 0; }
    .item-total { font-weight: 600; }
    .total td { font-size: 11px; }
    .total td:last-child { font-size: 14px; }
    .sep { margin: 5px 0; }
    .sep-solid { margin: 5px 0; }
    .metodo-pago { font-size: 8px; padding: 3px 8px; margin: 6px 0 0; }
    .puntos { font-size: 8px; margin-top: 4px; }
    .footer { font-size: 8px; margin-top: 6px; }
    .footer-thanks { font-size: 10px; }
    @page { margin: 0; size: 80mm auto; }
  }
</style></head>
<body>
  <div class="receipt">
    <div class="center">
      <div class="negocio">${this.escapeHtml(negocio)}</div>
      ${rnc ? `<div class="info-line">RNC: ${this.escapeHtml(rnc)}</div>` : ''}
      ${direccion ? `<div class="info-line">${this.escapeHtml(direccion)}</div>` : ''}
      ${telefono ? `<div class="info-line">Tel: ${this.escapeHtml(telefono)}</div>` : ''}
      <div class="titulo">${this.t('pos.recibo_venta_sub')}</div>
    </div>
    <hr class="sep">
    <div class="meta-grid">
      <span class="label">${this.t('pos.recibo_recibo')}</span><span class="value">${this.escapeHtml(reciboId)}</span>
      <span class="label">${this.t('pos.recibo_fecha')}</span><span class="value">${this.escapeHtml(fecha)}</span>
      ${v.cliente ? `<span class="label">${this.t('pos.recibo_cliente')}</span><span class="value">${this.escapeHtml((v.cliente as any).full_name || '')}</span>` : ''}
      ${v.empleado ? `<span class="label">${this.t('pos.recibo_barbero')}</span><span class="value">${this.escapeHtml(this.getEmpleadoDisplayName(v.empleado))}</span>` : ''}
      <span class="label">${this.t('pos.recibo_atendio')}</span><span class="value">${this.escapeHtml(v.cajero || '')}</span>
    </div>
    <hr class="sep">
    <table>
      <thead><tr><th>${this.t('pos.recibo_desc')}</th><th>${this.t('pos.recibo_cant')}</th><th>${this.t('pos.recibo_total')}</th></tr></thead>
      <tbody>${itemRows}</tbody>
    </table>
    <hr class="sep">
    <table class="summary">
      <tr><td>${this.t('pos.recibo_subtotal')}</td><td>${this.formatearMoneda(v.subtotal)}</td></tr>
      ${v.descuento > 0 ? `<tr><td>${this.t('pos.recibo_descuento')}${v.coupon_code ? ` (${v.coupon_code})` : ''}</td><td>-${this.formatearMoneda(v.descuento)}</td></tr>` : ''}
      ${v.points_redeemed ? `<tr><td>${this.t('pos.recibo_puntos')}</td><td>-${this.formatearMoneda(v.points_redeemed / 10)}</td></tr>` : ''}
    </table>
    <hr class="sep-solid">
    <table class="summary total">
      <tr><td>${this.t('pos.recibo_total_label')}</td><td>${this.formatearMoneda(v.total)}</td></tr>
      ${v.ncf ? `<tr><td>${this.t('pos.ncf')}:</td><td>${this.escapeHtml(v.ncf)}</td></tr>` : ''}
      ${v.ncf_type ? `<tr><td>${this.t('pos.ncf_type')}:</td><td>${this.escapeHtml(v.ncf_type)}</td></tr>` : ''}
      ${v.rnc ? `<tr><td>${this.t('pos.ncf_rnc')}:</td><td>${this.escapeHtml(v.rnc)}</td></tr>` : ''}
      ${v.company_name ? `<tr><td>${this.t('pos.ncf_company_name')}:</td><td>${this.escapeHtml(v.company_name)}</td></tr>` : ''}
      ${v.points_earned ? `<tr><td>${this.t('pos.recibo_gano_puntos').replace('{points}', v.points_earned.toString())}</td><td>+${this.formatearMoneda(v.points_earned / 10)}</td></tr>` : ''}
    </table>
    <div class="center"><span class="metodo-pago">${this.escapeHtml(metodoPago)}</span></div>
    ${v.points_earned ? `<div class="puntos">⭐ ${this.t('pos.recibo_gano_puntos').replace('{points}', v.points_earned.toString())}</div>` : ''}
    <hr class="sep">
    <div class="footer">
      <div class="footer-thanks">${this.t('pos.recibo_gracias')}</div>
      ${this.configuracionPos.receipt_footer ? `<div>${this.escapeHtml(this.configuracionPos.receipt_footer)}</div>` : ''}
    </div>
  </div>
</body></html>`

    w.document.write(html)
    w.document.close()
    w.focus()
    setTimeout(() => w.print(), 500)
  }

  private escapeHtml(text: string): string {
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
  }

  private encodeCP437(text: string): Uint8Array {
    const cp437Map: Record<string, number> = {
      'á': 0xA0, 'é': 0x82, 'í': 0xA1, 'ó': 0xA2, 'ú': 0xA3,
      'ñ': 0xA4, 'ü': 0x81, 'Á': 0xB5, 'É': 0x90, 'Í': 0xD6,
      'Ó': 0xE0, 'Ú': 0xE9, 'Ñ': 0xA5, 'Ü': 0x9A, '¿': 0xA8,
      '¡': 0xAD, '€': 0x80,
    }
    const bytes: number[] = []
    for (const ch of text) {
      const code = ch.charCodeAt(0)
      if (code < 128) {
        bytes.push(code)
      } else if (cp437Map[ch]) {
        bytes.push(cp437Map[ch])
      } else if (code >= 0xC0 && code <= 0xFF) {
        bytes.push(code - 0x40) // approximate fallback for accented uppercase
      } else {
        bytes.push(0x20) // replace unknown with space
      }
    }
    return new Uint8Array(bytes)
  }

  async imprimirTermica(serial: { requestPort: () => Promise<unknown> }) {
    const port = await serial.requestPort() as { open: (opts: Record<string, unknown>) => Promise<void>; writable: { getWriter: () => { write: (data: Uint8Array) => Promise<void>; releaseLock: () => void } }; close: () => Promise<void> }
    await this._escribirTermica(port)
  }

  private async _escribirTermica(port: any) {
    await port.open({ baudRate: 9600 })
    const writer = port.writable.getWriter()
    const v = this.ventaActual
    if (!v) return
    const lines = this.buildThermalLines(v)
    await writer.write(this.encodeCP437(lines.join('')))
    writer.releaseLock()
    await port.close()
  }

  cerrarTicket() {
    this.mostrarticket = false
    this.ventaActual = null
  }

  getPaymentMethodName(method: string): string {
    const key = `pos.payment_method.${method}`
    const translated = this.t(key)
    return translated !== key ? translated : method
  }

  formatearMoneda(valor: number | string | null | undefined): string {
    const num = Number(valor) || 0
    const currency = this.barbershopSettings.settings()?.currency || 'DOP'
    return new Intl.NumberFormat('es-DO', { style: 'currency', currency, minimumFractionDigits: 2 }).format(num)
  }

  getItemTotal(item: TicketItem): number {
    return item.subtotal ?? (item.quantity ?? 0) * (item.price ?? 0)
  }

  getEmpleadoDisplayName(empleado: Record<string, unknown> | null): string {
    const e = empleado as { displayName?: string; user?: { full_name?: string } } | null
    return e?.displayName || e?.user?.full_name || ''
  }

  getTicketId(id: number | undefined): string {
    return id != null ? id.toString().padStart(6, '0') : '000000'
  }

  getCurrentDateTime(): string {
    const now = new Date()
    now.setSeconds(0, 0)
    const locale = this.localeService.getCurrentAppLocale() || 'es-DO'
    return now.toLocaleString(locale, {
      weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  }

  // History
  async cargarHistorialVentas() {
    this.cargandoHistorial = true
    try {
      const branchId = this.selectedBranch()?.id
      const params = branchId ? { branch_id: String(branchId) } : {}
      const resp = await this.api.getSales(params)
      const ventas = resp?.results || resp || []
      this.historialVentas = (ventas as SaleData[])
        .filter(v => v.date_time)
        .sort((a, b) => new Date(b.date_time).getTime() - new Date(a.date_time).getTime())
        .slice(0, 20)
    } catch {
      this.historialVentas = []
    } finally {
      this.cargandoHistorial = false
    }
  }

  visualizarVenta(venta: SaleData) {
    this.ventaActual = {
      ...venta,
      items: venta.details?.map(d => ({
        item: { name: d.name },
        type: d.content_type,
        content_type: d.content_type,
        quantity: d.quantity,
        price: d.price,
        subtotal: d.quantity * d.price,
      })) || [],
      cliente: venta.client,
      empleado: (venta.employee ?? null) as Record<string, unknown> | null,
      cajero: venta.cashier_name || this.obtenerUsuarioActual(),
      subtotal: venta.total + (venta.discount || 0),
      descuento: venta.discount || 0,
      total: venta.total,
      metodoPago: venta.payment_method,
    }
    this.mostrarticket = true
  }

  // Old reembolsarVenta replaced by abrirReembolso/confirmarReembolso

  async reimprimirRecibo(ventaId: number) {
    try {
      await this.api.printReceipt(ventaId)
      this.messageService.add({ severity: 'success', summary: this.t('pos.alert.receipt'), detail: this.t('pos.alert.receipt_generated') })
    } catch {
      this.messageService.add({ severity: 'error', summary: this.t('pos.alert.error_title'), detail: this.t('pos.alert.receipt_generation_error') })
    }
  }

  // Promotions
  async aplicarPromocion(promo: Promotion) {
    try {
      const result = await this.api.applyPromotion(promo.id, this.cart.subtotal())
      const discount = Number(result?.discount) || 0
      this.cart.applyPromotion({ ...promo, validatedDiscount: discount })
      this.mostrarDialogoPromociones = false
      this.messageService.add({ severity: 'success', summary: this.t('pos.alert.promotion_applied'), detail: promo.name })
    } catch {
      this.messageService.add({ severity: 'error', summary: this.t('pos.alert.error_title'), detail: this.t('pos.alert.promotion_error') })
    }
  }

  // Coupons
  async aplicarCupon() {
    if (!this.couponCode.trim()) return
    this.aplicandoCupon = true
    try {
      const result = await this.api.validateCoupon(this.couponCode, this.cart.subtotal())
      this.cart.applyCoupon(result)
      this.couponCode = ''
      this.messageService.add({
        severity: 'success',
        summary: this.t('pos.alert.coupon_applied' as any) || 'Cupón aplicado',
        detail: result.code
      })
    } catch (err) {
      this.messageService.add({
        severity: 'error',
        summary: this.t('pos.alert.error_title'),
        detail: this.getErrorMessage(err)
      })
    } finally {
      this.aplicandoCupon = false
    }
  }

  removerCupon() {
    this.cart.couponApplied.set(null)
    this.cart.discount.set(0)
    this.messageService.add({
      severity: 'info',
      summary: 'Cupón removido',
      detail: 'El descuento ha sido cancelado'
    })
  }

  // Barcode
  async buscarPorCodigoBarras() {
    if (!this.codigoBarras.trim()) return
    try {
      const producto = await this.api.searchByBarcode(this.codigoBarras)
      if (producto) {
        this.tipoActivo = 'products'
        this.agregarAlCarrito(producto)
        this.sound.playScan()
        this.codigoBarras = ''
      }
    } catch {
      this.messageService.add({ severity: 'error', summary: this.t('pos.alert.not_found'), detail: this.t('pos.alert.invalid_barcode') })
      this.codigoBarras = ''
    }
  }

  // Camera scanner
  async activarCamara() {
    this.mostarCamara.set(true)
    try {
      const reader = new BrowserMultiFormatReader()
      const video = this.scannerVideoRef?.nativeElement
      if (!video) return
      this.scannerControls = await reader.decodeFromVideoDevice(undefined, video, (res) => {
        if (res) {
          this.codigoBarras = res.getText()
          this.detenerCamara()
          this.buscarPorCodigoBarras()
        }
      })
    } catch {
      this.messageService.add({ severity: 'error', summary: this.t('pos.alert.error_title'), detail: this.t('pos.alert.camera_error') })
      this.mostarCamara.set(false)
    }
  }

  detenerCamara() {
    if (this.scannerControls) {
      this.scannerControls.stop()
      this.scannerControls = null
    }
    this.mostarCamara.set(false)
  }

  async abrirCamara() {
    this.modoScanner = true
    setTimeout(() => this.activarCamara(), 100)
  }

  // Signature
  iniciarFirma(event: MouseEvent) {
    this.firmando = true
    const canvas = this.firmaCanvas.nativeElement
    const rect = canvas.getBoundingClientRect()
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.beginPath()
    ctx.moveTo(event.clientX - rect.left, event.clientY - rect.top)
  }

  dibujarFirma(event: MouseEvent) {
    if (!this.firmando) return
    const canvas = this.firmaCanvas.nativeElement
    const rect = canvas.getBoundingClientRect()
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.lineTo(event.clientX - rect.left, event.clientY - rect.top)
    ctx.stroke()
  }

  iniciarFirmaTouch(event: TouchEvent) {
    if (event.touches.length === 0) return
    event.preventDefault()
    this.firmando = true
    const touch = event.touches[0]
    const canvas = this.firmaCanvas.nativeElement
    const rect = canvas.getBoundingClientRect()
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.beginPath()
    ctx.moveTo(touch.clientX - rect.left, touch.clientY - rect.top)
  }

  dibujarFirmaTouch(event: TouchEvent) {
    if (!this.firmando || event.touches.length === 0) return
    event.preventDefault()
    const touch = event.touches[0]
    const canvas = this.firmaCanvas.nativeElement
    const rect = canvas.getBoundingClientRect()
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.lineTo(touch.clientX - rect.left, touch.clientY - rect.top)
    ctx.stroke()
  }

  terminarFirma() { this.firmando = false }

  limpiarFirma() {
    const canvas = this.firmaCanvas.nativeElement
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.clearRect(0, 0, canvas.width, canvas.height)
  }

  confirmarFirma() {
    const canvas = this.firmaCanvas.nativeElement
    this.firmaCliente = canvas.toDataURL()
    this.mostrarDialogoFirma = false
    this.confirmarVenta()
  }

  // Cash count
  realizarArqueoCaja() {
    const total = this.cart.countTotal()
    if (total === 0) {
      this.messageService.add({ severity: 'warn', summary: this.t('pos.alert.warning'), detail: this.t('pos.alert.must_count_denomination') })
      return
    }
    const diff = this.cart.countDifference()
    this.cart.resetCount()
    this.mostrarDialogoArqueo = false
    this.messageService.add({
      severity: diff === 0 ? 'success' : 'warn',
      summary: this.t('pos.alert.arqueo_completado'),
      detail: this.t('pos.alert.arqueo_detail')
        .replace('{total}', total.toFixed(2))
        .replace('{diff}', diff.toFixed(2)),
    })
  }

  // Dashboard
  private cssColor(variableName: string, fallback: string): string {
    if (typeof window === 'undefined') {
      return fallback
    }
    return getComputedStyle(document.documentElement).getPropertyValue(variableName).trim() || fallback
  }

  async abrirDashboard() {
    this.mostrarDashboard = true
    if (this.dashboardData) return
    this.dashboardLoading = true
    try {
      const data = await this.api.getDashboardStats()
      this.dashboardData = data
      const brand = this.cssColor('--brand', '#1A56DB')
      const brand400 = this.cssColor('--brand-400', '#527BFF')

      // Daily revenue chart
      const days: { day: string; revenue: number }[] = data.daily_revenue || []
      this.chartRevenue = {
        labels: days.map(d => d.day),
        datasets: [{
          label: 'Ingresos',
          data: days.map(d => Number(d.revenue)),
          borderColor: brand400,
          backgroundColor: 'rgba(59, 130, 246, 0.12)',
          pointBackgroundColor: brand400,
          pointBorderColor: '#fff',
          pointRadius: 3,
          fill: true,
          tension: 0.4,
        }]
      }

      // Payment breakdown chart
      const methods: { payment_method: string; total: number }[] = data.payment_breakdown || []
      const palette = [brand400, '#10B981', '#F59E0B', brand, '#EC4899', '#06B6D4']
      this.chartPayment = {
        labels: methods.map(m => this.getPaymentMethodName(m.payment_method) || 'Otro'),
        datasets: [{
          data: methods.map(m => Number(m.total)),
          backgroundColor: palette.slice(0, methods.length),
          borderColor: '#ffffff',
          borderWidth: 2,
        }]
      }

      // Monthly revenue chart
      const months: { month: string; revenue: number }[] = data.monthly_revenue || []
      this.chartMonthly = {
        labels: months.map(m => m.month),
        datasets: [{
          label: 'Ingresos mensuales',
          data: months.map(m => Number(m.revenue)),
          borderColor: '#10B981',
          backgroundColor: 'rgba(16, 185, 129, 0.12)',
          pointBackgroundColor: '#10B981',
          pointBorderColor: '#fff',
          pointRadius: 3,
          fill: true,
          tension: 0.3,
        }]
      }

      this.chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: '#64748B' },
          },
          y: {
            beginAtZero: true,
            grid: { color: 'rgba(148, 163, 184, 0.2)' },
            ticks: { color: '#64748B' },
          },
        }
      }
    } catch {
      this.dashboardData = {
        today: { ventas: 0, ingresos: 0, ticketPromedio: 0 },
        by_type: { services: 0, products: 0 },
        top_products: [],
        top_services: [],
        weekly_revenue: [],
        payment_methods: [],
        monthly_revenue: [],
      }
    } finally {
      this.dashboardLoading = false
    }
  }

  // Tarjeta (Stripe / CardNET según el proveedor del tenant)
  cardnetFlow = false

  async iniciarPagoTarjeta() {
    const pk = environment.stripePublishableKey
    this.cardnetFlow = !pk
    if (!this.cardnetFlow) {
      this.stripe = await loadStripe(pk)
      if (!this.stripe) {
        this.messageService.add({ severity: 'error', summary: this.t('pos.alert.error_title'), detail: this.t('pos.alert.stripe_load_error') })
        return
      }
      const elements = this.stripe.elements({ mode: 'payment', currency: 'dop', amount: Math.round(this.cart.total() * 100) })
      const card = elements.create('card', { style: { base: { fontSize: '16px', color: '#32325d' } } })
      this.stripeElements = elements
      this.stripeCard = card
      this.stripeError = ''
      this.mostrarDialogoTarjeta = true
      this.mountStripeCard(card)
    } else {
      // CardNET (RD): procesa directo sin formulario Stripe
      this.mostrarDialogoTarjeta = true
      this.stripeError = ''
      await this.procesarPagoTarjeta()
    }
  }

  private mountStripeCard(card: StripeCardElement) {
    const el = document.getElementById('stripe-card-element')
    if (el) {
      card.mount(el)
      return
    }
    const observer = new MutationObserver(() => {
      const target = document.getElementById('stripe-card-element')
      if (target) {
        card.mount(target)
        observer.disconnect()
      }
    })
    observer.observe(document.body, { childList: true, subtree: true })
  }

  async procesarPagoTarjeta() {
    if (!this.cardnetFlow && (!this.stripe || !this.stripeCard || !this.stripeElements)) return
    this.stripeLoading = true
    this.stripeError = ''
    try {
      const result = await this.api.chargeCard(this.cart.total())
      if (result.client_secret && !this.cardnetFlow) {
        // Stripe: confirmar el PaymentIntent con los datos de la tarjeta
        const { error } = await this.stripe!.confirmCardPayment(result.client_secret, {
          payment_method: { card: this.stripeCard! },
        })
        if (error) {
          this.stripeError = error.message || 'Error al procesar el pago'
          this.stripeLoading = false
          return
        }
        this.stripeCard!.clear()
      }
      if (!result.success) {
        this.stripeError = result.error || 'Error al procesar el pago'
        this.stripeLoading = false
        return
      }
      this.mostrarDialogoTarjeta = false
      await this.confirmarVenta()
      this.stripeLoading = false
    } catch {
      this.stripeError = 'Error al procesar el pago'
      this.stripeLoading = false
    }
  }

  // Reembolso guiado
  abrirReembolso(venta: SaleData) {
    this.ventaAReembolsar = venta
    this.motivoReembolso = ''
    this.mostrarDialogoReembolso = true
  }

  async confirmarReembolso() {
    if (!this.motivoReembolso || this.motivoReembolso.length < 10) {
      this.messageService.add({ severity: 'error', summary: this.t('pos.alert.error_title'), detail: this.t('pos.alert.refund_reason_min_length') })
      return
    }
    if (!this.ventaAReembolsar) return
    this.reembolsando = true
    try {
      await this.api.refundSale(this.ventaAReembolsar.id, { reason: this.motivoReembolso })
      this.messageService.add({ severity: 'success', summary: this.t('pos.alert.refunded'), detail: this.t('pos.alert.refund_success') })
      this.mostrarDialogoReembolso = false
      this.cargarHistorialVentas()
    } catch (err: unknown) {
      this.messageService.add({ severity: 'error', summary: this.t('pos.alert.error_title'), detail: this.getErrorMessage(err) })
    } finally {
      this.reembolsando = false
    }
  }

  // Keyboard shortcuts
  @HostListener('document:keydown', ['$event'])
  handleKeyboard(event: KeyboardEvent) {
    if (event.altKey || event.ctrlKey) {
      switch (event.key.toLowerCase()) {
        case 'n': event.preventDefault(); this.cart.clear(); break
        case 'p': event.preventDefault(); this.procesarVenta(); break
        case 'b': event.preventDefault(); this.modoScanner = !this.modoScanner; break
      }
    }
  }

  // Report PDF
  generarPDFCuadre(data: CashCloseData) {
    const html = `
      <div style="font-family:Arial,sans-serif;padding:20px;max-width:600px;">
        <div style="text-align:center;border-bottom:2px solid #333;padding-bottom:10px;margin-bottom:20px;">
          <h1 style="color:#333;margin:0;">${this.t('pos.recibo_brand_default')}</h1>
          <h2 style="color:#666;margin:5px 0;">${this.t('pos.pdf.cuadre_title')}</h2>
        </div>
        <div style="margin-bottom:20px;">
          <p><strong>${this.t('pos.recibo_fecha')}:</strong> ${data.fecha}</p>
          <p><strong>${this.t('pos.hora')}:</strong> ${data.hora}</p>
        </div>
        <div style="border:1px solid #ddd;padding:15px;margin-bottom:20px;background:#f9f9f9;">
          <h3 style="color:#333;margin-top:0;">${this.t('pos.pdf.movements')}</h3>
          <table style="width:100%;border-collapse:collapse;">
            <tr><td style="padding:5px 0;border-bottom:1px solid #eee;"><strong>${this.t('pos.pdf.monto_inicial')}</strong></td><td style="text-align:right;">$${data.montoInicial.toFixed(2)}</td></tr>
            <tr><td style="padding:5px 0;border-bottom:1px solid #eee;"><strong>${this.t('pos.pdf.ventas_efectivo')}</strong></td><td style="text-align:right;">$${data.ventasEfectivo.toFixed(2)}</td></tr>
            <tr><td style="padding:5px 0;border-bottom:1px solid #eee;"><strong>${this.t('pos.pdf.monto_esperado')}</strong></td><td style="text-align:right;">$${data.montoEsperado.toFixed(2)}</td></tr>
            <tr><td style="padding:5px 0;border-bottom:1px solid #eee;"><strong>${this.t('pos.pdf.monto_contado')}</strong></td><td style="text-align:right;">$${data.montoContado.toFixed(2)}</td></tr>
            <tr style="background:${data.diferencia === 0 ? '#d4edda' : '#f8d7da'};">
              <td style="padding:8px 0;font-weight:bold;"><strong>${this.t('pos.pdf.diferencia')}</strong></td>
              <td style="text-align:right;font-weight:bold;color:${data.diferencia === 0 ? '#155724' : '#721c24'};">$${data.diferencia.toFixed(2)}</td>
            </tr>
          </table>
        </div>
        <div style="text-align:center;margin-top:30px;padding-top:20px;border-top:1px solid #ddd;color:#666;font-size:12px;">
          <p>${this.t('pos.pdf.generated_auto')}</p>
        </div>
      </div>`
    const w = window.open('', '_blank')
    if (!w) {
      this.messageService.add({ severity: 'warn', summary: this.t('pos.alert.canceled'), detail: this.t('pos.alert.popup_blocked') })
      return
    }
    w.document.write(`<html><head><title>${this.t('pos.pdf.page_title')}</title><style>@media print{body{margin:0}@page{margin:1cm}}</style></head><body>${html}<script>window.onload=function(){window.print();setTimeout(()=>window.close(),1000)}<\/script></body></html>`)
    w.document.close()
  }

  obtenerUsuarioActual(): string {
    const user = this.authService.getCurrentUser()
    return user?.full_name || user?.email || this.t('pos.system_user')
  }

  esClienteFrecuente(cliente: Record<string, unknown>) {
    return this.repo.isFrequentClient(cliente)
  }

  getCatalogItemQuantity(item: CatalogItem) {
    const type = this.tipoActivo === 'services' ? 'service' : 'product'
    return this.cart.items().find(ci => ci.item.id === item.id && ci.type === type)?.quantity || 0
  }

  aplicarDescuentoClienteFrecuente() {
    if (this.cart.client() && this.esClienteFrecuente(this.cart.client())) {
      const desc = this.cart.subtotal() * 0.1
      this.cart.discount.set(Math.max(this.cart.discount(), desc))
      this.messageService.add({ severity: 'success', summary: this.t('pos.alert.vip_discount'), detail: this.t('pos.alert.vip_discount_detail').replace('{amount}', this.formatearMoneda(desc)) })
    }
  }

  trackByDenominacion(_: number, item: Denomination) { return item.valor }
}
