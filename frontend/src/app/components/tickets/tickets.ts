import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Ticket, TicketStatus } from '../../models/ticket';
import { AuthService } from '../../services/auth.service';
import { TicketService } from '../../services/ticket.service';

@Component({
  selector: 'app-tickets',
  imports: [FormsModule],
  templateUrl: './tickets.html',
  styleUrl: './tickets.css',
})
export class Tickets {
  private readonly ticketService = inject(TicketService);
  protected readonly authService = inject(AuthService);

  protected readonly tickets = signal<Ticket[]>([]);
  protected issue = '';
  protected readonly listError = signal('');
  protected readonly createMessage = signal('');
  protected readonly createError = signal('');
  protected readonly loading = signal(true);
  protected readonly creating = signal(false);
  protected readonly updatingTicketId = signal<number | null>(null);
  protected readonly actionMessage = signal('');
  protected readonly actionError = signal('');

  constructor() {
    this.loadTickets();
  }

  protected createTicket(): void {
    this.createMessage.set('');
    this.createError.set('');
    this.creating.set(true);

    this.ticketService.createTicket(this.issue).subscribe({
      next: () => {
        this.issue = '';
        this.creating.set(false);
        this.createMessage.set('Ticket created successfully.');
        this.loadTickets();
      },
      error: (error: HttpErrorResponse) => {
        this.creating.set(false);
        this.createError.set(this.readError(error, 'Unable to create the ticket.'));
      },
    });
  }

  protected updateStatus(ticket: Ticket, status: TicketStatus): void {
    this.updatingTicketId.set(ticket.ticket_id);
    this.actionMessage.set('');
    this.actionError.set('');

    this.ticketService.updateTicketStatus(ticket.ticket_id, status).subscribe({
      next: (updatedTicket) => {
        this.tickets.update((tickets) =>
          tickets.map((currentTicket) =>
            currentTicket.ticket_id === updatedTicket.ticket_id ? updatedTicket : currentTicket,
          ),
        );
        this.updatingTicketId.set(null);
        this.actionMessage.set(
          `Ticket #${updatedTicket.ticket_id} is now ${updatedTicket.status}.`,
        );
      },
      error: (error: HttpErrorResponse) => {
        this.updatingTicketId.set(null);
        this.actionError.set(this.readError(error, 'Unable to update the ticket.'));
      },
    });
  }

  private loadTickets(): void {
    this.loading.set(true);
    this.listError.set('');

    this.ticketService.getTickets().subscribe({
      next: (response) => {
        this.tickets.set(response.tickets);
        this.loading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.loading.set(false);
        this.listError.set(this.readError(error, 'Unable to load tickets.'));
      },
    });
  }

  private readError(error: HttpErrorResponse, fallback: string): string {
    if (error.status === 403) {
      return 'Permission denied';
    }

    const detail = error.error?.detail;
    return typeof detail === 'string' ? detail : fallback;
  }
}
