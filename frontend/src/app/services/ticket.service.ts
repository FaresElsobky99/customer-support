import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { CreateTicketResponse, Ticket, TicketListResponse, TicketStatus } from '../models/ticket';

@Injectable({ providedIn: 'root' })
export class TicketService {
  private readonly http = inject(HttpClient);

  getTickets(): Observable<TicketListResponse> {
    return this.http.get<TicketListResponse>(`${environment.apiUrl}/tickets`);
  }

  createTicket(issue: string): Observable<CreateTicketResponse> {
    return this.http.post<CreateTicketResponse>(`${environment.apiUrl}/tickets`, {
      issue,
    });
  }

  updateTicketStatus(ticketId: number, status: TicketStatus): Observable<Ticket> {
    return this.http.patch<Ticket>(`${environment.apiUrl}/tickets/${ticketId}/status`, {
      status,
    });
  }
}
