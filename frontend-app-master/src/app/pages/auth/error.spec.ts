import { TestBed } from '@angular/core/testing'
import { Error } from './error'
import { ActivatedRoute, Router } from '@angular/router'
import { AuthService } from '../../core/services/auth/auth.service'
import { AppConfigService } from '../../core/services/app-config.service'
import { LocaleService } from '../../core/services/locale/locale.service'

describe('Error', () => {
  let component: Error
  let routerMock: any
  let authServiceMock: any
  let appConfigMock: any
  let localeServiceMock: any

  const setupTest = (queryParams: any) => {
    routerMock = {
      navigate: jasmine.createSpy('navigate')
    }
    authServiceMock = {
      getCurrentUser: jasmine.createSpy('getCurrentUser').and.returnValue(null)
    }
    appConfigMock = {
      supportEmail: jasmine.createSpy('supportEmail').and.returnValue('soporte@auronsuite.com')
    }
    localeServiceMock = {
      t: jasmine.createSpy('t').and.callFake((key: string) => key)
    }

    TestBed.configureTestingModule({
      providers: [
        Error,
        { provide: Router, useValue: routerMock },
        { provide: AuthService, useValue: authServiceMock },
        { provide: AppConfigService, useValue: appConfigMock },
        { provide: LocaleService, useValue: localeServiceMock },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { queryParams }
          }
        }
      ]
    })

    return TestBed.inject(Error)
  }

  it('uses default message when no query param', () => {
    component = setupTest({})
    expect(component['message']).toBe('auth.error.default_message')
  })

  it('uses custom message from query param', () => {
    component = setupTest({ message: 'Custom error' })
    expect(component['message']).toBe('Custom error')
  })
})

