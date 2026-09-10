import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { ChatResponse, ChatTurn } from '../models/chat';

@Injectable({ providedIn: 'root' })
export class ChatService {
  private readonly http = inject(HttpClient);

  /**
   * Send one message to the support agent. The endpoint is stateless: pass the running
   * transcript and store the `history` from the response for the next call.
   */
  sendMessage(message: string, history: ChatTurn[]): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(`${environment.apiUrl}/agent/chat`, {
      message,
      history,
    });
  }
}
