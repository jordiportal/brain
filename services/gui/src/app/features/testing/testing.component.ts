import { Component, OnInit, signal, ViewChild, ElementRef, Pipe, PipeTransform } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDividerModule } from '@angular/material/divider';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { StrapiService } from '../../core/services/strapi.service';
import { LlmProvider } from '../../core/models';
import { HttpClient } from '@angular/common/http';
import { marked } from 'marked';

// Configurar marked para highlight de código
marked.setOptions({
  breaks: true,
  gfm: true
});

interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

// Pipe para renderizar Markdown
@Pipe({
  name: 'markdown',
  standalone: true
})
export class MarkdownPipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {}

  transform(value: string): SafeHtml {
    if (!value) return '';
    const html = marked(value) as string;
    return this.sanitizer.bypassSecurityTrustHtml(html);
  }
}

@Component({
  selector: 'app-testing',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    MatFormFieldModule,
    MatSelectModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatSnackBarModule,
    MatDividerModule,
    MatSlideToggleModule,
    MarkdownPipe
  ],
  template: `
    <div class="testing-page">
      <div class="page-header">
        <div>
          <h1>Testing LLM</h1>
          <p class="subtitle">Prueba la conexión con los proveedores de LLM configurados</p>
        </div>
      </div>

      <div class="testing-layout">
        <!-- Panel de Configuración -->
        <mat-card class="config-panel">
          <mat-card-header>
            <mat-card-title>Configuración</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <!-- Selector de Proveedor -->
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Proveedor LLM</mat-label>
              <mat-select [(value)]="selectedProvider" (selectionChange)="onProviderChange()">
                @for (provider of providers(); track provider.id) {
                  <mat-option [value]="provider">
                    {{ provider.name }} ({{ provider.type }})
                  </mat-option>
                }
              </mat-select>
            </mat-form-field>

            @if (selectedProvider) {
              <div class="provider-info">
                <p><strong>URL:</strong> {{ selectedProvider.baseUrl }}</p>
                <p><strong>Tipo:</strong> {{ selectedProvider.type | uppercase }}</p>
              </div>

              <!-- Test Connection -->
              <button mat-stroked-button 
                      color="primary" 
                      class="full-width"
                      (click)="testConnection()"
                      [disabled]="testingConnection()">
                @if (testingConnection()) {
                  <mat-spinner diameter="20"></mat-spinner>
                } @else {
                  <mat-icon>wifi_tethering</mat-icon>
                }
                Probar Conexión
              </button>

              @if (connectionStatus()) {
                <div class="connection-status" [class]="connectionStatus()!.success ? 'success' : 'error'">
                  <mat-icon>{{ connectionStatus()!.success ? 'check_circle' : 'error' }}</mat-icon>
                  <span>{{ connectionStatus()!.message }}</span>
                </div>
              }

              <mat-divider></mat-divider>

              <!-- Selector de Modelo -->
              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Modelo</mat-label>
                <mat-select [(value)]="selectedModel">
                  @for (model of availableModels(); track model) {
                    <mat-option [value]="model">{{ model }}</mat-option>
                  }
                </mat-select>
              </mat-form-field>

              <!-- Streaming Toggle -->
              <mat-slide-toggle [(ngModel)]="useStreaming" color="primary">
                Streaming (respuesta en tiempo real)
              </mat-slide-toggle>

              <!-- System Prompt -->
              <mat-form-field appearance="outline" class="full-width">
                <mat-label>System Prompt (opcional)</mat-label>
                <textarea matInput 
                          [(ngModel)]="systemPrompt" 
                          rows="3"
                          placeholder="Eres un asistente útil..."></textarea>
              </mat-form-field>
            }
          </mat-card-content>
        </mat-card>

        <!-- Panel de Chat -->
        <mat-card class="chat-panel">
          <mat-card-header>
            <mat-card-title>
              <mat-icon>chat</mat-icon>
              Chat de Prueba
            </mat-card-title>
            @if (selectedModel) {
              <mat-chip class="model-chip">{{ selectedModel }}</mat-chip>
            }
            @if (useStreaming) {
              <mat-chip class="streaming-chip">
                <mat-icon>stream</mat-icon>
                Streaming
              </mat-chip>
            }
          </mat-card-header>
          
          <mat-card-content>
            <div class="chat-container" #chatContainer>
              @if (messages().length === 0) {
                <div class="empty-chat">
                  <mat-icon>forum</mat-icon>
                  <p>Envía un mensaje para probar el LLM</p>
                </div>
              }

              @for (message of messages(); track message.timestamp) {
                <div class="message" [class]="message.role">
                  <div class="message-avatar">
                    <mat-icon>{{ message.role === 'user' ? 'person' : 'smart_toy' }}</mat-icon>
                  </div>
                  <div class="message-content">
                    <div class="message-header">
                      <span class="message-role">{{ message.role === 'user' ? 'Tú' : 'Asistente' }}</span>
                      <span class="message-time">{{ formatTime(message.timestamp) }}</span>
                    </div>
                    @if (message.role === 'user') {
                      <div class="message-text">{{ message.content }}</div>
                    } @else {
                      <div class="message-text markdown-content" [innerHTML]="message.content | markdown"></div>
                      @if (message.isStreaming) {
                        <span class="cursor-blink">▊</span>
                      }
                    }
                  </div>
                </div>
              }

              @if (sending() && !currentStreamingMessage()) {
                <div class="message assistant">
                  <div class="message-avatar">
                    <mat-icon>smart_toy</mat-icon>
                  </div>
                  <div class="message-content">
                    <div class="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                </div>
              }
            </div>

            <!-- Input de mensaje -->
            <div class="chat-input">
              <mat-form-field appearance="outline" class="message-input">
                <input matInput 
                       [(ngModel)]="newMessage" 
                       placeholder="Escribe un mensaje..."
                       (keyup.enter)="sendMessage()"
                       [disabled]="sending() || !selectedProvider || !selectedModel">
              </mat-form-field>
              <button mat-fab 
                      color="primary" 
                      (click)="sendMessage()"
                      [disabled]="!newMessage.trim() || sending() || !selectedProvider || !selectedModel">
                @if (sending()) {
                  <mat-spinner diameter="24"></mat-spinner>
                } @else {
                  <mat-icon>send</mat-icon>
                }
              </button>
            </div>
          </mat-card-content>

          <mat-card-actions>
            <button mat-button color="warn" (click)="clearChat()" [disabled]="messages().length === 0">
              <mat-icon>delete_sweep</mat-icon>
              Limpiar Chat
            </button>
            @if (totalTokens() > 0) {
              <span class="token-count">Tokens: {{ totalTokens() }}</span>
            }
          </mat-card-actions>
        </mat-card>
      </div>
    </div>
  `,
  styles: [`
    .testing-page {
      max-width: 1400px;
      margin: 0 auto;
    }

    .page-header {
      margin-bottom: 24px;
    }

    h1 {
      margin: 0;
      font-size: 28px;
      font-weight: 600;
      color: #1a1a2e;
    }

    .subtitle {
      color: #666;
      margin: 4px 0 0;
    }

    .testing-layout {
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 24px;
      align-items: start;
    }

    .config-panel, .chat-panel {
      border-radius: 12px;
    }

    .config-panel mat-card-content {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .full-width {
      width: 100%;
    }

    .provider-info {
      background: #f5f5f5;
      padding: 12px;
      border-radius: 8px;
      font-size: 13px;
    }

    .provider-info p {
      margin: 4px 0;
    }

    .connection-status {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px;
      border-radius: 8px;
      font-size: 14px;
    }

    .connection-status.success {
      background: #e8f5e9;
      color: #2e7d32;
    }

    .connection-status.error {
      background: #ffebee;
      color: #c62828;
    }

    .chat-panel {
      display: flex;
      flex-direction: column;
      height: calc(100vh - 200px);
      min-height: 500px;
    }

    .chat-panel mat-card-header {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .chat-panel mat-card-title {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0;
    }

    .model-chip {
      margin-left: auto;
    }

    .streaming-chip {
      background: #e3f2fd !important;
      color: #1976d2 !important;
    }

    .streaming-chip mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
      margin-right: 4px;
    }

    .chat-panel mat-card-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .chat-container {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
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
    }

    .empty-chat mat-icon {
      font-size: 64px;
      width: 64px;
      height: 64px;
      margin-bottom: 16px;
    }

    .message {
      display: flex;
      gap: 12px;
      max-width: 85%;
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
      background: #3f51b5;
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
    }

    .message.user .message-content {
      background: #3f51b5;
      color: white;
      border-bottom-right-radius: 4px;
    }

    .message.assistant .message-content {
      border-bottom-left-radius: 4px;
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

    /* Estilos para Markdown */
    .markdown-content {
      ::ng-deep {
        p {
          margin: 0 0 12px;
          &:last-child { margin-bottom: 0; }
        }
        
        h1, h2, h3, h4, h5, h6 {
          margin: 16px 0 8px;
          font-weight: 600;
          &:first-child { margin-top: 0; }
        }
        
        h1 { font-size: 1.5em; }
        h2 { font-size: 1.3em; }
        h3 { font-size: 1.1em; }
        
        code {
          background: rgba(0,0,0,0.08);
          padding: 2px 6px;
          border-radius: 4px;
          font-family: 'Fira Code', 'Monaco', monospace;
          font-size: 0.9em;
        }
        
        pre {
          background: #1e1e1e;
          color: #d4d4d4;
          padding: 16px;
          border-radius: 8px;
          overflow-x: auto;
          margin: 12px 0;
          
          code {
            background: none;
            padding: 0;
            color: inherit;
          }
        }
        
        ul, ol {
          margin: 8px 0;
          padding-left: 24px;
        }
        
        li {
          margin: 4px 0;
        }
        
        blockquote {
          border-left: 4px solid #3f51b5;
          margin: 12px 0;
          padding: 8px 16px;
          background: rgba(63, 81, 181, 0.08);
          border-radius: 0 8px 8px 0;
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
        
        a {
          color: #3f51b5;
          text-decoration: none;
          &:hover { text-decoration: underline; }
        }
        
        hr {
          border: none;
          border-top: 1px solid #ddd;
          margin: 16px 0;
        }

        img {
          max-width: 100%;
          border-radius: 8px;
        }
      }
    }

    .cursor-blink {
      animation: blink 1s infinite;
      color: #3f51b5;
      font-weight: bold;
    }

    @keyframes blink {
      0%, 50% { opacity: 1; }
      51%, 100% { opacity: 0; }
    }

    .typing-indicator {
      display: flex;
      gap: 4px;
      padding: 8px 0;
    }

    .typing-indicator span {
      width: 8px;
      height: 8px;
      background: #999;
      border-radius: 50%;
      animation: typing 1.4s infinite ease-in-out;
    }

    .typing-indicator span:nth-child(2) {
      animation-delay: 0.2s;
    }

    .typing-indicator span:nth-child(3) {
      animation-delay: 0.4s;
    }

    @keyframes typing {
      0%, 60%, 100% {
        transform: translateY(0);
        opacity: 0.4;
      }
      30% {
        transform: translateY(-8px);
        opacity: 1;
      }
    }

    .chat-input {
      display: flex;
      gap: 12px;
      padding: 16px;
      border-top: 1px solid #eee;
    }

    .message-input {
      flex: 1;
    }

    .message-input ::ng-deep .mat-mdc-form-field-subscript-wrapper {
      display: none;
    }

    .token-count {
      margin-left: auto;
      font-size: 13px;
      color: #666;
    }

    @media (max-width: 900px) {
      .testing-layout {
        grid-template-columns: 1fr;
      }

      .chat-panel {
        height: auto;
        min-height: 400px;
      }
    }
  `]
})
export class TestingComponent implements OnInit {
  @ViewChild('chatContainer') chatContainer!: ElementRef;

