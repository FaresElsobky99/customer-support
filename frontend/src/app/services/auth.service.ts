import { HttpClient } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';
import { LoginResponse, UserRole } from '../models/user';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly tokenKey = 'support_token';
  private readonly customerIdKey = 'support_customer_id';
  private readonly roleKey = 'support_role';

  private readonly authenticatedState = signal(Boolean(this.getToken()));
  private readonly roleState = signal<UserRole | null>(this.readStoredRole());

  login(email: string, password: string): Observable<LoginResponse> {
    return this.http
      .post<LoginResponse>(`${environment.apiUrl}/auth/login`, { email, password })
      .pipe(tap((response) => this.storeSession(response)));
  }

  logout(): void {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.customerIdKey);
    localStorage.removeItem(this.roleKey);
    this.authenticatedState.set(false);
    this.roleState.set(null);
    void this.router.navigate(['/login']);
  }

  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  getCustomerId(): number | null {
    const value = localStorage.getItem(this.customerIdKey);
    return value ? Number(value) : null;
  }

  getCurrentRole(): UserRole | null {
    return this.roleState();
  }

  isAuthenticated(): boolean {
    return this.authenticatedState();
  }

  isAdmin(): boolean {
    return this.roleState() === 'admin';
  }

  private storeSession(response: LoginResponse): void {
    localStorage.setItem(this.tokenKey, response.token);
    localStorage.setItem(this.customerIdKey, String(response.customer_id));
    localStorage.setItem(this.roleKey, response.role);
    this.authenticatedState.set(true);
    this.roleState.set(response.role);
  }

  private readStoredRole(): UserRole | null {
    const role = localStorage.getItem(this.roleKey);
    return role === 'admin' || role === 'customer' ? role : null;
  }
}
