import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatTabsModule } from '@angular/material/tabs';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatBadgeModule } from '@angular/material/badge';
import { MatListModule } from '@angular/material/list';
import { environment } from '../../../environments/environment';

interface Subagent {
  id: string;
  name: string;
  description: string;
  version: string;
  domain_tools: string[];
  status: string;
  icon: string;
}

interface SubagentTool {
  id: string;
  name: string;
  description: string;
  type: string;
  parameters: any;
}

interface SubagentConfig {
  enabled: boolean;
  default_provider?: string;
  default_model?: string;
  settings: Record<string, any>;
}

interface TestResult {
  agent_id: string;
  status: string;
  tools_count: number;
  tools_status: Array<{id: string; name: string; status: string}>;
  checks: Record<string, boolean>;
}

interface ExecuteResult {
  status: string;
  agent_id: string;
  result: {
    success: boolean;
    response: string;
    tools_used: string[];
    images: Array<{url?: string; base64?: string}>;
    error?: string;
    execution_time_ms: number;
  };
}

@Component({
  selector: 'app-subagents',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatDividerModule,
    MatTooltipModule,
    MatTabsModule,
    MatInputModule,
    MatFormFieldModule,
    MatSelectModule,
    MatExpansionModule,
    MatSnackBarModule,
    MatDialogModule,
    MatSlideToggleModule,
    MatBadgeModule,
    MatListModule
  ],
  template: `
    <div class="subagents-page">
      <div class="page-header">
        <div>
          <h1>Subagentes Especializados</h1>
          <p class="subtitle">Agentes de dominio para tareas específicas</p>
        </div>
        <button mat-raised-button color="primary" (click)="loadSubagents()" [disabled]="loading()">
          @if (loading()) {
            <mat-spinner diameter="20"></mat-spinner>
          } @else {
            <mat-icon>refresh</mat-icon>
          }
          Actualizar
        </button>
      </div>

      <!-- Grid de Subagentes -->
      @if (loading()) {
        <div class="loading-container">
          <mat-spinner diameter="48"></mat-spinner>
          <p>Cargando subagentes...</p>
        </div>
      } @else {
        <div class="subagents-grid">
          @for (agent of subagents(); track agent.id) {
            <mat-card class="subagent-card" [class.selected]="selectedAgent?.id === agent.id">
              <mat-card-header>
                <div class="agent-icon" [class]="agent.id">
                  <mat-icon>{{ agent.icon }}</mat-icon>
                </div>
                <mat-card-title>{{ agent.name }}</mat-card-title>
                <mat-card-subtitle>v{{ agent.version }}</mat-card-subtitle>
                <mat-chip class="status-chip" [class]="agent.status">
                  {{ agent.status | uppercase }}
                </mat-chip>
              </mat-card-header>
              
              <mat-card-content>
                <p class="description">{{ agent.description }}</p>
                
                <div class="tools-section">
                  <span class="tools-label">Herramientas:</span>
                  <div class="tools-chips">
                    @for (tool of agent.domain_tools; track tool) {
                      <mat-chip class="tool-chip">{{ tool }}</mat-chip>
                    }
                  </div>
                </div>
              </mat-card-content>

              <mat-card-actions align="end">
                <button mat-button (click)="testAgent(agent.id)" [disabled]="testingAgent() === agent.id">
                  @if (testingAgent() === agent.id) {
                    <mat-spinner diameter="16"></mat-spinner>
                  } @else {
                    <mat-icon>health_and_safety</mat-icon>
                  }
                  Test
                </button>
                <button mat-button color="primary" (click)="selectAgent(agent)">
                  <mat-icon>settings</mat-icon>
                  Configurar
                </button>
                <button mat-raised-button color="accent" (click)="openExecutePanel(agent)">
                  <mat-icon>play_arrow</mat-icon>
                  Ejecutar
                </button>
              </mat-card-actions>
            </mat-card>
          } @empty {
            <div class="empty-state">
              <mat-icon>smart_toy</mat-icon>
              <h3>No hay subagentes registrados</h3>
              <p>Los subagentes se registran automáticamente al iniciar la API</p>
              <button mat-raised-button color="primary" (click)="loadSubagents()">
                <mat-icon>refresh</mat-icon>
                Recargar
              </button>
            </div>
          }
        </div>

        <!-- Panel de Detalles/Configuración -->
        @if (selectedAgent) {
          <mat-card class="detail-panel">
            <mat-card-header>
              <mat-card-title>
                <mat-icon>{{ selectedAgent.icon }}</mat-icon>
                {{ selectedAgent.name }}
              </mat-card-title>
              <button mat-icon-button (click)="selectedAgent = null" class="close-btn">
                <mat-icon>close</mat-icon>
              </button>
            </mat-card-header>

            <mat-tab-group>
              <!-- Tab de Información -->
              <mat-tab label="Información">
                <div class="tab-content">
                  <div class="info-section">
                    <h3>Descripción</h3>
                    <p>{{ selectedAgent.description }}</p>
                  </div>

                  <div class="info-section">
                    <h3>Herramientas Disponibles</h3>
                    @if (loadingTools()) {
                      <mat-spinner diameter="24"></mat-spinner>
                    } @else {
                      <mat-list>
                        @for (tool of agentTools(); track tool.id) {
                          <mat-list-item>
                            <mat-icon matListItemIcon>build</mat-icon>
                            <div matListItemTitle>{{ tool.name }}</div>
                            <div matListItemLine>{{ tool.description }}</div>
                          </mat-list-item>
                        }
                      </mat-list>
                    }
                  </div>
                </div>
              </mat-tab>

              <!-- Tab de Configuración -->
              <mat-tab label="Configuración">
                <div class="tab-content">
                  @if (loadingConfig()) {
                    <div class="loading-container">
                      <mat-spinner diameter="32"></mat-spinner>
                    </div>
                  } @else {
                    <div class="config-form">
                      <mat-slide-toggle [(ngModel)]="agentConfig.enabled" color="primary">
                        Subagente habilitado
                      </mat-slide-toggle>

                      @if (selectedAgent.id === 'media_agent') {
                        <mat-form-field appearance="outline" class="full-width">
                          <mat-label>Proveedor por defecto</mat-label>
                          <mat-select [(ngModel)]="agentConfig.default_provider">
                            <mat-option value="openai">OpenAI (DALL-E)</mat-option>
                            <mat-option value="replicate">Replicate (Flux/SD)</mat-option>
                          </mat-select>
                        </mat-form-field>

                        <mat-form-field appearance="outline" class="full-width">
                          <mat-label>Modelo por defecto</mat-label>
                          <mat-select [(ngModel)]="agentConfig.default_model">
                            <mat-option value="dall-e-3">DALL-E 3</mat-option>
                            <mat-option value="dall-e-2">DALL-E 2</mat-option>
                            <mat-option value="flux-schnell">Flux Schnell</mat-option>
                          </mat-select>
                        </mat-form-field>

                        <mat-form-field appearance="outline" class="full-width">
                          <mat-label>Tamaño por defecto</mat-label>
                          <mat-select [(ngModel)]="agentConfig.settings['default_size']">
                            <mat-option value="1024x1024">1024x1024 (Cuadrado)</mat-option>
                            <mat-option value="1792x1024">1792x1024 (Paisaje)</mat-option>
                            <mat-option value="1024x1792">1024x1792 (Retrato)</mat-option>
                          </mat-select>
                        </mat-form-field>
                      }

                      <div class="config-actions">
                        <button mat-raised-button color="primary" (click)="saveConfig()" [disabled]="savingConfig()">
                          @if (savingConfig()) {
                            <mat-spinner diameter="20"></mat-spinner>
                          } @else {
                            <mat-icon>save</mat-icon>
                          }
                          Guardar Configuración
                        </button>
                      </div>
                    </div>
                  }
                </div>
              </mat-tab>

              <!-- Tab de Test -->
              <mat-tab label="Estado">
                <div class="tab-content">
                  @if (testResult()) {
                    <div class="test-result" [class]="testResult()!.status">
                      <div class="result-header">
                        <mat-icon>{{ testResult()!.status === 'healthy' ? 'check_circle' : 'warning' }}</mat-icon>
                        <span>{{ testResult()!.status | uppercase }}</span>
                      </div>

                      <div class="checks-grid">
                        @for (check of getChecks(); track check.key) {
                          <div class="check-item" [class.passed]="check.value">
                            <mat-icon>{{ check.value ? 'check' : 'close' }}</mat-icon>
                            <span>{{ check.label }}</span>
                          </div>
                        }
                      </div>

                      <h4>Estado de Herramientas</h4>
                      <mat-list dense>
                        @for (tool of testResult()!.tools_status; track tool.id) {
                          <mat-list-item>
                            <mat-icon matListItemIcon [class]="tool.status">
                              {{ tool.status === 'ok' ? 'check_circle' : 'error' }}
                            </mat-icon>
                            <span matListItemTitle>{{ tool.name }}</span>
                          </mat-list-item>
                        }
                      </mat-list>
                    </div>
                  } @else {
                    <div class="empty-test">
                      <mat-icon>health_and_safety</mat-icon>
                      <p>Ejecuta un test para ver el estado del subagente</p>
                      <button mat-raised-button color="primary" (click)="testAgent(selectedAgent.id)">
                        <mat-icon>play_arrow</mat-icon>
                        Ejecutar Test
                      </button>
                    </div>
                  }
                </div>
              </mat-tab>
            </mat-tab-group>
          </mat-card>
        }

        <!-- Panel de Ejecución -->
        @if (executeAgent) {
          <mat-card class="execute-panel">
            <mat-card-header>
              <mat-card-title>
                <mat-icon>play_circle</mat-icon>
                Ejecutar {{ executeAgent.name }}
              </mat-card-title>
              <button mat-icon-button (click)="executeAgent = null" class="close-btn">
                <mat-icon>close</mat-icon>
              </button>
            </mat-card-header>

            <mat-card-content>
              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Tarea a ejecutar</mat-label>
                <textarea matInput [(ngModel)]="executeTask" rows="3" 
                          placeholder="Ej: Genera una imagen de un gato astronauta"></textarea>
              </mat-form-field>

              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Contexto adicional (opcional)</mat-label>
                <textarea matInput [(ngModel)]="executeContext" rows="2"></textarea>
              </mat-form-field>

              <div class="execute-options">
                <mat-form-field appearance="outline">
                  <mat-label>LLM URL</mat-label>
                  <input matInput [(ngModel)]="executeLlmUrl" placeholder="http://192.168.7.101:11434">
                </mat-form-field>

                <mat-form-field appearance="outline">
                  <mat-label>Modelo</mat-label>
                  <input matInput [(ngModel)]="executeModel" placeholder="gpt-oss:120b">
                </mat-form-field>
              </div>
            </mat-card-content>

            <mat-card-actions>
              <button mat-raised-button color="primary" (click)="executeSubagent()" [disabled]="executing()">
                @if (executing()) {
                  <mat-spinner diameter="20"></mat-spinner>
                  Ejecutando...
                } @else {
                  <mat-icon>play_arrow</mat-icon>
                  Ejecutar
                }
              </button>
            </mat-card-actions>

            @if (executeResult()) {
              <mat-divider></mat-divider>
              <div class="execute-result" [class]="executeResult()!.result.success ? 'success' : 'error'">
                <div class="result-header">
                  <mat-icon>{{ executeResult()!.result.success ? 'check_circle' : 'error' }}</mat-icon>
                  <span>{{ executeResult()!.result.success ? 'Éxito' : 'Error' }}</span>
                  <span class="time">{{ executeResult()!.result.execution_time_ms }}ms</span>
                </div>

                <div class="result-content">
                  <p class="response">{{ executeResult()!.result.response }}</p>

                  @if (executeResult()!.result.images?.length) {
                    <div class="images-grid">
                      @for (img of executeResult()!.result.images; track $index) {
                        <div class="image-item">
                          @if (img.url) {
                            <img [src]="img.url" alt="Generated image">
                          }
                        </div>
                      }
                    </div>
                  }

                  @if (executeResult()!.result.tools_used?.length) {
                    <div class="tools-used">
                      <span>Tools usadas:</span>
                      @for (tool of executeResult()!.result.tools_used; track tool) {
                        <mat-chip>{{ tool }}</mat-chip>
                      }
                    </div>
                  }
                </div>
              </div>
            }
          </mat-card>
        }
      }
    </div>
  `,
  styles: [`
    .subagents-page {
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

    /* Subagents Grid */
    .subagents-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
      gap: 20px;
      margin-bottom: 24px;
    }

    .subagent-card {
      border-radius: 12px;
      transition: transform 0.2s, box-shadow 0.2s;
    }

    .subagent-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    }

    .subagent-card.selected {
      border: 2px solid #667eea;
    }

    .agent-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 16px;
    }

    .agent-icon mat-icon {
      color: white;
      font-size: 24px;
    }

    .agent-icon.media_agent {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }

    .agent-icon.sap_agent {
      background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }

    .agent-icon.mail_agent {
      background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }

    .agent-icon.office_agent {
      background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
    }

    .status-chip {
      margin-left: auto !important;
      font-size: 10px !important;
    }

    .status-chip.active {
      background: #e8f5e9 !important;
      color: #388e3c !important;
    }

    .status-chip.inactive {
      background: #ffebee !important;
      color: #d32f2f !important;
    }

    .description {
      color: #666;
      font-size: 14px;
      margin-bottom: 16px;
    }

    .tools-section {
      margin-top: 12px;
    }

    .tools-label {
      font-size: 12px;
      color: #888;
      display: block;
      margin-bottom: 8px;
    }

    .tools-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .tool-chip {
      font-size: 11px !important;
      min-height: 24px !important;
      background: #f5f5f5 !important;
    }

    /* Detail Panel */
    .detail-panel {
      margin-top: 24px;
      border-radius: 12px;
    }

    .detail-panel mat-card-header {
      display: flex;
      align-items: center;
    }

    .detail-panel mat-card-title {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .close-btn {
      margin-left: auto !important;
    }

    .tab-content {
      padding: 24px;
    }

    .info-section {
      margin-bottom: 24px;
    }

    .info-section h3 {
      font-size: 16px;
      font-weight: 500;
      margin-bottom: 12px;
      color: #333;
    }

    /* Config Form */
    .config-form {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .full-width {
      width: 100%;
    }

    .config-actions {
      margin-top: 16px;
    }

    /* Test Result */
    .test-result {
      padding: 16px;
      border-radius: 8px;
    }

    .test-result.healthy {
      background: #e8f5e9;
    }

    .test-result.degraded {
      background: #fff3e0;
    }

    .result-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 500;
      margin-bottom: 16px;
    }

    .test-result.healthy .result-header mat-icon {
      color: #388e3c;
    }

    .test-result.degraded .result-header mat-icon {
      color: #f57c00;
    }

    .checks-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      margin-bottom: 16px;
    }

    .check-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px;
      border-radius: 4px;
      background: white;
    }

    .check-item.passed mat-icon {
      color: #388e3c;
    }

    .check-item:not(.passed) mat-icon {
      color: #d32f2f;
    }

    mat-icon.ok {
      color: #388e3c;
    }

    mat-icon.missing_handler {
      color: #d32f2f;
    }

    .empty-test {
      text-align: center;
      padding: 32px;
      color: #666;
    }

    .empty-test mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: #ccc;
    }

    /* Execute Panel */
    .execute-panel {
      margin-top: 24px;
      border-radius: 12px;
    }

    .execute-options {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    .execute-result {
      padding: 16px;
      border-radius: 8px;
      margin: 16px;
    }

    .execute-result.success {
      background: #e8f5e9;
    }

    .execute-result.error {
      background: #ffebee;
    }

    .execute-result .result-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
    }

    .execute-result.success .result-header mat-icon {
      color: #388e3c;
    }

    .execute-result.error .result-header mat-icon {
      color: #d32f2f;
    }

    .time {
      margin-left: auto;
      color: #888;
      font-size: 12px;
    }

    .response {
      white-space: pre-wrap;
      font-size: 14px;
      line-height: 1.6;
    }

    .images-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 16px;
      margin-top: 16px;
    }

    .image-item img {
      width: 100%;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .tools-used {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 12px;
      font-size: 13px;
      color: #666;
    }

    /* Empty State */
    .empty-state {
      text-align: center;
      padding: 64px;
      background: white;
      border-radius: 12px;
      grid-column: 1 / -1;
    }

    .empty-state mat-icon {
      font-size: 72px;
      width: 72px;
      height: 72px;
      color: #ccc;
    }
  `]
})
export class SubagentsComponent implements OnInit {
  private http = inject(HttpClient);
  private snackBar = inject(MatSnackBar);

