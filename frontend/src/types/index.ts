// User Types
export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  department: string;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login?: string;
}

// Chat Types
export interface ChatMessage {
  id: number;
  conversation_id: number;
  sender_type: 'user' | 'bot' | 'system';
  message_content: string;
  timestamp: string;
  message_metadata?: {
    server_name?: string;
    correlation_id?: string;
    data_sources?: string[];
    suggestions?: string[];
    [key: string]: any;
  };
}

export interface ChatConversation {
  id: number;
  title: string;
  status: 'active' | 'resolved' | 'escalated';
  priority: 'low' | 'medium' | 'high' | 'critical';
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatResponse {
  message: string;
  conversation_id: number;
  message_id?: number; // Backend message ID for resolution feedback tracking
  suggestions?: string[];
  data_sources?: string[];
  incident_required: boolean;
}

// Dashboard Types
export interface DashboardStats {
  total_users: number;
  total_conversations: number;
  total_queries_resolved: number;
  active_conversations: number;
  queries_today: number;
  common_issues: Array<{
    issue_type: string;
    count: number;
  }>;
  resolution_rate: number;
}

export interface UserStats {
  id: number;
  username: string;
  full_name: string;
  department: string;
  total_conversations: number;
  last_active?: string;
  queries_resolved: number;
}

// API Types
export interface ApiError {
  message: string;
  detail?: string;
  status_code?: number;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_info: {
    id: number;
    username: string;
    full_name: string;
    department: string;
    role: string;
  };
}

export interface MessageRequest {
  message: string;
  conversation_id?: number;
  server_name?: string;
  correlation_id?: string;
}

// Theme Types
export interface HSBCTheme {
  colors: {
    primary: string;
    secondary: string;
    background: string;
    surface: string;
    text: {
      primary: string;
      secondary: string;
    };
  };
  spacing: {
    xs: string;
    sm: string;
    md: string;
    lg: string;
    xl: string;
  };
}