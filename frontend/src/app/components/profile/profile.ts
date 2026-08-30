import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { Customer } from '../../models/user';
import { CustomerService } from '../../services/customer.service';

@Component({
  selector: 'app-profile',
  templateUrl: './profile.html',
  styleUrl: './profile.css',
})
export class Profile {
  private readonly customerService = inject(CustomerService);

  protected readonly customer = signal<Customer | null>(null);
  protected readonly errorMessage = signal('');
  protected readonly loading = signal(true);

  constructor() {
    this.customerService.getProfile().subscribe({
      next: (customer) => {
        this.customer.set(customer);
        this.loading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.loading.set(false);
        this.errorMessage.set(
          error.status === 403 ? 'Permission denied' : 'Unable to load your profile.',
        );
      },
    });
  }
}
