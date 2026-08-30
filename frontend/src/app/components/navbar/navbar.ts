import { Component, effect, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { CustomerService } from '../../services/customer.service';

@Component({
  selector: 'app-navbar',
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './navbar.html',
  styleUrl: './navbar.css',
})
export class Navbar {
  protected readonly authService = inject(AuthService);
  private readonly customerService = inject(CustomerService);
  protected readonly customerName = signal('');

  constructor() {
    effect((onCleanup) => {
      if (!this.authService.isAuthenticated()) {
        this.customerName.set('');
        return;
      }

      const subscription = this.customerService.getProfile().subscribe({
        next: (customer) => this.customerName.set(customer.name),
        error: () => this.customerName.set(''),
      });

      onCleanup(() => subscription.unsubscribe());
    });
  }
}
