import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { Customer, CustomerListResponse } from '../models/user';

@Injectable({ providedIn: 'root' })
export class CustomerService {
  private readonly http = inject(HttpClient);

  getProfile(): Observable<Customer> {
    return this.http.get<Customer>(`${environment.apiUrl}/customers/me`);
  }

  getCustomers(): Observable<CustomerListResponse> {
    return this.http.get<CustomerListResponse>(`${environment.apiUrl}/customers`);
  }
}