  subagents = signal<Subagent[]>([]);
  agentTools = signal<SubagentTool[]>([]);
  testResult = signal<TestResult | null>(null);
  executeResult = signal<ExecuteResult | null>(null);

  loading = signal(true);
  loadingTools = signal(false);
  loadingConfig = signal(false);
  savingConfig = signal(false);
  testingAgent = signal<string | null>(null);
  executing = signal(false);

  selectedAgent: Subagent | null = null;
  executeAgent: Subagent | null = null;

  agentConfig: SubagentConfig = {
    enabled: true,
    settings: {}
  };

  // Execute form
  executeTask = '';
  executeContext = '';
  executeLlmUrl = 'http://192.168.7.101:11434';
  executeModel = 'gpt-oss:120b';

  ngOnInit(): void {
    this.loadSubagents();
  }

  loadSubagents(): void {
    this.loading.set(true);
    this.http.get<any>(`${environment.apiUrl}/subagents`)
      .subscribe({
        next: (response) => {
          this.subagents.set(response.subagents || []);
          this.loading.set(false);
        },
        error: (err) => {
          console.error('Error loading subagents:', err);
          this.snackBar.open('Error cargando subagentes', 'Cerrar', { duration: 3000 });
          this.loading.set(false);
        }
      });
  }

  selectAgent(agent: Subagent): void {
    this.selectedAgent = agent;
    this.testResult.set(null);
    this.loadAgentTools(agent.id);
    this.loadAgentConfig(agent.id);
  }

