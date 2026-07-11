export interface User {
  id: string;
  email: string;
  full_name: string | null;
}

export interface Paper {
  id: string;
  user_id: string;
  title: string;
  file_name: string;
  file_size: number;
  status: "pending" | "processing" | "completed" | "failed";
  error_message: string | null;
  num_pages: number | null;
  summary: string | null;
  abstract: string | null;
  key_points: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  paper_id: string;
  paper_title: string;
  page_number: number;
  chunk_index: number;
  content: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[] | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface SearchResult {
  chunk_id: string;
  paper_id: string;
  paper_title: string;
  page_number: number;
  content: string;
  score: number;
}

export interface SummaryResponse {
  summary: string;
  abstract: string;
  key_points: string[];
  explain_simple: string;
}
