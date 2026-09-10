export type ChatRole = 'user' | 'assistant';

export interface ChatTurn {
  role: ChatRole;
  content: string;
}

export interface ChatRequest {
  message: string;
  history: ChatTurn[];
}

export interface ChatResponse {
  reply: string;
  history: ChatTurn[];
  tool_calls: string[];
  stopped_reason: string;
}
