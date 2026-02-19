import { Injectable, WritableSignal } from '@angular/core';
import { ChatMessage, IntermediateStep, ImageData, VideoData } from '../components/chat';

export interface SseStreamConfig {
  url: string;
  payload: any;
  messages: WritableSignal<ChatMessage[]>;
  /** node_ids que deben tratarse como respuesta final (tokens acumulados en content) */
  finalResponseNodeIds?: string[];
  /** Callback opcional para mapear node_name a icono de Material */
  getStepIcon?: (nodeName: string) => string;
  /** Callback cuando se recibe un step content enriquecido (node_end con data) */
  buildStepContent?: (step: IntermediateStep) => string;
}

export interface SseStreamResult {
  finalContent: string;
  intermediateSteps: IntermediateStep[];
  images: ImageData[];
  videos: VideoData[];
  tokens: number;
  error?: string;
}

const DEFAULT_FINAL_NODE_IDS = ['synthesizer', 'adaptive_agent'];

function defaultStepIcon(nodeName: string): string {
  const n = (nodeName || '').toLowerCase();
  if (n.includes('iteration') || n.includes('iteraci')) return 'loop';
  if (n.includes('planificador') || n.includes('planner') || n.includes('plan')) return 'assignment';
  if (n.includes('pensando') || n.includes('think') || n.includes('reflexion') || n.includes('reflect')) return 'psychology';
  if (n.includes('delegando') || n.includes('delegate')) return 'bolt';
  if (n.includes('sintetiz') || n.includes('synthes') || n.includes('respuesta final')) return 'auto_awesome';
  if (n.includes('sap')) return 'storage';
  if (n.includes('rag') || n.includes('búsqueda') || n.includes('search') || n.includes('busca')) return 'search';
  if (n.includes('resum') || n.includes('summar')) return 'summarize';
  if (n.includes('consult') || n.includes('equipo')) return 'groups';
  if (n.includes('tool') || n.includes('ejecut')) return 'build';
  if (n.includes('llm') || n.includes('generación')) return 'smart_toy';
  return 'radio_button_checked';
}

function defaultBuildStepContent(step: IntermediateStep): string {
  const d = step.data || {};
  const parts: string[] = [];
  if (step.content) parts.push(step.content);
  if (d.thinking) parts.push('**Pensamiento:**\n' + d.thinking);
  if (d.observation) parts.push('**Observación:**\n' + d.observation);
  if (d.conversation) parts.push(d.conversation);
  else if (d.result_preview) parts.push('**Resultado:**\n' + d.result_preview);
  if (d.arguments && Object.keys(d.arguments).length > 0) {
    const args = typeof d.arguments === 'string' ? d.arguments : JSON.stringify(d.arguments, null, 2);
    parts.push('**Argumentos:**\n```json\n' + args + '\n```');
  }
  return parts.join('\n\n');
}

@Injectable({ providedIn: 'root' })
export class SseStreamService {