  loadAgentTools(agentId: string): void {
    this.loadingTools.set(true);
    this.http.get<any>(`${environment.apiUrl}/subagents/${agentId}/tools`)
      .subscribe({
        next: (response) => {
          this.agentTools.set(response.tools || []);
          this.loadingTools.set(false);
        },
        error: (err) => {
          console.error('Error loading tools:', err);
          this.loadingTools.set(false);
        }
      });
  }

  loadAgentConfig(agentId: string): void {
    this.loadingConfig.set(true);
    this.http.get<any>(`${environment.apiUrl}/subagents/${agentId}/config`)
      .subscribe({
        next: (response) => {
          this.agentConfig = response.config || { enabled: true, settings: {} };
          this.loadingConfig.set(false);
        },
        error: (err) => {
          console.error('Error loading config:', err);
          this.loadingConfig.set(false);
        }
      });
  }

  saveConfig(): void {
    if (!this.selectedAgent) return;

    this.savingConfig.set(true);
    this.http.put<any>(`${environment.apiUrl}/subagents/${this.selectedAgent.id}/config`, this.agentConfig)
      .subscribe({
        next: () => {
          this.snackBar.open('Configuración guardada', 'Cerrar', { duration: 3000 });
          this.savingConfig.set(false);
        },
        error: (err) => {
          this.snackBar.open('Error guardando configuración', 'Cerrar', { duration: 3000 });
          this.savingConfig.set(false);
        }
      });
  }

