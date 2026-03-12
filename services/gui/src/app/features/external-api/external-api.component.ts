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

            <!-- Edit Key Form -->
            @if (editingKey()) {
              <mat-card class="edit-form">
                <mat-card-header>
                  <mat-card-title>Editar API Key</mat-card-title>
                </mat-card-header>
                <mat-card-content>
                  <div class="form-grid">
                    <mat-form-field appearance="outline">
                      <mat-label>Nombre</mat-label>
                      <input matInput [(ngModel)]="editKeyData.name" placeholder="Mi aplicación">
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Modelos permitidos</mat-label>
                      <mat-select [(ngModel)]="editKeyData.models" multiple>
                        <mat-option value="brain-adaptive">Brain Adaptive</mat-option>
                        <mat-option value="brain-chat">Brain Chat</mat-option>
                      </mat-select>
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Rate Limit (req/min)</mat-label>
                      <input matInput type="number" [(ngModel)]="editKeyData.rateLimit">
                    </mat-form-field>

                    <mat-form-field appearance="outline" class="full-width">
                      <mat-label>Notas</mat-label>
                      <textarea matInput [(ngModel)]="editKeyData.notes" rows="2"></textarea>
                    </mat-form-field>

                    <div class="toggle-field">
                      <mat-slide-toggle [(ngModel)]="editKeyData.isActive">
                        {{ editKeyData.isActive ? 'Activa' : 'Inactiva' }}
                      </mat-slide-toggle>
                    </div>
                  </div>
                </mat-card-content>
                <mat-card-actions align="end">
                  <button mat-button (click)="cancelEditKey()">Cancelar</button>
                  <button mat-raised-button color="primary" (click)="saveEditKey()" [disabled]="savingKey()">
                    @if (savingKey()) {
                      <mat-spinner diameter="20"></mat-spinner>
                    } @else {
                      <mat-icon>save</mat-icon>
                    }
                    Guardar Cambios
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
                        <button mat-menu-item (click)="startEditKey(key)">
                          <mat-icon>edit</mat-icon>
                          <span>Editar</span>
                        </button>
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
                    <div class="model-icon" mat-card-avatar>
                      <mat-icon>psychology</mat-icon>
                    </div>
                    <div>
                      <mat-card-title>{{ model.name }}</mat-card-title>
                      <mat-card-subtitle>{{ model.id }}</mat-card-subtitle>
                    </div>
                  </mat-card-header>
                  <mat-card-content>
                    <p class="description">{{ model.description }}</p>
                  </mat-card-content>
                  <mat-card-actions>
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
                  </mat-card-actions>
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

        <!-- Tab A2A Protocol -->
        <mat-tab>
          <ng-template mat-tab-label>
            <mat-icon>hub</mat-icon>
            <span class="tab-label">A2A Protocol</span>
            <span class="badge a2a-badge">NEW</span>
          </ng-template>

          <div class="tab-content">
            <!-- A2A Status -->
            <div class="a2a-status-bar">
              <div class="a2a-status-item">
                <mat-icon [class.active]="agentCard()">{{ agentCard() ? 'check_circle' : 'hourglass_empty' }}</mat-icon>
                <span>Agent Card</span>
              </div>
              <div class="a2a-status-item">
                <mat-icon class="active">check_circle</mat-icon>
                <span>HTTP+JSON Binding</span>
              </div>
              <div class="a2a-status-item">
                <mat-icon class="active">check_circle</mat-icon>
                <span>SSE Streaming</span>
              </div>
              <div class="a2a-status-item">
                <mat-icon class="disabled">remove_circle_outline</mat-icon>
                <span>Push Notifications</span>
              </div>
            </div>

            <!-- Agent Card -->
            <mat-card class="a2a-card">
              <mat-card-header>
                <div class="a2a-card-icon" mat-card-avatar>
                  <mat-icon>badge</mat-icon>
                </div>
                <mat-card-title>Agent Card</mat-card-title>
                <mat-card-subtitle>
                  <code>GET /.well-known/agent-card.json</code>
                  <button mat-icon-button (click)="copyToClipboard(getBaseUrl() + '/.well-known/agent-card.json')" matTooltip="Copiar URL">
                    <mat-icon>content_copy</mat-icon>
                  </button>
                </mat-card-subtitle>
              </mat-card-header>
              <mat-card-content>
                @if (loadingAgentCard()) {
                  <div class="loading-container" style="padding: 24px">
                    <mat-spinner diameter="32"></mat-spinner>
                    <p>Cargando Agent Card...</p>
                  </div>
                } @else if (agentCard()) {
                  <div class="agent-card-summary">
                    <div class="agent-meta">
                      <div class="meta-row">
                        <span class="meta-label">Nombre</span>
                        <span class="meta-value">{{ agentCard()!.name }}</span>
                      </div>
                      <div class="meta-row">
                        <span class="meta-label">Versión</span>
                        <span class="meta-value">{{ agentCard()!.version }}</span>
                      </div>
                      <div class="meta-row">
                        <span class="meta-label">Binding</span>
                        <span class="meta-value">{{ agentCard()!.supportedInterfaces?.[0]?.protocolBinding }} v{{ agentCard()!.supportedInterfaces?.[0]?.protocolVersion }}</span>
                      </div>
                      <div class="meta-row">
                        <span class="meta-label">Endpoint</span>
                        <code class="meta-value">{{ agentCard()!.supportedInterfaces?.[0]?.url }}</code>
                      </div>
                    </div>

                    <!-- Capabilities -->
                    <h4>Capabilities</h4>
                    <div class="capabilities-row">
                      <mat-chip [class]="agentCard()!.capabilities?.streaming ? 'cap-on' : 'cap-off'">
                        <mat-icon>{{ agentCard()!.capabilities?.streaming ? 'check' : 'close' }}</mat-icon>
                        Streaming
                      </mat-chip>
                      <mat-chip [class]="agentCard()!.capabilities?.pushNotifications ? 'cap-on' : 'cap-off'">
                        <mat-icon>{{ agentCard()!.capabilities?.pushNotifications ? 'check' : 'close' }}</mat-icon>
                        Push Notifications
                      </mat-chip>
                      <mat-chip [class]="agentCard()!.capabilities?.extendedAgentCard ? 'cap-on' : 'cap-off'">
                        <mat-icon>{{ agentCard()!.capabilities?.extendedAgentCard ? 'check' : 'close' }}</mat-icon>
                        Extended Card
                      </mat-chip>
                    </div>

                    <!-- Skills -->
                    @if (agentCard()!.skills?.length) {
                      <h4>Skills ({{ agentCard()!.skills.length }})</h4>
                      <div class="skills-grid">
                        @for (skill of agentCard()!.skills; track skill.id) {
                          <div class="skill-item">
                            <div class="skill-header">
                              <strong>{{ skill.name }}</strong>
                              <code class="skill-id">{{ skill.id }}</code>
                            </div>
                            <p class="skill-desc">{{ skill.description }}</p>
                            <div class="skill-tags">
                              @for (tag of skill.tags; track tag) {
                                <mat-chip class="skill-tag">{{ tag }}</mat-chip>
                              }
                            </div>
                          </div>
                        }
                      </div>
                    }
                  </div>

                  <!-- Raw JSON toggle -->
                  <div class="json-toggle">
                    <button mat-button (click)="showAgentCardJson = !showAgentCardJson">
                      <mat-icon>{{ showAgentCardJson ? 'visibility_off' : 'code' }}</mat-icon>
                      {{ showAgentCardJson ? 'Ocultar JSON' : 'Ver JSON completo' }}
                    </button>
                    @if (showAgentCardJson) {
                      <button mat-icon-button (click)="copyToClipboard(agentCardJson())" matTooltip="Copiar JSON">
                        <mat-icon>content_copy</mat-icon>
                      </button>
                    }
                  </div>
                  @if (showAgentCardJson) {
                    <pre class="code-block json-block"><code [innerText]="agentCardJson()"></code></pre>
                  }
                } @else {
                  <div class="empty-state" style="padding: 24px">
                    <mat-icon>error_outline</mat-icon>
                    <p>No se pudo cargar el Agent Card</p>
                    <button mat-raised-button color="primary" (click)="loadAgentCard()">Reintentar</button>
                  </div>
                }
              </mat-card-content>
            </mat-card>

            <!-- Endpoints A2A -->
            <mat-card class="docs-card" style="margin-top: 24px">
              <mat-card-header>
                <mat-card-title>Endpoints A2A (HTTP+JSON/REST)</mat-card-title>
                <mat-card-subtitle>Prefijo: <code>{{ getBaseUrl() }}/a2a</code></mat-card-subtitle>
              </mat-card-header>
              <mat-card-content>
                <table class="docs-table a2a-endpoints-table">
                  <thead>
                    <tr>
                      <th>Método</th>
                      <th>Endpoint</th>
                      <th>Operación A2A</th>
                      <th>Tipo</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td><code class="method post">POST</code></td>
                      <td><code>/a2a/message:send</code></td>
                      <td>SendMessage</td>
                      <td><mat-chip class="type-chip core">Core</mat-chip></td>
                    </tr>
                    <tr>
                      <td><code class="method post">POST</code></td>
                      <td><code>/a2a/message:stream</code></td>
                      <td>SendStreamingMessage</td>
                      <td><mat-chip class="type-chip streaming">SSE</mat-chip></td>
                    </tr>
                    <tr>
                      <td><code class="method get">GET</code></td>
                      <td><code>/a2a/tasks/&#123;id&#125;</code></td>
                      <td>GetTask</td>
                      <td><mat-chip class="type-chip core">Core</mat-chip></td>
                    </tr>
                    <tr>
                      <td><code class="method get">GET</code></td>
                      <td><code>/a2a/tasks</code></td>
                      <td>ListTasks</td>
                      <td><mat-chip class="type-chip core">Core</mat-chip></td>
                    </tr>
                    <tr>
                      <td><code class="method post">POST</code></td>
                      <td><code>/a2a/tasks/&#123;id&#125;:cancel</code></td>
                      <td>CancelTask</td>
                      <td><mat-chip class="type-chip core">Core</mat-chip></td>
                    </tr>
                    <tr>
                      <td><code class="method post">POST</code></td>
                      <td><code>/a2a/tasks/&#123;id&#125;:subscribe</code></td>
                      <td>SubscribeToTask</td>
                      <td><mat-chip class="type-chip streaming">SSE</mat-chip></td>
                    </tr>
                    <tr>
                      <td><code class="method get">GET</code></td>
                      <td><code>/a2a/extendedAgentCard</code></td>
                      <td>GetExtendedAgentCard</td>
                      <td><mat-chip class="type-chip optional">Auth</mat-chip></td>
                    </tr>
                  </tbody>
                </table>

                <h3>Ejemplo: SendMessage (cURL)</h3>
                <pre class="code-block"><code [innerText]="getA2aCurlExample()"></code></pre>

                <h3>Ejemplo: SendMessage (Python)</h3>
                <pre class="code-block"><code [innerText]="getA2aPythonExample()"></code></pre>

                <h3>Ejemplo: SendStreamingMessage (Python)</h3>
                <pre class="code-block"><code [innerText]="getA2aStreamPythonExample()"></code></pre>
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

    /* Edit Form */
    .edit-form {
      margin-bottom: 24px;
      border-radius: 12px;
      border: 2px solid #2196f3;
    }

    .form-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 16px;
    }

    .full-width {
      grid-column: 1 / -1;
    }

    .toggle-field {
      grid-column: 1 / -1;
      padding: 8px 0;
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
      display: flex;
      flex-direction: column;
      height: 100%;
    }

    .model-card mat-card-header {
      display: flex;
      align-items: flex-start;
      padding: 16px 16px 0;
    }

    .model-card mat-card-title {
      font-size: 16px;
      font-weight: 600;
      line-height: 1.3;
      margin-bottom: 4px;
    }

    .model-card mat-card-subtitle {
      font-size: 13px;
      line-height: 1.4;
    }

    .model-card mat-card-content {
      flex: 1 1 auto;
      padding: 16px;
    }

    .model-card mat-card-actions {
      margin-top: auto;
      padding: 16px;
      border-top: 1px solid #f0f0f0;
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
      flex-shrink: 0;
    }

    .model-icon mat-icon {
      color: white;
      font-size: 24px;
    }

    .model-features {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
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

    /* A2A Protocol Tab */
    .a2a-badge {
      background: #00bfa5 !important;
    }

    .a2a-status-bar {
      display: flex;
      gap: 24px;
      margin-bottom: 24px;
      padding: 16px 20px;
      background: #f8f9fa;
      border-radius: 12px;
      border: 1px solid #e0e0e0;
    }

    .a2a-status-item {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      font-weight: 500;
    }

    .a2a-status-item mat-icon.active {
      color: #388e3c;
    }

    .a2a-status-item mat-icon.disabled {
      color: #bdbdbd;
    }

    .a2a-card {
      border-radius: 12px;
    }

    .a2a-card-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      background: linear-gradient(135deg, #00bfa5 0%, #00897b 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 16px;
      flex-shrink: 0;
    }

    .a2a-card-icon mat-icon {
      color: white;
      font-size: 24px;
    }

    .a2a-card mat-card-subtitle {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .a2a-card mat-card-subtitle code {
      background: #f5f5f5;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 12px;
    }

    .agent-card-summary h4 {
      margin: 20px 0 12px;
      font-size: 15px;
      font-weight: 600;
      color: #333;
    }

    .agent-meta {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
      padding: 16px;
      background: #f8f9fa;
      border-radius: 8px;
    }

    .meta-row {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .meta-label {
      font-size: 11px;
      color: #888;
      text-transform: uppercase;
      font-weight: 600;
      letter-spacing: 0.5px;
    }

    .meta-value {
      font-size: 14px;
      font-weight: 500;
    }

    code.meta-value {
      font-family: monospace;
      font-size: 12px;
      background: #e8eaf6;
      padding: 2px 6px;
      border-radius: 4px;
      width: fit-content;
    }

    .capabilities-row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    .cap-on {
      background: #e8f5e9 !important;
      color: #2e7d32 !important;
    }

    .cap-off {
      background: #fafafa !important;
      color: #9e9e9e !important;
    }

    .skills-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 12px;
    }

    .skill-item {
      padding: 12px 16px;
      background: #f8f9fa;
      border-radius: 8px;
      border: 1px solid #e0e0e0;
    }

    .skill-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 4px;
    }

    .skill-id {
      font-size: 11px;
      background: #e8eaf6;
      padding: 2px 6px;
      border-radius: 4px;
    }

    .skill-desc {
      font-size: 13px;
      color: #666;
      margin: 4px 0 8px;
    }

    .skill-tags {
      display: flex;
      gap: 4px;
      flex-wrap: wrap;
    }

    .skill-tag {
      font-size: 10px !important;
      min-height: 20px !important;
      padding: 0 8px !important;
    }

    .json-toggle {
      display: flex;
      align-items: center;
      margin-top: 16px;
    }

    .json-block {
      max-height: 400px;
      overflow: auto;
    }

    .a2a-endpoints-table {
      border-collapse: collapse;
    }

    .a2a-endpoints-table thead th {
      text-align: left;
      padding: 12px;
      font-size: 12px;
      text-transform: uppercase;
      color: #888;
      border-bottom: 2px solid #e0e0e0;
    }

    .a2a-endpoints-table tbody td {
      padding: 12px;
      border-bottom: 1px solid #eee;
      vertical-align: middle;
    }

    .method {
      font-weight: 600;
      font-size: 12px;
      padding: 2px 8px;
      border-radius: 4px;
    }

    .method.post {
      background: #e3f2fd;
      color: #1565c0;
    }

    .method.get {
      background: #e8f5e9;
      color: #2e7d32;
    }

    .type-chip {
      font-size: 10px !important;
      min-height: 22px !important;
    }

    .type-chip.core {
      background: #e3f2fd !important;
      color: #1565c0 !important;
    }

    .type-chip.streaming {
      background: #fce4ec !important;
      color: #c62828 !important;
    }

    .type-chip.optional {
      background: #fff3e0 !important;
      color: #e65100 !important;
    }

    @media (max-width: 768px) {
      .info-grid {
        grid-template-columns: repeat(2, 1fr);
      }

      .form-row {
        grid-template-columns: 1fr;
      }

      .a2a-status-bar {
        flex-wrap: wrap;
      }

      .agent-meta {
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

  // A2A Protocol
  agentCard = signal<any>(null);
  loadingAgentCard = signal(false);
  showAgentCardJson = false;

  displayedColumns = ['name', 'key', 'usage', 'lastUsed', 'actions'];

  showCreateKeyForm = false;
  newlyCreatedKey = signal<string | null>(null);

  newKey = {
    name: '',
    models: ['brain-adaptive', 'brain-chat'],
    rateLimit: 60,
    notes: ''
  };
  
  editingKey = signal<ApiKey | null>(null);
  editKeyData = {
    name: '',
    models: [] as string[],
    rateLimit: 60,
    notes: '',
    isActive: true
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
    this.loadAgentCard();
  }

  getBaseUrl(): string {
    const apiUrl = environment.apiUrl;
    if (apiUrl.startsWith('http')) {
      try {
        return new URL(apiUrl).origin;
      } catch { /* fallback below */ }
    }
    return window.location.origin;
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
    
    // Usar API de Python en lugar de Strapi
    this.http.get<any[]>(`${environment.apiUrl}/config/api-keys`).subscribe({
      next: (keys) => {
        this.apiKeys.set(keys.map((k: any) => ({
          id: k.id,
          name: k.name,
          key: k.key || k.keyPrefix,
          keyPrefix: k.keyPrefix,
          isActive: k.isActive,
          permissions: k.permissions || {},
          usageStats: k.usageStats || { totalRequests: 0, totalTokens: 0, lastUsed: null },
          expiresAt: k.expiresAt,
          createdAt: k.createdAt,
          notes: k.notes
        })));
        this.loadingKeys.set(false);
      },
      error: (err) => {
        console.error('Error loading API keys:', err);
        this.loadingKeys.set(false);
      }
    });
  }

  loadConfig(): void {
    // Usar modelos por defecto (sin Strapi)
    this.availableModels.set([
      { id: 'brain-adaptive', name: 'Brain Adaptive', description: 'Full agent with tools', chainId: 'adaptive', maxTokens: 4096, supportsStreaming: true, supportsTools: true },
      { id: 'brain-chat', name: 'Brain Chat', description: 'Simple chat', chainId: 'conversational', maxTokens: 4096, supportsStreaming: true, supportsTools: false }
    ]);
    
    // Cargar configuración de LLM providers desde la API
    this.http.get<any[]>(`${environment.apiUrl}/config/llm-providers?active_only=true`).subscribe({
      next: (providers) => {
        if (providers.length > 0) {
          const activeProvider = providers[0];
          this.config.backendLlm = {
            provider: activeProvider.type,
            url: activeProvider.baseUrl,
            model: activeProvider.defaultModel || 'gpt-oss:120b'
          };
        }
      },
      error: (err) => {
        console.log('Using default LLM config');
      }
    });
  }

  checkApiStatus(): void {
    const statusUrl = `${this.getBaseUrl()}/v1/brain/status`;
    this.http.get<any>(statusUrl).subscribe({
      next: (response) => {
        this.apiStatus.set(response.status === 'online' ? 'online' : response.status);
      },
      error: () => {
        // Fallback: check via internal API health
        this.http.get<any>(`${environment.apiUrl}/config/api-keys`).subscribe({
          next: () => this.apiStatus.set('online'),
          error: () => this.apiStatus.set('offline')
        });
      }
    });
  }

  createApiKey(): void {
    if (!this.newKey.name.trim()) {
      this.snackBar.open('El nombre es requerido', 'Cerrar', { duration: 3000 });
      return;
    }

    this.creatingKey.set(true);

    const payload = {
      name: this.newKey.name,
      permissions: {
        models: this.newKey.models,
        maxTokensPerRequest: 4096,
        rateLimit: this.newKey.rateLimit
      },
      notes: this.newKey.notes
    };

    // Usar API de Python
    this.http.post<any>(`${environment.apiUrl}/config/api-keys`, payload).subscribe({
      next: (response) => {
        this.newlyCreatedKey.set(response.key);
        this.showCreateKeyForm = false;
        this.newKey = { name: '', models: ['brain-adaptive', 'brain-chat'], rateLimit: 60, notes: '' };
        this.loadApiKeys();
        this.creatingKey.set(false);
        this.snackBar.open('API key creada', 'Cerrar', { duration: 3000 });
      },
      error: (err) => {
        console.error('Error creating API key:', err);
        this.snackBar.open('Error creando API key: ' + (err.error?.detail || 'Unknown error'), 'Cerrar', { duration: 5000 });
        this.creatingKey.set(false);
      }
    });
  }

  toggleKeyStatus(key: ApiKey): void {
    // Usar API de Python
    this.http.put<any>(`${environment.apiUrl}/config/api-keys/${key.id}`, {
      isActive: !key.isActive
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

    // Usar API de Python
    this.http.delete<any>(`${environment.apiUrl}/config/api-keys/${key.id}`).subscribe({
      next: () => {
        this.loadApiKeys();
        this.snackBar.open('API key eliminada', 'Cerrar', { duration: 3000 });
      },
      error: () => {
        this.snackBar.open('Error eliminando key', 'Cerrar', { duration: 3000 });
      }
    });
  }

  startEditKey(key: ApiKey): void {
    this.editingKey.set(key);
    this.editKeyData = {
      name: key.name,
      models: key.permissions?.models || ['brain-adaptive', 'brain-chat'],
      rateLimit: key.permissions?.rateLimit || 60,
      notes: key.notes || '',
      isActive: key.isActive
    };
  }

  cancelEditKey(): void {
    this.editingKey.set(null);
    this.editKeyData = {
      name: '',
      models: [],
      rateLimit: 60,
      notes: '',
      isActive: true
    };
  }

  savingKey = signal(false);

  saveEditKey(): void {
    const key = this.editingKey();
    if (!key) return;
    
    if (!this.editKeyData.name.trim()) {
      this.snackBar.open('El nombre es requerido', 'Cerrar', { duration: 3000 });
      return;
    }

    this.savingKey.set(true);

    const payload = {
      name: this.editKeyData.name,
      permissions: {
        models: this.editKeyData.models,
        maxTokensPerRequest: 4096,
        rateLimit: this.editKeyData.rateLimit
      },
      notes: this.editKeyData.notes,
      isActive: this.editKeyData.isActive
    };

    this.http.put<any>(`${environment.apiUrl}/config/api-keys/${key.id}`, payload).subscribe({
      next: () => {
        this.editingKey.set(null);
        this.loadApiKeys();
        this.savingKey.set(false);
        this.snackBar.open('API key actualizada', 'Cerrar', { duration: 3000 });
      },
      error: (err) => {
        console.error('Error updating API key:', err);
        this.snackBar.open('Error actualizando API key: ' + (err.error?.detail || 'Unknown error'), 'Cerrar', { duration: 5000 });
        this.savingKey.set(false);
      }
    });
  }

  saveConfig(): void {
    this.savingConfig.set(true);
    
    // Por ahora solo mostrar mensaje - la configuración se gestiona desde la DB
    this.snackBar.open('Configuración guardada localmente. Para cambios permanentes, edita la base de datos.', 'Cerrar', { duration: 5000 });
    this.savingConfig.set(false);
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

  // ── A2A Protocol ──────────────────────────────────

  loadAgentCard(): void {
    this.loadingAgentCard.set(true);
    const url = `${this.getBaseUrl()}/.well-known/agent-card.json`;
    this.http.get<any>(url).subscribe({
      next: (card) => {
        this.agentCard.set(card);
        this.loadingAgentCard.set(false);
      },
      error: () => {
        this.agentCard.set(null);
        this.loadingAgentCard.set(false);
      }
    });
  }

  agentCardJson(): string {
    const card = this.agentCard();
    return card ? JSON.stringify(card, null, 2) : '';
  }

  getA2aCurlExample(): string {
    return `# SendMessage — enviar un mensaje a un agente A2A
curl ${this.getBaseUrl()}/a2a/message:send \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer sk-brain-tu-api-key" \\
  -H "A2A-Version: 1.0" \\
  -d '{
    "message": {
      "messageId": "msg-001",
      "role": "ROLE_USER",
      "parts": [{"text": "Resume las ventas del último trimestre"}]
    }
  }'`;
  }

  getA2aPythonExample(): string {
    return `import requests

base = "${this.getBaseUrl()}/a2a"
headers = {
    "Authorization": "Bearer sk-brain-tu-api-key",
    "Content-Type": "application/json",
    "A2A-Version": "1.0",
}

# 1. SendMessage
resp = requests.post(f"{base}/message:send", headers=headers, json={
    "message": {
        "messageId": "msg-001",
        "role": "ROLE_USER",
        "parts": [{"text": "Hola, ¿qué puedes hacer?"}],
    }
})
data = resp.json()
task = data.get("task", {})
print(f"Task {task['id']} → {task['status']['state']}")

# 2. GetTask
task_id = task["id"]
resp = requests.get(f"{base}/tasks/{task_id}", headers=headers)
print(resp.json())

# 3. ListTasks
resp = requests.get(f"{base}/tasks?pageSize=10", headers=headers)
print(resp.json())`;
  }

  getA2aStreamPythonExample(): string {
    return `import requests
import json

base = "${this.getBaseUrl()}/a2a"
headers = {
    "Authorization": "Bearer sk-brain-tu-api-key",
    "Content-Type": "application/json",
    "A2A-Version": "1.0",
}

# SendStreamingMessage — recibe SSE en tiempo real
resp = requests.post(
    f"{base}/message:stream",
    headers=headers,
    json={
        "message": {
            "messageId": "msg-002",
            "role": "ROLE_USER",
            "parts": [{"text": "Explica qué es A2A"}],
        }
    },
    stream=True,
)

for line in resp.iter_lines():
    if line and line.startswith(b"data: "):
        event = json.loads(line[6:])
        if "taskStatusUpdate" in event:
            status = event["taskStatusUpdate"]["status"]
            msg = status.get("message", {})
            parts = msg.get("parts", [])
            for p in parts:
                if "text" in p:
                    print(p["text"], end="", flush=True)
        elif "task" in event:
            print(f"\\n→ Final: {event['task']['status']['state']}")`;
  }
}