  providers = signal<LlmProvider[]>([]);
  selectedProvider: LlmProvider | null = null;
  selectedModel: string = '';
  availableModels = signal<string[]>([]);
  systemPrompt: string = '';
  useStreaming: boolean = true;
  
  messages = signal<ChatMessage[]>([]);
  newMessage: string = '';
  currentStreamingMessage = signal<ChatMessage | null>(null);
  
  testingConnection = signal(false);
  connectionStatus = signal<{ success: boolean; message: string } | null>(null);
  sending = signal(false);
  totalTokens = signal(0);

  private readonly API_URL = 'http://localhost:8000/api/v1';

  constructor(
    private strapiService: StrapiService,
    private http: HttpClient,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadProviders();
  }

  loadProviders(): void {
    this.strapiService.getLlmProviders().subscribe({
      next: (providers) => {
        this.providers.set(providers.filter(p => p.isActive));
        if (providers.length > 0) {
          this.selectedProvider = providers[0];
          this.onProviderChange();
        }
      },
      error: () => this.snackBar.open('Error cargando proveedores', 'Cerrar', { duration: 3000 })
    });
  }

  onProviderChange(): void {
    if (this.selectedProvider) {
      this.selectedModel = this.selectedProvider.defaultModel || '';
      this.connectionStatus.set(null);
      this.loadModels();
    }
  }

