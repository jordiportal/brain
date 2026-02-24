import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap, catchError, throwError } from 'rxjs';
import { AuthResponse, LoginCredentials, User, UserRole } from '../models';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly API_URL = environment.apiUrl.replace('/api/v1', '');
  private readonly TOKEN_KEY = 'brain_token';
  private readonly USER_KEY = 'brain_user';

  private currentUserSignal = signal<User | null>(this.getStoredUser());
  private isAuthenticatedSignal = signal<boolean>(this.hasValidToken());

  readonly currentUser = computed(() => this.currentUserSignal());
  readonly isAuthenticated = computed(() => this.isAuthenticatedSignal());
  readonly userRole = computed(() => this.currentUserSignal()?.role ?? 'viewer');
  readonly isAdmin = computed(() => this.userRole() === 'admin');

  constructor(
    private http: HttpClient,
    private router: Router
  ) {
    setTimeout(() => this.checkAuthStatus(), 0);
  }

  login(credentials: LoginCredentials): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(
      `${this.API_URL}/api/auth/local`,
      credentials
    ).pipe(
      tap(response => {
        this.setSession(response);
      }),
      catchError(error => {
        return throwError(() => new Error(error.error?.detail || error.error?.error?.message || 'Error de autenticación'));
      })
    );
  }

  register(username: string, email: string, password: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(
      `${this.API_URL}/api/auth/local/register`,
      { username, email, password }
    ).pipe(
      tap(response => this.setSession(response)),
      catchError(error => {
        return throwError(() => new Error(error.error?.detail || error.error?.error?.message || 'Error de registro'));
      })
    );
  }

  logout(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    this.currentUserSignal.set(null);
    this.isAuthenticatedSignal.set(false);
    this.router.navigate(['/login']);
  }

  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  hasRole(...roles: UserRole[]): boolean {
    const current = this.currentUserSignal()?.role;
    return !!current && roles.includes(current);
  }

  private checkAuthStatus(): void {
    const token = this.getToken();
    if (token) {
      this.isAuthenticatedSignal.set(true);

      this.http.get<User>(`${this.API_URL}/api/users/me`).pipe(
        tap(user => {
          this.currentUserSignal.set(user);
          localStorage.setItem(this.USER_KEY, JSON.stringify(user));
        }),
        catchError((error) => {
          if (error.status === 401) {
            this.logout();
          }
          return throwError(() => error);
        })
      ).subscribe();
    }
  }

  private setSession(authResult: AuthResponse): void {
    localStorage.setItem(this.TOKEN_KEY, authResult.jwt);
    localStorage.setItem(this.USER_KEY, JSON.stringify(authResult.user));
    this.currentUserSignal.set(authResult.user);
    this.isAuthenticatedSignal.set(true);
  }

  private hasValidToken(): boolean {
    return !!localStorage.getItem(this.TOKEN_KEY);
  }

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
