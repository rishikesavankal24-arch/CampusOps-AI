export interface SourceReference {
  id: string;
  title: string;
  category: string;
  similarity: number;
  snippet: string;
  source_file?: string | null;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources?: SourceReference[];
  is_grounded?: boolean | null;
  insufficient_context?: boolean;
  created_at: string;
  isPending?: boolean;
  isError?: boolean;
}

export interface ChatQueryResponse {
  message_id: string;
  answer: string;
  sources: SourceReference[];
  is_grounded: boolean;
  insufficient_context: boolean;
  created_at: string;
}

export interface ChatHistoryResponse {
  messages: ChatMessage[];
  total: number;
}
