export interface User {
  id: number
  email: string
  full_name: string
  role: 'admin' | 'user'
  groups: string[]
}

export interface Source {
  ref: number
  document_id: number
  document_title: string
  page: number | null
  snippet: string
  score: number
}

export interface ChatResponse {
  conversation_id: number
  answer: string
  sources: Source[]
  corrected_query: string | null
  grounded: boolean
}

export interface Conversation {
  id: number
  title: string
  created_at: string
}

export interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  sources: Source[] | null
  corrected_query?: string | null
}

export interface DocumentInfo {
  id: number
  title: string
  filename: string
  content_type: string
  allowed_groups: string[]
  n_chunks: number
  created_at: string
}
