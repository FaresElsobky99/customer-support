import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject } from '@angular/core';
import { Customer } from '../../models/user';
import { CustomerService } from '../../services/customer.service';

@Component({
  selector: 'app-customers',
  templateUrl: './customers.html',
  styleUrl: './customers.css',
})
export class Customers {
  private readonly customerService = inject(CustomerService);

  protected customers: Customer[] = [];
  protected errorMessage = '';
  protected loading = true;

  constructor() {
    this.customerService.getCustomers().subscribe({
      next: (response) => {
        this.customers = response.customers;
        this.loading = false;
      },
      error: (error: HttpErrorResponse) => {
        this.loading = false;
        this.errorMessage =
          error.status === 403 ? 'Permission denied' : 'Unable to load customers.';
      },
    });
  }
}
