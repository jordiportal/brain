// ===========================================
// Brain GUI - Data Models
// ===========================================

// Auth
export interface User {
  id: number;
  username: string;
  email: string;
  blocked: boolean;
  confirmed: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface AuthResponse {
  jwt: string;
  user: User;
}

export interface LoginCredentials {
  identifier: string;
  password: string;
}

// LLM Providers
export interface LlmProvider {
  id: number;
  documentId: string;
  name: string;
  type: 'ollama' | 'openai' | 'gemini' | 'anthropic' | 'azure' | 'groq' | 'custom';
  baseUrl: string;
  apiKey?: string;
  defaultModel?: string;
  embeddingModel?: string;
  isActive: boolean;
  isDefault?: boolean;  // Proveedor preferido del usuario
  config?: Record<string, any>;
  description?: string;
  createdAt: string;
  updatedAt: string;
}

// MCP Connections
export interface McpConnection {
  id: number;
  documentId: string;
  name: string;
  type: 'stdio' | 'sse' | 'http';
  command?: string;
  args?: string[];
  serverUrl?: string;
  env?: Record<string, string>;
  isActive: boolean;
  config?: Record<string, any>;
  description?: string;
  tools?: any[];
  createdAt: string;
  updatedAt: string;
}

// Brain Chains
export interface BrainChain {
  id: number;
  documentId: string;
  name: string;
  slug: string;
  type: 'chain' | 'graph' | 'agent' | 'rag';
  description?: string;
  version: string;
  definition: Record<string, any>;
  nodes?: GraphNode[];
  edges?: GraphEdge[];
  isActive: boolean;
  llmProvider?: LlmProvider;
  config?: Record<string, any>;
  tags?: string[];
  createdAt: string;
  updatedAt: string;
  publishedAt?: string;
}

export interface GraphNode {
  id: string;
  type: 'entry' | 'exit' | 'action' | 'condition' | 'parallel' | 'subgraph';
  label: string;
  description?: string;
  config?: Record<string, any>;
}

export interface GraphEdge {
  source: string;
  target: string;
  condition?: string;
  label?: string;
}

// Execution Logs
export interface ExecutionLog {
  id: number;
  documentId: string;
  executionId: string;
  brainChain?: BrainChain;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  input?: Record<string, any>;
  output?: Record<string, any>;
  trace?: ExecutionStep[];
  error?: string;
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
  tokensUsed?: number;
  cost?: number;
  metadata?: Record<string, any>;
  createdAt: string;
}

export interface ExecutionStep {
  step: number;
  nodeId: string;
  timestamp: string;
  input: Record<string, any>;
  output: Record<string, any>;
  durationMs: number;
  error?: string;
}

// System Settings
export interface SystemSetting {
  id: number;
  documentId: string;
  key: string;
  value: any;
  type: 'string' | 'number' | 'boolean' | 'json' | 'secret';
  category: 'general' | 'security' | 'llm' | 'mcp' | 'rag' | 'monitoring' | 'other';
  description?: string;
  isPublic: boolean;
  createdAt: string;
  updatedAt: string;
}

// Strapi Response wrapper
export interface StrapiResponse<T> {
  data: T[];
  meta: {
    pagination: {
      page: number;
      pageSize: number;
      pageCount: number;
      total: number;
    };
  };
}

export interface StrapiSingleResponse<T> {
  data: T;
  meta: {};
}

// Menu items
export interface MenuItem {
  label: string;
  icon: string;
  route: string;
  children?: MenuItem[];
}
