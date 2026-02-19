import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule
  ],
  template: `
    <div class="login-container">
      <mat-card class="login-card">
        <mat-card-header>
          <div class="logo">
            <mat-icon class="brain-icon">psychology</mat-icon>
            <h1>Brain</h1>
          </div>
          <p class="subtitle">Sistema de Gestión de Asistentes IA</p>
        </mat-card-header>
        
        <mat-card-content>
          <form [formGroup]="loginForm" (ngSubmit)="onSubmit()">
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Usuario o Email</mat-label>
              <input matInput formControlName="identifier" placeholder="usuario@email.com">
              <mat-icon matPrefix>person</mat-icon>
              @if (loginForm.get('identifier')?.hasError('required') && loginForm.get('identifier')?.touched) {
                <mat-error>El usuario es requerido</mat-error>
              }
            </mat-form-field>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Contraseña</mat-label>
              <input matInput 
                     [type]="hidePassword() ? 'password' : 'text'" 
                     formControlName="password"
                     placeholder="••••••••">
              <mat-icon matPrefix>lock</mat-icon>
              <button mat-icon-button matSuffix type="button" (click)="hidePassword.set(!hidePassword())">
                <mat-icon>{{ hidePassword() ? 'visibility_off' : 'visibility' }}</mat-icon>
              </button>
              @if (loginForm.get('password')?.hasError('required') && loginForm.get('password')?.touched) {
                <mat-error>La contraseña es requerida</mat-error>
              }
            </mat-form-field>

            <button mat-raised-button 
                    color="primary" 
                    type="submit" 
                    class="full-width login-button"
                    [disabled]="loading() || loginForm.invalid">
              @if (loading()) {
                <mat-spinner diameter="20"></mat-spinner>
              } @else {
                <mat-icon>login</mat-icon>
                Iniciar Sesión
              }
            </button>
          </form>
        </mat-card-content>

        <mat-card-footer>
          <p class="footer-text">
            ¿No tienes cuenta? Contacta con el administrador
          </p>
        </mat-card-footer>
      </mat-card>
    </div>
  `,
  styles: [`
    .login-container {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
      padding: 20px;
    }

    .login-card {
      width: 100%;
      max-width: 420px;
      padding: 40px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.95);
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }

    mat-card-header {
      display: flex;
      flex-direction: column;
      align-items: center;
      margin-bottom: 32px;
    }

    .logo {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 8px;
    }

    .brain-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: #0f3460;
    }

    .logo h1 {
      margin: 0;
      font-size: 32px;
      font-weight: 700;
      color: #1a1a2e;
    }

    .subtitle {
      margin: 0;
      color: #666;
      font-size: 14px;
      text-align: center;
    }

    .full-width {
      width: 100%;
    }

    mat-form-field {
      margin-bottom: 16px;
    }

    .login-button {
      height: 48px;
      font-size: 16px;
      margin-top: 16px;
    }

    .login-button mat-spinner {
      display: inline-block;
    }

    mat-card-footer {
      padding-top: 24px;
      border-top: 1px solid #eee;
      margin-top: 24px;
    }

    .footer-text {
      margin: 0;
      text-align: center;
      color: #888;
      font-size: 13px;
    }
  `]
})
export class LoginComponent {
  loginForm: FormGroup;
  loading = signal(false);
  hidePassword = signal(true);

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private snackBar: MatSnackBar
  ) {
    this.loginForm = this.fb.group({
      identifier: ['', [Validators.required]],
      password: ['', [Validators.required]]
    });
  }

  onSubmit(): void {
    if (this.loginForm.invalid) return;

    this.loading.set(true);
    
    this.authService.login(this.loginForm.value).subscribe({
      next: () => {
        const returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/dashboard';
        this.router.navigateByUrl(returnUrl);
        this.snackBar.open('¡Bienvenido!', 'Cerrar', { duration: 3000 });
      },
      error: (error) => {
        this.loading.set(false);
        this.snackBar.open(error.message || 'Error de autenticación', 'Cerrar', { 
          duration: 5000,
          panelClass: ['error-snackbar']
        });
      }
    });
  }
}
