import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap, catchError, throwError } from 'rxjs';
import { AuthResponse, LoginCredentials, User } from '../models';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly STRAPI_URL = 'http://localhost:1337';
  private readonly TOKEN_KEY = 'brain_token';
  private readonly USER_KEY = 'brain_user';

  // Signals para estado reactivo
  private currentUserSignal = signal<User | null>(this.getStoredUser());
  private isAuthenticatedSignal = signal<boolean>(this.hasValidToken());

  // Computed values
  readonly currentUser = computed(() => this.currentUserSignal());
  readonly isAuthenticated = computed(() => this.isAuthenticatedSignal());

  constructor(
    private http: HttpClient,
    private router: Router
  ) {
    // Verificar token al iniciar
    this.checkAuthStatus();
  }

  /**
   * Login con Strapi
   */
  login(credentials: LoginCredentials): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(
      `${this.STRAPI_URL}/api/auth/local`,
      credentials
    ).pipe(
      tap(response => {
        this.setSession(response);
      }),
      catchError(error => {
        console.error('Login error:', error);
        return throwError(() => new Error(error.error?.error?.message || 'Error de autenticación'));
      })
    );
  }

  /**
   * Registro de nuevo usuario
   */
  register(username: string, email: string, password: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(
      `${this.STRAPI_URL}/api/auth/local/register`,
      { username, email, password }
    ).pipe(
      tap(response => {
        this.setSession(response);
      }),
      catchError(error => {
        console.error('Register error:', error);
        return throwError(() => new Error(error.error?.error?.message || 'Error de registro'));
      })
    );
  }

  /**
   * Logout
   */
  logout(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    this.currentUserSignal.set(null);
    this.isAuthenticatedSignal.set(false);
    this.router.navigate(['/login']);
  }

  /**
   * Obtener token actual
   */
  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  /**
   * Verificar estado de autenticación
   * Solo hace logout si el token es explícitamente inválido (401)
   */
  private checkAuthStatus(): void {
    const token = this.getToken();
    if (token) {
      // Si hay token, asumir autenticado hasta que se demuestre lo contrario
      this.isAuthenticatedSignal.set(true);
      
      // Verificar que el token sigue siendo válido en background
      this.http.get<User>(`${this.STRAPI_URL}/api/users/me`).pipe(
        tap(user => {
          this.currentUserSignal.set(user);
          localStorage.setItem(this.USER_KEY, JSON.stringify(user));
        }),
        catchError((error) => {
          // Solo hacer logout si es un error 401 (token inválido/expirado)
          if (error.status === 401) {
            console.warn('Token inválido o expirado, cerrando sesión');
            this.logout();
          } else {
            // Para otros errores (red, servidor caído, etc.), mantener sesión
            console.warn('Error verificando sesión, manteniendo token:', error.message);
          }
          return throwError(() => error);
        })
      ).subscribe();
    }
  }

  /**
   * Guardar sesión
   */
  private setSession(authResult: AuthResponse): void {
    localStorage.setItem(this.TOKEN_KEY, authResult.jwt);
    localStorage.setItem(this.USER_KEY, JSON.stringify(authResult.user));
    this.currentUserSignal.set(authResult.user);
    this.isAuthenticatedSignal.set(true);
  }

  /**
   * Verificar si hay token válido
   */
  private hasValidToken(): boolean {
    const token = localStorage.getItem(this.TOKEN_KEY);
    return !!token;
  }

  /**
   * Obtener usuario almacenado
   */
  private getStoredUser(): User | null {
    const userStr = localStorage.getItem(this.USER_KEY);
    if (userStr) {
      try {
        return JSON.parse(userStr);
      } catch {
        return null;
      }
    }
    return null;
  }
}