  loadModels(): void {
    if (!this.selectedProvider) return;

    this.http.get<{ models: { name: string }[] }>(
      `${this.API_URL}/llm/models`,
      { params: { provider_url: this.selectedProvider.baseUrl } }
    ).subscribe({
      next: (response) => {
        const models = response.models.map(m => m.name);
        this.availableModels.set(models);
        if (models.length > 0 && !this.selectedModel) {
          this.selectedModel = models[0];
        }
      },
      error: () => {
        this.availableModels.set([]);
        if (this.selectedProvider?.defaultModel) {
          this.availableModels.set([this.selectedProvider.defaultModel]);
        }
      }
    });
  }

  testConnection(): void {
    if (!this.selectedProvider) return;

    this.testingConnection.set(true);
    this.connectionStatus.set(null);

    this.http.post<{ success: boolean; message: string; models?: string[] }>(
      `${this.API_URL}/llm/test-connection`,
      { 
        provider_url: this.selectedProvider.baseUrl,
        provider_type: this.selectedProvider.type,
        api_key: this.selectedProvider.apiKey
      }
    ).subscribe({
      next: (response) => {
        this.connectionStatus.set(response);
        if (response.success && response.models) {
          this.availableModels.set(response.models);
        }
        this.testingConnection.set(false);
      },
      error: (err) => {
        this.connectionStatus.set({
          success: false,
          message: err.error?.detail || 'Error de conexión'
        });
        this.testingConnection.set(false);
      }
    });
  }

