import { TestBed } from '@angular/core/testing'
import { HelpComponent } from './help.component'
import { Router } from '@angular/router'
import { BarbershopSettingsService } from '../../../shared/services/barbershop-settings.service'
import { AppConfigService } from '../../../core/services/app-config.service'
import { LocaleService } from '../../../core/services/locale/locale.service'

describe('HelpComponent', () => {
  let component: HelpComponent
  let routerMock: any
  let barbershopSettingsMock: any
  let appConfigMock: any
  let localeServiceMock: any

  beforeEach(() => {
    routerMock = {
      navigate: jasmine.createSpy('navigate')
    }
    barbershopSettingsMock = {
      settings: () => null
    }
    appConfigMock = {
      supportEmail: () => 'soporte@auronsuite.com'
    }
    localeServiceMock = {
      t: (key: string) => {
        if (key === 'help.faq1.title') return '¿Cómo configurar mi barbería?'
        if (key === 'help.faq1.content') return 'Puedes cambiar tu contraseña en el perfil.'
        return key
      }
    }

    TestBed.configureTestingModule({
      providers: [
        HelpComponent,
        { provide: Router, useValue: routerMock },
        { provide: BarbershopSettingsService, useValue: barbershopSettingsMock },
        { provide: AppConfigService, useValue: appConfigMock },
        { provide: LocaleService, useValue: localeServiceMock }
      ]
    })

    component = TestBed.inject(HelpComponent)
  })


  it('starts with empty search', () => {
    expect(component.searchTerm).toBe('')
  })

  it('returns all faqs when search is empty', () => {
    const result = component.filteredFaqs()
    expect(result.length).toBe(component['faqs'].length)
  })

  it('filters faqs by title', () => {
    component.searchTerm = 'barbería'
    const result = component.filteredFaqs()
    expect(result.length).toBe(1)
    expect(result[0].title).toContain('barbería')
  })

  it('filters faqs by content', () => {
    component.searchTerm = 'contraseña'
    const result = component.filteredFaqs()
    expect(result.length).toBeGreaterThan(0)
    expect(result.some(f => f.content.toLowerCase().includes('contraseña'))).toBeTrue()
  })

  it('returns empty when no match', () => {
    component.searchTerm = 'zzzznotfound'
    const result = component.filteredFaqs()
    expect(result.length).toBe(0)
  })

  it('is case insensitive', () => {
    component.searchTerm = 'CONTRASEÑA'
    const result = component.filteredFaqs()
    expect(result.length).toBeGreaterThan(0)
  })

  it('returns default support email when settings empty', () => {
    const email = component.supportEmail()
    expect(email).toContain('@')
  })
})
