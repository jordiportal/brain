import { 
  Component, 
  Input, 
  Output, 
  EventEmitter, 
  ViewChild, 
  ElementRef,
  ChangeDetectionStrategy,
  Signal,
  signal
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeUrl } from '@angular/platform-browser';

import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';

import { 
  ChatMessage, 
  ChatFeatures, 
  ChatLLMConfig,
  IntermediateStep,
  ImageData,
  VideoData
} from './chat-message.interface';
import { MarkdownPipe } from './markdown.pipe';

/**
 * ChatComponent - Componente de chat unificado y reutilizable.
 * 
 * Features:
 * - Mensajes con avatares
 * - Pasos intermedios desplegables (para chains)
 * - Imágenes y vídeos generados
 * - Soporte para presentaciones HTML
 * - Streaming indicator
 * - Configuración de LLM (opcional)
 * - Limpieza de chat
 * 
 * Usado por:
 * - TestingComponent (chat simple)
 * - ChainsComponent (con pasos intermedios)
 * - SubagentsComponent (con historial)
 */
@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    MatFormFieldModule,
    MatExpansionModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatTooltipModule,
    MarkdownPipe
  ],
  template: `
    <div class="chat-container" #chatContainer>
      <!-- Mensajes -->
      <div class="messages-area">
        @if (messages().length === 0) {
          <div class="empty-chat">
            <mat-icon>chat</mat-icon>
            <p>{{ emptyMessage }}</p>
          </div>
        }

        @for (msg of messages(); track $index) {
          <div class="message" [class]="msg.role">
            <div class="message-avatar">
              <mat-icon>{{ msg.role === 'user' ? 'person' : 'smart_toy' }}</mat-icon>
            </div>
            <div class="message-content">
              <!-- Header con role y timestamp -->
              @if (features.timestamps && msg.timestamp) {
                <div class="message-header">
                  <span class="message-role">{{ msg.role === 'user' ? 'Tú' : 'Asistente' }}</span>
                  <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
                </div>
              }

              @if (msg.role === 'user') {
                <div class="message-text">{{ msg.content }}</div>
              } @else {
                <!-- Pasos intermedios (para chains) -->
                @if (features.intermediateSteps && msg.intermediateSteps && msg.intermediateSteps.length > 0) {
                  <mat-accordion class="steps-accordion" multi>
                    @for (step of msg.intermediateSteps; track step.id) {
                      <mat-expansion-panel 
                        [expanded]="step.expanded"
                        [class.step-running]="step.status === 'running'"
                        [class.step-completed]="step.status === 'completed'"
                        [class.step-failed]="step.status === 'failed'">
                        <mat-expansion-panel-header>
                          <mat-panel-title>
                            <div class="step-header">
                              @if (step.status === 'running') {
                                <mat-spinner diameter="16"></mat-spinner>
                              } @else {
                                <mat-icon [class]="'step-icon-' + step.status">{{ step.icon }}</mat-icon>
                              }
                              <span class="step-name">{{ step.name }}</span>
                            </div>
                          </mat-panel-title>
                          <mat-panel-description>
                            @if (step.status === 'completed' && step.endTime && step.startTime) {
                              <span class="step-duration">
                                {{ getDuration(step.startTime, step.endTime) }}
                              </span>
                            }
                            @if (step.status === 'running') {
                              <span class="step-running-label">En progreso...</span>
                            }
                          </mat-panel-description>
                        </mat-expansion-panel-header>
                        
                        <div class="step-content">
                          @if (step.content) {
                            <div class="step-conversation">
                              <div class="step-text" [innerHTML]="step.content | markdown"></div>
                            </div>
                          }
                          
                          <!-- Presentación HTML -->
                          @if (features.presentations && step.data?.html) {
                            <div class="presentation-viewer">
                              <button mat-stroked-button color="primary" (click)="openPresentation(step.data.html)">
                                <mat-icon>slideshow</mat-icon>
                                Ver presentación
                              </button>
                            </div>
                          }

                          <!-- Datos avanzados -->
                          @if (hasAdvancedData(step)) {
                            <details class="step-data-details">
                              <summary>Datos avanzados</summary>
                              <pre class="step-data">{{ getAdvancedData(step) | json }}</pre>
                            </details>
                          }
                        </div>
                      </mat-expansion-panel>
                    }
                  </mat-accordion>
                }

                <!-- Respuesta final -->
                @if (msg.content) {
                  <div class="final-response">
                    @if (features.intermediateSteps) {
                      <div class="response-label">
                        <mat-icon>auto_awesome</mat-icon>
                        Respuesta Final
                      </div>
                    }
                    
                    <div class="markdown-content" [innerHTML]="msg.content | markdown"></div>

                    <!-- Presentación en respuesta final -->
                    @if (features.presentations && getPresentationHtml(msg)) {
                      <div class="presentation-viewer">
                        <button mat-stroked-button color="primary" (click)="openPresentation(getPresentationHtml(msg)!)">
                          <mat-icon>slideshow</mat-icon>
                          Ver presentación
                        </button>
                      </div>
                    }
                  </div>
                }

                <!-- Imágenes generadas -->
                @if (features.images && msg.images && msg.images.length > 0) {
                  <div class="generated-images">
                    @for (img of msg.images; track $index) {
                      <img 
                        [src]="sanitizeImageUrl(img)"
                        [alt]="img.altText"
                        class="generated-image"
                        loading="lazy"
                      />
                    }
                  </div>
                }

                <!-- Vídeos generados -->
                @if (features.videos && msg.videos && msg.videos.length > 0) {
                  <div class="generated-videos">
                    @for (video of msg.videos; track $index) {
                      <video 
                        [src]="sanitizeVideoUrl(video)"
                        class="generated-video"
                        controls
                        autoplay
                        loop
                        muted
                      >
                        Tu navegador no soporta vídeos HTML5.
                      </video>
                      @if (video.duration || video.resolution) {
                        <div class="video-info">
                          @if (video.duration) {
                            <span>{{ video.duration }}s</span>
                          }
                          @if (video.resolution) {
                            <span>{{ video.resolution }}</span>
                          }
                        </div>
                      }
                    }
                  </div>
                }

                <!-- Indicador de streaming -->
                @if (features.streaming && msg.isStreaming) {
                  <span class="cursor-blink">▊</span>
                }

                <!-- Tokens -->
                @if (features.tokens && msg.tokens) {
                  <span class="token-count">{{ msg.tokens }} tokens</span>
                }
              }
            </div>
          </div>
        }

        <!-- Typing indicator -->
        @if (isLoading() && !hasStreamingMessage()) {
          <div class="message assistant">
            <div class="message-avatar">
              <mat-icon>smart_toy</mat-icon>
            </div>
            <div class="message-content">
              <div class="typing-indicator">
                <span></span><span></span><span></span>
              </div>
              @if (currentStepName()) {
                <div class="current-step">
                  <mat-icon>{{ getStepIcon(currentStepName()!) }}</mat-icon>
                  {{ currentStepName() }}
                </div>
              }
            </div>
          </div>
        }
      </div>

      <!-- Área de input -->
      <div class="input-area">
        <mat-form-field appearance="outline" class="message-input">
          <textarea matInput 
                    [(ngModel)]="newMessageText" 
                    [placeholder]="placeholder"
                    (keydown.enter)="$event.preventDefault(); sendMessage()"
                    [disabled]="isLoading()"
                    rows="1">
          </textarea>
        </mat-form-field>
        <button mat-fab color="primary" 
                (click)="sendMessage()" 
                [disabled]="isLoading() || !newMessageText.trim()">
          @if (isLoading()) {
            <mat-spinner diameter="24" color="accent"></mat-spinner>
          } @else {
            <mat-icon>send</mat-icon>
          }
        </button>
      </div>

      <!-- Botón de limpiar -->
      @if (features.clearButton && messages().length > 0) {
        <div class="chat-actions">
          <button mat-button color="warn" (click)="clearChat()">
            <mat-icon>delete_sweep</mat-icon>
            Limpiar chat
          </button>
        </div>
      }
    </div>
  `,
  styles: [`
    .chat-container {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: white;
      border-radius: 12px;
      overflow: hidden;
    }

    .messages-area {
      flex: 1;
      overflow-y: auto;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .empty-chat {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: #999;
      padding: 64px;
    }

    .empty-chat mat-icon {
      font-size: 64px;
      width: 64px;
      height: 64px;
      margin-bottom: 16px;
    }

    /* Mensajes */
    .message {
      display: flex;
      gap: 12px;
      max-width: 90%;
    }

    .message.user {
      align-self: flex-end;
      flex-direction: row-reverse;
    }

    .message-avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .message.user .message-avatar {
      background: #667eea;
      color: white;
    }

    .message.assistant .message-avatar {
      background: #e8f5e9;
      color: #2e7d32;
    }

    .message-content {
      background: #f5f5f5;
      padding: 12px 16px;
      border-radius: 16px;
      min-width: 60px;
      max-width: 100%;
    }

    .message.user .message-content {
      background: #667eea;
      color: white;
      border-bottom-right-radius: 4px;
    }

    .message.assistant .message-content {
      background: transparent;
      padding: 0;
      border-radius: 0;
    }

    .message-header {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      font-size: 12px;
      margin-bottom: 4px;
      opacity: 0.7;
    }

    .message-text {
      word-break: break-word;
      line-height: 1.6;
    }

    /* Pasos intermedios */
    .steps-accordion {
      margin-bottom: 16px;
    }

    .steps-accordion mat-expansion-panel {
      margin-bottom: 8px !important;
      border-radius: 8px !important;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    }

    .steps-accordion mat-expansion-panel.step-running {
      border-left: 3px solid #2196f3;
      background: linear-gradient(90deg, rgba(33, 150, 243, 0.05) 0%, transparent 100%);
    }

    .steps-accordion mat-expansion-panel.step-completed {
      border-left: 3px solid #4caf50;
    }

    .steps-accordion mat-expansion-panel.step-failed {
      border-left: 3px solid #f44336;
    }

    .step-header {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .step-icon-completed { color: #4caf50; }
    .step-icon-failed { color: #f44336; }
    .step-icon-running { color: #2196f3; }

    .step-name {
      font-weight: 500;
      font-size: 14px;
    }

    .step-duration {
      font-size: 12px;
      color: #888;
      background: #f5f5f5;
      padding: 2px 8px;
      border-radius: 10px;
    }

    .step-running-label {
      font-size: 12px;
      color: #2196f3;
      font-style: italic;
    }

    .step-content {
      padding: 8px 0;
    }

    .step-conversation {
      margin-bottom: 12px;
      padding: 12px;
      background: #f8f9fa;
      border-radius: 8px;
      border-left: 3px solid #667eea;
    }

    .step-text {
      font-size: 13px;
      line-height: 1.6;
      color: #444;
    }

    .presentation-viewer {
      margin: 12px 0;
    }

    .step-data-details {
      margin-top: 12px;
    }

    .step-data-details summary {
      cursor: pointer;
      font-size: 12px;
      color: #666;
      padding: 4px 0;
    }

    .step-data {
      background: #1a1a2e;
      color: #a0f0a0;
      padding: 12px;
      border-radius: 8px;
      font-size: 11px;
      overflow-x: auto;
      max-height: 200px;
      margin-top: 8px;
    }

    /* Respuesta final */
    .final-response {
      background: #f8f9fa;
      border-radius: 12px;
      padding: 16px;
      border: 1px solid #e0e0e0;
    }

    .response-label {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      font-weight: 600;
      color: #667eea;
      margin-bottom: 12px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .markdown-content {
      line-height: 1.6;
    }

    .markdown-content ::ng-deep {
      p { margin: 0 0 12px; }
      p:last-child { margin-bottom: 0; }
      
      pre {
        background: #1a1a2e;
        color: #e0e0e0;
        padding: 12px;
        border-radius: 8px;
        overflow-x: auto;
      }
      
      code {
        background: rgba(0,0,0,0.1);
        padding: 2px 6px;
        border-radius: 4px;
      }
      
      table {
        border-collapse: collapse;
        width: 100%;
        margin: 12px 0;
      }
      
      th, td {
        border: 1px solid #ddd;
        padding: 8px 12px;
        text-align: left;
      }
      
      th {
        background: #f5f5f5;
        font-weight: 600;
      }
    }

    /* Imágenes y vídeos */
    .generated-images {
      margin-top: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .generated-image {
      max-width: 100%;
      height: auto;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .generated-videos {
      margin-top: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .generated-video {
      max-width: 100%;
      height: auto;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .video-info {
      display: flex;
      gap: 8px;
      font-size: 12px;
      color: #888;
      margin-top: 4px;
    }

    /* Cursor y tokens */
    .cursor-blink {
      animation: blink 1s infinite;
      color: #667eea;
      font-weight: bold;
    }

    @keyframes blink {
      0%, 50% { opacity: 1; }
      51%, 100% { opacity: 0; }
    }

    .token-count {
      display: block;
      font-size: 11px;
      color: #888;
      margin-top: 12px;
      text-align: right;
    }

    /* Typing indicator */
    .typing-indicator {
      display: flex;
      gap: 4px;
      padding: 8px 0;
    }

    .typing-indicator span {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #999;
      animation: typing 1.4s infinite ease-in-out both;
    }

    .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
    .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

    @keyframes typing {
      0%, 80%, 100% { transform: scale(0); }
      40% { transform: scale(1); }
    }

    .current-step {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: #666;
      margin-top: 8px;
    }

    /* Input area */
    .input-area {
      display: flex;
      gap: 12px;
      padding: 16px;
      border-top: 1px solid #eee;
      align-items: flex-end;
    }

    .message-input {
      flex: 1;
    }

    .message-input textarea {
      min-height: 40px;
      max-height: 120px;
      resize: none;
    }

    /* Actions */
    .chat-actions {
      display: flex;
      justify-content: flex-end;
      padding: 8px 16px;
      border-top: 1px solid #f0f0f0;
      background: #fafafa;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ChatComponent {
  @ViewChild('chatContainer') chatContainer!: ElementRef;

  // Inputs
  @Input() messages: Signal<ChatMessage[]> = signal([]);
  @Input() features: ChatFeatures = {
    intermediateSteps: false,
    images: true,
    videos: true,
    presentations: false,
    streaming: true,
    tokens: true,
    timestamps: false,
    clearButton: true,
    configPanel: false
  };
  @Input() isLoading: Signal<boolean> = signal(false);
  @Input() placeholder = 'Escribe un mensaje...';
  @Input() emptyMessage = 'Envía un mensaje para comenzar';
  @Input() currentStepName: Signal<string | null> = signal(null);

  // Outputs
  @Output() messageSent = new EventEmitter<string>();
  @Output() chatCleared = new EventEmitter<void>();
  @Output() presentationOpened = new EventEmitter<string>();

  // Internal state
  newMessageText = '';

  constructor(private sanitizer: DomSanitizer) {}

  sendMessage(): void {
    if (!this.newMessageText.trim() || this.isLoading()) return;
    
    const message = this.newMessageText.trim();
    this.newMessageText = '';
    this.messageSent.emit(message);
    this.scrollToBottom();
  }

  clearChat(): void {
    this.chatCleared.emit();
  }

  scrollToBottom(): void {
    setTimeout(() => {
      if (this.chatContainer) {
        const container = this.chatContainer.nativeElement.querySelector('.messages-area');
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      }
    }, 50);
  }

  formatTime(date: Date): string {
    return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
  }

  getDuration(start: Date, end: Date): string {
    const ms = end.getTime() - start.getTime();
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  }

  hasStreamingMessage(): boolean {
    const msgs = this.messages();
    return msgs.length > 0 && msgs[msgs.length - 1].role === 'assistant' && msgs[msgs.length - 1].isStreaming === true;
  }

  // Safe URL sanitization
  sanitizeImageUrl(img: ImageData): SafeUrl {
    if (img.url) {
      return this.sanitizer.bypassSecurityTrustUrl(img.url);
    } else if (img.base64) {
      return this.sanitizer.bypassSecurityTrustUrl(`data:${img.mimeType || 'image/png'};base64,${img.base64}`);
    }
    return '' as SafeUrl;
  }

  sanitizeVideoUrl(video: VideoData): SafeUrl {
    if (video.url) {
      return this.sanitizer.bypassSecurityTrustUrl(video.url);
    } else if (video.base64) {
      return this.sanitizer.bypassSecurityTrustUrl(`data:${video.mimeType || 'video/mp4'};base64,${video.base64}`);
    }
    return '' as SafeUrl;
  }

  openPresentation(html: string): void {
    this.presentationOpened.emit(html);
  }

  getPresentationHtml(msg: ChatMessage): string | null {
    if (!msg.intermediateSteps) return null;
    for (const step of msg.intermediateSteps) {
      if (step.data?.html) return step.data.html;
    }
    return null;
  }

  hasAdvancedData(step: IntermediateStep): boolean {
    if (!step.data) return false;
    const keys = Object.keys(step.data);
    return keys.length > 0 && !(keys.length === 1 && keys[0] === 'html');
  }

  getAdvancedData(step: IntermediateStep): any {
    if (!step.data) return null;
    const { html, ...rest } = step.data;
    return rest;
  }

  getStepIcon(stepName: string): string {
    const iconMap: Record<string, string> = {
      'input': 'input',
      'llm': 'psychology',
      'rag': 'search',
      'tool': 'build',
      'output': 'output',
      'synthesizer': 'merge_type',
      'adaptive_agent': 'smart_toy',
      'browser': 'web',
      'designer': 'palette',
      'researcher': 'search',
      'communication': 'campaign'
    };
    return iconMap[stepName?.toLowerCase()] || 'circle';
  }
}
