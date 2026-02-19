import { Component, OnInit, signal, inject, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
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
import { MatExpansionModule } from '@angular/material/expansion';
import { DomSanitizer, SafeUrl } from '@angular/platform-browser';
import { ApiService } from '../../core/services/api.service';
import { StrapiService } from '../../core/services/config.service';
import { LlmProvider } from '../../core/models';
import { ChainEditorComponent } from './chain-editor/chain-editor.component';
import { BrowserViewerComponent } from '../../shared/components/browser-viewer/browser-viewer.component';
import { ArtifactSidebarComponent } from '../../shared/components/artifact-sidebar/artifact-sidebar.component';
import { environment } from '../../../environments/environment';

// Chat unificado
import { ChatComponent, ChatMessage, IntermediateStep } from '../../shared/components/chat';
import { SseStreamService } from '../../shared/services/sse-stream.service';

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
    MatExpansionModule,
    ChatComponent,
    ChainEditorComponent,
    BrowserViewerComponent,
    ArtifactSidebarComponent
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
                    <div class="chain-icon" [class]="chain.type" mat-card-avatar>
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
                  <!-- Selector de Proveedor -->
                  <mat-form-field appearance="outline" class="provider-select">
                    <mat-label>Proveedor</mat-label>
                    <mat-select [(ngModel)]="selectedProvider" (selectionChange)="onProviderChange()">
                      @for (provider of llmProviders(); track provider.id) {
                        <mat-option [value]="provider">
                          {{ provider.name }} ({{ provider.type }})
                        </mat-option>
                      }
                    </mat-select>
                  </mat-form-field>
                  
                  <!-- Selector de Modelo -->
                  <mat-form-field appearance="outline" class="model-select">
                    <mat-label>Modelo</mat-label>
                    <mat-select [(ngModel)]="llmModel" [disabled]="loadingModels()">
                      @if (loadingModels()) {
                        <mat-option disabled>Cargando modelos...</mat-option>
                      }
                      @for (model of availableModels(); track model) {
                        <mat-option [value]="model">{{ model }}</mat-option>
                      }
                    </mat-select>
                    @if (loadingModels()) {
                      <mat-spinner matSuffix diameter="20"></mat-spinner>
                    }
                  </mat-form-field>
                  
                  <mat-slide-toggle [(ngModel)]="useStreaming">
                    Streaming
                  </mat-slide-toggle>
                  <mat-slide-toggle [(ngModel)]="useMemory" [disabled]="!selectedChain()!.config.use_memory">
                    Usar Memoria
                  </mat-slide-toggle>
                </div>
              </div>

              <!-- Chat Area with Sidebar -->
              <div class="execution-content" [class.sidebar-collapsed]="!sidebarExpanded()">
                <div class="chat-wrapper">
                  <app-chat
                    [messages]="messages"
                    [features]="chatFeatures"
                    [isLoading]="isExecuting"
                    [placeholder]="'Escribe tu mensaje...'"
                    [emptyMessage]="'Selecciona una cadena y envía un mensaje para comenzar'"
                    [currentStepName]="currentStepName"
                    (messageSent)="onChatMessageSent($event)"
                    (presentationOpened)="openPresentation($event)">
                  </app-chat>

                  <!-- Browser Viewer - Solo para Browser Agent -->
                  @if (selectedChain()?.id === 'browser_agent') {
                    <app-browser-viewer 
                      [apiUrl]="apiBaseUrl"
                      [browserPort]="6080"
                      (connectionChange)="onBrowserConnectionChange($event)">
                    </app-browser-viewer>
                  }

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

                <!-- Artifact Sidebar -->
                <app-artifact-sidebar
                  [conversationId]="sessionId"
                  [isExpanded]="sidebarExpanded()"
                  (expandChanged)="sidebarExpanded.set($event)">
                </app-artifact-sidebar>
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
      display: flex;
      flex-direction: column;
      height: 100%;
    }

    .chain-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    }

    .chain-card.selected {
      border: 2px solid #667eea;
    }

    .chain-card mat-card-content {
      flex: 1 1 auto;
    }

    .chain-card mat-card-actions {
      margin-top: auto;
      padding-top: 16px;
      border-top: 1px solid #f0f0f0;
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
    .chain-icon.agent { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }

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

    .provider-select {
      min-width: 180px;
    }

    .model-select {
      min-width: 220px;
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
      max-width: 85%;
      min-width: 300px;
    }

    .message.user .message-content {
      background: #667eea;
      color: white;
      padding: 12px 16px;
      border-radius: 12px 12px 0 12px;
    }

    .message.assistant .message-content {
      background: transparent;
    }

    .message-content p {
      margin: 0;
    }

    /* Chat area - integración con ChatComponent */
    .chat-area {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      background: white;
      border-radius: 12px;
      min-height: 500px;
    }

    .chat-area ::ng-deep .chat-container {
      border-radius: 0;
      height: 100%;
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

    /* Execution Content Layout with Sidebar */
    .execution-content {
      display: flex;
      flex: 1;
      gap: 16px;
      overflow: hidden;
      min-height: 500px;
    }

    .chat-wrapper {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      min-width: 0;
      background: white;
      border-radius: 12px;
    }

    /* Artifact Sidebar */
    app-artifact-sidebar {
      flex-shrink: 0;
      height: 100%;
      max-height: calc(100vh - 280px);
      border-radius: 12px;
      overflow: hidden;
    }

    /* Collapsed state */
    .execution-content.sidebar-collapsed app-artifact-sidebar {
      width: 60px;
    }

    /* Responsive */
    @media (max-width: 1024px) {
      .execution-content {
        flex-direction: column;
      }
      
      app-artifact-sidebar {
        max-height: 300px;
        border-left: none;
        border-top: 1px solid #e0e0e0;
      }
    }
  `]
})
export class ChainsComponent implements OnInit {
  private http = inject(HttpClient);
  private apiService = inject(ApiService);
  private strapiService = inject(StrapiService);
  private snackBar = inject(MatSnackBar);
  private sanitizer = inject(DomSanitizer);
  private sseStream = inject(SseStreamService);

  @ViewChild(MatTabGroup) tabGroup!: MatTabGroup;
  @ViewChild('messagesContainer') messagesContainer!: ElementRef;

  engineChains = signal<EngineChain[]>([]);
  loading = signal(true);
  
  selectedChain = signal<EngineChain | null>(null);
  editingChainId = signal<string | null>(null);
  messages = signal<ChatMessage[]>([]);
  isExecuting = signal(false);
  currentStep = signal<ExecutionStep | null>(null);
  // currentAssistantMessage ya no se usa con el streaming unificado
  
  userInput = '';
  useStreaming = true;
  useMemory = true;
  sessionId = '';
  
  // Configuración de LLM
  llmProviders = signal<LlmProvider[]>([]);
  selectedProvider: LlmProvider | null = null;
  llmModel = '';
  availableModels = signal<string[]>([]);
  loadingModels = signal(false);

  // Browser viewer
  apiBaseUrl = environment.apiUrl;
  browserConnected = signal(false);

  // Artifact sidebar
  sidebarExpanded = signal(true);
  artifactRefreshTrigger = signal(0);

  // Chat unificado
  chatFeatures = {
    intermediateSteps: true,
    images: true,
    videos: true,
    presentations: true,
    streaming: true,
    tokens: true,
    timestamps: false,
    clearButton: true,
    configPanel: false
  };

  currentStepName = signal<string | null>(null);

  // activeSteps gestionado por SseStreamService

  ngOnInit(): void {
    this.loadChains();
    this.loadLlmProviders();
    this.sessionId = `session-${Date.now()}`;
  }
  
  onBrowserConnectionChange(connected: boolean): void {
    this.browserConnected.set(connected);
    if (connected) {
      console.log('Browser viewer connected');
    }
  }
  
  loadLlmProviders(): void {
    // Solo cargar la lista de proveedores disponibles
    // El proveedor específico se carga cuando se selecciona una cadena
    this.strapiService.getLlmProviders().subscribe({
      next: (providers) => {
        this.llmProviders.set(providers);
      },
      error: (err) => {
        console.error('Error cargando proveedores LLM:', err);
        this.snackBar.open('Error cargando proveedores LLM', 'Cerrar', { duration: 3000 });
      }
    });
  }
  
  onProviderChange(): void {
    if (this.selectedProvider) {
      this.loadModelsForProvider(this.selectedProvider);
    }
  }
  
  loadModelsForProvider(provider: LlmProvider, defaultModel?: string): void {
    this.loadingModels.set(true);
    this.availableModels.set([]);
    
    this.apiService.getLlmModels({
      providerUrl: provider.baseUrl,
      providerType: provider.type,
      apiKey: provider.apiKey
    }).subscribe({
      next: (response) => {
        const models = response.models?.map(m => m.name) || [];
        this.availableModels.set(models);
        
        // Usar el modelo especificado o el default del proveedor
        if (defaultModel && models.includes(defaultModel)) {
          this.llmModel = defaultModel;
        } else if (provider.defaultModel && models.includes(provider.defaultModel)) {
          this.llmModel = provider.defaultModel;
        } else if (models.length > 0) {
          this.llmModel = models[0];
        }
        
        this.loadingModels.set(false);
      },
      error: (err) => {
        console.error('Error cargando modelos:', err);
        this.loadingModels.set(false);
        
        // Fallback: usar modelo por defecto del proveedor
        if (provider.defaultModel) {
          this.availableModels.set([provider.defaultModel]);
          this.llmModel = provider.defaultModel;
        }
      }
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
    
    // Cargar proveedor LLM de la cadena
    this.loadChainLlmProvider(chain.id);
    
    setTimeout(() => {
      if (this.tabGroup) {
        this.tabGroup.selectedIndex = 2;
      }
    }, 0);
  }
  
  loadChainLlmProvider(chainId: string): void {
    // Obtener detalles de la cadena con su proveedor asociado
    this.http.get<any>(`${environment.apiUrl}/chains/${chainId}/details`).subscribe({
      next: (response) => {
        const provider = response.llm_provider;
        if (provider) {
          // Buscar el proveedor en la lista cargada
          const fullProvider = this.llmProviders().find(p => p.id === provider.id);
          if (fullProvider) {
            this.selectedProvider = fullProvider;
            this.llmModel = provider.defaultModel || fullProvider.defaultModel || '';
            // Cargar modelos disponibles del proveedor
            this.loadModelsForProvider(fullProvider, this.llmModel);
          }
        }
      },
      error: (err) => {
        console.error('Error cargando proveedor de la cadena:', err);
      }
    });
  }

  async executeChain(): Promise<void> {
    if (!this.selectedChain() || !this.userInput.trim()) return;

    const chain = this.selectedChain()!;
    const userMessage = this.userInput.trim();
    
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
      this.currentStepName.set(null);
    }
  }

  // Handler para mensajes del ChatComponent
  onChatMessageSent(message: string): void {
    this.userInput = message;
    this.executeChain();
  }

  private async executeWithStreaming(chainId: string, message: string): Promise<void> {
    const sessionId = this.useMemory ? this.sessionId : undefined;
    const url = `${environment.apiUrl}/chains/${chainId}/invoke/stream${sessionId ? `?session_id=${sessionId}` : ''}`;

    await this.sseStream.stream({
      url,
      payload: {
        input: { message },
        llm_provider_url: this.selectedProvider?.baseUrl || environment.ollamaDefaultUrl,
        llm_provider_type: this.selectedProvider?.type || 'ollama',
        api_key: this.selectedProvider?.apiKey,
        model: this.llmModel
      },
      messages: this.messages,
      finalResponseNodeIds: ['synthesizer', 'adaptive_agent'],
    });
    this.scrollToBottom();
  }

  private async executeWithoutStreaming(chainId: string, message: string): Promise<void> {
    const sessionId = this.useMemory ? this.sessionId : undefined;
    
    this.apiService.invokeChain(chainId, { 
      input: { message },
      llm_provider_url: this.selectedProvider?.baseUrl || environment.ollamaDefaultUrl,
      llm_provider_type: this.selectedProvider?.type || 'ollama',
      api_key: this.selectedProvider?.apiKey,
      model: this.llmModel
    }, sessionId).subscribe({
      next: (response) => {
        const content = response.output?.response || 'Sin respuesta';
        const steps: IntermediateStep[] = response.steps?.map((s: any, i: number) => {
          const step: IntermediateStep = {
            id: s.node_id || `step-${i}`,
            name: s.node_name || 'Paso',
            icon: this.getStepIconName(s.node_name),
            status: 'completed' as const,
            content: '',
            type: 'generic',
            data: s.output_data,
            startTime: new Date(s.started_at),
            endTime: new Date(s.completed_at),
          };
          step.content = this.buildStepContent(step);
          if (!step.content && s.output_data?.response) step.content = s.output_data.response;
          return step;
        }) || [];
        
        this.messages.update(msgs => [...msgs, {
          role: 'assistant',
          content,
          intermediateSteps: steps,
          tokens: response.total_tokens,
          isStreaming: false
        }]);
      },
      error: (err) => {
        console.error('Invoke error:', err);
        this.snackBar.open('Error en la ejecución', 'Cerrar', { duration: 3000 });
      }
    });
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      if (this.messagesContainer) {
        const container = this.messagesContainer.nativeElement;
        container.scrollTop = container.scrollHeight;
      }
    }, 50);
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
      custom: 'settings',
      agent: 'psychology'
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

  getStepIconName(nodeName: string): string {
    const name = (nodeName || '').toLowerCase();
    
    if (name.includes('planificador') || name.includes('planner')) return 'assignment';
    if (name.includes('pensando') || name.includes('think') || name.includes('reflexion')) return 'psychology';
    if (name.includes('actuando') || name.includes('act') || name.includes('delegando') || name.includes('delegate')) return 'bolt';
    if (name.includes('observando') || name.includes('observ')) return 'visibility';
    if (name.includes('sintetiz') || name.includes('synthes') || name.includes('respuesta final')) return 'auto_awesome';
    if (name.includes('sap')) return 'storage';
    if (name.includes('rag') || name.includes('búsqueda')) return 'search';
    if (name.includes('llm') || name.includes('generación')) return 'smart_toy';
    if (name.includes('consult') || name.includes('miembro') || name.includes('equipo')) return 'groups';
    if (name.includes('iteration')) return 'loop';
    
    return 'radio_button_checked';
  }

  getDuration(start: Date, end: Date): string {
    const ms = new Date(end).getTime() - new Date(start).getTime();
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  }

  /** Construye el contenido legible del paso (pensamiento, conversación, resultado) */
  private buildStepContent(step: IntermediateStep): string {
    const d = step.data || {};
    const parts: string[] = [];
    if (step.content) parts.push(step.content);
    if (d.thinking) parts.push('**Pensamiento:**\n' + d.thinking);
    if (d.observation) parts.push('**Observación:**\n' + d.observation);
    // Usar conversation (completo) si existe, sino result_preview (truncado)
    if (d.conversation) parts.push(d.conversation);
    else if (d.result_preview) parts.push('**Resultado:**\n' + d.result_preview);
    if (d.arguments && Object.keys(d.arguments).length > 0) {
      const args = typeof d.arguments === 'string' ? d.arguments : JSON.stringify(d.arguments, null, 2);
      parts.push('**Argumentos:**\n```json\n' + args + '\n```');
    }
    return parts.join('\n\n');
  }

  /** Contenido a mostrar en el paso (conversación/pensamiento visible) */
  getStepDisplayContent(step: IntermediateStep): string {
    return step.content || '';
  }

  /** Hay datos avanzados además del contenido principal (excluir html y conversation) */
  hasAdvancedData(step: IntermediateStep): boolean {
    const d = step.data || {};
    const keys = Object.keys(d).filter(k => !['html', 'conversation', 'thinking', 'result_preview'].includes(k));
    return keys.length > 0;
  }

  /** Datos para "Datos avanzados" (sin html/conversation que ya se muestran) */
  getAdvancedData(step: IntermediateStep): object {
    const d = step.data || {};
    const { html, conversation, thinking, result_preview, ...rest } = d;
    return Object.keys(rest).length ? rest : {};
  }

  /** Obtiene HTML de presentación de los pasos del mensaje (si existe) */
  getPresentationHtml(msg: ChatMessage): string | null {
    const html = msg.intermediateSteps?.find(s => s.data?.html)?.data?.html;
    return html || null;
  }

  /** Abre la presentación HTML en nueva pestaña */
  openPresentation(html: string): void {
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank', 'noopener');
  }

  /** Sanitiza una URL de imagen (HTTP o data URL) para uso seguro */
  sanitizeImageUrl(url: string | undefined, base64?: string, mimeType?: string): SafeUrl {
    // Si hay URL directa (puede ser HTTP o data URL)
    if (url) {
      if (url.startsWith('data:')) {
        return this.sanitizer.bypassSecurityTrustUrl(url);
      }
      return url;
    }
    // Si hay base64, construir data URL
    if (base64) {
      const dataUrl = `data:${mimeType || 'image/png'};base64,${base64}`;
      return this.sanitizer.bypassSecurityTrustUrl(dataUrl);
    }
    return '';
  }

  /** Sanitiza una URL de vídeo (HTTP o data URL) para uso seguro */
  sanitizeVideoUrl(url: string | undefined, base64?: string, mimeType?: string): SafeUrl {
    // Si hay URL directa (puede ser HTTP o data URL)
    if (url) {
      if (url.startsWith('data:')) {
        return this.sanitizer.bypassSecurityTrustUrl(url);
      }
      return url;
    }
    // Si hay base64, construir data URL
    if (base64) {
      const dataUrl = `data:${mimeType || 'video/mp4'};base64,${base64}`;
      return this.sanitizer.bypassSecurityTrustUrl(dataUrl);
    }
    return '';
  }
}
