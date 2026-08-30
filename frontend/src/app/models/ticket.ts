export type TicketStatus = 'open' | 'closed';

export interface Ticket {
  ticket_id: number;
  customer_id: number;
  issue: string;
  status: TicketStatus;
}

export interface TicketListResponse {
  tickets: Ticket[];
}

export interface CreateTicketResponse extends Ticket {}
