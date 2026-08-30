import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { HealthService } from '../../services/health.service';

@Component({
  selector: 'app-dashboard',
  imports: [RouterLink],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class Dashboard {
  protected readonly authService = inject(AuthService);
  private readonly healthService = inject(HealthService);

  protected apiStatus = 'Checking…';

  constructor() {
    this.healthService.check().subscribe({
      next: (response) => {
        this.apiStatus = response.status === 'ok' ? 'Online' : response.status;
      },
      error: () => {
        this.apiStatus = 'Unavailable';
      },
    });
  }
}
