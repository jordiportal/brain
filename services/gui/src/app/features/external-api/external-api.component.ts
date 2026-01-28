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
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatTableModule } from '@angular/material/table';
import { MatMenuModule } from '@angular/material/menu';
import { Clipboard } from '@angular/cdk/clipboard';
import { environment } from '../../../environments/environment';

interface ApiKey {
  id: number;
  name: string;
  key: string;
  keyPrefix: string;
  isActive: boolean;
  permissions: {
    models: string[];
    maxTokensPerRequest: number;
    rateLimit: number;
  };
  usageStats: {
    totalRequests: number;
    totalTokens: number;
    lastUsed: string | null;
  };
  expiresAt: string | null;
  createdAt: string;
  notes: string;
}

interface BrainModel {
  id: string;
  name: string;
  description: string;
  chainId: string;
  maxTokens: number;
  supportsStreaming: boolean;
  supportsTools: boolean;
}

interface ApiConfig {
  isEnabled: boolean;
  baseUrl: string;
  defaultModel: string;
  availableModels: BrainModel[];
  backendLlm: {
    provider: string;
    url: string;
    model: string;
  };
  rateLimits: {
    requestsPerMinute: number;
    tokensPerMinute: number;
  };
}

@Component({
  selector: 'app-external-api',
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
    MatSnackBarModule,
    MatDialogModule,
    MatSlideToggleModule,
    MatTableModule,
    MatMenuModule
  ],
  template: `
    <div class="external-api-page">
      <div class="page-header">
        <div>
          <h1>API Externa</h1>
          <p class="subtitle">Endpoint OpenAI-compatible para clientes externos</p>
        </div>
        <div class="header-actions">
          <mat-chip class="status-chip" [class]="apiStatus()">
            <mat-icon>{{ apiStatus() === 'online' ? 'check_circle' : 'error' }}</mat-icon>
            {{ apiStatus() | uppercase }}
          </mat-chip>
        </div>
      </div>

      <!-- Quick Info Card -->
      <mat-card class="info-card">
        <mat-card-content>
          <div class="info-grid">
            <div class="info-item">
              <mat-icon>link</mat-icon>
              <div>
                <span class="label">Endpoint Base</span>
                <code class="value">{{ getBaseUrl() }}/v1</code>
              </div>
              <button mat-icon-button (click)="copyToClipboard(getBaseUrl() + '/v1')" matTooltip="Copiar">
                <mat-icon>content_copy</mat-icon>
              </button>
            </div>
            <div class="info-item">
              <mat-icon>vpn_key</mat-icon>
              <div>
                <span class="label">API Keys Activas</span>
                <span class="value">{{ activeKeysCount() }}</span>
              </div>
            </div>
            <div class="info-item">
              <mat-icon>smart_toy</mat-icon>
              <div>
                <span class="label">Modelos Disponibles</span>
                <span class="value">{{ modelsCount() }}</span>
              </div>
            </div>
            <div class="info-item">
              <mat-icon>analytics</mat-icon>
              <div>
                <span class="label">Requests Totales</span>
                <span class="value">{{ totalRequests() }}</span>
              </div>
            </div>
          </div>
        </mat-card-content>
      </mat-card>

      <mat-tab-group>
        <!-- Tab de API Keys -->
        <mat-tab>
          <ng-template mat-tab-label>
            <mat-icon>vpn_key</mat-icon>
            <span class="tab-label">API Keys</span>
            <span class="badge" *ngIf="apiKeys().length">{{ apiKeys().length }}</span>
          </ng-template>

          <div class="tab-content">
            <div class="section-header">
              <h2>Gestión de API Keys</h2>
              <button mat-raised-button color="primary" (click)="showCreateKeyForm = true">
                <mat-icon>add</mat-icon>
                Nueva API Key
              </button>
            </div>

            <!-- Create Key Form -->
            @if (showCreateKeyForm) {
              <mat-card class="create-form">
                <mat-card-header>
                  <mat-card-title>Crear Nueva API Key</mat-card-title>
                </mat-card-header>
                <mat-card-content>
                  <div class="form-grid">
                    <mat-form-field appearance="outline">
                      <mat-label>Nombre</mat-label>
                      <input matInput [(ngModel)]="newKey.name" placeholder="Mi aplicación">
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Modelos permitidos</mat-label>
                      <mat-select [(ngModel)]="newKey.models" multiple>
                        <mat-option value="brain-adaptive">Brain Adaptive</mat-option>
                        <mat-option value="brain-chat">Brain Chat</mat-option>
                        <mat-option value="brain-rag">Brain RAG</mat-option>
                      </mat-select>
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Rate Limit (req/min)</mat-label>
                      <input matInput type="number" [(ngModel)]="newKey.rateLimit">
                    </mat-form-field>

                    <mat-form-field appearance="outline" class="full-width">
                      <mat-label>Notas</mat-label>
                      <textarea matInput [(ngModel)]="newKey.notes" rows="2"></textarea>
                    </mat-form-field>
                  </div>
                </mat-card-content>
                <mat-card-actions align="end">
                  <button mat-button (click)="showCreateKeyForm = false">Cancelar</button>
                  <button mat-raised-button color="primary" (click)="createApiKey()" [disabled]="creatingKey()">
                    @if (creatingKey()) {
                      <mat-spinner diameter="20"></mat-spinner>
                    } @else {
                      <mat-icon>add</mat-icon>
                    }
                    Crear Key
                  </button>
                </mat-card-actions>
              </mat-card>
            }

            <!-- Show New Key -->
            @if (newlyCreatedKey()) {
              <mat-card class="new-key-card">
                <mat-card-content>
                  <div class="new-key-warning">
                    <mat-icon>warning</mat-icon>
                    <span>Guarda esta API key. No se mostrará de nuevo.</span>
                  </div>
                  <div class="new-key-display">
                    <code>{{ newlyCreatedKey() }}</code>
                    <button mat-icon-button (click)="copyToClipboard(newlyCreatedKey()!)" matTooltip="Copiar">
                      <mat-icon>content_copy</mat-icon>
                    </button>
                  </div>
                  <button mat-button (click)="newlyCreatedKey.set(null)">Entendido</button>
                </mat-card-content>
              </mat-card>
            }

            <!-- Keys Table -->
            @if (loadingKeys()) {
              <div class="loading-container">
                <mat-spinner diameter="48"></mat-spinner>
                <p>Cargando API keys...</p>
              </div>
            } @else {
              <div class="keys-table">
                <table mat-table [dataSource]="apiKeys()">
                  <ng-container matColumnDef="name">
                    <th mat-header-cell *matHeaderCellDef>Nombre</th>
                    <td mat-cell *matCellDef="let key">
                      <div class="key-name">
                        <span>{{ key.name }}</span>
                        <mat-chip class="status-mini" [class]="key.isActive ? 'active' : 'inactive'">
                          {{ key.isActive ? 'Activa' : 'Inactiva' }}
                        </mat-chip>
                      </div>
                    </td>
                  </ng-container>

                  <ng-container matColumnDef="key">
                    <th mat-header-cell *matHeaderCellDef>Key</th>
                    <td mat-cell *matCellDef="let key">
                      <code class="key-preview">{{ key.keyPrefix || key.key?.substring(0, 20) }}...</code>
                    </td>
                  </ng-container>

                  <ng-container matColumnDef="usage">
                    <th mat-header-cell *matHeaderCellDef>Uso</th>
                    <td mat-cell *matCellDef="let key">
                      <div class="usage-stats">
                        <span>{{ key.usageStats?.totalRequests || 0 }} requests</span>
                        <span class="tokens">{{ key.usageStats?.totalTokens || 0 }} tokens</span>
                      </div>
                    </td>
                  </ng-container>

                  <ng-container matColumnDef="lastUsed">
                    <th mat-header-cell *matHeaderCellDef>Último uso</th>
                    <td mat-cell *matCellDef="let key">
                      {{ key.usageStats?.lastUsed ? (key.usageStats.lastUsed | date:'short') : 'Nunca' }}
                    </td>
                  </ng-container>

                  <ng-container matColumnDef="actions">
                    <th mat-header-cell *matHeaderCellDef></th>
                    <td mat-cell *matCellDef="let key">
                      <button mat-icon-button [matMenuTriggerFor]="keyMenu">
                        <mat-icon>more_vert</mat-icon>
                      </button>
                      <mat-menu #keyMenu="matMenu">
                        <button mat-menu-item (click)="toggleKeyStatus(key)">
                          <mat-icon>{{ key.isActive ? 'pause' : 'play_arrow' }}</mat-icon>
                          <span>{{ key.isActive ? 'Desactivar' : 'Activar' }}</span>
                        </button>
                        <button mat-menu-item (click)="copyToClipboard(key.key)">
                          <mat-icon>content_copy</mat-icon>
                          <span>Copiar Key</span>
                        </button>
                        <mat-divider></mat-divider>
                        <button mat-menu-item class="danger" (click)="deleteKey(key)">
                          <mat-icon>delete</mat-icon>
                          <span>Eliminar</span>
                        </button>
                      </mat-menu>
                    </td>
                  </ng-container>

                  <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
                  <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
                </table>

                @if (apiKeys().length === 0) {
                  <div class="empty-state">
                    <mat-icon>vpn_key</mat-icon>
                    <h3>No hay API keys</h3>
                    <p>Crea una API key para empezar a usar la API externa</p>
                  </div>
                }
              </div>
            }
          </div>
        </mat-tab>

        <!-- Tab de Modelos -->
        <mat-tab>
          <ng-template mat-tab-label>
            <mat-icon>smart_toy</mat-icon>
            <span class="tab-label">Modelos</span>
          </ng-template>

          <div class="tab-content">
            <div class="section-header">
              <h2>Modelos Disponibles</h2>
            </div>

            <div class="models-grid">
              @for (model of availableModels(); track model.id) {
                <mat-card class="model-card">
                  <mat-card-header>
                    <div class="model-icon">
                      <mat-icon>psychology</mat-icon>
                    </div>
                    <mat-card-title>{{ model.name }}</mat-card-title>
                    <mat-card-subtitle>{{ model.id }}</mat-card-subtitle>
                  </mat-card-header>
                  <mat-card-content>
                    <p class="description">{{ model.description }}</p>
                    <div class="model-features">
                      <mat-chip class="feature">
                        <mat-icon>memory</mat-icon>
                        {{ model.maxTokens }} tokens
                      </mat-chip>
                      @if (model.supportsStreaming) {
                        <mat-chip class="feature supported">
                          <mat-icon>stream</mat-icon>
                          Streaming
                        </mat-chip>
                      }
                      @if (model.supportsTools) {
                        <mat-chip class="feature supported">
                          <mat-icon>build</mat-icon>
                          Tools
                        </mat-chip>
                      }
                    </div>
                  </mat-card-content>
                </mat-card>
              }
            </div>
          </div>
        </mat-tab>

        <!-- Tab de Configuración -->
        <mat-tab>
          <ng-template mat-tab-label>
            <mat-icon>settings</mat-icon>
            <span class="tab-label">Configuración</span>
          </ng-template>

          <div class="tab-content">
            <mat-card class="config-card">
              <mat-card-header>
                <mat-card-title>Configuración General</mat-card-title>
              </mat-card-header>
              <mat-card-content>
                <div class="config-form">
                  <mat-slide-toggle [(ngModel)]="config.isEnabled" color="primary">
                    API Externa Habilitada
                  </mat-slide-toggle>

                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>Modelo por defecto</mat-label>
                    <mat-select [(ngModel)]="config.defaultModel">
                      @for (model of availableModels(); track model.id) {
                        <mat-option [value]="model.id">{{ model.name }}</mat-option>
                      }
                    </mat-select>
                  </mat-form-field>

                  <mat-divider></mat-divider>
                  <h3>Backend LLM</h3>

                  <div class="form-row">
                    <mat-form-field appearance="outline">
                      <mat-label>Proveedor</mat-label>
                      <mat-select [(ngModel)]="config.backendLlm.provider">
                        <mat-option value="ollama">Ollama</mat-option>
                        <mat-option value="openai">OpenAI</mat-option>
                      </mat-select>
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>URL</mat-label>
                      <input matInput [(ngModel)]="config.backendLlm.url">
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Modelo</mat-label>
                      <input matInput [(ngModel)]="config.backendLlm.model">
                    </mat-form-field>
                  </div>

                  <mat-divider></mat-divider>
                  <h3>Rate Limits</h3>

                  <div class="form-row">
                    <mat-form-field appearance="outline">
                      <mat-label>Requests por minuto</mat-label>
                      <input matInput type="number" [(ngModel)]="config.rateLimits.requestsPerMinute">
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Tokens por minuto</mat-label>
                      <input matInput type="number" [(ngModel)]="config.rateLimits.tokensPerMinute">
                    </mat-form-field>
                  </div>
                </div>
              </mat-card-content>
              <mat-card-actions align="end">
                <button mat-raised-button color="primary" (click)="saveConfig()" [disabled]="savingConfig()">
                  @if (savingConfig()) {
                    <mat-spinner diameter="20"></mat-spinner>
                  } @else {
                    <mat-icon>save</mat-icon>
                  }
                  Guardar Configuración
                </button>
              </mat-card-actions>
            </mat-card>
          </div>
        </mat-tab>

        <!-- Tab de Documentación -->
        <mat-tab>
          <ng-template mat-tab-label>
            <mat-icon>description</mat-icon>
            <span class="tab-label">Documentación</span>
          </ng-template>

          <div class="tab-content">
            <mat-card class="docs-card">
              <mat-card-header>
                <mat-card-title>Uso de la API</mat-card-title>
              </mat-card-header>
              <mat-card-content>
                <h3>Ejemplo con Python (OpenAI SDK)</h3>
                <pre class="code-block"><code [innerText]="getPythonExample()"></code></pre>

                <h3>Ejemplo con cURL</h3>
                <pre class="code-block"><code [innerText]="getCurlExample()"></code></pre>

                <h3>Endpoints Disponibles</h3>
                <table class="docs-table">
                  <tr>
                    <td><code>POST /v1/chat/completions</code></td>
                    <td>Chat completion (streaming y no-streaming)</td>
                  </tr>
                  <tr>
                    <td><code>GET /v1/models</code></td>
                    <td>Lista de modelos disponibles</td>
                  </tr>
                  <tr>
                    <td><code>GET /v1/models/&#123;model&#125;</code></td>
                    <td>Detalles de un modelo</td>
                  </tr>
                </table>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
  styles: [`
    .external-api-page {
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

    .status-chip {
      font-weight: 500;
    }

    .status-chip.online {
      background: #e8f5e9 !important;
      color: #388e3c !important;
    }

    .status-chip.disabled, .status-chip.offline {
      background: #ffebee !important;
      color: #d32f2f !important;
    }

    /* Info Card */
    .info-card {
      margin-bottom: 24px;
      border-radius: 12px;
    }

    .info-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 24px;
    }

    .info-item {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .info-item mat-icon {
      color: #667eea;
      font-size: 28px;
      width: 28px;
      height: 28px;
    }

    .info-item .label {
      display: block;
      font-size: 12px;
      color: #888;
    }

    .info-item .value {
      font-size: 16px;
      font-weight: 500;
    }

    .info-item code.value {
      font-family: monospace;
      background: #f5f5f5;
      padding: 4px 8px;
      border-radius: 4px;
    }

    /* Tabs */
    .tab-label {
      margin-left: 8px;
    }

    .badge {
      margin-left: 8px;
      background: #667eea;
      color: white;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 12px;
    }

    .tab-content {
      padding: 24px 0;
    }

    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
    }

    .section-header h2 {
      margin: 0;
      font-size: 20px;
    }

    /* Create Form */
    .create-form {
      margin-bottom: 24px;
      border-radius: 12px;
    }

    .form-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 16px;
    }

    .full-width {
      grid-column: 1 / -1;
    }

    /* New Key Card */
    .new-key-card {
      margin-bottom: 24px;
      background: #fff3e0;
      border-radius: 12px;
    }

    .new-key-warning {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #f57c00;
      margin-bottom: 12px;
    }

    .new-key-display {
      display: flex;
      align-items: center;
      gap: 8px;
      background: white;
      padding: 12px;
      border-radius: 8px;
      margin-bottom: 12px;
    }

    .new-key-display code {
      flex: 1;
      font-family: monospace;
      font-size: 14px;
      word-break: break-all;
    }

    /* Keys Table */
    .keys-table {
      background: white;
      border-radius: 12px;
      overflow: hidden;
    }

    .keys-table table {
      width: 100%;
    }

    .key-name {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .status-mini {
      font-size: 10px !important;
      min-height: 20px !important;
    }

    .status-mini.active {
      background: #e8f5e9 !important;
      color: #388e3c !important;
    }

    .status-mini.inactive {
      background: #ffebee !important;
      color: #d32f2f !important;
    }

    .key-preview {
      font-family: monospace;
      font-size: 12px;
      color: #666;
    }

    .usage-stats {
      display: flex;
      flex-direction: column;
      font-size: 13px;
    }

    .usage-stats .tokens {
      color: #888;
      font-size: 11px;
    }

    .danger {
      color: #d32f2f !important;
    }

    /* Models Grid */
    .models-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 20px;
    }

    .model-card {
      border-radius: 12px;
    }

    .model-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 16px;
    }

    .model-icon mat-icon {
      color: white;
      font-size: 24px;
    }

    .model-features {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }

    .feature {
      font-size: 11px !important;
      min-height: 24px !important;
    }

    .feature.supported {
      background: #e8f5e9 !important;
      color: #388e3c !important;
    }

    /* Config */
    .config-card {
      border-radius: 12px;
    }

    .config-form {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .config-form h3 {
      margin: 16px 0 8px;
      font-size: 16px;
      color: #333;
    }

    .form-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
    }

    /* Docs */
    .docs-card {
      border-radius: 12px;
    }

    .docs-card h3 {
      margin: 24px 0 12px;
      font-size: 16px;
    }

    .docs-card h3:first-child {
      margin-top: 0;
    }

    .code-block {
      background: #1a1a2e;
      color: #e0e0e0;
      padding: 16px;
      border-radius: 8px;
      overflow-x: auto;
      font-size: 13px;
    }

    .docs-table {
      width: 100%;
      border-collapse: collapse;
    }

    .docs-table td {
      padding: 12px;
      border-bottom: 1px solid #eee;
    }

    .docs-table code {
      background: #f5f5f5;
      padding: 4px 8px;
      border-radius: 4px;
    }

    /* Empty & Loading */
    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 64px;
      color: #666;
    }

    .empty-state {
      text-align: center;
      padding: 64px;
      color: #666;
    }

    .empty-state mat-icon {
      font-size: 64px;
      width: 64px;
      height: 64px;
      color: #ccc;
    }

    @media (max-width: 768px) {
      .info-grid {
        grid-template-columns: repeat(2, 1fr);
      }

      .form-row {
        grid-template-columns: 1fr;
      }
    }
  `]
})
export class ExternalApiComponent implements OnInit {
  private http = inject(HttpClient);
  private snackBar = inject(MatSnackBar);
  private clipboard = inject(Clipboard);

  apiKeys = signal<ApiKey[]>([]);
  availableModels = signal<BrainModel[]>([]);
  apiStatus = signal<string>('offline');
  
  loadingKeys = signal(true);
  creatingKey = signal(false);
  savingConfig = signal(false);

  displayedColumns = ['name', 'key', 'usage', 'lastUsed', 'actions'];

  showCreateKeyForm = false;
  newlyCreatedKey = signal<string | null>(null);

  newKey = {
    name: '',
    models: ['brain-adaptive', 'brain-chat', 'brain-rag'],
    rateLimit: 60,
    notes: ''
  };

  config: ApiConfig = {
    isEnabled: true,
    baseUrl: '/v1',
    defaultModel: 'brain-adaptive',
    availableModels: [],
    backendLlm: {
      provider: 'ollama',
      url: 'http://192.168.7.101:11434',
      model: 'gpt-oss:120b'
    },
    rateLimits: {
      requestsPerMinute: 60,
      tokensPerMinute: 100000
    }
  };

  ngOnInit(): void {
    this.loadApiKeys();
    this.loadConfig();
    this.checkApiStatus();
  }

  getBaseUrl(): string {
    return window.location.origin.replace(':4200', ':8000');
  }

  activeKeysCount(): number {
    return this.apiKeys().filter(k => k.isActive).length;
  }

  modelsCount(): number {
    return this.availableModels().length;
  }

  totalRequests(): number {
    return this.apiKeys().reduce((sum, k) => sum + (k.usageStats?.totalRequests || 0), 0);
  }

  loadApiKeys(): void {
    this.loadingKeys.set(true);
    
    this.http.get<any>(`${environment.strapiUrl}/api/brain-api-keys`, {
      headers: { 'Authorization': `Bearer ${this.getStrapiToken()}` }
    }).subscribe({
      next: (response) => {
        const keys = (response.data || []).map((item: any) => ({
          id: item.id,
          ...item.attributes
        }));
        this.apiKeys.set(keys);
        this.loadingKeys.set(false);
      },
      error: (err) => {
        console.error('Error loading API keys:', err);
        this.loadingKeys.set(false);
      }
    });
  }

  loadConfig(): void {
    // Cargar desde Strapi
    this.http.get<any>(`${environment.strapiUrl}/api/brain-model-config`, {
      headers: { 'Authorization': `Bearer ${this.getStrapiToken()}` }
    }).subscribe({
      next: (response) => {
        if (response.data?.attributes) {
          const attrs = response.data.attributes;
          this.config = {
            isEnabled: attrs.isEnabled ?? true,
            baseUrl: attrs.baseUrl ?? '/v1',
            defaultModel: attrs.defaultModel ?? 'brain-adaptive',
            availableModels: attrs.availableModels ?? [],
            backendLlm: attrs.backendLlm ?? this.config.backendLlm,
            rateLimits: attrs.rateLimits ?? this.config.rateLimits
          };
          this.availableModels.set(this.config.availableModels);
        }
      },
      error: (err) => {
        console.log('Config not found, using defaults');
        // Usar modelos por defecto
        this.availableModels.set([
          { id: 'brain-adaptive', name: 'Brain Adaptive', description: 'Full agent with tools', chainId: 'adaptive', maxTokens: 4096, supportsStreaming: true, supportsTools: true },
          { id: 'brain-chat', name: 'Brain Chat', description: 'Simple chat', chainId: 'conversational', maxTokens: 4096, supportsStreaming: true, supportsTools: false },
          { id: 'brain-rag', name: 'Brain RAG', description: 'Chat with documents', chainId: 'rag', maxTokens: 4096, supportsStreaming: true, supportsTools: false }
        ]);
      }
    });
  }

  checkApiStatus(): void {
    this.http.get<any>(`${this.getBaseUrl()}/v1/brain/status`).subscribe({
      next: (response) => {
        this.apiStatus.set(response.status);
      },
      error: () => {
        this.apiStatus.set('offline');
      }
    });
  }

  createApiKey(): void {
    if (!this.newKey.name.trim()) {
      this.snackBar.open('El nombre es requerido', 'Cerrar', { duration: 3000 });
      return;
    }

    this.creatingKey.set(true);

    // Generar key
    const key = 'sk-brain-' + this.generateRandomString(48);
    
    const payload = {
      data: {
        name: this.newKey.name,
        key: key,
        keyPrefix: key.substring(0, 20),
        isActive: true,
        permissions: {
          models: this.newKey.models,
          maxTokensPerRequest: 4096,
          rateLimit: this.newKey.rateLimit
        },
        usageStats: {
          totalRequests: 0,
          totalTokens: 0,
          lastUsed: null
        },
        notes: this.newKey.notes
      }
    };

    this.http.post<any>(`${environment.strapiUrl}/api/brain-api-keys`, payload, {
      headers: { 'Authorization': `Bearer ${this.getStrapiToken()}` }
    }).subscribe({
      next: () => {
        this.newlyCreatedKey.set(key);
        this.showCreateKeyForm = false;
        this.newKey = { name: '', models: ['brain-adaptive', 'brain-chat', 'brain-rag'], rateLimit: 60, notes: '' };
        this.loadApiKeys();
        this.creatingKey.set(false);
        this.snackBar.open('API key creada', 'Cerrar', { duration: 3000 });
      },
      error: (err) => {
        this.snackBar.open('Error creando API key', 'Cerrar', { duration: 3000 });
        this.creatingKey.set(false);
      }
    });
  }

  toggleKeyStatus(key: ApiKey): void {
    this.http.put<any>(`${environment.strapiUrl}/api/brain-api-keys/${key.id}`, {
      data: { isActive: !key.isActive }
    }, {
      headers: { 'Authorization': `Bearer ${this.getStrapiToken()}` }
    }).subscribe({
      next: () => {
        this.loadApiKeys();
        this.snackBar.open(`Key ${key.isActive ? 'desactivada' : 'activada'}`, 'Cerrar', { duration: 3000 });
      },
      error: () => {
        this.snackBar.open('Error actualizando key', 'Cerrar', { duration: 3000 });
      }
    });
  }

  deleteKey(key: ApiKey): void {
    if (!confirm(`¿Eliminar la API key "${key.name}"?`)) return;

    this.http.delete<any>(`${environment.strapiUrl}/api/brain-api-keys/${key.id}`, {
      headers: { 'Authorization': `Bearer ${this.getStrapiToken()}` }
    }).subscribe({
      next: () => {
        this.loadApiKeys();
        this.snackBar.open('API key eliminada', 'Cerrar', { duration: 3000 });
      },
      error: () => {
        this.snackBar.open('Error eliminando key', 'Cerrar', { duration: 3000 });
      }
    });
  }

  saveConfig(): void {
    this.savingConfig.set(true);

    // Intentar actualizar, si no existe crear
    this.http.put<any>(`${environment.strapiUrl}/api/brain-model-config`, {
      data: {
        isEnabled: this.config.isEnabled,
        baseUrl: this.config.baseUrl,
        defaultModel: this.config.defaultModel,
        backendLlm: this.config.backendLlm,
        rateLimits: this.config.rateLimits
      }
    }, {
      headers: { 'Authorization': `Bearer ${this.getStrapiToken()}` }
    }).subscribe({
      next: () => {
        this.snackBar.open('Configuración guardada', 'Cerrar', { duration: 3000 });
        this.savingConfig.set(false);
      },
      error: () => {
        this.snackBar.open('Error guardando configuración', 'Cerrar', { duration: 3000 });
        this.savingConfig.set(false);
      }
    });
  }

  copyToClipboard(text: string): void {
    this.clipboard.copy(text);
    this.snackBar.open('Copiado al portapapeles', 'Cerrar', { duration: 2000 });
  }

  private generateRandomString(length: number): string {
    const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  }

  private getStrapiToken(): string {
    // Obtener token de localStorage o usar uno por defecto para desarrollo
    return localStorage.getItem('strapi_token') || '32e50d52a2501158aa673bc3c37ec4a3bb0e57149c68d5361dc9cbbf9bf0475fad1a43c869943002e3aa936203b5abbbd0d7dfb698f8d85d5d24919e27472d507d445178ce809aaf6477995ce474cf0a6aa17ad932f58d0be6293077dd93e0a92b034bbb46bbfe565e08b8e2d19b54233eec65c96a2adf4e0045eede459b237b';
  }

  getPythonExample(): string {
    return `from openai import OpenAI

client = OpenAI(
    base_url="${this.getBaseUrl()}/v1",
    api_key="sk-brain-tu-api-key"
)

response = client.chat.completions.create(
    model="brain-adaptive",
    messages=[
        {"role": "user", "content": "Hola, genera una imagen de un gato"}
    ]
)

print(response.choices[0].message.content)`;
  }

  getCurlExample(): string {
    return `curl ${this.getBaseUrl()}/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer sk-brain-tu-api-key" \\
  -d '{
    "model": "brain-adaptive",
    "messages": [{"role": "user", "content": "Hola"}]
  }'`;
  }
}
