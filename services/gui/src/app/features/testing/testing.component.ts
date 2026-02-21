import { Component, OnInit, signal, ViewChild, ElementRef, inject } from '@angular/core';
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
import { StrapiService } from '../../core/services/config.service';
import { LlmProvider } from '../../core/models';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

// Chat unificado
import { ChatComponent, ChatMessage } from '../../shared/components/chat';
import { LlmSelectorComponent, LlmSelectionService } from '../../shared/components/llm-selector';

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
    ChatComponent,
    LlmSelectorComponent
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
            <!-- Selector LLM Unificado -->
            <app-llm-selector
              [(providerId)]="selectedProviderId"
              [(model)]="selectedModel"
              (selectionChange)="onLlmSelectionChange($event)"
              mode="standard">
            </app-llm-selector>

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
            @if (effectiveModel) {
              <mat-chip class="model-chip">{{ effectiveModel }}</mat-chip>
            }
            @if (useStreaming) {
              <mat-chip class="streaming-chip">
                <mat-icon>stream</mat-icon>
                Streaming
              </mat-chip>
            }
          </mat-card-header>
          
          <mat-card-content class="chat-content">
            <app-chat
              [messages]="messages"
              [features]="chatFeatures"
              [isLoading]="sending"
              [placeholder]="'Escribe un mensaje...'"
              [emptyMessage]="'Envía un mensaje para probar el LLM'"
              (messageSent)="onChatMessageSent($event)"
              (chatCleared)="clearChat()">
            </app-chat>
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

    /* Estilos para Markdown */
    /* Chat content - integración con ChatComponent */
    .chat-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      padding: 0 !important;
    }

    .chat-content ::ng-deep .chat-container {
      border-radius: 0;
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
  
  private llmSelectionService = inject(LlmSelectionService);
  
  // Usamos el servicio para providers y modelos
  providers = this.llmSelectionService.providers;
  availableModels = signal<string[]>([]);
  
  selectedProviderId: string | number | null = null;
  selectedModel: string = '';
  systemPrompt: string = '';
  useStreaming: boolean = true;
  
  messages = signal<ChatMessage[]>([]);
  newMessage: string = '';
  currentStreamingMessage = signal<ChatMessage | null>(null);
  
  testingConnection = signal(false);
  connectionStatus = signal<{ success: boolean; message: string } | null>(null);
  sending = signal(false);
  totalTokens = signal(0);

  // Features del chat unificado
  chatFeatures = {
    intermediateSteps: false,
    images: false,
    videos: false,
    presentations: false,
    streaming: true,
    tokens: false,  // Lo mostramos en el footer
    timestamps: true,
    clearButton: false,  // Lo manejamos en el footer
    configPanel: true
  };

  private readonly API_URL = environment.apiUrl;

  constructor(
    private strapiService: StrapiService,
    private http: HttpClient,
    private snackBar: MatSnackBar
  ) {}

  // Getter para obtener el proveedor seleccionado
  get selectedProvider(): LlmProvider | null | undefined {
    return this.llmSelectionService.getProviderById(this.selectedProviderId);
  }

  // Resuelve el modelo efectivo: el seleccionado explícitamente o el default del provider
  get effectiveModel(): string {
    return this.selectedModel || this.selectedProvider?.defaultModel || '';
  }

  ngOnInit(): void {
    // Cargar proveedores desde el servicio
    this.llmSelectionService.loadProviders().subscribe();
  }

  // Handler para el selector LLM unificado
  onLlmSelectionChange(event: any): void {
    this.selectedProviderId = event.providerId;
    this.selectedModel = event.model;
    
    if (event.provider) {
      this.connectionStatus.set(null);
      // Cargar modelos para este proveedor
      this.llmSelectionService.loadModels(event.provider).subscribe((models: string[]) => {
        this.availableModels.set(models);
      });
    }
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
    const model = this.effectiveModel;
    if (!this.newMessage.trim() || !this.selectedProvider || !model) return;

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
      await this.sendStreamingMessage(apiMessages, model);
    } else {
      this.sendNormalMessage(apiMessages, model);
    }
  }

  private async sendStreamingMessage(apiMessages: { role: string; content: string }[], model: string): Promise<void> {
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
          model,
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
                this.messages.update(msgs => {
                  const updated = [...msgs];
                  const last = updated[updated.length - 1];
                  if (last.role === 'assistant') {
                    updated[updated.length - 1] = { ...last, content: fullContent };
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
        const last = updated[updated.length - 1];
        if (last.role === 'assistant') {
          updated[updated.length - 1] = { ...last, isStreaming: false };
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

  private sendNormalMessage(apiMessages: { role: string; content: string }[], model: string): void {
    this.http.post<{ content: string; model: string; tokens_used?: number }>(
      `${this.API_URL}/llm/chat`,
      {
        provider_url: this.selectedProvider!.baseUrl,
        provider_type: this.selectedProvider!.type,
        api_key: this.selectedProvider!.apiKey,
        model,
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

  // Handler para mensajes del ChatComponent
  onChatMessageSent(message: string): void {
    this.newMessage = message;
    this.sendMessage();
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
