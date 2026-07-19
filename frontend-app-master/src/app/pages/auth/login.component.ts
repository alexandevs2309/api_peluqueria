import { Component, OnInit, OnDestroy, inject, computed } from '@angular/core';
import { FormBuilder, FormGroup, FormControl, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { ButtonModule } from 'primeng/button';
import { CheckboxModule } from 'primeng/checkbox';
import { PasswordModule } from 'primeng/password';
import { InputTextModule } from 'primeng/inputtext';
import { InputOtpModule } from 'primeng/inputotp';
import { DialogModule } from 'primeng/dialog';
import { MessageService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';
import { RippleModule } from 'primeng/ripple';
import { AuBtn } from '../../shared/components';
import { AuthService, LoginResponse, MFALoginVerifyRequest } from '../../core/services/auth/auth.service';
import { AppConfigService } from '../../core/services/app-config.service';
import { LocaleService } from '../../core/services/locale/locale.service';
import { roleKey } from '../../core/utils/role-normalizer';
import { getHttpErrorMessage } from '../../core/utils/http-error-message';
import { LayoutService } from '../../layout/service/layout.service';
import { safeGetItem, safeSetItem, safeRemoveItem } from '../../core/utils/storage';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    ButtonModule,
    CheckboxModule,
    PasswordModule,
    InputTextModule,
    InputOtpModule,
    DialogModule,
    ReactiveFormsModule,
    ToastModule,
    RippleModule,
    RouterModule,
    AuBtn
  ],
  providers: [MessageService],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class Login implements OnInit, OnDestroy {
  loginForm!: FormGroup;
  mfaCode = new FormControl('', [Validators.required, Validators.pattern(/^\d{6}$/)]);
  isLoading = false;
  requiresMfa = false;
  pendingMfaEmail: string | null = null;
  pendingMfaTenantSubdomain: string | null = null;
  private tenantStorageKey = 'tenant_subdomain';

  readonly slides = [
    {
      eyebrow:  'PLATAFORMA DE GESTIÓN · LATINOAMÉRICA',
      headline: 'Tu negocio, bajo control.',
      sub:      'Agenda, cobros, comisiones e inventario en un solo lugar.',
    },
    {
      eyebrow:  'AGENDA INTELIGENTE',
      headline: 'Sin llamadas. Sin papel.',
      sub:      'Tus clientes reservan solos, tú solo apareces a trabajar.',
    },
    {
      eyebrow:  'PUNTO DE VENTA',
      headline: 'Cobra en segundos.',
      sub:      'Efectivo, tarjeta o transferencia. Con comprobante fiscal incluido.',
    },
    {
      eyebrow:  'COMISIONES AUTOMÁTICAS',
      headline: 'Cada barbero sabe lo que ganó.',
      sub:      'Sin calculadoras, sin Excel, sin discusiones al cierre.',
    },
    {
      eyebrow:  'REPORTES EN TIEMPO REAL',
      headline: '¿Cuánto hiciste hoy?',
      sub:      'Ventas, servicios más populares y rendimiento por empleado.',
    },
  ];

  currentSlide = 0;
  slideVisible = true;
  private slideInterval: ReturnType<typeof setInterval> | null = null;

  private fb = inject(FormBuilder);
  private authService = inject(AuthService);
  public appConfig = inject(AppConfigService);
  private router = inject(Router);
  private messageService = inject(MessageService);
  private localeService = inject(LocaleService);
  public layoutService = inject(LayoutService);

  readonly isDarkTheme = computed(() => this.layoutService.layoutConfig().darkTheme);

  ngOnInit(): void {
    this.authService.isAuthenticated$.subscribe(isAuth => {
      if (isAuth) {
        const currentUser = this.authService.getCurrentUser();
        const userRole = currentUser?.role;
        this.redirectUser(userRole || '');
      }
    });

    const savedEmail = safeGetItem('remembered_email');
    const rememberVal = !!savedEmail;

    this.loginForm = this.fb.group({
      email: [savedEmail || '', [Validators.required, Validators.email]],
      tenant: [''],
      password: ['', Validators.required],
      rememberMe: [rememberVal]
    });

    this.startSlideRotation();
  }

  ngOnDestroy(): void {
    if (this.slideInterval) clearInterval(this.slideInterval);
  }

  private startSlideRotation(): void {
    this.slideInterval = setInterval(() => {
      this.slideVisible = false;
      setTimeout(() => {
        this.currentSlide = (this.currentSlide + 1) % this.slides.length;
        this.slideVisible = true;
      }, 400);
    }, 4000);
  }

  get email(): FormControl { return this.loginForm.get('email') as FormControl; }
  get password(): FormControl { return this.loginForm.get('password') as FormControl; }
  get tenant(): FormControl { return this.loginForm.get('tenant') as FormControl; }
  get rememberMe(): FormControl { return this.loginForm.get('rememberMe') as FormControl; }

  onSubmit(): void {
    if (this.loginForm.valid) {
      this.isLoading = true;
      const { email, password, tenant, rememberMe } = this.loginForm.value;

      this.authService.login({ email, password, tenant_subdomain: tenant || undefined }).subscribe({
        next: (response: LoginResponse) => {
          this.isLoading = false;
          if (response.requires_mfa) {
            this.requiresMfa = true;
            this.pendingMfaEmail = email;
            this.pendingMfaTenantSubdomain = tenant || undefined;
            return;
          }

          if (rememberMe) {
            safeSetItem('remembered_email', email);
          } else {
            safeRemoveItem('remembered_email');
          }

          this.redirectUser(response.user?.role || '');
        },
        error: (error) => {
          this.isLoading = false;
          this.messageService.add({ 
            severity: 'error', 
            summary: 'Login Failed', 
            detail: getHttpErrorMessage(error, 'Error al iniciar sesión') 
          });
        }
      });
    } else {
      this.loginForm.markAllAsTouched();
    }
  }


  onVerifyMfa(): void {
    if (this.mfaCode.invalid) {
      this.messageService.add({
        severity: 'error',
        summary: 'Código MFA inválido',
        detail: 'Ingrese un código MFA de 6 dígitos válido'
      });
      return;
    }

    this.isLoading = true;
    const mfaCode = this.mfaCode.value;

    const verifyData: MFALoginVerifyRequest = {
      email: this.pendingMfaEmail || '',
      code: mfaCode || '',
      tenant_subdomain: this.pendingMfaTenantSubdomain || undefined
    };

    this.authService.verifyLoginMfa(verifyData).subscribe({
      next: (response: LoginResponse) => {
        this.isLoading = false;

        const emailVal = this.email.value;
        const rememberMeVal = this.rememberMe.value;
        if (rememberMeVal) {
          safeSetItem('remembered_email', emailVal);
        } else {
          safeRemoveItem('remembered_email');
        }

        this.resetMfaState();
        this.redirectUser(response.user?.role || '');
      },
      error: (error) => {
        this.isLoading = false;
        this.messageService.add({
          severity: 'error',
          summary: 'Verificación MFA fallida',
          detail: getHttpErrorMessage(error, 'Código MFA inválido. Intente nuevamente.')
        });
      }
    });
  }

  cancelMfa(): void {
    this.resetMfaState(true);
  }

  private resetMfaState(resetPassword = false): void {
    this.requiresMfa = false;
    this.pendingMfaEmail = null;
    this.pendingMfaTenantSubdomain = null;
    this.isLoading = false;
    this.mfaCode.reset();
    if (resetPassword) {
      this.password?.reset();
    }
  }



  private redirectUser(role: string): void {
    const normalizedRole = roleKey(role);
    
    if (normalizedRole === 'SUPER_ADMIN') {
      this.router.navigate(['/admin/dashboard']);
    } else if (normalizedRole === 'UTILITY') {
      this.router.navigate(['/client/profile']).then(() => {
        this.messageService.add({
          severity: 'success',
          summary: this.t('auth.login.profile_updated'),
          detail: 'Su cuenta ha sido gestionada correctamente.'
        });
      });
    } else {
      this.router.navigate(['/client/dashboard']).then(() => {
        this.messageService.add({
          severity: 'success',
          summary: this.t('auth.login.welcome'),
          detail: 'Bienvenido a su panel de control.'
        });
      });
    }
  }

  toggleDarkMode(): void {
    this.layoutService.layoutConfig.update((state) => ({ 
      ...state, 
      darkTheme: !state.darkTheme 
    }));
  }

  getEmailErrorMessage(): string {
    if (this.email?.errors?.['required']) {
      return 'El correo electrónico es requerido';
    }
    if (this.email?.errors?.['email']) {
      return 'Por favor ingrese un correo electrónico válido';
    }
    return '';
  }

  getPasswordErrorMessage(): string {
    if (this.password?.errors?.['required']) {
      return 'La contraseña es requerida';
    }
    return '';
  }

  t(key: string): string {
    return this.localeService.translate(key as any);
  }

  onResendVerification(): void {
    const emailVal = this.email?.value;
    if (!emailVal) {
      this.messageService.add({
        severity: 'error',
        summary: this.t('auth.login.error'),
        detail: this.t('auth.login.enter_email')
      });
      return;
    }

    this.isLoading = true;
    this.authService.resendVerificationEmail(emailVal.trim().toLowerCase()).subscribe({
      next: (response) => {
        this.isLoading = false;
        this.messageService.add({
          severity: 'success',
          summary: this.t('auth.login.verification_sent'),
          detail: this.t('auth.login.check_email')
        });
      },
      error: (err) => {
        this.isLoading = false;
        this.messageService.add({
          severity: 'error',
          summary: this.t('auth.login.error'),
          detail: getHttpErrorMessage(err, 'Error al reenviar verificación')
        });
      }
    });
  }
}