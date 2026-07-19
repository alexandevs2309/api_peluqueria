import { TestBed } from '@angular/core/testing'
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing'
import { PayrollService } from './payroll.service'

describe('PayrollService', () => {
  let service: PayrollService
  let httpMock: HttpTestingController

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [PayrollService],
    })
    service = TestBed.inject(PayrollService)
    httpMock = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    httpMock.verify()
  })

  it('fetches periods', () => {
    service.getPeriods().subscribe(res => {
      expect(res.periods.length).toBe(2)
    })
    const req = httpMock.expectOne(r => r.url.includes('/employees/payroll/client/payroll/'))
    expect(req.request.method).toBe('GET')
    req.flush({ periods: [{ id: 1 }, { id: 2 }] })
  })

  it('registers payment with token refresh', () => {
    const payment = { period_id: 1, amount: 500, payment_method: 'cash' as const }
    service.registerPayment(payment).subscribe()

    const refreshReq = httpMock.expectOne(r => r.url.includes('/auth/cookie-refresh/'))
    expect(refreshReq.request.method).toBe('POST')
    refreshReq.flush({})

    const paymentReq = httpMock.expectOne(r => r.url.includes('/register_payment/'))
    expect(paymentReq.request.method).toBe('POST')
    expect(paymentReq.request.body).toEqual(payment)
    paymentReq.flush({ success: true })
  })

  it('registers payment even when refresh fails', () => {
    const payment = { period_id: 2, amount: 750, payment_method: 'cash' as const }
    service.registerPayment(payment).subscribe()

    const refreshReq = httpMock.expectOne(r => r.url.includes('/auth/cookie-refresh/'))
    refreshReq.error(new ErrorEvent('Network error'))

    const paymentReq = httpMock.expectOne(r => r.url.includes('/register_payment/'))
    expect(paymentReq.request.method).toBe('POST')
    paymentReq.flush({ success: true })
  })

  it('submits period for approval', () => {
    service.submitForApproval(1).subscribe()
    const req = httpMock.expectOne(r => r.url.includes('/1/submit/'))
    expect(req.request.method).toBe('POST')
    req.flush({})
  })

  it('approves period', () => {
    service.approvePeriod(1).subscribe()
    const req = httpMock.expectOne(r => r.url.includes('/1/approve/'))
    expect(req.request.method).toBe('POST')
    req.flush({})
  })

  it('rejects period with reason', () => {
    service.rejectPeriod(1, 'Monto incorrecto').subscribe()
    const req = httpMock.expectOne(r => r.url.includes('/1/reject/'))
    expect(req.request.method).toBe('POST')
    expect(req.request.body.reason).toBe('Monto incorrecto')
    req.flush({})
  })

  it('gets payment receipt', () => {
    service.getPaymentReceipt('pay_123').subscribe()
    const req = httpMock.expectOne(r => r.url.includes('/payments/pay_123/receipt/'))
    expect(req.request.method).toBe('GET')
    req.flush({ id: 'pay_123' })
  })
})