  testAgent(agentId: string): void {
    this.testingAgent.set(agentId);
    this.http.post<TestResult>(`${environment.apiUrl}/subagents/${agentId}/test`, {})
      .subscribe({
        next: (result) => {
          this.testResult.set(result);
          this.testingAgent.set(null);
          
          const status = result.status === 'healthy' ? 'OK' : 'Degradado';
          this.snackBar.open(`Test completado: ${status}`, 'Cerrar', { duration: 3000 });
        },
        error: (err) => {
          this.snackBar.open('Error ejecutando test', 'Cerrar', { duration: 3000 });
          this.testingAgent.set(null);
        }
      });
  }

  openExecutePanel(agent: Subagent): void {
    this.executeAgent = agent;
    this.executeResult.set(null);
    this.executeTask = '';
    this.executeContext = '';
  }

  executeSubagent(): void {
    if (!this.executeAgent || !this.executeTask.trim()) {
      this.snackBar.open('Ingresa una tarea', 'Cerrar', { duration: 3000 });
      return;
    }

    this.executing.set(true);
    this.executeResult.set(null);

    this.http.post<ExecuteResult>(`${environment.apiUrl}/subagents/${this.executeAgent.id}/execute`, {
      task: this.executeTask,
      context: this.executeContext || null,
      llm_url: this.executeLlmUrl,
      model: this.executeModel,
      provider_type: 'ollama'
    }).subscribe({
      next: (result) => {
        this.executeResult.set(result);
        this.executing.set(false);
        
        if (result.result.success) {
          this.snackBar.open('Ejecución completada', 'Cerrar', { duration: 3000 });
        } else {
          this.snackBar.open('Error en la ejecución', 'Cerrar', { duration: 3000 });
        }
      },
      error: (err) => {
        this.snackBar.open('Error ejecutando subagente', 'Cerrar', { duration: 3000 });
        this.executing.set(false);
      }
    });
  }

  getChecks(): Array<{key: string; label: string; value: boolean}> {
    const result = this.testResult();
    if (!result?.checks) return [];

    const labels: Record<string, string> = {
      registered: 'Registrado',
      has_tools: 'Tiene herramientas',
      all_handlers_present: 'Handlers OK'
    };

    return Object.entries(result.checks).map(([key, value]) => ({
      key,
      label: labels[key] || key,
      value
    }));
  }
}
