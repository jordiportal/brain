import { Component, OnInit, signal, inject, Pipe, PipeTransform, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatTabsModule, MatTabGroup } from '@angular/material/tabs';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { ApiService } from '../../core/services/api.service';
import { StrapiService } from '../../core/services/strapi.service';
import { ChainEditorComponent } from './chain-editor/chain-editor.component';
import { marked } from 'marked';

// Configurar marked para evitar warnings
marked.setOptions({ async: false });

// Pipe para Markdown
@Pipe({ name: 'markdown', standalone: true })
export class MarkdownPipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {}
  transform(value: string): SafeHtml {
    if (!value) return '';
    const html = marked.parse(value, { async: false }) as string;
    return this.sanitizer.bypassSecurityTrustHtml(html);
  }
}

interface EngineChain {
  id: string;
  name: string;
  description: string;
  type: string;
  version: string;
  nodes: { id: string; name: string; type: string }[];
  config: { use_memory: boolean; temperature: number };
}

interface ExecutionStep {
  event_type: string;
  node_id?: string;
  node_name?: string;
  content?: string;
  data?: any;
}

@Component({
  selector: 'app-chains',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatMenuModule,
    MatProgressSpinnerModule,
    MatDividerModule,
    MatTooltipModule,
    MatTabsModule,
    MatInputModule,
    MatFormFieldModule,
    MatDialogModule,
    MatSnackBarModule,
    MatSelectModule,
    MatSlideToggleModule,
    MarkdownPipe,
    ChainEditorComponent
  ],
  template: `
    <div class="chains-page">
      <div class="page-header">
        <div>
          <h1>Cadenas de Pensamiento</h1>
          <p class="subtitle">Motor de ejecución de cadenas con LangGraph</p>
        </div>
      </div>

      <mat-tab-group>
        <!-- Tab de Cadenas Predefinidas -->
        <mat-tab label="Cadenas del Motor">
          @if (loading()) {
            <div class="loading-container">
              <mat-spinner diameter="48"></mat-spinner>
              <p>Cargando cadenas...</p>
            </div>
          } @else {
            <div class="chains-grid">
              @for (chain of engineChains(); track chain.id) {
                <mat-card class="chain-card" [class.selected]="selectedChain()?.id === chain.id">
                  <mat-card-header>
                    <div class="chain-icon" [class]="chain.type">
                      <mat-icon>{{ getChainIcon(chain.type) }}</mat-icon>
                    </div>
                    <mat-card-title>{{ chain.name }}</mat-card-title>
                    <mat-card-subtitle>{{ chain.type | uppercase }} - v{{ chain.version }}</mat-card-subtitle>
                  </mat-card-header>
                  
                  <mat-card-content>
                    <p class="description">{{ chain.description }}</p>
                    
                    <div class="chain-nodes">
                      <span class="nodes-label">Nodos:</span>
                      <div class="nodes-flow">
                        @for (node of chain.nodes; track node.id; let last = $last) {
                          <span class="node-chip" [class]="node.type">{{ node.name }}</span>
                          @if (!last) {
                            <mat-icon class="flow-arrow">arrow_forward</mat-icon>
                          }
                        }
                      </div>
                    </div>

                    <div class="chain-config">
                      <mat-chip-set>
                        <mat-chip>
                          <mat-icon>memory</mat-icon>
                          Memoria: {{ chain.config.use_memory ? 'Sí' : 'No' }}
                        </mat-chip>
                        <mat-chip>
                          <mat-icon>thermostat</mat-icon>
                          Temp: {{ chain.config.temperature }}
                        </mat-chip>
                      </mat-chip-set>
                    </div>
                  </mat-card-content>

                  <mat-card-actions align="end">
                    <button mat-button (click)="openEditor(chain)">
                      <mat-icon>edit</mat-icon>
                      Editar
                    </button>
                    <button mat-raised-button color="primary" (click)="openExecuteDialog(chain)">
                      <mat-icon>play_arrow</mat-icon>
                      Ejecutar
                    </button>
                  </mat-card-actions>
                </mat-card>
              } @empty {
                <div class="empty-state">
                  <mat-icon>account_tree</mat-icon>
                  <h3>No hay cadenas en el motor</h3>
                  <p>Verifica que la API esté activa</p>
                </div>
              }
            </div>
          }
        </mat-tab>

        <!-- Tab de Editor -->
        <mat-tab label="Editor de Cadena" [disabled]="!editingChainId()">
          @if (editingChainId()) {
            <app-chain-editor 
              [chainId]="editingChainId()!"
              (close)="closeEditor()"
              (saved)="onChainSaved()">
            </app-chain-editor>
          }
        </mat-tab>

        <!-- Tab de Ejecución -->
        <mat-tab label="Ejecutar Cadena" [disabled]="!selectedChain()">
          @if (selectedChain()) {
            <div class="execution-panel">
              <div class="execution-header">
                <div class="chain-info">
                  <div class="chain-icon" [class]="selectedChain()!.type">
                    <mat-icon>{{ getChainIcon(selectedChain()!.type) }}</mat-icon>
                  </div>
                  <div>
                    <h2>{{ selectedChain()!.name }}</h2>
                    <p>{{ selectedChain()!.description }}</p>
                  </div>
                </div>
                
                <div class="execution-options">
                  <mat-form-field appearance="outline" class="model-select">
                    <mat-label>Modelo</mat-label>
                    <mat-select [(ngModel)]="llmModel">
                      @for (model of availableModels; track model) {
                        <mat-option [value]="model">{{ model }}</mat-option>
                      }
                    </mat-select>
                  </mat-form-field>
                  <mat-slide-toggle [(ngModel)]="useStreaming">
                    Streaming
                  </mat-slide-toggle>
                  <mat-slide-toggle [(ngModel)]="useMemory" [disabled]="!selectedChain()!.config.use_memory">
                    Usar Memoria
                  </mat-slide-toggle>
                </div>
              </div>

              <!-- Chat Area -->
              <div class="chat-container">
                <div class="messages-area" #messagesContainer>
                  @for (msg of messages(); track $index) {
                    <div class="message" [class]="msg.role">
                      <div class="message-avatar">
                        <mat-icon>{{ msg.role === 'user' ? 'person' : 'smart_toy' }}</mat-icon>
                      </div>
                      <div class="message-content">
                        @if (msg.role === 'assistant') {
                          <div class="markdown-content" [innerHTML]="msg.content | markdown"></div>
                        } @else {
                          <p>{{ msg.content }}</p>
                        }
                        @if (msg.steps && msg.steps.length > 0) {
                          <div class="execution-trace">
                            <span class="trace-label">Trace:</span>
                            @for (step of msg.steps; track $index) {
                              <span class="step-chip" [class]="step.event_type">
                                <mat-icon>{{ getStepIcon(step.event_type) }}</mat-icon>
                                {{ step.node_name || step.event_type }}
                              </span>
                            }
                          </div>
                        }
                        @if (msg.tokens) {
                          <span class="token-count">{{ msg.tokens }} tokens</span>
                        }
                      </div>
                    </div>
                  }
                  
                  @if (isExecuting()) {
                    <div class="message assistant">
                      <div class="message-avatar">
                        <mat-icon>smart_toy</mat-icon>
                      </div>
                      <div class="message-content">
                        <div class="typing-indicator">
                          <span></span><span></span><span></span>
                        </div>
                        @if (currentStep()) {
                          <div class="current-step">
                            <mat-icon>{{ getStepIcon(currentStep()!.event_type) }}</mat-icon>
                            {{ currentStep()!.node_name || currentStep()!.event_type }}
                          </div>
                        }
                      </div>
                    </div>
                  }
                </div>

                <div class="input-area">
                  <mat-form-field appearance="outline" class="message-input">
                    <textarea matInput 
                              [(ngModel)]="userInput" 
                              placeholder="Escribe tu mensaje..."
                              (keydown.enter)="$event.preventDefault(); executeChain()"
                              [disabled]="isExecuting()">
                    </textarea>
                  </mat-form-field>
                  <button mat-fab color="primary" 
                          (click)="executeChain()" 
                          [disabled]="isExecuting() || !userInput.trim()">
                    @if (isExecuting()) {
                      <mat-spinner diameter="24" color="accent"></mat-spinner>
                    } @else {
                      <mat-icon>send</mat-icon>
                    }
                  </button>
                </div>

                @if (useMemory && sessionId) {
                  <div class="session-info">
                    <span>Sesión: {{ sessionId }}</span>
                    <button mat-button color="warn" (click)="clearMemory()">
                      <mat-icon>delete</mat-icon>
                      Limpiar memoria
                    </button>
                  </div>
                }
              </div>
            </div>
          }
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
  styles: [`
    .chains-page {
      max-width: 1400px;
      margin: 0 auto;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
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

    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 64px;
      color: #666;
    }

    .chains-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
      gap: 20px;
      padding: 24px 0;
    }

    .chain-card {
      border-radius: 12px;
      transition: transform 0.2s, box-shadow 0.2s;
      cursor: pointer;
    }

    .chain-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    }

    .chain-card.selected {
      border: 2px solid #667eea;
    }

    .chain-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 16px;
    }

    .chain-icon.conversational { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .chain-icon.tools { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .chain-icon.rag { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
    .chain-icon.custom { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }

    .chain-icon mat-icon {
      color: white;
      font-size: 24px;
    }

    .description {
      color: #666;
      font-size: 14px;
      margin: 16px 0;
    }

    .chain-nodes {
      margin: 16px 0;
    }

    .nodes-label {
      font-size: 12px;
      color: #888;
      display: block;
      margin-bottom: 8px;
    }

    .nodes-flow {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
    }

    .node-chip {
      padding: 4px 12px;
      border-radius: 16px;
      font-size: 12px;
      background: #e3e3e3;
    }

    .node-chip.input { background: #e3f2fd; color: #1976d2; }
    .node-chip.llm { background: #f3e5f5; color: #7b1fa2; }
    .node-chip.rag { background: #e8f5e9; color: #388e3c; }
    .node-chip.tool { background: #fff3e0; color: #f57c00; }
    .node-chip.output { background: #fce4ec; color: #c2185b; }

    .flow-arrow {
      font-size: 16px;
      width: 16px;
      height: 16px;
      color: #ccc;
    }

    .chain-config {
      margin-top: 16px;
    }

    .empty-state {
      grid-column: 1 / -1;
      text-align: center;
      padding: 64px;
      background: white;
      border-radius: 12px;
    }

    .empty-state mat-icon {
      font-size: 72px;
      width: 72px;
      height: 72px;
      color: #ccc;
    }

    /* Execution Panel */
    .execution-panel {
      padding: 24px 0;
    }

    .execution-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      padding: 16px;
      background: white;
      border-radius: 12px;
    }

    .chain-info {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .chain-info h2 {
      margin: 0;
    }

    .chain-info p {
      margin: 4px 0 0;
      color: #666;
    }

    .execution-options {
      display: flex;
      gap: 24px;
      align-items: center;
    }

    .model-select {
      min-width: 200px;
    }

    .chat-container {
      background: white;
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      height: calc(100vh - 400px);
      min-height: 500px;
    }

    .messages-area {
      flex: 1;
      overflow-y: auto;
      padding: 24px;
    }

    .message {
      display: flex;
      gap: 12px;
      margin-bottom: 16px;
    }

    .message.user {
      flex-direction: row-reverse;
    }

    .message-avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #e3e3e3;
      flex-shrink: 0;
    }

    .message.user .message-avatar {
      background: #667eea;
      color: white;
    }

    .message.assistant .message-avatar {
      background: #43e97b;
      color: white;
    }

    .message-content {
      max-width: 70%;
      padding: 12px 16px;
      border-radius: 12px;
      background: #f5f5f5;
    }

    .message.user .message-content {
      background: #667eea;
      color: white;
      border-radius: 12px 12px 0 12px;
    }

    .message.assistant .message-content {
      background: #f0f0f0;
      border-radius: 12px 12px 12px 0;
    }

    .message-content p {
      margin: 0;
    }

    .markdown-content {
      line-height: 1.6;
    }

    .markdown-content pre {
      background: #1a1a2e;
      color: #e0e0e0;
      padding: 12px;
      border-radius: 8px;
      overflow-x: auto;
    }

    .markdown-content code {
      background: rgba(0,0,0,0.1);
      padding: 2px 6px;
      border-radius: 4px;
    }

    .execution-trace {
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px solid #ddd;
    }

    .trace-label {
      font-size: 11px;
      color: #888;
      display: block;
      margin-bottom: 8px;
    }

    .step-chip {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 11px;
      margin-right: 8px;
      background: #e0e0e0;
    }

    .step-chip mat-icon {
      font-size: 14px;
      width: 14px;
      height: 14px;
    }

    .step-chip.node_start { background: #e3f2fd; color: #1976d2; }
    .step-chip.node_end { background: #e8f5e9; color: #388e3c; }
    .step-chip.token { background: #f3e5f5; color: #7b1fa2; }

    .token-count {
      display: block;
      font-size: 11px;
      color: #888;
      margin-top: 8px;
    }

    .typing-indicator {
      display: flex;
      gap: 4px;
      padding: 8px 0;
    }

    .typing-indicator span {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #667eea;
      animation: bounce 1.4s infinite ease-in-out both;
    }

    .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
    .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

    @keyframes bounce {
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
    }

    .session-info {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 16px;
      background: #f5f5f5;
      font-size: 12px;
      color: #666;
    }
  `]
})
export class ChainsComponent implements OnInit {
  private apiService = inject(ApiService);
  private strapiService = inject(StrapiService);
  private snackBar = inject(MatSnackBar);

  @ViewChild(MatTabGroup) tabGroup!: MatTabGroup;

  engineChains = signal<EngineChain[]>([]);
  loading = signal(true);
  
  selectedChain = signal<EngineChain | null>(null);
  editingChainId = signal<string | null>(null);
  messages = signal<{role: string; content: string; steps?: ExecutionStep[]; tokens?: number}[]>([]);
  isExecuting = signal(false);
  currentStep = signal<ExecutionStep | null>(null);
  
  userInput = '';
  useStreaming = true;
  useMemory = true;
  sessionId = '';
  
  // Configuración de LLM
  llmProviderUrl = 'http://192.168.7.101:11434';  // Por defecto
  llmModel = 'qwen3:8b';  // Por defecto
  availableModels: string[] = [];

  ngOnInit(): void {
    this.loadChains();
    this.loadLlmConfig();
    this.sessionId = `session-${Date.now()}`;
  }
  
  loadLlmConfig(): void {
    // Cargar configuración del provider activo desde Strapi
    this.strapiService.getLlmProviders().subscribe({
      next: (providers) => {
        // Buscar el provider activo
        const activeProvider = providers.find(p => p.isActive);
        if (activeProvider) {
          this.llmProviderUrl = activeProvider.baseUrl;
          this.llmModel = activeProvider.defaultModel || 'qwen3:8b';
        }
        this.loadModels();
      },
      error: () => {
        this.loadModels();  // Intentar cargar modelos con config por defecto
      }
    });
  }
  
  loadModels(): void {
    // Cargar modelos disponibles del provider
    fetch(`${this.llmProviderUrl}/api/tags`)
      .then(res => res.json())
      .then(data => {
        this.availableModels = data.models?.map((m: any) => m.name) || [];
      })
      .catch(() => {
        console.warn('No se pudieron cargar los modelos');
      });
  }

  loadChains(): void {
    this.loading.set(true);
    this.apiService.getChains().subscribe({
      next: (response) => {
        this.engineChains.set(response.chains || []);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Error loading chains:', err);
        this.loading.set(false);
        this.snackBar.open('Error al cargar cadenas', 'Cerrar', { duration: 3000 });
      }
    });
  }

  openEditor(chain: EngineChain): void {
    this.editingChainId.set(chain.id);
    // Switch to editor tab (index 1)
    setTimeout(() => {
      if (this.tabGroup) {
        this.tabGroup.selectedIndex = 1;
      }
    }, 0);
  }

  closeEditor(): void {
    this.editingChainId.set(null);
    if (this.tabGroup) {
      this.tabGroup.selectedIndex = 0;
    }
  }

  onChainSaved(): void {
    this.loadChains();
    this.snackBar.open('Cadena guardada', 'Cerrar', { duration: 2000 });
  }

  openExecuteDialog(chain: EngineChain): void {
    this.selectedChain.set(chain);
    this.messages.set([]);
    this.useMemory = chain.config.use_memory;
    // Switch to execute tab (index 2 now)
    setTimeout(() => {
      if (this.tabGroup) {
        this.tabGroup.selectedIndex = 2;
      }
    }, 0);
  }

  async executeChain(): Promise<void> {
    if (!this.selectedChain() || !this.userInput.trim()) return;

    const chain = this.selectedChain()!;
    const userMessage = this.userInput.trim();
    
    // Añadir mensaje del usuario
    this.messages.update(msgs => [...msgs, { role: 'user', content: userMessage }]);
    this.userInput = '';
    this.isExecuting.set(true);
    this.currentStep.set(null);

    try {
      if (this.useStreaming) {
        await this.executeWithStreaming(chain.id, userMessage);
      } else {
        await this.executeWithoutStreaming(chain.id, userMessage);
      }
    } catch (error) {
      console.error('Execution error:', error);
      this.snackBar.open('Error en la ejecución', 'Cerrar', { duration: 3000 });
    } finally {
      this.isExecuting.set(false);
      this.currentStep.set(null);
    }
  }

  private async executeWithStreaming(chainId: string, message: string): Promise<void> {
    const sessionId = this.useMemory ? this.sessionId : undefined;
    const url = `http://localhost:8000/api/v1/chains/${chainId}/invoke/stream${sessionId ? `?session_id=${sessionId}` : ''}`;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        input: { message },
        llm_provider_url: this.llmProviderUrl,
        model: this.llmModel
      })
    });

    if (!response.ok) throw new Error('Stream request failed');

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No reader available');

    const decoder = new TextDecoder();
    let fullContent = '';
    const steps: ExecutionStep[] = [];
    let tokens = 0;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            
            if (data.event_type === 'token' && data.content) {
              fullContent += data.content;
              // Actualizar mensaje en tiempo real
              this.updateOrAddAssistantMessage(fullContent, steps, tokens);
            } else if (data.event_type === 'node_start') {
              this.currentStep.set(data);
              steps.push(data);
            } else if (data.event_type === 'node_end') {
              if (data.data?.tokens) tokens = data.data.tokens;
              steps.push(data);
            } else if (data.event_type === 'end') {
              if (data.data?.output?.response) {
                fullContent = data.data.output.response;
              }
            }
          } catch (e) {
            // Ignore parse errors
          }
        }
      }
    }

    this.updateOrAddAssistantMessage(fullContent, steps, tokens);
  }

  private async executeWithoutStreaming(chainId: string, message: string): Promise<void> {
    const sessionId = this.useMemory ? this.sessionId : undefined;
    
    this.apiService.invokeChain(chainId, { 
      input: { message },
      llm_provider_url: this.llmProviderUrl,
      model: this.llmModel
    }, sessionId).subscribe({
      next: (response) => {
        const content = response.output?.response || 'Sin respuesta';
        const steps = response.steps?.map((s: any) => ({
          event_type: 'node_end',
          node_id: s.node_id,
          node_name: s.node_name
        })) || [];
        
        this.messages.update(msgs => [...msgs, {
          role: 'assistant',
          content,
          steps,
          tokens: response.total_tokens
        }]);
      },
      error: (err) => {
        console.error('Invoke error:', err);
        this.snackBar.open('Error en la ejecución', 'Cerrar', { duration: 3000 });
      }
    });
  }

  private updateOrAddAssistantMessage(content: string, steps: ExecutionStep[], tokens: number): void {
    this.messages.update(msgs => {
      const lastMsg = msgs[msgs.length - 1];
      if (lastMsg?.role === 'assistant') {
        return [
          ...msgs.slice(0, -1),
          { role: 'assistant', content, steps, tokens }
        ];
      }
      return [...msgs, { role: 'assistant', content, steps, tokens }];
    });
  }

  clearMemory(): void {
    if (!this.selectedChain()) return;
    
    this.apiService.clearChainMemory(this.selectedChain()!.id, this.sessionId).subscribe({
      next: () => {
        this.messages.set([]);
        this.sessionId = `session-${Date.now()}`;
        this.snackBar.open('Memoria limpiada', 'Cerrar', { duration: 2000 });
      },
      error: () => {
        this.snackBar.open('Error al limpiar memoria', 'Cerrar', { duration: 3000 });
      }
    });
  }

  getChainIcon(type: string): string {
    const icons: Record<string, string> = {
      conversational: 'chat',
      rag: 'search',
      tools: 'build',
      custom: 'settings'
    };
    return icons[type] || 'psychology';
  }

  getStepIcon(eventType: string): string {
    const icons: Record<string, string> = {
      node_start: 'play_circle',
      node_end: 'check_circle',
      token: 'text_fields',
      start: 'flag',
      end: 'sports_score',
      error: 'error'
    };
    return icons[eventType] || 'radio_button_checked';
  }
}