  /**
   * Ejecuta un POST SSE y actualiza el signal de mensajes en tiempo real.
   * Retorna cuando el stream se cierra.
   */
  async stream(config: SseStreamConfig): Promise<SseStreamResult> {
    const finalNodeIds = new Set(config.finalResponseNodeIds ?? DEFAULT_FINAL_NODE_IDS);
    const getIcon = config.getStepIcon ?? defaultStepIcon;
    const buildContent = config.buildStepContent ?? defaultBuildStepContent;

    let response: Response;
    try {
      response = await fetch(config.url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config.payload)
      });
    } catch {
      return this.errorResult('Error de conexión con el servidor.');
    }
    if (!response.ok) {
      return this.errorResult(`Error del servidor (${response.status}).`);
    }
    const reader = response.body?.getReader();
    if (!reader) {
      return this.errorResult('Stream no disponible.');
    }

    const decoder = new TextDecoder();
    let finalContent = '';
    let tokens = 0;
    const intermediateSteps: IntermediateStep[] = [];
    const activeSteps = new Map<string, IntermediateStep>();
    let currentStepId: string | null = null;
    let stepContentBuffer = '';
    const images: ImageData[] = [];
    const videos: VideoData[] = [];

    const assistantMessage: ChatMessage = {
      role: 'assistant',
      content: '',
      intermediateSteps: [],
      isStreaming: true,
      images: [],
      videos: [],
      timestamp: new Date()
    };
    config.messages.update(msgs => [...msgs, assistantMessage]);

    const updateMessage = (streaming: boolean = true) => {
      config.messages.update(msgs => {
        const updated = [...msgs];
        updated[updated.length - 1] = {
          ...assistantMessage,
          content: finalContent,
          intermediateSteps: [...intermediateSteps],
          tokens,
          isStreaming: streaming,
          images: [...images],
          videos: [...videos]
        };
        return updated;
      });
    };

    let buffer = '';
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';

        for (const part of parts) {
          for (const line of part.split('\n')) {
            if (!line.startsWith('data: ')) continue;
            let data: any;
            try { data = JSON.parse(line.slice(6)); } catch { continue; }

            switch (data.event_type) {
              case 'node_start': {
                const stepId = data.node_id || `step-${Date.now()}`;
                const nodeName = data.node_name || 'Procesando';
                intermediateSteps.forEach(s => s.expanded = false);
                const newStep: IntermediateStep = {
                  id: stepId,
                  name: nodeName,
                  icon: getIcon(nodeName),
                  status: 'running',
                  content: '',
                  data: data.data,
                  startTime: new Date(),
                  expanded: true
                };
                intermediateSteps.push(newStep);
                activeSteps.set(stepId, newStep);
                currentStepId = stepId;
                stepContentBuffer = '';
                updateMessage();
                break;
              }
              case 'token': {
                if (!data.content) break;
                const isFinal = finalNodeIds.has(data.node_id) || !data.node_id;
                if (isFinal) {
                  finalContent += data.content;
                } else if (currentStepId && activeSteps.has(currentStepId)) {
                  stepContentBuffer += data.content;
                  activeSteps.get(currentStepId)!.content = stepContentBuffer;
                }
                updateMessage();
                break;
              }
              case 'node_end': {
                const stepId = data.node_id;
                if (stepId && activeSteps.has(stepId)) {
                  const step = activeSteps.get(stepId)!;
                  step.status = 'completed';
                  step.endTime = new Date();
                  if (data.data) {
                    step.data = { ...step.data, ...data.data };
                    step.content = buildContent(step);
                  }
                  if (data.data?.tokens) tokens = data.data.tokens;
                  const idx = intermediateSteps.findIndex(s => s.id === stepId);
                  if (idx >= 0) {
                    intermediateSteps[idx] = { ...step };
                    activeSteps.set(stepId, intermediateSteps[idx]);
                  }
                }
                currentStepId = null;
                updateMessage();
                break;
              }
              case 'image': {
                if (data.data) {
                  images.push({
                    url: data.data.image_url,
                    base64: data.data.image_data,
                    mimeType: data.data.mime_type || 'image/png',
                    altText: data.data.alt_text || 'Generated image'
                  });
                  updateMessage();
                }
                break;
              }
              case 'video': {
                if (data.data) {
                  videos.push({
                    url: data.data.video_url,
                    base64: data.data.video_data,
                    mimeType: data.data.mime_type || 'video/mp4',
                    duration: data.data.duration_seconds,
                    resolution: data.data.resolution
                  } as any);
                  updateMessage();
                }
                break;
              }
              case 'response_complete': {
                if (data.content) finalContent = data.content;
                if (data.data?.iterations) tokens = data.data.iterations;
                break;
              }
              case 'error': {
                if (currentStepId && activeSteps.has(currentStepId)) {
                  const step = activeSteps.get(currentStepId)!;
                  step.status = 'failed';
                  step.content = data.data?.error || 'Error desconocido';
                }
                updateMessage();
                break;
              }
            }
          }
        }
      }
    } catch (e) {
      console.error('SSE stream read error', e);
    }

    updateMessage(false);

    return { finalContent, intermediateSteps, images, videos, tokens };
  }

  private errorResult(msg: string): SseStreamResult {
    return {
      finalContent: '', intermediateSteps: [], images: [], videos: [], tokens: 0, error: msg
    };
  }
}
