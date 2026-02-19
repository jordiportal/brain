/**
 * Interfaces compartidas para el sistema de chat unificado.
 * 
 * Estas interfaces son utilizadas por:
 * - ChatComponent (componente compartido)
 * - TestingComponent
 * - ChainsComponent
 * - SubagentsComponent
 */

export type StepType = 'tool' | 'subtask' | 'thinking' | 'generic';

/**
 * Paso intermedio con contenido streaming.
 * 
 * `type` determina la visualización:
 * - tool: línea inline compacta (icono + nombre + duración)
 * - subtask: bloque con borde, resumen de agente y children anidados
 * - thinking: línea discreta para reflexiones del LLM
 * - generic: fallback, misma visualización que tool
 */
export interface IntermediateStep {
  id: string;
  name: string;
  icon: string;
  status: 'running' | 'completed' | 'failed';
  content: string;
  type: StepType;
  data?: any;
  startTime: Date;
  endTime?: Date;
  /** Para subtasks: ID de sesión hija */
  sessionId?: string;
  /** Para subtasks: ID de sesión padre */
  parentId?: string;
  /** Para subtasks: tipo de agente (sap_analyst, etc.) */
  agentType?: string;
  /** Para subtasks: pasos anidados del agente */
  children?: IntermediateStep[];
  /** Para subtasks: número de tool calls */
  toolCount?: number;
}

/**
 * Datos de imagen generada
 */
export interface ImageData {
  url?: string;        // URL de Strapi o data URL
  base64?: string;     // Fallback
  mimeType?: string;
  altText: string;
}

/**
 * Datos de vídeo generado
 */
export interface VideoData {
  url?: string;        // Data URL del vídeo
  base64?: string;     // Fallback
  mimeType?: string;
  duration?: number;
  resolution?: string;
}

/**
 * Mensaje de chat unificado
 * 
 * Soporta:
 * - Mensajes simples (testing)
 * - Pasos intermedios (chains)
 * - Imágenes y vídeos generados
 * - Streaming
 * - Tokens de uso
 * - Timestamps
 */
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: Date;
  intermediateSteps?: IntermediateStep[];
  tokens?: number;
  isStreaming?: boolean;
  images?: ImageData[];
  videos?: VideoData[];
  /** Iteración actual del executor (para badge discreto durante streaming) */
  currentIteration?: number;
  /** Total de iteraciones máximas */
  maxIterations?: number;
}

/**
 * Configuración de features del chat
 * 
 * Permite habilitar/deshabilitar características según el contexto:
 * - testing: configPanel=true, timestamps=true
 * - chains: intermediateSteps=true, presentations=true
 * - subagents: history=true, images=true
 */
export interface ChatFeatures {
  /** Mostrar pasos intermedios inline */
  intermediateSteps: boolean;
  /** Mostrar imágenes generadas */
  images: boolean;
  /** Mostrar vídeos generados */
  videos: boolean;
  /** Soporte para presentaciones HTML */
  presentations: boolean;
  /** Indicador de streaming */
  streaming: boolean;
  /** Contador de tokens */
  tokens: boolean;
  /** Mostrar timestamp del mensaje */
  timestamps: boolean;
  /** Botón para limpiar chat */
  clearButton: boolean;
  /** Panel de configuración lateral (testing) */
  configPanel: boolean;
}

/**
 * Configuración de LLM para el chat
 * Usado cuando configPanel=true
 */
export interface ChatLLMConfig {
  providerUrl: string;
  providerType: string;
  apiKey?: string;
  model: string;
  systemPrompt?: string;
}

/**
 * Evento de mensaje enviado
 */
export interface MessageSentEvent {
  content: string;
  config?: ChatLLMConfig;
}

/**
 * Evento de presentación abierta
 */
export interface PresentationOpenEvent {
  html: string;
  title?: string;
}
