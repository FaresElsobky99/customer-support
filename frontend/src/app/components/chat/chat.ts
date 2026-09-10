import { HttpErrorResponse } from '@angular/common/http';
import { Component, effect, ElementRef, inject, signal, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ChatRole, ChatTurn } from '../../models/chat';
import { ChatService } from '../../services/chat.service';

interface ChatMessage {
  role: ChatRole;
  content: string;
  tools?: string[];
  note?: string;
}

const SUGGESTIONS = [
  'List my open support tickets',
  'Open a ticket: my password reset email never arrives',
  'What does the support policy say about inactive accounts?',
];

@Component({
  selector: 'app-chat',
  imports: [FormsModule],
  templateUrl: './chat.html',
  styleUrl: './chat.css',
})
export class Chat {
  private readonly chatService = inject(ChatService);
  private readonly scrollAnchor = viewChild<ElementRef<HTMLDivElement>>('anchor');

  protected readonly suggestions = SUGGESTIONS;
  protected readonly messages = signal<ChatMessage[]>([]);
  protected readonly sending = signal(false);
  protected readonly error = signal('');
  protected draft = '';

  constructor() {
    effect(() => {
      this.messages();
      this.sending();
      const anchor = this.scrollAnchor()?.nativeElement;
      if (anchor) {
        setTimeout(() => anchor.scrollIntoView({ behavior: 'smooth', block: 'end' }), 0);
      }
    });
  }

  protected useSuggestion(text: string): void {
    if (this.sending()) {
      return;
    }
    this.draft = text;
    this.send();
  }

  protected send(): void {
    const message = this.draft.trim();
    if (!message || this.sending()) {
      return;
    }

    const history: ChatTurn[] = this.messages().map(({ role, content }) => ({ role, content }));

    this.messages.update((list) => [...list, { role: 'user', content: message }]);
    this.draft = '';
    this.sending.set(true);
    this.error.set('');

    this.chatService.sendMessage(message, history).subscribe({
      next: (response) => {
        const rebuilt: ChatMessage[] = response.history.map(({ role, content }) => ({
          role,
          content,
        }));

        const last = rebuilt.at(-1);
        if (last?.role === 'assistant') {
          last.tools = response.tool_calls;
          last.note = this.noteFor(response.stopped_reason);
        }

        this.messages.set(rebuilt);
        this.sending.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.messages.update((list) => list.slice(0, -1));
        this.draft = message;
        this.sending.set(false);
        this.error.set(this.readError(error));
      },
    });
  }

  protected clear(): void {
    this.messages.set([]);
    this.error.set('');
    this.draft = '';
  }

  private noteFor(stoppedReason: string): string | undefined {
    if (stoppedReason === 'max_steps') {
      return 'The assistant ran out of steps for this turn. Try rephrasing or breaking it up.';
    }
    if (stoppedReason === 'rate_limited') {
      return 'The assistant is briefly rate-limited. Please try again in a few moments.';
    }
    return undefined;
  }

  private readError(error: HttpErrorResponse): string {
    if (error.status === 0) {
      return 'Could not reach the support service. Check your connection and try again.';
    }
    if (error.status === 403) {
      return 'Permission denied.';
    }
    const detail = error.error?.detail;
    return typeof detail === 'string' ? detail : 'Something went wrong. Please try again.';
  }
}