  async sendMessage(): Promise<void> {
    if (!this.newMessage.trim() || !this.selectedProvider || !this.selectedModel) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: this.newMessage.trim(),
      timestamp: new Date()
    };

    this.messages.update(msgs => [...msgs, userMessage]);
    const messageContent = this.newMessage.trim();
    this.newMessage = '';
    this.sending.set(true);
    this.scrollToBottom();

    // Preparar mensajes para la API
    const apiMessages: { role: string; content: string }[] = [];
    
    if (this.systemPrompt.trim()) {
      apiMessages.push({ role: 'system', content: this.systemPrompt.trim() });
    }

    this.messages().forEach(msg => {
      apiMessages.push({ role: msg.role, content: msg.content });
    });

    if (this.useStreaming) {
      await this.sendStreamingMessage(apiMessages);
    } else {
      this.sendNormalMessage(apiMessages);
    }
  }

  private async sendStreamingMessage(apiMessages: { role: string; content: string }[]): Promise<void> {
    // Crear mensaje de asistente vacío para streaming
    const assistantMessage: ChatMessage = {
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true
    };

    this.messages.update(msgs => [...msgs, assistantMessage]);
    this.currentStreamingMessage.set(assistantMessage);
    this.scrollToBottom();

    try {
      const response = await fetch(`${this.API_URL}/llm/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          provider_url: this.selectedProvider!.baseUrl,
          provider_type: this.selectedProvider!.type,
          api_key: this.selectedProvider!.apiKey,
          model: this.selectedModel,
          messages: apiMessages
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No reader available');
      }

      let fullContent = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.content) {
                fullContent += data.content;
                // Actualizar el mensaje en el array
                this.messages.update(msgs => {
                  const updated = [...msgs];
                  const lastMsg = updated[updated.length - 1];
                  if (lastMsg.role === 'assistant') {
                    lastMsg.content = fullContent;
                  }
                  return updated;
                });
                this.scrollToBottom();
              }

              if (data.done) {
                this.totalTokens.update(t => t + (data.total_tokens || 0));
              }
            } catch (e) {
              // Ignorar errores de parsing
            }
          }
        }
      }

      // Finalizar streaming
      this.messages.update(msgs => {
        const updated = [...msgs];
        const lastMsg = updated[updated.length - 1];
        if (lastMsg.role === 'assistant') {
          lastMsg.isStreaming = false;
        }
        return updated;
      });

    } catch (error: any) {
      this.snackBar.open(
        error.message || 'Error al comunicarse con el LLM',
        'Cerrar',
        { duration: 5000 }
      );
      // Eliminar el mensaje vacío de error
      this.messages.update(msgs => msgs.filter(m => m.content !== '' || m.role !== 'assistant'));
    } finally {
      this.sending.set(false);
      this.currentStreamingMessage.set(null);
    }
  }

  private sendNormalMessage(apiMessages: { role: string; content: string }[]): void {
    this.http.post<{ content: string; model: string; tokens_used?: number }>(
      `${this.API_URL}/llm/chat`,
      {
        provider_url: this.selectedProvider!.baseUrl,
        provider_type: this.selectedProvider!.type,
        api_key: this.selectedProvider!.apiKey,
        model: this.selectedModel,
        messages: apiMessages
      }
    ).subscribe({
      next: (response) => {
        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: response.content,
          timestamp: new Date()
        };
        this.messages.update(msgs => [...msgs, assistantMessage]);
        this.totalTokens.update(t => t + (response.tokens_used || 0));
        this.sending.set(false);
        this.scrollToBottom();
      },
      error: (err) => {
        this.snackBar.open(
          err.error?.detail || 'Error al comunicarse con el LLM',
          'Cerrar',
          { duration: 5000 }
        );
        this.sending.set(false);
      }
    });
  }

  clearChat(): void {
    this.messages.set([]);
    this.totalTokens.set(0);
  }

  formatTime(date: Date): string {
    return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      if (this.chatContainer) {
        const container = this.chatContainer.nativeElement;
        container.scrollTop = container.scrollHeight;
      }
    }, 50);
  }
}
