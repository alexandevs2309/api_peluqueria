import { TestBed } from '@angular/core/testing'
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing'
import { AppointmentService } from './appointment.service'
import { NotificationService } from '../notification/notification.service'
import { API_CONFIG } from '../../config/api.config'

describe('AppointmentService', () => {
  let service: AppointmentService
  let httpMock: HttpTestingController

  beforeEach(() => {
    const notificationSpy = jasmine.createSpyObj('NotificationService', ['refresh'])
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        AppointmentService,
        { provide: NotificationService, useValue: notificationSpy },
      ],
    })
    service = TestBed.inject(AppointmentService)
    httpMock = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    httpMock.verify()
  })

  it('fetches appointments', () => {
    service.getAppointments({ page: 1 }).subscribe()
    const req = httpMock.expectOne(r => r.url.includes(API_CONFIG.ENDPOINTS.APPOINTMENTS.BASE))
    expect(req.request.method).toBe('GET')
    req.flush({ results: [] })
  })

  it('fetches single appointment', () => {
    service.getAppointment(1).subscribe()
    const req = httpMock.expectOne(r => r.url.includes('/1/'))
    expect(req.request.method).toBe('GET')
    req.flush({ id: 1 })
  })

  it('creates appointment', () => {
    const data = { client: 1, stylist: 1, date_time: '2026-06-01T10:00:00Z' }
    service.createAppointment(data).subscribe()
    const req = httpMock.expectOne(r => r.url.includes(API_CONFIG.ENDPOINTS.APPOINTMENTS.BASE))
    expect(req.request.method).toBe('POST')
    expect(req.request.body).toEqual(data)
    req.flush({ id: 1, ...data })
  })

  it('updates appointment', () => {
    service.updateAppointment(1, { status: 'completed' }).subscribe()
    const req = httpMock.expectOne(r => r.url.includes('/1/'))
    expect(req.request.method).toBe('PUT')
    req.flush({ id: 1 })
  })

  it('deletes appointment', () => {
    service.deleteAppointment(1).subscribe()
    const req = httpMock.expectOne(r => r.url.includes('/1/'))
    expect(req.request.method).toBe('DELETE')
    req.flush({})
  })

  it('confirms appointment', () => {
    service.confirmAppointment(1).subscribe()
    const req = httpMock.expectOne(r => r.url.includes('/1/confirm/'))
    expect(req.request.method).toBe('POST')
    req.flush({})
  })

  it('cancels appointment', () => {
    service.cancelAppointment(1, 'Cliente no disponible').subscribe()
    const req = httpMock.expectOne(r => r.url.includes('/1/cancel/'))
    expect(req.request.method).toBe('POST')
    expect(req.request.body.reason).toBe('Cliente no disponible')
    req.flush({})
  })

  it('completes appointment', () => {
    service.completeAppointment(1).subscribe()
    const req = httpMock.expectOne(r => r.url.includes('/1/complete/'))
    expect(req.request.method).toBe('POST')
    req.flush({})
  })

  it('reschedules appointment', () => {
    service.rescheduleAppointment(1, '2026-06-02T14:00:00Z').subscribe()
    const req = httpMock.expectOne(r => r.url.includes('/1/reschedule/'))
    expect(req.request.method).toBe('POST')
    expect(req.request.body.new_date_time).toBe('2026-06-02T14:00:00Z')
    req.flush({})
  })

  it('checks availability', () => {
    service.checkAvailability(1, '2026-06-01', 60).subscribe()
    const req = httpMock.expectOne(r => r.url.includes('check_availability'))
    expect(req.request.method).toBe('GET')
    expect(req.request.params.get('stylist_id')).toBe('1')
    req.flush({ available: true })
  })

  it('gets available slots', () => {
    service.getAvailableSlots(1, '2026-06-01').subscribe()
    const req = httpMock.expectOne(r => r.url.includes('available_slots'))
    expect(req.request.method).toBe('GET')
    req.flush(['10:00', '11:00'])
  })

  it('gets today appointments', () => {
    service.getTodayAppointments().subscribe()
    const req = httpMock.expectOne(r => r.url.includes('today'))
    expect(req.request.method).toBe('GET')
    req.flush([])
  })
})
